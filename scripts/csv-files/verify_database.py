#!/usr/bin/env python3
"""
Verify database records against CSV files.

This script compares the data in MongoDB with the CSV files to ensure
ingestion is working correctly.

Usage:
    python scripts/csv-files/verify_database.py --politicians
    python scripts/csv-files/verify_database.py --bills
    python scripts/csv-files/verify_database.py --all
"""
import asyncio
import csv
import logging
import argparse
from pathlib import Path
from typing import Dict, Set
from motor.motor_asyncio import AsyncIOMotorClient

from src.config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data"


class DatabaseVerifier:
    """Verifies database records against CSV files."""

    def __init__(self):
        self.client = None
        self.db = None

    async def connect(self):
        """Connect to MongoDB."""
        self.client = AsyncIOMotorClient(settings.MONGODB_URI)
        self.db = self.client[settings.MONGODB_DATABASE]
        logger.info(f"Connected to MongoDB: {settings.MONGODB_DATABASE}")

    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    async def verify_politicians(self):
        """Verify politicians collection against CSV."""
        csv_file = DATA_DIR / "politicians.csv"

        if not csv_file.exists():
            logger.error(f"CSV file not found: {csv_file}")
            return

        logger.info("\n=== Verifying Politicians ===")

        # Load CSV data
        csv_politicians: Dict[str, dict] = {}
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                csv_politicians[row['bioguide_id']] = row

        logger.info(f"CSV file contains {len(csv_politicians)} politicians")

        # Load DB data
        db_politicians = {}
        async for doc in self.db.politicians.find():
            db_politicians[doc['bioguide_id']] = doc

        logger.info(f"Database contains {len(db_politicians)} politicians")

        # Find differences
        csv_ids = set(csv_politicians.keys())
        db_ids = set(db_politicians.keys())

        # Missing in DB
        missing_in_db = csv_ids - db_ids
        if missing_in_db:
            logger.warning(f"Missing in database: {len(missing_in_db)} politicians")
            for bioguide_id in sorted(missing_in_db):
                logger.warning(f"  - {bioguide_id}: {csv_politicians[bioguide_id]['full_name']}")
        else:
            logger.info("All CSV politicians are in database")

        # Extra in DB (not in CSV)
        extra_in_db = db_ids - csv_ids
        if extra_in_db:
            logger.info(f"Extra in database (not in CSV): {len(extra_in_db)} politicians")
            for bioguide_id in sorted(list(extra_in_db)[:10]):  # Show first 10
                logger.info(f"  - {bioguide_id}: {db_politicians[bioguide_id].get('full_name', 'N/A')}")
            if len(extra_in_db) > 10:
                logger.info(f"  ... and {len(extra_in_db) - 10} more")

        # Compare common records
        common_ids = csv_ids & db_ids
        mismatches = []

        for bioguide_id in common_ids:
            csv_row = csv_politicians[bioguide_id]
            db_doc = db_politicians[bioguide_id]

            # Compare key fields
            fields_to_check = ['full_name', 'party', 'state', 'chamber']
            for field in fields_to_check:
                csv_value = csv_row[field]
                db_value = str(db_doc.get(field, ''))

                if csv_value != db_value:
                    mismatches.append({
                        'bioguide_id': bioguide_id,
                        'field': field,
                        'csv_value': csv_value,
                        'db_value': db_value
                    })

        if mismatches:
            logger.warning(f"Found {len(mismatches)} field mismatches:")
            for mismatch in mismatches[:20]:  # Show first 20
                logger.warning(
                    f"  {mismatch['bioguide_id']}.{mismatch['field']}: "
                    f"CSV='{mismatch['csv_value']}' vs DB='{mismatch['db_value']}'"
                )
            if len(mismatches) > 20:
                logger.warning(f"  ... and {len(mismatches) - 20} more mismatches")
        else:
            logger.info("All common politicians match!")

        # Summary
        logger.info(f"\nSummary:")
        logger.info(f"  CSV: {len(csv_ids)} records")
        logger.info(f"  DB: {len(db_ids)} records")
        logger.info(f"  Common: {len(common_ids)} records")
        logger.info(f"  Missing in DB: {len(missing_in_db)}")
        logger.info(f"  Extra in DB: {len(extra_in_db)}")
        logger.info(f"  Mismatches: {len(mismatches)}")

    async def verify_bills(self):
        """Verify bills collection against CSV."""
        csv_file = DATA_DIR / "bills.csv"

        if not csv_file.exists():
            logger.error(f"CSV file not found: {csv_file}")
            return

        logger.info("\n=== Verifying Bills ===")

        # Load CSV data
        csv_bills: Dict[str, dict] = {}
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                csv_bills[row['bill_id']] = row

        logger.info(f"CSV file contains {len(csv_bills)} bills")

        # Load DB data
        db_bills = {}
        async for doc in self.db.legislation.find():
            db_bills[doc['bill_id']] = doc

        logger.info(f"Database contains {len(db_bills)} bills")

        # Find differences
        csv_ids = set(csv_bills.keys())
        db_ids = set(db_bills.keys())

        # Missing in DB
        missing_in_db = csv_ids - db_ids
        if missing_in_db:
            logger.warning(f"Missing in database: {len(missing_in_db)} bills")
            for bill_id in sorted(list(missing_in_db)[:10]):  # Show first 10
                logger.warning(f"  - {bill_id}: {csv_bills[bill_id]['title'][:50]}...")
            if len(missing_in_db) > 10:
                logger.warning(f"  ... and {len(missing_in_db) - 10} more")
        else:
            logger.info("All CSV bills are in database")

        # Extra in DB (not in CSV)
        extra_in_db = db_ids - csv_ids
        if extra_in_db:
            logger.info(f"Extra in database (not in CSV): {len(extra_in_db)} bills")
            for bill_id in sorted(list(extra_in_db)[:10]):  # Show first 10
                logger.info(f"  - {bill_id}: {db_bills[bill_id].get('title', 'N/A')[:50]}...")
            if len(extra_in_db) > 10:
                logger.info(f"  ... and {len(extra_in_db) - 10} more")

        # Compare common records
        common_ids = csv_ids & db_ids
        mismatches = []

        for bill_id in common_ids:
            csv_row = csv_bills[bill_id]
            db_doc = db_bills[bill_id]

            # Compare key fields
            fields_to_check = ['bill_type', 'number', 'congress', 'status']
            for field in fields_to_check:
                csv_value = csv_row[field]
                db_value = str(db_doc.get(field, ''))

                if csv_value != db_value:
                    mismatches.append({
                        'bill_id': bill_id,
                        'field': field,
                        'csv_value': csv_value,
                        'db_value': db_value
                    })

        if mismatches:
            logger.warning(f"Found {len(mismatches)} field mismatches:")
            for mismatch in mismatches[:20]:  # Show first 20
                logger.warning(
                    f"  {mismatch['bill_id']}.{mismatch['field']}: "
                    f"CSV='{mismatch['csv_value']}' vs DB='{mismatch['db_value']}'"
                )
            if len(mismatches) > 20:
                logger.warning(f"  ... and {len(mismatches) - 20} more mismatches")
        else:
            logger.info("All common bills match!")

        # Summary
        logger.info(f"\nSummary:")
        logger.info(f"  CSV: {len(csv_ids)} records")
        logger.info(f"  DB: {len(db_ids)} records")
        logger.info(f"  Common: {len(common_ids)} records")
        logger.info(f"  Missing in DB: {len(missing_in_db)}")
        logger.info(f"  Extra in DB: {len(extra_in_db)}")
        logger.info(f"  Mismatches: {len(mismatches)}")

    async def run(self, verify_politicians: bool = False, verify_bills: bool = False):
        """
        Run the verification.

        Args:
            verify_politicians: Whether to verify politicians
            verify_bills: Whether to verify bills
        """
        try:
            await self.connect()

            if verify_politicians:
                await self.verify_politicians()

            if verify_bills:
                await self.verify_bills()

        finally:
            await self.disconnect()


async def main():
    parser = argparse.ArgumentParser(description='Verify database records against CSV files')
    parser.add_argument('--politicians', action='store_true', help='Verify politicians')
    parser.add_argument('--bills', action='store_true', help='Verify bills')
    parser.add_argument('--all', action='store_true', help='Verify both politicians and bills')

    args = parser.parse_args()

    # Default to --all if nothing specified
    if not (args.politicians or args.bills or args.all):
        args.all = True

    verifier = DatabaseVerifier()

    await verifier.run(
        verify_politicians=args.politicians or args.all,
        verify_bills=args.bills or args.all
    )


if __name__ == "__main__":
    asyncio.run(main())
