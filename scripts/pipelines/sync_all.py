"""
Master script to run all data pipelines in sequence.

This orchestrates the complete data sync workflow, running each pipeline
in the correct dependency order.

Usage:
    uv run python scripts/pipelines/sync_all.py                    # Run everything
    uv run python scripts/pipelines/sync_all.py --skip-embeddings  # Skip slow steps
    uv run python scripts/pipelines/sync_all.py --only members,bills  # Selective
    uv run python scripts/pipelines/sync_all.py --dry-run          # See what would run
"""
import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.constants import CURRENT_CONGRESS

# Import ingesters
from src.ingestion.congress_members import CongressMembersIngester
from src.ingestion.congress_bills import CongressBillsIngester
from src.ingestion.committees import CommitteeIngester
from src.ingestion.votes import VotesIngester
from src.ingestion.fec import FECIngester

logger = logging.getLogger(__name__)


# ============================================================================
# Pipeline Definitions
# ============================================================================

class Pipeline:
    """Represents a single data pipeline"""
    
    def __init__(
        self, 
        name: str, 
        description: str, 
        run_func,
        depends_on: List[str] = None,
        slow: bool = False
    ):
        self.name = name
        self.description = description
        self.run_func = run_func
        self.depends_on = depends_on or []
        self.slow = slow  # Mark time-consuming pipelines


# Define all available pipelines
PIPELINES = {
    "members": Pipeline(
        name="members",
        description="Sync current members of Congress",
        run_func=lambda: sync_members(),
        depends_on=[],
        slow=False
    ),
    
    "bills": Pipeline(
        name="bills",
        description="Sync federal legislation",
        run_func=lambda: sync_bills(),
        depends_on=["members"],  # Bills reference sponsors
        slow=True
    ),
    
    "embeddings": Pipeline(
        name="embeddings",
        description="Generate embeddings for semantic search",
        run_func=lambda: generate_embeddings(),
        depends_on=["bills"],  # Need bills first
        slow=True
    ),
    
    "committees": Pipeline(
        name="committees",
        description="Sync committee assignments",
        run_func=lambda: sync_committees(),
        depends_on=["members"],
        slow=False
    ),
    
    "votes": Pipeline(
        name="votes",
        description="Sync roll call votes",
        run_func=lambda: sync_votes(),
        depends_on=["members", "bills"],  # Votes reference both
        slow=True
    ),
    
    "contributions": Pipeline(
        name="contributions",
        description="Sync campaign contributions (FEC)",
        run_func=lambda: sync_contributions(),
        depends_on=["members"],  # Contributions linked to politicians
        slow=True
    ),
}


# ============================================================================
# Individual Pipeline Functions
# ============================================================================

async def sync_members() -> dict:
    """Sync current members of Congress"""
    print("\n" + "="*60)
    print("👥 SYNCING MEMBERS")
    print("="*60)
    
    ingester = CongressMembersIngester(congress=CURRENT_CONGRESS)
    stats = await ingester.run_full_sync()
    
    print(f"✅ Members: {stats['processed']} processed, "
          f"{stats['inserted']} new, {stats['updated']} updated")
    
    return stats


async def sync_bills() -> dict:
    """Sync federal legislation"""
    print("\n" + "="*60)
    print("📜 SYNCING BILLS")
    print("="*60)
    
    total_stats = {
        "processed": 0,
        "inserted": 0,
        "updated": 0,
        "errors": 0
    }
    
    # Sync House and Senate bills
    for bill_type in ["hr", "s"]:
        print(f"\n🔍 Fetching {bill_type.upper()} bills...")
        
        ingester = CongressBillsIngester(congress=CURRENT_CONGRESS)
        stats = await ingester.run(bill_type=bill_type, max_bills=100)
        
        # Aggregate
        for key in total_stats:
            total_stats[key] += stats.get(key, 0)
    
    print(f"\n✅ Bills: {total_stats['processed']} processed, "
          f"{total_stats['inserted']} new, {total_stats['updated']} updated")
    
    return total_stats


