"""
Test script for legislation tools.

Usage:
    uv run python scripts/test_legislation_tools.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from src.config.settings import settings
from src.agents.tools.legislation import (
    search_legislation,
    get_bill_details,
    get_bill_votes,
    get_politician_sponsored_bills,
    get_recent_legislation
)


class MockContext:
    """Mock context object for testing tools"""
    def __init__(self, db):
        self.deps = MockDeps(db)


class MockDeps:
    """Mock dependencies"""
    def __init__(self, db):
        self.db = db


async def test_search_legislation(ctx):
    """Test 1: Search for bills by keyword"""
    print("\n" + "="*60)
    print("TEST 1: Search Legislation")
    print("="*60)
    
    query = "infrastructure"
    print(f"\n🔍 Searching for bills about '{query}'...")
    
    results = await search_legislation(query=query, limit=5, ctx=ctx)
    
    print(f"\n✅ Found {len(results)} bills:")
    for i, bill in enumerate(results, 1):
        print(f"\n{i}. {bill.get('title', 'No title')[:80]}...")
        print(f"   Status: {bill.get('status')}")
        print(f"   Bill ID: {bill.get('bill_id')}")
        print(f"   Sponsor: {bill.get('sponsor_bioguide_id')}")


async def test_get_bill_details(ctx):
    """Test 2: Get details for a specific bill"""
    print("\n" + "="*60)
    print("TEST 2: Get Bill Details")
    print("="*60)
    
    # First, get a bill_id from the database
    bill = await ctx.deps.db.legislation.find_one({})
    if not bill:
        print("❌ No bills in database to test with")
        return
    
    bill_id = bill.get("bill_id")
    print(f"\n🔍 Getting details for bill: {bill_id}")
    
    details = await get_bill_details(bill_id=bill_id, ctx=ctx)
    
    if "error" in details:
        print(f"❌ Error: {details['error']}")
    else:
        print(f"\n✅ Bill Details:")
        print(f"   Title: {details.get('title', 'N/A')[:100]}...")
        print(f"   Status: {details.get('status')}")
        print(f"   Congress: {details.get('congress')}")
        print(f"   Sponsor: {details.get('sponsor')}")
        print(f"   Cosponsors: {details.get('cosponsor_count')}")
        print(f"   Policy Area: {details.get('policy_area')}")
        print(f"   Subjects: {len(details.get('subjects', []))} topics")
        if details.get('summary'):
            print(f"   Summary: {details['summary'][:150]}...")


async def test_get_bill_votes(ctx):
    """Test 3: Get votes on a bill (may be empty)"""
    print("\n" + "="*60)
    print("TEST 3: Get Bill Votes")
    print("="*60)
    
    # Get a bill_id
    bill = await ctx.deps.db.legislation.find_one({})
    if not bill:
        print("❌ No bills in database to test with")
        return
    
    bill_id = bill.get("bill_id")
    print(f"\n🔍 Getting votes for bill: {bill_id}")
    
    result = await get_bill_votes(bill_id=bill_id, ctx=ctx)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    elif "message" in result:
        print(f"ℹ️  {result['message']}")
        print("   (This is expected if votes haven't been ingested yet)")
    else:
        votes = result.get('votes', [])
        print(f"\n✅ Found {len(votes)} votes:")
        for vote in votes:
            print(f"   • {vote.get('chamber').title()}: {vote.get('result')}")
            print(f"     Yea: {vote.get('yea_count')} | Nay: {vote.get('nay_count')}")


async def test_get_sponsored_bills(ctx):
    """Test 4: Get bills sponsored by a politician"""
    print("\n" + "="*60)
    print("TEST 4: Get Sponsored Bills")
    print("="*60)
    
    # Find a politician with bioguide_id
    politician = await ctx.deps.db.politicians.find_one(
        {"bioguide_id": {"$exists": True}}
    )
    
    if not politician:
        print("❌ No politicians with bioguide_id in database")
        return
    
    bioguide_id = politician.get("bioguide_id")
    name = politician.get("full_name", "Unknown")
    
    print(f"\n🔍 Getting bills sponsored by {name} ({bioguide_id})...")
    
    results = await get_politician_sponsored_bills(
        bioguide_id=bioguide_id,
        limit=5,
        ctx=ctx
    )
    
    if isinstance(results, dict) and "error" in results:
        print(f"❌ Error: {results['error']}")
    else:
        print(f"\n✅ Found {len(results)} sponsored bills:")
        for i, bill in enumerate(results, 1):
            print(f"\n{i}. {bill.get('title', 'No title')[:80]}...")
            print(f"   Status: {bill.get('status')}")
            print(f"   Introduced: {bill.get('introduced_date')}")
            print(f"   Cosponsors: {bill.get('cosponsor_count')}")


async def test_recent_legislation(ctx):
    """Test 5: Get recent legislation"""
    print("\n" + "="*60)
    print("TEST 5: Recent Legislation")
    print("="*60)
    
    print(f"\n🔍 Getting legislation from the last 90 days...")
    
    results = await get_recent_legislation(days=90, limit=5, ctx=ctx)
    
    print(f"\n✅ Found {len(results)} recent bills:")
    for i, bill in enumerate(results, 1):
        print(f"\n{i}. {bill.get('title', 'No title')[:80]}...")
        print(f"   Status: {bill.get('status')}")
        print(f"   Latest Action: {bill.get('latest_action', {}).get('date')}")


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 TESTING LEGISLATION TOOLS")
    print("="*60)
    
    # Connect to database
    print("\n📡 Connecting to MongoDB...")
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    
    # Create mock context
    ctx = MockContext(db)
    
    # Check data exists
    bill_count = await db.legislation.count_documents({})
    politician_count = await db.politicians.count_documents({})
    print(f"✅ Connected! Found {bill_count} bills, {politician_count} politicians")
    
    try:
        # Run all tests
        await test_search_legislation(ctx)
        await test_get_bill_details(ctx)
        await test_get_bill_votes(ctx)
        await test_get_sponsored_bills(ctx)
        await test_recent_legislation(ctx)
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETE")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
