"""
Populate FEC candidate IDs for politicians in the database.

This uses the FEC API to look up candidate IDs by name and state.

Usage:
    uv run python scripts/populate_fec_ids.py --limit 10  # Test with 10
    uv run python scripts/populate_fec_ids.py             # All politicians
"""
import asyncio
import sys
from pathlib import Path
import httpx
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from src.config.settings import settings
from src.database.normalization import normalize_politician

# State name to abbreviation mapping (reuse from politician.py)
STATE_TO_ABBREV = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
    'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID',
    'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS',
    'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
    'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
    'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
    'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK',
    'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
    'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV',
    'Wisconsin': 'WI', 'Wyoming': 'WY', 'District of Columbia': 'DC'
}


async def lookup_fec_id(name: str, state: str, api_key: str, office: str = None) -> str | None:
    """
    Look up FEC candidate ID from FEC API.
    
    Args:
        name: Politician name (e.g., "Lee, Mike")
        state: State name or code (e.g., "Utah" or "UT")
        api_key: FEC API key
        office: "S" for Senate, "H" for House
    
    Returns:
        FEC candidate ID or None
    """
    # Convert state name to abbreviation if needed
    state_abbrev = STATE_TO_ABBREV.get(state, state)
    
    url = "https://api.open.fec.gov/v1/candidates/search/"
    
    # Try different name formats
    name_variants = []
    
    if ", " in name:
        last, first = name.split(", ", 1)
        # Remove middle initials/names for better matching
        first_clean = first.split()[0] if first else first
        name_variants = [
            f"{first_clean} {last}",  # "Mike Lee"
            f"{last}, {first_clean}",  # "Lee, Mike"
            last,  # Just "Lee"
        ]
    else:
        name_variants = [name]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name_variant in name_variants:
            try:
                params = {
                    "api_key": api_key,
                    "q": name_variant,
                    "state": state_abbrev,
                    "per_page": 10
                }
                
                # Add office filter if known
                if office:
                    params["office"] = office
                
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                
                if results:
                    # Return the first match (most recent by default)
                    # FEC returns candidates sorted by most recent cycle
                    return results[0].get("candidate_id")
                
            except Exception as e:
                print(f"  ⚠️  Error looking up '{name_variant}': {e}")
                continue
    
    return None


async def populate_fec_ids(limit: int | None = None):
    """Populate FEC IDs for all politicians"""
    
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    
    print("\n" + "="*60)
    print("🔍 POPULATING FEC CANDIDATE IDS")
    print("="*60)
    
    # Get politicians without FEC IDs (federal only)
    query = {
        "chamber": {"$in": ["senate", "house"]},  # Federal only
        "$or": [
            {"fec_candidate_id": {"$exists": False}},
            {"fec_candidate_id": None}
        ]
    }
    
    cursor = db.politicians.find(query)
    if limit:
        cursor = cursor.limit(limit)
    
    politicians = await cursor.to_list(None)
    total = len(politicians)
    
    print(f"\n📊 Found {total} federal politicians without FEC IDs")
    
    if not settings.FEC_API_KEY:
        print("❌ FEC_API_KEY not found in settings!")
        return
    
    updated = 0
    not_found = 0
    
    for i, pol in enumerate(politicians, 1):
        name = pol.get("full_name")
        state = pol.get("state")
        bioguide_id = pol.get("bioguide_id")
        chamber = pol.get("chamber")
        
        # Determine office code
        office = "S" if chamber == "senate" else "H" if chamber == "house" else None
        
        print(f"\n[{i}/{total}] {name} ({state}, {chamber})")
        
        fec_id = await lookup_fec_id(name, state, settings.FEC_API_KEY, office)
        
        if fec_id:
            print(f"  ✅ Found: {fec_id}")
            
            # ✨ Fetch the current politician record
            politician = await db.politicians.find_one({"bioguide_id": bioguide_id})
            
            if politician:
                # Add the FEC ID
                politician["fec_candidate_id"] = fec_id
                
                # ✨ Normalize the entire record (fixes state, party, chamber, etc.)
                normalized = normalize_politician(politician)
                
                # ✨ Replace with normalized version
                await db.politicians.replace_one(
                    {"bioguide_id": bioguide_id},
                    normalized
                )
                updated += 1
            else:
                print(f"  ⚠️  Politician record not found for {bioguide_id}")
        else:
            print(f"  ❌ Not found")
            not_found += 1
        
        # Rate limiting
        await asyncio.sleep(0.3)
    
    print("\n" + "="*60)
    print("✅ COMPLETE")
    print("="*60)
    print(f"Updated: {updated}")
    print(f"Not found: {not_found}")
    print(f"\n💡 All updated records have been normalized!")
    print(f"   State: 2-letter codes (e.g., UT)")
    print(f"   Party: Single letters (e.g., R, D, I)")
    print(f"   Chamber: lowercase (e.g., senate, house)")
    
    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate FEC candidate IDs")
    parser.add_argument("--limit", type=int, help="Limit number of politicians to process")
    args = parser.parse_args()
    
    asyncio.run(populate_fec_ids(limit=args.limit))