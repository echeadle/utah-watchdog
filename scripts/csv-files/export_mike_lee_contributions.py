#!/usr/bin/env python3
"""
Export all Mike Lee contributions from MongoDB to CSV.

This script queries MongoDB for all campaign contributions associated with
Mike Lee (bioguide_id: L000577) and exports them to a CSV file.

Usage:
    python scripts/csv-files/export_mike_lee_contributions.py
    python scripts/csv-files/export_mike_lee_contributions.py --output mike_lee_contributions.csv
"""
import asyncio
import csv
import logging
import argparse
from pathlib import Path
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

from src.config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Output directory for CSV files
DATA_DIR = Path(__file__).parent.parent / "data"

# Mike Lee's bioguide ID
MIKE_LEE_BIOGUIDE_ID = "L000577"


async def export_mike_lee_contributions(output_filename: str = "mike_lee_contributions.csv"):
    """
    Export all Mike Lee contributions from MongoDB to CSV.

    Args:
        output_filename: Name of the output CSV file
    """
    logger.info("="*70)
    logger.info("MIKE LEE CONTRIBUTIONS EXPORT")
    logger.info("="*70)
    logger.info(f"Bioguide ID: {MIKE_LEE_BIOGUIDE_ID}")
    logger.info(f"Database: {settings.MONGODB_DATABASE}")
    logger.info("="*70)

    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]

    try:
        # Query for Mike Lee's contributions
        logger.info(f"Querying contributions for Mike Lee...")

        query = {"bioguide_id": MIKE_LEE_BIOGUIDE_ID}
        contributions = []

        async for doc in db.contributions.find(query):
            contributions.append(doc)

        logger.info(f"Found {len(contributions)} contributions for Mike Lee")

        if not contributions:
            logger.warning("No contributions found. Database may be empty.")
            return

        # Prepare output file
        output_file = DATA_DIR / output_filename
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Define CSV columns
        fieldnames = [
            'id',
            'bioguide_id',
            'recipient_name',
            'recipient_id',
            'committee_id',
            'contributor_name',
            'contributor_type',
            'contributor_employer',
            'contributor_occupation',
            'contributor_city',
            'contributor_state',
            'contributor_zip',
            'amount',
            'contribution_date',
            'industry_code',
            'industry_name',
            'sector_code',
            'sector_name',
            'cycle',
            'source',
            'fec_transaction_id',
            'last_updated'
        ]

        # Write to CSV
        logger.info(f"Writing to {output_file}...")

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for contrib in contributions:
                # Handle Decimal/date conversions
                row = {
                    'id': contrib.get('id', ''),
                    'bioguide_id': contrib.get('bioguide_id', ''),
                    'recipient_name': contrib.get('recipient_name', ''),
                    'recipient_id': contrib.get('recipient_id', ''),
                    'committee_id': contrib.get('committee_id', ''),
                    'contributor_name': contrib.get('contributor_name', ''),
                    'contributor_type': contrib.get('contributor_type', ''),
                    'contributor_employer': contrib.get('contributor_employer', ''),
                    'contributor_occupation': contrib.get('contributor_occupation', ''),
                    'contributor_city': contrib.get('contributor_city', ''),
                    'contributor_state': contrib.get('contributor_state', ''),
                    'contributor_zip': contrib.get('contributor_zip', ''),
                    'amount': str(contrib.get('amount', '')),
                    'contribution_date': contrib.get('contribution_date', ''),
                    'industry_code': contrib.get('industry_code', ''),
                    'industry_name': contrib.get('industry_name', ''),
                    'sector_code': contrib.get('sector_code', ''),
                    'sector_name': contrib.get('sector_name', ''),
                    'cycle': contrib.get('cycle', ''),
                    'source': contrib.get('source', ''),
                    'fec_transaction_id': contrib.get('fec_transaction_id', ''),
                    'last_updated': contrib.get('last_updated', '')
                }

                # Convert datetime objects to ISO format strings
                if isinstance(row['contribution_date'], datetime):
                    row['contribution_date'] = row['contribution_date'].date().isoformat()
                elif hasattr(row['contribution_date'], 'isoformat'):
                    row['contribution_date'] = row['contribution_date'].isoformat()

                if isinstance(row['last_updated'], datetime):
                    row['last_updated'] = row['last_updated'].date().isoformat()
                elif hasattr(row['last_updated'], 'isoformat'):
                    row['last_updated'] = row['last_updated'].isoformat()

                writer.writerow(row)

        logger.info(f"✓ Successfully exported {len(contributions)} contributions to {output_file}")

        # Print summary statistics
        logger.info("")
        logger.info("="*70)
        logger.info("SUMMARY STATISTICS")
        logger.info("="*70)

        # Total amount
        total_amount = sum(float(c.get('amount', 0)) for c in contributions)
        logger.info(f"Total amount: ${total_amount:,.2f}")

        # By cycle
        cycles = {}
        for c in contributions:
            cycle = c.get('cycle', 'Unknown')
            cycles[cycle] = cycles.get(cycle, 0) + 1

        logger.info(f"\nContributions by cycle:")
        for cycle in sorted(cycles.keys(), reverse=True):
            logger.info(f"  {cycle}: {cycles[cycle]:,} contributions")

        # By source
        sources = {}
        for c in contributions:
            source = c.get('source', 'Unknown')
            sources[source] = sources.get(source, 0) + 1

        logger.info(f"\nContributions by source:")
        for source, count in sources.items():
            logger.info(f"  {source}: {count:,} contributions")

        # By contributor type
        types = {}
        for c in contributions:
            contrib_type = c.get('contributor_type', 'Unknown')
            types[contrib_type] = types.get(contrib_type, 0) + 1

        logger.info(f"\nContributions by type:")
        for contrib_type, count in types.items():
            logger.info(f"  {contrib_type}: {count:,} contributions")

        logger.info("")
        logger.info("="*70)
        logger.info("EXPORT COMPLETE!")
        logger.info("="*70)

    except Exception as e:
        logger.error(f"Error exporting contributions: {e}", exc_info=True)
        raise
    finally:
        client.close()


async def main():
    parser = argparse.ArgumentParser(
        description='Export all Mike Lee contributions from MongoDB to CSV'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='mike_lee_contributions.csv',
        help='Output CSV filename (default: mike_lee_contributions.csv)'
    )

    args = parser.parse_args()

    await export_mike_lee_contributions(output_filename=args.output)


if __name__ == "__main__":
    asyncio.run(main())
