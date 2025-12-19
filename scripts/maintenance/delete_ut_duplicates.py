"""
Delete duplicate politicians with state="UT".

These are old development records that should not exist.
The correct records have state="Utah".

Usage:
    uv run python scripts/delete_ut_duplicates.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from src.config.settings import settings

async def delete_ut_duplicates():
    """Delete politicians with state='UT' (duplicates from development)"""
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    
    print("🔍 Finding politicians with state='UT'...")
    
    # Find and display records to be deleted
    ut_politicians = await db.politicians.find({'state': 'UT'}).to_list(10)
    
    if not ut_politicians:
        print("✅ No politicians with state='UT' found. Database is clean!")
        client.close()
        return
    
    print(f"\n⚠️  Found {len(ut_politicians)} duplicate records to delete:")
    for p in ut_politicians:
        print(f"   - {p.get('full_name')} ({p.get('bioguide_id')})")
        print(f"     In office: {p.get('in_office')}")
        print(f"     Last updated: {p.get('last_updated')}")
    
    # Confirm deletion
    print(f"\n❓ Delete these {len(ut_politicians)} records? (y/n): ", end='')
    confirm = input().strip().lower()
    
    if confirm != 'y':
        print("❌ Deletion cancelled.")
        client.close()
        return
    
    # Delete the records
    result = await db.politicians.delete_many({'state': 'UT'})
    
    print(f"\n✅ Deleted {result.deleted_count} duplicate records")
    
    # Verify
    remaining = await db.politicians.count_documents({'state': 'UT'})
    if remaining == 0:
        print("✅ All 'UT' records removed successfully")
    else:
        print(f"⚠️  Warning: {remaining} 'UT' records still remain")
    
    # Show current Utah politicians
    print("\n📊 Current Utah politicians:")
    utah_pols = await db.politicians.find({'state': 'Utah'}).to_list(10)
    for p in utah_pols:
        print(f"   - {p.get('full_name')} ({p.get('bioguide_id')})")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(delete_ut_duplicates())
