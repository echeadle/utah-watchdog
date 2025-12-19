"""
Script to sync bills from Congress.gov.

Run this to populate or update the legislation collection.

Usage:
    uv run python scripts/sync_bills.py                    # All bill types, last 100
    uv run python scripts/sync_bills.py --type hr          # Just House bills
    uv run python scripts/sync_bills.py --max 500          # Fetch 500 bills
    uv run python scripts/sync_bills.py --congress 118     # Different Congress
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.congress_bills import CongressBillsIngester
from src.config.constants import CURRENT_CONGRESS


async def sync_bills(
    congress: int = CURRENT_CONGRESS,
    bill_types: list = None,
    max_bills_per_type: int = 100):
    """
    Sync bills from Congress.gov.
    
    Args:
        congress: Congress number
        bill_types: List of bill types to sync
        max_bills_per_type: Max bills to fetch per type
    """
    if bill_types is None:
        bill_types = ["hr", "s"]  # House and Senate bills only by default
    
    print(f"📜 Syncing bills from the {congress}th Congress...")
    print("=" * 60)
    print(f"Bill types: {', '.join([t.upper() for t in bill_types])}")
    print(f"Max per type: {max_bills_per_type}")
    print()
    
    total_stats = {
        "processed": 0,
        "inserted": 0,
        "updated": 0,
        "errors": 0
    }
    
    for bill_type in bill_types:
        print(f"\n🔍 Fetching {bill_type.upper()} bills...")
        print("-" * 60)
        
        # FIXED: Create a NEW ingester for each bill type
        # (The old one's database connection was closed after run())
        ingester = CongressBillsIngester(congress=congress)
        
        stats = await ingester.run(
            bill_type=bill_type,
            max_bills=max_bills_per_type
        )
        
        # Aggregate stats
        for key in total_stats:
            total_stats[key] += stats.get(key, 0)
        
        print(f"✅ {bill_type.upper()} complete: {stats['processed']} processed")
    
    print("\n" + "=" * 60)
    print("✅ All Bill Types Complete!")
    print("=" * 60)
    print(f"📊 Total Statistics:")
    print(f"   • Processed: {total_stats['processed']}")
    print(f"   • Inserted:  {total_stats['inserted']} new bills")
    print(f"   • Updated:   {total_stats['updated']} existing bills")
    print(f"   • Errors:    {total_stats['errors']}")
    
    return total_stats


async def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sync bills from Congress.gov API"
    )
    parser.add_argument(
        "--congress",
        type=int,
        default=CURRENT_CONGRESS,
        help=f"Congress number (default: {CURRENT_CONGRESS})"
    )
    parser.add_argument(
        "--type",
        dest="bill_types",
        action="append",
        help="Bill type to sync (can specify multiple times). Default: hr, s"
    )
    parser.add_argument(
        "--max",
        type=int,
        default=100,
        help="Maximum bills to fetch per type (default: 100)"
    )
    parser.add_argument(
        "--all-types",
        action="store_true",
        help="Sync all bill types (hr, s, hres, sres, hjres, sjres, hconres, sconres)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Determine bill types
    if args.all_types:
        bill_types = ["hr", "s", "hres", "sres", "hjres", "sjres", "hconres", "sconres"]
    elif args.bill_types:
        bill_types = args.bill_types
    else:
        bill_types = ["hr", "s"]  # Default: just House and Senate bills
    
    try:
        stats = await sync_bills(
            congress=args.congress,
            bill_types=bill_types,
            max_bills_per_type=args.max
        )
        
        # Exit with error code if there were errors
        sys.exit(1 if stats['errors'] > 0 else 0)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Sync interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        logging.exception("Fatal error during sync")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
