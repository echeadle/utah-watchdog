"""
Script to sync roll call votes from Congress.gov.

Usage:
    uv run python scripts/sync_votes.py                  # House + Senate, 100 each
    uv run python scripts/sync_votes.py --chamber house  # House only
    uv run python scripts/sync_votes.py --max 500        # 500 votes per chamber
"""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.votes import VotesIngester
from src.config.constants import CURRENT_CONGRESS


async def sync_votes(
    congress: int = CURRENT_CONGRESS,
    chambers: list = None,
    max_votes_per_chamber: int = 100
):
    """
    Sync roll call votes from Congress.gov.
    
    Args:
        congress: Congress number
        chambers: List of chambers ("house", "senate")
        max_votes_per_chamber: Max votes to fetch per chamber
    """
    if chambers is None:
        chambers = ["house", "senate"]
    
    print(f"🗳️  Syncing roll call votes from the {congress}th Congress...")
    print("=" * 60)
    print(f"Chambers: {', '.join(chambers).title()}")
    print(f"Max per chamber: {max_votes_per_chamber}")
    print()
    
    total_stats = {
        "processed": 0,
        "inserted": 0,
        "updated": 0,
        "errors": 0
    }
    
    for chamber in chambers:
        print(f"\n🔍 Fetching {chamber.title()} votes...")
        print("-" * 60)
        
        ingester = VotesIngester(congress=congress)
        stats = await ingester.run(chamber=chamber, limit=max_votes_per_chamber)
        
        # Aggregate stats
        for key in total_stats:
            total_stats[key] += stats.get(key, 0)
        
        print(f"✅ {chamber.title()} complete: {stats['processed']} processed")
    
    print("\n" + "=" * 60)
    print("✅ All Chambers Complete!")
    print("=" * 60)
    print(f"📊 Total Statistics:")
    print(f"   • Processed: {total_stats['processed']}")
    print(f"   • Inserted:  {total_stats['inserted']} new votes")
    print(f"   • Updated:   {total_stats['updated']} existing votes")
    print(f"   • Errors:    {total_stats['errors']}")
    
    return total_stats


async def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sync roll call votes from Congress.gov"
    )
    parser.add_argument(
        "--congress",
        type=int,
        default=CURRENT_CONGRESS,
        help=f"Congress number (default: {CURRENT_CONGRESS})"
    )
    parser.add_argument(
        "--chamber",
        choices=["house", "senate", "both"],
        default="both",
        help="Which chamber to sync (default: both)"
    )
    parser.add_argument(
        "--max",
        type=int,
        default=100,
        help="Maximum votes per chamber (default: 100)"
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
    
    # Determine chambers
    if args.chamber == "both":
        chambers = ["house", "senate"]
    else:
        chambers = [args.chamber]
    
    try:
        stats = await sync_votes(
            congress=args.congress,
            chambers=chambers,
            max_votes_per_chamber=args.max
        )
        
        sys.exit(1 if stats['errors'] > 0 else 0)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Sync interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        logging.exception("Fatal error during sync")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())