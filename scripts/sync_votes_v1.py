"""
Script to sync roll call votes from Congress.gov and Senate.gov.

Usage:
    uv run python scripts/sync_votes.py                  # House + Senate, 100 each
    uv run python scripts/sync_votes.py --chamber house  # House only
    uv run python scripts/sync_votes.py --max 500        # 500 votes per chamber
"""
import asyncio
import logging
import sys
from pathlib import Path

# Ensure project root is in path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the renamed class from your votes.py file
from src.ingestion.votes import ReliableCongressionalIngester
from src.config.constants import CURRENT_CONGRESS

async def sync_votes(
    congress: int = CURRENT_CONGRESS,
    chambers: list = None,
    max_votes_per_chamber: int = 100
):
    """
    Sync roll call votes using the ReliableCongressionalIngester.
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
    
    # Initialize the ingester once
    ingester = ReliableCongressionalIngester(congress=congress)
    
    for chamber in chambers:
        print(f"\n🔍 Fetching {chamber.title()} votes...")
        print("-" * 60)
        
        try:
            # Run the ingestion for this specific chamber
            stats = await ingester.run(chamber=chamber, limit=max_votes_per_chamber)
            
            # Aggregate results
            for key in total_stats:
                total_stats[key] += stats.get(key, 0)
            
            print(f"✅ {chamber.title()} complete: {stats['processed']} processed")
            
        except Exception as e:
            logging.error(f"Error syncing {chamber}: {str(e)}")
            total_stats["errors"] += 1
    
    print("\n" + "=" * 60)
    print("✅ All Chambers Complete!")
    print("=" * 60)
    print(f"📊 Total Statistics:")
    print(f"   • Processed: {total_stats['processed']}")
    print(f"   • Inserted:  {total_stats['inserted']} new records")
    print(f"   • Updated:   {total_stats['updated']} records")
    print(f"   • Errors:    {total_stats['errors']}")
    
    return total_stats


async def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sync roll call votes from official House/Senate sources"
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
    
    # Setup logging level
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Filter chambers based on CLI arg
    chambers = ["house", "senate"] if args.chamber == "both" else [args.chamber]
    
    try:
        stats = await sync_votes(
            congress=args.congress,
            chambers=chambers,
            max_votes_per_chamber=args.max
        )
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n⚠️  Sync interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())