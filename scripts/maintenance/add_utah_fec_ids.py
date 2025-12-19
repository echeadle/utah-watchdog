"""
Manually add FEC IDs for specific Utah politicians.

After looking up the IDs, run this to update the database.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from src.config.settings import settings
from src.database.normalization import normalize_politician


# FEC IDs found via manual lookup
UTAH_FEC_IDS = {
    "M001228": "H2UT03149",  # Celeste Maloy
    "M001213": "H0UT01129",  # Blake D. Moore
    "K000403": "H4UT04206",  # Mike Kennedy
}


async def add_fec_ids():
    """Add FEC IDs to Utah politicians"""
    
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    
    print("=" * 60)
    print("🔧 ADDING FEC IDS TO UTAH POLITICIANS")
    print("=" * 60)
    
    for bioguide_id, fec_id in UTAH_FEC_IDS.items():
        politician = await db.politicians.find_one({"bioguide_id": bioguide_id})
        
        if not politician:
            print(f"❌ Politician not found: {bioguide_id}")
            continue
        
        name = politician.get("full_name")
        print(f"\n✅ {name} ({bioguide_id})")
        print(f"   Adding FEC ID: {fec_id}")
        
        # Add FEC ID
        politician["fec_candidate_id"] = fec_id
        
        # Normalize entire record
        normalized = normalize_politician(politician)
        
        # Update in database
        await db.politicians.replace_one(
            {"bioguide_id": bioguide_id},
            normalized
        )
        
        print(f"   Updated and normalized!")
    
    print("\n" + "=" * 60)
    print("✅ COMPLETE")
    print("=" * 60)
    print(f"Added {len(UTAH_FEC_IDS)} FEC IDs")
    print("\nAll Utah delegation now has FEC IDs!")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(add_fec_ids())
