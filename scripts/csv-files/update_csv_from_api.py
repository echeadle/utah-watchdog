#!/usr/bin/env python3
"""
Fetch data from Congress.gov API and save to CSV files.

This script fetches senators/representatives and bills from the API
and saves them to CSV files for development/testing purposes.

Usage:
    python scripts/csv-files/update_csv_from_api.py --politicians
    python scripts/csv-files/update_csv_from_api.py --bills --congress 119
    python scripts/csv-files/update_csv_from_api.py --all
"""
import asyncio
import csv
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import List

from src.ingestion.congress_members import CongressMembersIngester
from src.ingestion.congress_bills import CongressBillsIngester
from src.ingestion.fec import FECIngester
from src.models.politician import Politician
from src.models.legislation import Bill
from src.models.finance import Contribution

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Output directory for CSV files
DATA_DIR = Path(__file__).parent.parent / "data"


class CSVExporter:
    """Exports data to CSV files without database connection."""

    def __init__(self):
        self.politicians: List[Politician] = []
        self.bills: List[Bill] = []
        self.contributions: List[Contribution] = []

    async def fetch_politicians(self, congress: int = 119, state_filter: str = None):
        """
        Fetch politicians from API.

        Args:
            congress: Congress number (default 119)
            state_filter: Optional state filter (e.g., "UT")
        """
        logger.info(f"Fetching politicians from Congress {congress}...")

        # Create ingester (no DB connection needed for fetch/transform)
        ingester = CongressMembersIngester(
            congress=congress,
            state_filter=state_filter,
            fetch_details=True
        )

        # Fetch and transform data
        async for raw_data in ingester.fetch_data():
            try:
                politician = await ingester.transform(raw_data)
                self.politicians.append(politician)
            except Exception as e:
                logger.error(f"Error transforming politician: {e}")

        logger.info(f"Fetched {len(self.politicians)} politicians")

    async def fetch_bills(self, congress: int = 119, bill_type: str = "hr", max_bills: int = None):
        """
        Fetch bills from API.

        Args:
            congress: Congress number (default 119)
            bill_type: Type of bill (hr, s, etc.)
            max_bills: Maximum number of bills to fetch
        """
        logger.info(f"Fetching {bill_type.upper()} bills from Congress {congress}...")

        # Create ingester
        ingester = CongressBillsIngester(congress=congress)

        # Fetch and transform data
        async for raw_data in ingester.fetch_data(bill_type=bill_type, max_bills=max_bills):
            try:
                bill = await ingester.transform(raw_data)
                self.bills.append(bill)
            except Exception as e:
                logger.error(f"Error transforming bill: {e}")

        logger.info(f"Fetched {len(self.bills)} bills")

    def save_politicians_csv(self):
        """Save politicians to CSV file."""
        if not self.politicians:
            logger.warning("No politicians to save")
            return

        output_file = DATA_DIR / "politicians.csv"
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Define CSV columns
        fieldnames = [
            'bioguide_id', 'first_name', 'last_name', 'full_name',
            'party', 'state', 'chamber', 'district', 'title',
            'in_office', 'website', 'phone', 'office', 'last_updated'
        ]

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for politician in self.politicians:
                row = {
                    'bioguide_id': politician.bioguide_id,
                    'first_name': politician.first_name,
                    'last_name': politician.last_name,
                    'full_name': politician.full_name,
                    'party': politician.party.value,
                    'state': politician.state,
                    'chamber': politician.chamber.value,
                    'district': politician.district or '',
                    'title': politician.title or '',
                    'in_office': politician.in_office,
                    'website': politician.website or '',
                    'phone': politician.phone or '',
                    'office': politician.office or '',
                    'last_updated': politician.last_updated.isoformat()
                }
                writer.writerow(row)

        logger.info(f"Saved {len(self.politicians)} politicians to {output_file}")

    def save_bills_csv(self):
        """Save bills to CSV file."""
        if not self.bills:
            logger.warning("No bills to save")
            return

        output_file = DATA_DIR / "bills.csv"
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Define CSV columns
        fieldnames = [
            'bill_id', 'bill_type', 'number', 'congress',
            'title', 'short_title', 'summary', 'status',
            'introduced_date', 'latest_action_date', 'latest_action_text',
            'sponsor_bioguide_id', 'policy_area', 'subjects',
            'congress_gov_url', 'last_updated'
        ]

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for bill in self.bills:
                row = {
                    'bill_id': bill.bill_id,
                    'bill_type': bill.bill_type.value,
                    'number': bill.number,
                    'congress': bill.congress,
                    'title': bill.title,
                    'short_title': bill.short_title or '',
                    'summary': bill.summary or '',
                    'status': bill.status.value,
                    'introduced_date': bill.introduced_date.isoformat() if bill.introduced_date else '',
                    'latest_action_date': bill.latest_action_date.isoformat() if bill.latest_action_date else '',
                    'latest_action_text': bill.latest_action_text or '',
                    'sponsor_bioguide_id': bill.sponsor_bioguide_id or '',
                    'policy_area': bill.policy_area or '',
                    'subjects': '|'.join(bill.subjects) if bill.subjects else '',
                    'congress_gov_url': bill.congress_gov_url or '',
                    'last_updated': bill.last_updated.isoformat()
                }
                writer.writerow(row)

        logger.info(f"Saved {len(self.bills)} bills to {output_file}")

    async def fetch_contributions(self, state_filter: str = None, cycle: int = 2024, max_per_politician: int = 100):
        """
        Fetch campaign contributions from FEC API.

        Args:
            state_filter: Optional state filter (e.g., "UT")
            cycle: Election cycle (default: 2024)
            max_per_politician: Max contributions per politician (default: 100)
        """
        from motor.motor_asyncio import AsyncIOMotorClient
        from src.config.settings import settings

        logger.info(f"Fetching contributions for cycle {cycle}...")

        # Connect to DB to get politicians with FEC IDs
        client = AsyncIOMotorClient(settings.MONGODB_URI)
        db = client[settings.MONGODB_DATABASE]

        query = {
            "fec_candidate_id": {"$exists": True, "$ne": None},
            "bioguide_id": {"$exists": True, "$ne": None}
        }

        if state_filter:
            query["state"] = state_filter.upper()

        politicians = await db.politicians.find(query).to_list(None)
        client.close()

        logger.info(f"Found {len(politicians)} politicians with FEC IDs")

        if not politicians:
            logger.warning("No politicians with FEC IDs found")
            return

        # Fetch contributions for each politician
        for politician in politicians:
            name = politician.get("full_name")
            fec_id = politician.get("fec_candidate_id")
            bioguide_id = politician.get("bioguide_id")

            logger.info(f"Fetching contributions for {name} ({bioguide_id})...")

            ingester = FECIngester(
                candidate_name=name,
                bioguide_id=bioguide_id
            )

            try:
                count = 0
                async for raw_data in ingester.fetch_data(
                    candidate_id=fec_id,
                    cycle=cycle,
                    per_page=100,
                    max_pages=1  # Limit to 100 contributions per politician
                ):
                    try:
                        contribution = await ingester.transform(raw_data)
                        self.contributions.append(contribution)
                        count += 1

                        if count >= max_per_politician:
                            break

                    except Exception as e:
                        logger.error(f"Error transforming contribution: {e}")

                logger.info(f"  Fetched {count} contributions for {name}")

            except Exception as e:
                logger.error(f"Error fetching contributions for {name}: {e}")

        logger.info(f"Total contributions fetched: {len(self.contributions)}")

    def save_contributions_csv(self):
        """Save contributions to CSV file."""
        if not self.contributions:
            logger.warning("No contributions to save")
            return

        output_file = DATA_DIR / "contributions.csv"
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Define CSV columns
        fieldnames = [
            'id', 'bioguide_id', 'recipient_name', 'contributor_name',
            'contributor_type', 'contributor_employer', 'contributor_occupation',
            'contributor_city', 'contributor_state', 'contributor_zip',
            'amount', 'contribution_date', 'cycle', 'source', 'last_updated'
        ]

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for contrib in self.contributions:
                row = {
                    'id': contrib.id,
                    'bioguide_id': contrib.bioguide_id or '',
                    'recipient_name': contrib.recipient_name,
                    'contributor_name': contrib.contributor_name,
                    'contributor_type': contrib.contributor_type.value,
                    'contributor_employer': contrib.contributor_employer or '',
                    'contributor_occupation': contrib.contributor_occupation or '',
                    'contributor_city': contrib.contributor_city or '',
                    'contributor_state': contrib.contributor_state or '',
                    'contributor_zip': contrib.contributor_zip or '',
                    'amount': str(contrib.amount),
                    'contribution_date': contrib.contribution_date.isoformat(),
                    'cycle': contrib.cycle,
                    'source': contrib.source,
                    'last_updated': contrib.last_updated.isoformat()
                }
                writer.writerow(row)

        logger.info(f"Saved {len(self.contributions)} contributions to {output_file}")


