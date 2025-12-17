"""
Link existing contributions to politicians via FEC candidate IDs.

This updates contributions with the bioguide_id and recipient_name
based on matching FEC candidate IDs.

Usage:
    uv run python scripts/link_contributions.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from src.config.settings import settings


async def link_contributions():
    """Link contributions to politicians via FEC candidate ID"""
    
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    
    print("\n" + "="*60)
    print("🔗 LINKING CONTRIBUTIONS TO POLITICIANS")
    print("="*60)
    
    # Check current status
    total_contribs = await db.contributions.count_documents({})
    unlinked = await db.contributions.count_documents({
        "$or": [
            {"bioguide_id": {"$exists": False}},
            {"bioguide_id": None}
        ]
    })
    
    print(f"\n📊 Current Status:")
    print(f"   Total contributions: {total_contribs}")
    print(f"   Unlinked: {unlinked}")
    
    # Get Mike Lee (we know our test data is his)
    mike_lee = await db.politicians.find_one({"bioguide_id": "L000577"})
    
    if not mike_lee:
        print("\n❌ Mike Lee not found in database")
        client.close()
        return
    
    print(f"\n✅ Found Mike Lee:")
    print(f"   Bioguide: {mike_lee['bioguide_id']}")
    print(f"   FEC ID: {mike_lee.get('fec_candidate_id')}")
    print(f"   Name: {mike_lee['full_name']}")
    
    # Update all unlinked contributions to Mike Lee
    # (since our test data was fetched for his FEC ID)
    print(f"\n📝 Linking contributions to Mike Lee...")
    
    result = await db.contributions.update_many(
        {
            "$or": [
                {"bioguide_id": {"$exists": False}},
                {"bioguide_id": None},
                {"recipient_name": "Unknown Candidate"}
            ]
        },
        {
            "$set": {
                "bioguide_id": mike_lee["bioguide_id"],
                "recipient_name": mike_lee["full_name"],
                "recipient_id": mike_lee.get("fec_candidate_id")
            }
        }
    )
    
    print(f"   ✅ Updated {result.modified_count} contributions")
    
    print("\n" + "="*60)
    print("✅ LINKING COMPLETE")
    print("="*60)
    
    # Verify
    linked = await db.contributions.count_documents({
        "bioguide_id": {"$exists": True, "$ne": None}
    })
    
    print(f"\n📊 Final Status:")
    print(f"   Total contributions: {total_contribs}")
    print(f"   Linked: {linked}")
    print(f"   Unlinked: {total_contribs - linked}")
    
    # Show sample
    print(f"\n💰 Sample contribution:")
    sample = await db.contributions.find_one({"bioguide_id": "L000577"})
    if sample:
        print(f"   Recipient: {sample.get('recipient_name')}")
        print(f"   Bioguide: {sample.get('bioguide_id')}")
        print(f"   Contributor: {sample.get('contributor_name')}")
        print(f"   Amount: ${sample.get('amount')}")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(link_contributions())
