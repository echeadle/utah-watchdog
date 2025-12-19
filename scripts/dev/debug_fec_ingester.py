"""
Test FEC ingester with Utah politicians.

Usage:
    uv run python scripts/test_fec_ingester.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.fec import FECIngester


async def test_fec():
    """Test fetching contributions for Mike Lee"""
    
    print("\n" + "="*60)
    print("🔍 TESTING FEC INGESTER")
    print("="*60)
    
    ingester = FECIngester()
    
    # Mike Lee's FEC ID: S2UT00106
    # Fetch just 1 page (100 contributions) as a test
    print("\n📊 Fetching contributions for Mike Lee (S2UT00106)...")
    print("   Cycle: 2024")
    print("   Max pages: 1 (100 contributions)")
    
    stats = await ingester.run(
        candidate_id="S2UT00106",
        cycle=2024,
        max_pages=1  # Just 1 page for testing
    )
    
    print("\n" + "="*60)
    print("✅ INGESTION COMPLETE")
    print("="*60)
    print(f"📊 Statistics:")
    print(f"   Processed: {stats['processed']}")
    print(f"   Inserted:  {stats['inserted']}")
    print(f"   Updated:   {stats['updated']}")
    print(f"   Errors:    {stats['errors']}")
    print(f"   Duration:  {stats['completed_at'] - stats['started_at']}")


if __name__ == "__main__":
    asyncio.run(test_fec())
