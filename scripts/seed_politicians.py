"""
Seed the database with Utah's federal delegation.

Run with: uv run python scripts/seed_politicians.py
"""

from datetime import datetime

from src.database import get_sync_database, close_sync_client
from src.models import Politician, Party, Chamber
from src.config.constants import COLLECTION_POLITICIANS


# Utah's federal delegation (current as of 2024)
UTAH_DELEGATION_DATA = [
    # Senators
    {
        "bioguide_id": "L000577",
        "first_name": "Mike",
        "last_name": "Lee",
        "full_name": "Mike Lee",
        "party": Party.REPUBLICAN,
        "state": "UT",
        "chamber": Chamber.SENATE,
        "district": None,
        "title": "Senator",
        "in_office": True,
    },
    {
        "bioguide_id": "R000615",
        "first_name": "Mitt",
        "last_name": "Romney",
        "full_name": "Mitt Romney",
        "party": Party.REPUBLICAN,
        "state": "UT",
        "chamber": Chamber.SENATE,
        "district": None,
        "title": "Senator",
        "in_office": True,  # Retiring Jan 2025, but still in office
    },
    # Representatives
    {
        "bioguide_id": "M001209",
        "first_name": "Blake",
        "last_name": "Moore",
        "full_name": "Blake Moore",
        "party": Party.REPUBLICAN,
        "state": "UT",
        "chamber": Chamber.HOUSE,
        "district": 1,
        "title": "Representative",
        "in_office": True,
    },
    {
        "bioguide_id": "M000317",
        "first_name": "Celeste",
        "last_name": "Maloy",
        "full_name": "Celeste Maloy",
        "party": Party.REPUBLICAN,
        "state": "UT",
        "chamber": Chamber.HOUSE,
        "district": 2,
        "title": "Representative",
        "in_office": True,
    },
    {
        "bioguide_id": "C001114",
        "first_name": "John",
        "last_name": "Curtis",
        "full_name": "John Curtis",
        "party": Party.REPUBLICAN,
        "state": "UT",
        "chamber": Chamber.HOUSE,
        "district": 3,
        "title": "Representative",
        "in_office": True,
    },
    {
        "bioguide_id": "O000086",
        "first_name": "Burgess",
        "last_name": "Owens",
        "full_name": "Burgess Owens",
        "party": Party.REPUBLICAN,
        "state": "UT",
        "chamber": Chamber.HOUSE,
        "district": 4,
        "title": "Representative",
        "in_office": True,
    },
]


def main():
    print("=" * 50)
    print("Seeding Utah Federal Delegation")
    print("=" * 50)
    
    db = get_sync_database()
    collection = db[COLLECTION_POLITICIANS]
    
    # Create index on bioguide_id for fast lookups
    collection.create_index("bioguide_id", unique=True)
    print("✅ Created unique index on bioguide_id")
    
    inserted = 0
    updated = 0
    
    for data in UTAH_DELEGATION_DATA:
        # Create Politician model (validates data)
        politician = Politician(**data)
        
        # Convert to dict for MongoDB
        doc = politician.model_dump()
        
        # Upsert: insert if new, update if exists
        result = collection.update_one(
            {"bioguide_id": politician.bioguide_id},
            {"$set": doc},
            upsert=True
        )
        
        if result.upserted_id:
            print(f"   ➕ Inserted: {politician}")
            inserted += 1
        else:
            print(f"   🔄 Updated: {politician}")
            updated += 1
    
    # Summary
    total = collection.count_documents({"state": "UT"})
    
    print(f"\n📊 Summary:")
    print(f"   Inserted: {inserted}")
    print(f"   Updated: {updated}")
    print(f"   Total Utah legislators in DB: {total}")
    
    close_sync_client()
    
    print("\n" + "=" * 50)
    print("✅ Seeding complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()