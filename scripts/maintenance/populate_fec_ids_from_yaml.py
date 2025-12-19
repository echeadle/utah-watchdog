"""
Populate FEC IDs from the official congress-legislators data.

This uses the authoritative mapping from unitedstates/congress-legislators
which includes verified FEC IDs for all current members.

Much more reliable than searching the FEC API by name!

Usage:
    uv run python scripts/populate_fec_ids_from_yaml.py
"""
from pymongo import MongoClient
import requests
from src.config.settings import settings
import yaml


def get_legislators_data():
    """Download current legislators data with FEC IDs"""
    
    # This file has current members with all their IDs
    url = "https://raw.githubusercontent.com/unitedstates/congress-legislators/main/legislators-current.yaml"
    
    print("📥 Downloading legislators data from congress-legislators repo...")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    data = yaml.safe_load(response.text)
    print(f"✅ Downloaded data for {len(data)} current legislators")
    
    return data


def populate_fec_ids():
    """Populate FEC IDs for all politicians from official data"""
    
    client = MongoClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    
    print("=" * 60)
    print("🔧 POPULATING FEC IDS FROM OFFICIAL DATA")
    print("=" * 60)
    
    # Get official data
    legislators = get_legislators_data()
    
    stats = {
        "processed": 0,
        "updated": 0,
        "already_had": 0,
        "no_fec_id": 0,
        "not_found": 0
    }
    
    print(f"\n🔍 Processing {len(legislators)} legislators...")
    print()
    
    for legislator in legislators:
        stats["processed"] += 1
        
        # Extract IDs
        bioguide_id = legislator.get("id", {}).get("bioguide")
        fec_ids = legislator.get("id", {}).get("fec", [])
        
        if not bioguide_id:
            continue
        
        # Find politician in our database
        politician = db.politicians.find_one({"bioguide_id": bioguide_id})
        
        if not politician:
            stats["not_found"] += 1
            continue
        
        name = politician.get("full_name", "Unknown")
        
        # Check if they already have FEC ID
        if politician.get("fec_candidate_id"):
            stats["already_had"] += 1
            continue
        
        # Get most recent FEC ID (they're in chronological order)
        if not fec_ids:
            stats["no_fec_id"] += 1
            print(f"⚠️  {name} - No FEC ID in official data")
            continue
        
        # Use the most recent FEC ID
        fec_id = fec_ids[-1] if isinstance(fec_ids, list) else fec_ids
        
        # Update politician with FEC ID
        db.politicians.update_one(
            {"bioguide_id": bioguide_id},
            {"$set": {"fec_candidate_id": fec_id}}
        )
        
        stats["updated"] += 1
        print(f"✅ {name} - Added FEC ID: {fec_id}")
    
    print()
    print("=" * 60)
    print("✅ COMPLETE")
    print("=" * 60)
    print(f"📊 Statistics:")
    print(f"   Processed:     {stats['processed']}")
    print(f"   Updated:       {stats['updated']} (added FEC IDs)")
    print(f"   Already had:   {stats['already_had']}")
    print(f"   No FEC ID:     {stats['no_fec_id']} (not running for re-election)")
    print(f"   Not in DB:     {stats['not_found']}")
    print()
    print(f"🎉 Total politicians with FEC IDs: {stats['already_had'] + stats['updated']}")
    
    client.close()


if __name__ == "__main__":
    try:
        populate_fec_ids()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