async def generate_embeddings() -> dict:
    """Generate embeddings for semantic search"""
    print("\n" + "="*60)
    print("🧠 GENERATING EMBEDDINGS")
    print("="*60)
    
    # Import here to avoid loading OpenAI if not needed
    from motor.motor_asyncio import AsyncIOMotorClient
    from openai import AsyncOpenAI
    from src.config.settings import settings
    
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    # Find bills without embeddings
    bills_without_embeddings = await db.legislation.find(
        {'embedding': {'$exists': False}}
    ).to_list(None)
    
    total = len(bills_without_embeddings)
    print(f"📊 Found {total} bills without embeddings")
    
    if total == 0:
        print("✅ All bills already have embeddings!")
        client.close()
        return {"processed": 0, "inserted": 0, "errors": 0}
    
    processed = 0
    errors = 0
    
    for bill in bills_without_embeddings:
        try:
            # Create text to embed
            title = bill.get('title', '')
            summary = bill.get('summary', '')
            short_title = bill.get('short_title', '')
            
            text_to_embed = f"{short_title or title}"
            if summary:
                text_to_embed += f"\n\n{summary}"
            
            text_to_embed = text_to_embed[:8000]  # Truncate
            
            if not text_to_embed.strip():
                continue
            
            # Generate embedding
            response = await openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text_to_embed
            )
            
            embedding = response.data[0].embedding
            
            # Update bill
            await db.legislation.update_one(
                {'_id': bill['_id']},
                {'$set': {'embedding': embedding}}
            )
            
            processed += 1
            
            if processed % 10 == 0:
                print(f"   Processed {processed}/{total}...")
            
        except Exception as e:
            errors += 1
            logger.error(f"Error processing bill {bill.get('bill_id')}: {e}")
    
    client.close()
    
    print(f"✅ Embeddings: {processed} generated, {errors} errors")
    
    return {"processed": processed, "inserted": processed, "errors": errors}


async def sync_committees() -> dict:
    """Sync committee assignments"""
    print("\n" + "="*60)
    print("🏛️ SYNCING COMMITTEES")
    print("="*60)
    
    ingester = CommitteeIngester(congress=CURRENT_CONGRESS)
    stats = await ingester.run()
    
    print(f"✅ Committees: {stats['processed']} processed")
    
    return stats


async def sync_votes() -> dict:
    """Sync roll call votes"""
    print("\n" + "="*60)
    print("🗳️ SYNCING VOTES")
    print("="*60)
    
    total_stats = {
        "processed": 0,
        "inserted": 0,
        "updated": 0,
        "errors": 0
    }
    
    # Sync both chambers
    ingester = VotesIngester(congress=CURRENT_CONGRESS)
    
    for chamber in ["house", "senate"]:
        print(f"\n🔍 Fetching {chamber.title()} votes...")
        
        stats = await ingester.run(chamber=chamber, limit=100)
        
        # Aggregate
        for key in total_stats:
            total_stats[key] += stats.get(key, 0)
    
    print(f"\n✅ Votes: {total_stats['processed']} processed, "
          f"{total_stats['inserted']} new, {total_stats['updated']} updated")
    
    return total_stats


async def sync_contributions() -> dict:
    """Sync campaign contributions from FEC"""
    print("\n" + "="*60)
    print("💰 SYNCING CONTRIBUTIONS")
    print("="*60)
    
    from motor.motor_asyncio import AsyncIOMotorClient
    from src.config.settings import settings
    
    # Get politicians with FEC IDs
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    
    politicians = await db.politicians.find({
        "fec_candidate_id": {"$exists": True, "$ne": None},
        "bioguide_id": {"$exists": True, "$ne": None}
    }).limit(10).to_list(None)  # Limit to 10 for now
    
    client.close()
    
    print(f"📊 Found {len(politicians)} politicians with FEC IDs (limiting to 10)")
    
    total_stats = {
        "processed": 0,
        "inserted": 0,
        "updated": 0,
        "errors": 0
    }
    
    for politician in politicians:
        name = politician.get("full_name")
        fec_id = politician.get("fec_candidate_id")
        bioguide_id = politician.get("bioguide_id")
        
        print(f"   {name}...", end=" ")
        
        try:
            ingester = FECIngester(bioguide_id=bioguide_id)
            stats = await ingester.run(
                candidate_id=fec_id,
                cycle=2024,
                max_pages=1  # Limit for speed
            )
            
            # Aggregate
            for key in total_stats:
                total_stats[key] += stats.get(key, 0)
            
            print(f"{stats['inserted']} new")
            
            await asyncio.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            total_stats["errors"] += 1
            print(f"error: {e}")
            logger.error(f"Error syncing {name}: {e}")
    
    print(f"\n✅ Contributions: {total_stats['processed']} processed, "
          f"{total_stats['inserted']} new")
    
    return total_stats


# ============================================================================
# Main Orchestration
# ============================================================================

def resolve_dependencies(pipelines_to_run: List[str]) -> List[str]:
    """
    Resolve dependencies and return pipelines in correct order.
    
    Args:
        pipelines_to_run: List of pipeline names to run
        
    Returns:
        Ordered list including dependencies
    """
    resolved = []
    seen = set()
    
    def add_with_deps(name: str):
        if name in seen:
            return
        
        pipeline = PIPELINES[name]
        
        # Add dependencies first
        for dep in pipeline.depends_on:
            if dep in pipelines_to_run or dep not in seen:
                add_with_deps(dep)
        
        if name not in resolved:
            resolved.append(name)
            seen.add(name)
    
    for name in pipelines_to_run:
        add_with_deps(name)
    
    return resolved


