"""
Test finance query tools.

Usage:
    uv run python scripts/test_finance_tools.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from src.config.settings import settings
from src.agents.tools.finance import (
    get_politician_contributions,
    get_top_donors_by_industry,
    search_contributions,
    get_contribution_summary_stats
)


async def test_tools():
    """Test all finance tools"""
    
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    
    print("\n" + "="*60)
    print("💰 TESTING FINANCE TOOLS")
    print("="*60)
    
    # Test 1: Get contributions (we don't have bioguide linked yet, so use recipient_name)
    print("\n1️⃣ Get Politician Contributions (by name)")
    print("-"*60)
    result = await get_politician_contributions(
        db=db,
        recipient_name="Unknown Candidate",  # Our test data
        cycle="2024",
        limit=5
    )
    print(f"Total Raised: ${result['total_raised']:,.2f}")
    print(f"Total Contributions: {result['total_contributions']}")
    print(f"\nTop 3 Contributors:")
    for contrib in result['top_contributors'][:3]:
        print(f"  - {contrib['name']}: ${contrib['total']:,.2f} ({contrib['count']} contributions)")
    
    # Test 2: Top donors by employer
    print("\n2️⃣ Top Donors by Employer")
    print("-"*60)
    employers = await get_top_donors_by_industry(
        db=db,
        recipient_name="Unknown Candidate",
        cycle="2024",
        limit=5
    )
    for emp in employers:
        print(f"  - {emp['employer']}: ${emp['total']:,.2f} ({emp['num_contributors']} people)")
    
    # Test 3: Search contributions
    print("\n3️⃣ Search Contributions (from California)")
    print("-"*60)
    ca_contribs = await search_contributions(
        db=db,
        state="CA",
        cycle="2024",
        limit=5
    )
    for contrib in ca_contribs:
        print(f"  - {contrib['contributor']} ({contrib['city']}, {contrib['state']}): ${contrib['amount']:,.2f}")
    
    # Test 4: Overall stats
    print("\n4️⃣ Overall Statistics")
    print("-"*60)
    stats = await get_contribution_summary_stats(db=db, cycle="2024")
    print(f"Total Raised (all candidates): ${stats['total_raised']:,.2f}")
    print(f"Total Contributions: {stats['total_contributions']}")
    print(f"Average Contribution: ${stats['average_contribution']:,.2f}")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETE")
    print("="*60)
    
    client.close()


if __name__ == "__main__":
    asyncio.run(test_tools())
