"""
Manual script to sync current members of Congress.

Run this to populate or update the politicians collection with current members.

Usage:
    uv run python scripts/sync_members.py
    uv run python scripts/sync_members.py --congress 119  # Specify congress number
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.congress_members import CongressMembersIngester
from src.config.constants import CURRENT_CONGRESS


async def sync_members(congress: int = CURRENT_CONGRESS):
    """
    Sync current members from Congress.gov.
    
    Args:
        congress: Congress number to sync (default: current)
    """
    print(f"🇺🇸 Syncing members of the {congress}th Congress...")
    print("=" * 60)
    
    ingester = CongressMembersIngester(congress=congress)
    stats = await ingester.run_full_sync()
    
    print("\n✅ Sync Complete!")
    print("=" * 60)
    print(f"📊 Statistics:")
    print(f"   • Processed: {stats['processed']}")
    print(f"   • Inserted:  {stats['inserted']} new members")
    print(f"   • Updated:   {stats['updated']} existing members")
    print(f"   • Errors:    {stats['errors']}")
    
    duration = stats['completed_at'] - stats['started_at']
    print(f"   • Duration:  {duration}")
    
    if stats['errors'] > 0:
        print("\n⚠️  Some errors occurred. Check logs for details.")
    
    return stats


async def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sync current members of Congress from Congress.gov API"
    )
    parser.add_argument(
        "--congress",
        type=int,
        default=CURRENT_CONGRESS,
        help=f"Congress number (default: {CURRENT_CONGRESS})"
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
    
    try:
        stats = await sync_members(congress=args.congress)
        
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