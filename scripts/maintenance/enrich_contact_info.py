"""
Script to enrich politician records with contact information.

Run this after syncing members to add office addresses and phone numbers.

Usage:
    uv run python scripts/enrich_contact_info.py
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.contact_info import ContactInfoIngester


async def enrich_contact_info():
    """
    Enrich politician records with office and phone data.
    """
    print("📞 Enriching politician records with contact information...")
    print("=" * 60)
    print("Source: github.com/unitedstates/congress-legislators")
    print()
    
    ingester = ContactInfoIngester()
    stats = await ingester.run_enrichment()
    
    print("\n✅ Enrichment Complete!")
    print("=" * 60)
    print(f"📊 Statistics:")
    print(f"   • Processed: {stats['processed']}")
    print(f"   • Updated:   {stats['updated']} records")
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
        description="Enrich politician records with contact information"
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
        stats = await enrich_contact_info()
        
        # Exit with error code if there were errors
        sys.exit(1 if stats['errors'] > 0 else 0)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Enrichment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        logging.exception("Fatal error during enrichment")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())