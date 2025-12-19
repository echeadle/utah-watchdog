"""
Quick script to fix Mike Lee's party affiliation in the database.

Mike Lee is a Republican Senator from Utah.

NOTE: After running standardize_database.py, this script won't be needed!
The standardize_database.py script handles all data normalization including
Mike Lee's party affiliation.
"""
from pymongo import MongoClient
from src.config.settings import settings
from src.database.normalization import normalize_politician


def fix_mike_lee_party():
    """Update Mike Lee's party to 'R' (Republican) and normalize entire record"""
    
    client = MongoClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    
    # Mike Lee's bioguide_id
    bioguide_id = "L000577"
    
    # Check current record
    current = db.politicians.find_one({"bioguide_id": bioguide_id})
    
    if not current:
        print(f"❌ Mike Lee not found in database (bioguide_id: {bioguide_id})")
        client.close()
        return
    
    print(f"📋 Current record for {current.get('full_name')}:")
    print(f"   Party: {current.get('party')}")
    print(f"   State: {current.get('state')}")
    print(f"   Chamber: {current.get('chamber')}")
    print()
    
    # Update party
    current["party"] = "R"
    
    # ✨ Normalize the entire record
    # This also fixes state (Utah → UT), chamber (Senate → senate), etc.
    normalized = normalize_politician(current)
    
    print("🔧 After normalization:")
    print(f"   Party: {normalized.get('party')}")
    print(f"   State: {normalized.get('state')}")
    print(f"   Chamber: {normalized.get('chamber')}")
    print()
    
    # ✨ Replace with normalized version
    result = db.politicians.replace_one(
        {"bioguide_id": bioguide_id},
        normalized
    )
    
    if result.modified_count > 0:
        print("✅ Successfully updated and normalized Mike Lee's record!")
        print()
        print("💡 Changes made:")
        print(f"   Party: {current.get('party', 'Unknown')} → R")
        
        if current.get('state') != normalized.get('state'):
            print(f"   State: {current.get('state')} → {normalized.get('state')}")
        
        if current.get('chamber') != normalized.get('chamber'):
            print(f"   Chamber: {current.get('chamber')} → {normalized.get('chamber')}")
    else:
        print("ℹ️  No changes needed (record already correct)")
    
    client.close()


if __name__ == "__main__":
    print("🔧 Fixing Mike Lee's party affiliation...")
    print("=" * 60)
    fix_mike_lee_party()
    print("=" * 60)
    print()
    print("✅ Done! Refresh the Streamlit page to see the change.")
    print()
    print("💡 TIP: Instead of using this script, run standardize_database.py")
    print("   to fix ALL politicians at once:")
    print("   uv run python standardize_database.py")