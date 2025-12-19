"""
Script to sync committee assignments.

Usage:
    uv run python scripts/sync_committees.py
"""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.committees import CommitteeIngester
from src.config.constants import CURRENT_CONGRESS


async def sync_committees(congress: int = CURRENT_CONGRESS):
    """Sync committee assignments"""
    print(f"🏛️ Syncing committee assignments for Congress {congress}...")
    print("=" * 60)
    
    ingester = CommitteeIngester(congress=congress)
    stats = await ingester.run()
    
    print("\n✅ Committee Sync Complete!")
    print("=" * 60)
    print(f"📊 Statistics:")
    print(f"   • Processed: {stats['processed']} committees")
    print(f"   • Errors:    {stats['errors']}")
    
    return stats


async def main():
    logging.basicConfig(level=logging.INFO)
    
    try:
        stats = await sync_committees()
        sys.exit(1 if stats['errors'] > 0 else 0)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logging.exception("Fatal error")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())