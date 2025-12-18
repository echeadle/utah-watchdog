"""
Sync FEC campaign contributions for all politicians with FEC IDs.

This script fetches contribution data from the FEC API for all politicians
that have fec_candidate_id populated.

Usage:
    # Sync 2024 contributions for all politicians
    uv run python scripts/sync_fec_contributions.py --cycle 2024
    
    # Sync for specific politicians (testing)
    uv run python scripts/sync_fec_contributions.py --cycle 2024 --limit 5
    
    # Sync multiple cycles
    uv run python scripts/sync_fec_contributions.py --cycle 2024 --cycle 2022
    
    # Dry run (see what would be synced)
    uv run python scripts/sync_fec_contributions.py --cycle 2024 --dry-run
"""
import asyncio
import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from src.ingestion.fec import FECIngester
from src.config.settings import settings


async def get_politicians_with_fec_ids(limit: int = None):
    """Get politicians that have FEC candidate IDs"""
    
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    
    query = {
        "fec_candidate_id": {"$exists": True, "$ne": None}
    }
    
    cursor = db.politicians.find(query)
    if limit:
        cursor = cursor.limit(limit)
    
    politicians = await cursor.to_list(None)
    
    client.close()
    
    return politicians


async def sync_contributions_for_politician(
    politician: dict,
    cycle: int,
    max_pages: int = None,
    dry_run: bool = False
):
    """
    Sync contributions for a single politician.
    
    Args:
        politician: Politician document with fec_candidate_id
        cycle: Election cycle (e.g., 2024)
        max_pages: Maximum pages to fetch (None = all)
        dry_run: If True, don't actually save data
    """
    name = politician.get("full_name")
    fec_id = politician.get("fec_candidate_id")
    state = politician.get("state")
    party = politician.get("party")
    
    print(f"\n📊 {name} ({party}-{state})")
    print(f"   FEC ID: {fec_id}")
    print(f"   Cycle: {cycle}")
    
    if dry_run:
        print(f"   [DRY RUN] Would fetch contributions...")
        return {"processed": 0, "inserted": 0, "updated": 0, "errors": 0}
    
    ingester = FECIngester()
    
    try:
        stats = await ingester.run(
            candidate_id=fec_id,
            cycle=cycle,
            max_pages=max_pages
        )
        
        print(f"   ✅ Processed: {stats['processed']}, "
              f"Inserted: {stats['inserted']}, "
              f"Updated: {stats['updated']}, "
              f"Errors: {stats['errors']}")
        
        return stats
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"processed": 0, "inserted": 0, "updated": 0, "errors": 1}


async def sync_all_contributions(
    cycles: list[int],
    limit: int = None,
    max_pages: int = None,
    dry_run: bool = False
):
    """
    Sync contributions for all politicians with FEC IDs.
    
    Args:
        cycles: List of election cycles to sync
        limit: Limit number of politicians to process
        max_pages: Max pages per politician (None = all available)
        dry_run: If True, don't actually save data
    """
    print("=" * 60)
    print("💰 FEC CAMPAIGN CONTRIBUTIONS SYNC")
    print("=" * 60)
    
    if not settings.FEC_API_KEY:
        print("❌ FEC_API_KEY not found in settings!")
        return
    
    # Get politicians with FEC IDs
    print(f"\n🔍 Finding politicians with FEC IDs...")
    politicians = await get_politicians_with_fec_ids(limit=limit)
    
    print(f"✅ Found {len(politicians)} politicians with FEC IDs")
    
    if dry_run:
        print("\n⚠️  DRY RUN MODE - No data will be saved")
    
    if limit:
        print(f"⚠️  LIMITED MODE - Processing only {limit} politicians")
    
    if max_pages:
        print(f"⚠️  LIMITED MODE - Fetching max {max_pages} pages per politician")
    
    print(f"\n📅 Cycles to sync: {', '.join(map(str, cycles))}")
    
    # Aggregate stats
    total_stats = {
        "processed": 0,
        "inserted": 0,
        "updated": 0,
        "errors": 0
    }
    
    # Process each politician
    for i, politician in enumerate(politicians, 1):
        print(f"\n[{i}/{len(politicians)}]", end=" ")
        
        for cycle in cycles:
            stats = await sync_contributions_for_politician(
                politician,
                cycle,
                max_pages=max_pages,
                dry_run=dry_run
            )
            
            # Aggregate stats
            for key in total_stats:
                total_stats[key] += stats.get(key, 0)
            
            # Rate limiting between requests
            await asyncio.sleep(0.5)
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ SYNC COMPLETE")
    print("=" * 60)
    print(f"📊 Total Statistics:")
    print(f"   Politicians: {len(politicians)}")
    print(f"   Cycles: {', '.join(map(str, cycles))}")
    print(f"   Processed: {total_stats['processed']} contributions")
    print(f"   Inserted:  {total_stats['inserted']} new")
    print(f"   Updated:   {total_stats['updated']} existing")
    print(f"   Errors:    {total_stats['errors']}")
    
    if dry_run:
        print("\n💡 This was a dry run. Run without --dry-run to actually sync data.")


async def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sync FEC campaign contributions"
    )
    parser.add_argument(
        "--cycle",
        type=int,
        action="append",
        help="Election cycle to sync (can specify multiple times)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of politicians to process (for testing)"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Max pages per politician (100 contributions per page)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually save data, just show what would be synced"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Default to 2024 if no cycles specified
    cycles = args.cycle if args.cycle else [2024]
    
    try:
        await sync_all_contributions(
            cycles=cycles,
            limit=args.limit,
            max_pages=args.max_pages,
            dry_run=args.dry_run
        )
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Sync interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        logging.exception("Fatal error during sync")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