async def run_all_pipelines(
    only: Optional[List[str]] = None,
    skip: Optional[List[str]] = None,
    skip_slow: bool = False,
    dry_run: bool = False
):
    """
    Run all or selected pipelines.
    
    Args:
        only: If set, only run these pipelines (plus dependencies)
        skip: Skip these pipelines
        skip_slow: Skip time-consuming pipelines
        dry_run: Don't actually run, just show what would run
    """
    start_time = datetime.now(timezone.utc)
    
    print("="*60)
    print("🚀 UTAH WATCHDOG - FULL DATA SYNC")
    print("="*60)
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    # Determine which pipelines to run
    if only:
        pipelines_to_run = only
    else:
        pipelines_to_run = list(PIPELINES.keys())
    
    # Apply filters
    if skip:
        pipelines_to_run = [p for p in pipelines_to_run if p not in skip]
    
    if skip_slow:
        pipelines_to_run = [p for p in pipelines_to_run 
                           if not PIPELINES[p].slow]
    
    # Resolve dependencies
    ordered = resolve_dependencies(pipelines_to_run)
    
    print("📋 Pipeline Order:")
    for i, name in enumerate(ordered, 1):
        pipeline = PIPELINES[name]
        slow_tag = " [SLOW]" if pipeline.slow else ""
        print(f"   {i}. {name}{slow_tag} - {pipeline.description}")
    print()
    
    if dry_run:
        print("🏁 Dry run complete. Use without --dry-run to actually run.")
        return
    
    # Run each pipeline
    all_stats = {}
    
    for i, name in enumerate(ordered, 1):
        pipeline = PIPELINES[name]
        
        print(f"\n{'='*60}")
        print(f"[{i}/{len(ordered)}] Running: {name}")
        print(f"{'='*60}")
        
        try:
            stats = await pipeline.run_func()
            all_stats[name] = stats
            
        except Exception as e:
            logger.error(f"Pipeline '{name}' failed: {e}")
            print(f"\n❌ Pipeline '{name}' FAILED: {e}")
            all_stats[name] = {"error": str(e)}
    
    # Final summary
    end_time = datetime.now(timezone.utc)
    duration = end_time - start_time
    
    print("\n" + "="*60)
    print("✅ ALL PIPELINES COMPLETE")
    print("="*60)
    print(f"Duration: {duration}")
    print()
    print("📊 Summary:")
    
    for name, stats in all_stats.items():
        if "error" in stats:
            print(f"   ❌ {name}: FAILED - {stats['error']}")
        else:
            processed = stats.get('processed', 0)
            inserted = stats.get('inserted', 0)
            print(f"   ✅ {name}: {processed} processed, {inserted} new")
    
    print()


async def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run all data pipelines in sequence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run everything
  uv run python scripts/pipelines/sync_all.py
  
  # Run only specific pipelines (plus dependencies)
  uv run python scripts/pipelines/sync_all.py --only members,bills
  
  # Skip slow pipelines (embeddings, votes, contributions)
  uv run python scripts/pipelines/sync_all.py --skip-slow
  
  # Skip specific pipelines
  uv run python scripts/pipelines/sync_all.py --skip embeddings,contributions
  
  # See what would run without running
  uv run python scripts/pipelines/sync_all.py --dry-run
        """
    )
    
    parser.add_argument(
        "--only",
        type=str,
        help="Comma-separated list of pipelines to run (e.g., members,bills)"
    )
    
    parser.add_argument(
        "--skip",
        type=str,
        help="Comma-separated list of pipelines to skip"
    )
    
    parser.add_argument(
        "--skip-slow",
        action="store_true",
        help="Skip time-consuming pipelines (embeddings, votes, contributions)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would run without actually running"
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
    
    # Parse comma-separated lists
    only = args.only.split(",") if args.only else None
    skip = args.skip.split(",") if args.skip else None
    
    # Validate pipeline names
    all_pipeline_names = set(PIPELINES.keys())
    
    if only:
        invalid = set(only) - all_pipeline_names
        if invalid:
            print(f"❌ Unknown pipelines: {', '.join(invalid)}")
            print(f"   Available: {', '.join(all_pipeline_names)}")
            sys.exit(1)
    
    if skip:
        invalid = set(skip) - all_pipeline_names
        if invalid:
            print(f"❌ Unknown pipelines: {', '.join(invalid)}")
            print(f"   Available: {', '.join(all_pipeline_names)}")
            sys.exit(1)
    
    try:
        await run_all_pipelines(
            only=only,
            skip=skip,
            skip_slow=args.skip_slow,
            dry_run=args.dry_run
        )
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Sync interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        logging.exception("Fatal error")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
