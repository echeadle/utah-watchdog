#!/usr/bin/env python3
"""
Ingest data from CSV files into the database.

This script reads CSV files and populates the database using the same
models and normalization logic as the API ingesters.

Usage:
    python scripts/csv-files/ingest_from_csv.py --politicians
    python scripts/csv-files/ingest_from_csv.py --bills
    python scripts/csv-files/ingest_from_csv.py --all
"""
import asyncio
import csv
import logging
import argparse
from pathlib import Path
from datetime import datetime, date
from motor.motor_asyncio import AsyncIOMotorClient

from src.models.politician import Politician, Chamber, Party
from src.models.legislation import Bill, BillType, BillStatus
from src.models.finance import Contribution, ContributionType
from src.config.settings import settings
from src.database.normalization import normalize_politician, normalize_legislation, normalize_contribution

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data"


class CSVIngester:
    """Ingests data from CSV files into MongoDB."""

    def __init__(self):
        self.client = None
        self.db = None
        self.stats = {
            'politicians_inserted': 0,
            'politicians_updated': 0,
            'bills_inserted': 0,
            'bills_updated': 0,
            'contributions_inserted': 0,
            'contributions_updated': 0,
            'errors': 0
        }

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

    async def ingest_politicians(self):
        """Ingest politicians from CSV file."""
        csv_file = DATA_DIR / "politicians.csv"

        if not csv_file.exists():
            logger.error(f"CSV file not found: {csv_file}")
            return

        logger.info(f"Reading politicians from {csv_file}...")

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    # Convert CSV row to Politician model
                    politician = Politician(
                        bioguide_id=row['bioguide_id'],
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        full_name=row['full_name'],
                        party=Party(row['party']),
                        state=row['state'],
                        chamber=Chamber(row['chamber']),
                        district=int(row['district']) if row['district'] else None,
                        title=row['title'] or None,
                        in_office=row['in_office'].lower() in ('true', '1', 'yes'),
                        website=row['website'] or None,
                        phone=row['phone'] or None,
                        office=row['office'] or None,
                        last_updated=datetime.fromisoformat(row['last_updated'])
                    )

                    # Convert to dict and normalize
                    politician_data = politician.model_dump()
                    normalized_data = normalize_politician(politician_data)

                    # Upsert to database
                    result = await self.db.politicians.update_one(
                        {"bioguide_id": politician.bioguide_id},
                        {"$set": normalized_data},
                        upsert=True
                    )

                    if result.upserted_id:
                        self.stats['politicians_inserted'] += 1
                    else:
                        self.stats['politicians_updated'] += 1

                except Exception as e:
                    logger.error(f"Error ingesting politician {row.get('bioguide_id', 'unknown')}: {e}")
                    self.stats['errors'] += 1

        logger.info(
            f"Politicians: {self.stats['politicians_inserted']} inserted, "
            f"{self.stats['politicians_updated']} updated"
        )

    async def ingest_bills(self):
        """Ingest bills from CSV file."""
        csv_file = DATA_DIR / "bills.csv"

        if not csv_file.exists():
            logger.error(f"CSV file not found: {csv_file}")
            return

        logger.info(f"Reading bills from {csv_file}...")

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    # Parse subjects (stored as pipe-separated)
                    subjects = row['subjects'].split('|') if row['subjects'] else []

                    # Convert CSV row to Bill model
                    bill = Bill(
                        bill_id=row['bill_id'],
                        bill_type=BillType(row['bill_type']),
                        number=int(row['number']),
                        congress=int(row['congress']),
                        title=row['title'],
                        short_title=row['short_title'] or None,
                        summary=row['summary'] or None,
                        status=BillStatus(row['status']),
                        introduced_date=date.fromisoformat(row['introduced_date']) if row['introduced_date'] else None,
                        latest_action_date=date.fromisoformat(row['latest_action_date']) if row['latest_action_date'] else None,
                        latest_action_text=row['latest_action_text'] or None,
                        sponsor_bioguide_id=row['sponsor_bioguide_id'] or None,
                        policy_area=row['policy_area'] or None,
                        subjects=subjects,
                        congress_gov_url=row['congress_gov_url'] or None,
                        last_updated=datetime.fromisoformat(row['last_updated'])
                    )

                    # Convert to dict
                    bill_data = bill.model_dump()

                    # Convert date objects to datetime for MongoDB
                    if bill_data.get('introduced_date'):
                        bill_data['introduced_date'] = datetime.combine(
                            bill_data['introduced_date'],
                            datetime.min.time()
                        )

                    if bill_data.get('latest_action_date'):
                        bill_data['latest_action_date'] = datetime.combine(
                            bill_data['latest_action_date'],
                            datetime.min.time()
                        )

                    # Convert enum values to strings
                    if 'bill_type' in bill_data:
                        bill_data['bill_type'] = bill_data['bill_type'].value if hasattr(bill_data['bill_type'], 'value') else bill_data['bill_type']

                    if 'status' in bill_data:
                        bill_data['status'] = bill_data['status'].value if hasattr(bill_data['status'], 'value') else bill_data['status']

                    # Normalize
                    normalized_data = normalize_legislation(bill_data)

                    # Upsert to database
                    result = await self.db.legislation.update_one(
                        {"bill_id": bill.bill_id},
                        {"$set": normalized_data},
                        upsert=True
                    )

                    if result.upserted_id:
                        self.stats['bills_inserted'] += 1
                    else:
                        self.stats['bills_updated'] += 1

                except Exception as e:
                    logger.error(f"Error ingesting bill {row.get('bill_id', 'unknown')}: {e}")
                    self.stats['errors'] += 1

        logger.info(
            f"Bills: {self.stats['bills_inserted']} inserted, "
            f"{self.stats['bills_updated']} updated"
        )

    async def ingest_contributions(self):
        """Ingest contributions from CSV file."""
        from decimal import Decimal
        csv_file = DATA_DIR / "contributions.csv"

        if not csv_file.exists():
            logger.error(f"CSV file not found: {csv_file}")
            return

        logger.info(f"Reading contributions from {csv_file}...")

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    # Convert CSV row to Contribution model
                    contribution = Contribution(
                        id=row['id'],
                        bioguide_id=row['bioguide_id'] or None,
                        recipient_name=row['recipient_name'],
                        contributor_name=row['contributor_name'],
                        contributor_type=ContributionType(row['contributor_type']),
                        contributor_employer=row['contributor_employer'] or None,
                        contributor_occupation=row['contributor_occupation'] or None,
                        contributor_city=row['contributor_city'] or None,
                        contributor_state=row['contributor_state'] or None,
                        contributor_zip=row['contributor_zip'] or None,
                        amount=Decimal(row['amount']),
                        contribution_date=date.fromisoformat(row['contribution_date']),
                        cycle=row['cycle'],
                        source=row['source'],
                        last_updated=date.fromisoformat(row['last_updated'])
                    )

                    # Convert to dict
                    contrib_data = contribution.model_dump()

                    # Convert Decimal to float for MongoDB
                    if 'amount' in contrib_data:
                        contrib_data['amount'] = float(contrib_data['amount'])

                    # Convert enum to string
                    if 'contributor_type' in contrib_data:
                        contrib_data['contributor_type'] = contrib_data['contributor_type'].value if hasattr(contrib_data['contributor_type'], 'value') else contrib_data['contributor_type']

                    # Convert date to datetime for MongoDB
                    if contrib_data.get('contribution_date'):
                        contrib_data['contribution_date'] = datetime.combine(
                            contrib_data['contribution_date'],
                            datetime.min.time()
                        )

                    if contrib_data.get('last_updated'):
                        if isinstance(contrib_data['last_updated'], date):
                            contrib_data['last_updated'] = datetime.combine(
                                contrib_data['last_updated'],
                                datetime.min.time()
                            )

                    # Normalize
                    normalized_data = normalize_contribution(contrib_data)

                    # Upsert to database using composite key (id + bioguide_id)
                    # This prevents duplicate FEC transaction IDs from overwriting each other
                    result = await self.db.contributions.update_one(
                        {
                            "id": contribution.id,
                            "bioguide_id": contribution.bioguide_id
                        },
                        {"$set": normalized_data},
                        upsert=True
                    )

                    if result.upserted_id:
                        self.stats['contributions_inserted'] += 1
                    else:
                        self.stats['contributions_updated'] += 1

                except Exception as e:
                    logger.error(f"Error ingesting contribution {row.get('id', 'unknown')}: {e}")
                    self.stats['errors'] += 1

        logger.info(
            f"Contributions: {self.stats['contributions_inserted']} inserted, "
            f"{self.stats['contributions_updated']} updated"
        )

    async def run(self, ingest_politicians: bool = False, ingest_bills: bool = False, ingest_contributions: bool = False):
        """
        Run the CSV ingestion.

        Args:
            ingest_politicians: Whether to ingest politicians
            ingest_bills: Whether to ingest bills
            ingest_contributions: Whether to ingest contributions
        """
        try:
            await self.connect()

            if ingest_politicians:
                await self.ingest_politicians()

            if ingest_bills:
                await self.ingest_bills()

            if ingest_contributions:
                await self.ingest_contributions()

            logger.info("\n=== Ingestion Complete ===")
            logger.info(f"Politicians: {self.stats['politicians_inserted']} inserted, {self.stats['politicians_updated']} updated")
            logger.info(f"Bills: {self.stats['bills_inserted']} inserted, {self.stats['bills_updated']} updated")
            logger.info(f"Contributions: {self.stats['contributions_inserted']} inserted, {self.stats['contributions_updated']} updated")
            logger.info(f"Errors: {self.stats['errors']}")

        finally:
            await self.disconnect()


async def main():
    parser = argparse.ArgumentParser(description='Ingest data from CSV files to database')
    parser.add_argument('--politicians', action='store_true', help='Ingest politicians')
    parser.add_argument('--bills', action='store_true', help='Ingest bills')
    parser.add_argument('--contributions', action='store_true', help='Ingest campaign contributions')
    parser.add_argument('--all', action='store_true', help='Ingest politicians, bills, and contributions')

    args = parser.parse_args()

    # Default to --all if nothing specified
    if not (args.politicians or args.bills or args.contributions or args.all):
        args.all = True

    ingester = CSVIngester()

    await ingester.run(
        ingest_politicians=args.politicians or args.all,
        ingest_bills=args.bills or args.all,
        ingest_contributions=args.contributions or args.all
    )


if __name__ == "__main__":
    asyncio.run(main())
