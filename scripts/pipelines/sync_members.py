"""
Manual script to sync current members of Congress.

Run this to populate or update the politicians collection with current members.

Usage:
    uv run python scripts/sync_members.py                    # All members
    uv run python scripts/sync_members.py --congress 119     # Specify congress
    uv run python scripts/sync_members.py --state UT         # Utah only (efficient!)
    uv run python scripts/sync_members.py --chamber senate   # Senate only
    uv run python scripts/sync_members.py --state UT --chamber senate  # Utah senators
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path (we're in scripts/pipelines/, need to go up 2 levels)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ingestion.congress_members import CongressMembersIngester
from src.config.constants import CURRENT_CONGRESS


async def sync_members(
    congress: int = CURRENT_CONGRESS,
    state: str = None,
    chamber: str = None
):
    """
    Sync current members from Congress.gov.
    
    Args:
        congress: Congress number to sync (default: current)
        state: Optional 2-letter state code to filter (e.g., "UT")
        chamber: Optional chamber filter ("senate" or "house")
    """
    print(f"🇺🇸 Syncing members of the {congress}th Congress...")
    print("=" * 60)
    
    if state:
        print(f"   State filter: {state}")
    if chamber:
        print(f"   Chamber filter: {chamber.title()}")
    
    if state or chamber:
        print(f"   ✨ Using native filtering (efficient!)")
    print()
    
    # Create ingester with native filtering
    ingester = CongressMembersIngester(
        congress=congress,
        state_filter=state,
        chamber_filter=chamber
    )
    
    # Run sync
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
        description="Sync current members of Congress from Congress.gov API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sync all current members
  uv run python scripts/sync_members.py
  
  # Sync only Utah delegation (only 1 API call instead of 50+!)
  uv run python scripts/sync_members.py --state UT
  
  # Sync only Senate (filters during fetch)
  uv run python scripts/sync_members.py --chamber senate
  
  # Sync Utah senators only (most efficient)
  uv run python scripts/sync_members.py --state UT --chamber senate
  
  # Different congress
  uv run python scripts/sync_members.py --congress 119
        """
    )
    parser.add_argument(
        "--congress",
        type=int,
        default=CURRENT_CONGRESS,
        help=f"Congress number (default: {CURRENT_CONGRESS})"
    )
    parser.add_argument(
        "--state",
        type=str,
        help="Filter by state (2-letter code, e.g., UT, CA)"
    )
    parser.add_argument(
        "--chamber",
        choices=["senate", "house"],
        help="Filter by chamber"
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
        stats = await sync_members(
            congress=args.congress,
            state=args.state,
            chamber=args.chamber
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