async def main():
    parser = argparse.ArgumentParser(description='Fetch data from API and save to CSV')
    parser.add_argument('--politicians', action='store_true', help='Fetch politicians')
    parser.add_argument('--bills', action='store_true', help='Fetch bills')
    parser.add_argument('--contributions', action='store_true', help='Fetch campaign contributions')
    parser.add_argument('--all', action='store_true', help='Fetch politicians, bills, and contributions')
    parser.add_argument('--congress', type=int, default=119, help='Congress number (default: 119)')
    parser.add_argument('--state', type=str, help='State filter for politicians/contributions (e.g., UT)')
    parser.add_argument('--bill-type', type=str, default='hr', help='Bill type (default: hr)')
    parser.add_argument('--max-bills', type=int, help='Maximum bills to fetch')
    parser.add_argument('--cycle', type=int, default=2024, help='Election cycle for contributions (default: 2024)')
    parser.add_argument('--max-contributions', type=int, default=100, help='Max contributions per politician (default: 100)')

    args = parser.parse_args()

    # Default to --all if nothing specified
    if not (args.politicians or args.bills or args.contributions or args.all):
        args.all = True

    exporter = CSVExporter()

    # Fetch politicians
    if args.politicians or args.all:
        await exporter.fetch_politicians(
            congress=args.congress,
            state_filter=args.state
        )
        exporter.save_politicians_csv()

    # Fetch bills
    if args.bills or args.all:
        await exporter.fetch_bills(
            congress=args.congress,
            bill_type=args.bill_type,
            max_bills=args.max_bills
        )
        exporter.save_bills_csv()

    # Fetch contributions
    if args.contributions or args.all:
        await exporter.fetch_contributions(
            state_filter=args.state,
            cycle=args.cycle,
            max_per_politician=args.max_contributions
        )
        exporter.save_contributions_csv()

    logger.info("Done! CSV files are in scripts/data/")


if __name__ == "__main__":
    asyncio.run(main())
