#!/usr/bin/env python3
"""
Troubleshooting script to fetch ALL contributions for Utah's 6 federal politicians.

This standalone script fetches campaign contributions from the FEC API for:
- 2 Utah Senators
- 4 Utah Representatives

Useful for debugging why all 6 representatives show the same contributions.

Usage:
    python scripts/csv-files/troubleshoot_utah_contributions.py --cycles 2024 2022 2020
    python scripts/csv-files/troubleshoot_utah_contributions.py --cycles 2024 --max-pages 5
    python scripts/csv-files/troubleshoot_utah_contributions.py --all  # Fetch ALL contributions (no limit)
"""
import asyncio
import csv
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import List

from src.ingestion.fec import FECIngester
from src.models.finance import Contribution

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Output directory for CSV files
DATA_DIR = Path(__file__).parent.parent / "data"

# Utah's 6 federal politicians with their FEC IDs
UTAH_POLITICIANS = [
    # Senators
    {
        "name": "Mike Lee",
        "bioguide_id": "L000577",
        "fec_candidate_id": "S0UT00165",
        "chamber": "Senate"
    },
    {
        "name": "John Curtis",
        "bioguide_id": "C001114",
        "fec_candidate_id": "S4UT00282",
        "chamber": "Senate"
    },
    # Representatives
    {
        "name": "Blake Moore",
        "bioguide_id": "M001213",
        "fec_candidate_id": "H0UT01129",
        "chamber": "House",
        "district": "1"
    },
    {
        "name": "Celeste Maloy",
        "bioguide_id": "M001228",
        "fec_candidate_id": "H2UT03149",
        "chamber": "House",
        "district": "2"
    },
    {
        "name": "John Curtis (former House)",
        "bioguide_id": "C001114",
        "fec_candidate_id": "H6UT03179",  # House FEC ID
        "chamber": "House",
        "district": "3"
    },
    {
        "name": "Burgess Owens",
        "bioguide_id": "O000086",
        "fec_candidate_id": "H0UT04076",
        "chamber": "House",
        "district": "4"
    },
    {
        "name": "Mike Kennedy",
        "bioguide_id": "K000403",
        "fec_candidate_id": "H4UT04206",
        "chamber": "House",
        "district": "3"
    },
]


class UtahContributionsDebugger:
    """Fetches and analyzes contributions for Utah politicians."""

    def __init__(self):
        self.contributions: List[Contribution] = []
        self.stats = {}

    async def fetch_all_contributions(self, cycles: List[int], max_pages: int = None):
        """
        Fetch contributions for all Utah politicians across multiple cycles.

        Args:
            cycles: List of election cycles (e.g., [2024, 2022, 2020])
            max_pages: Maximum pages to fetch per politician/cycle (None = unlimited)
        """
        logger.info("="*70)
        logger.info("UTAH CONTRIBUTIONS DEBUGGING SCRIPT")
        logger.info("="*70)
        logger.info(f"Fetching contributions for {len(UTAH_POLITICIANS)} Utah politicians")
        logger.info(f"Cycles: {cycles}")
        logger.info(f"Max pages per politician/cycle: {max_pages or 'UNLIMITED'}")
        logger.info("="*70)

        for politician in UTAH_POLITICIANS:
            name = politician["name"]
            bioguide_id = politician["bioguide_id"]
            fec_id = politician["fec_candidate_id"]
            chamber = politician["chamber"]
            district = politician.get("district", "")

            logger.info("")
            logger.info(f"{'='*70}")
            logger.info(f"Politician: {name} ({chamber}{f' District {district}' if district else ''})")
            logger.info(f"  Bioguide ID: {bioguide_id}")
            logger.info(f"  FEC ID: {fec_id}")
            logger.info(f"{'='*70}")

            politician_key = f"{name} ({bioguide_id})"
            self.stats[politician_key] = {}

            for cycle in cycles:
                logger.info(f"  → Fetching {cycle} contributions...")

                ingester = FECIngester(
                    candidate_name=name,
                    bioguide_id=bioguide_id
                )

                try:
                    count = 0
                    unique_ids = set()

                    async for raw_data in ingester.fetch_data(
                        candidate_id=fec_id,
                        cycle=cycle,
                        per_page=100,
                        max_pages=max_pages
                    ):
                        try:
                            contribution = await ingester.transform(raw_data)
                            self.contributions.append(contribution)
                            unique_ids.add(contribution.id)
                            count += 1

                        except Exception as e:
                            logger.error(f"    Error transforming contribution: {e}")

                    self.stats[politician_key][cycle] = {
                        'count': count,
                        'unique_ids': len(unique_ids)
                    }

                    logger.info(f"    ✓ Fetched {count} contributions ({len(unique_ids)} unique IDs)")

                except Exception as e:
                    logger.error(f"    ✗ Error fetching contributions: {e}")
                    self.stats[politician_key][cycle] = {
                        'count': 0,
                        'unique_ids': 0,
                        'error': str(e)
                    }

        logger.info("")
        logger.info("="*70)
        logger.info(f"TOTAL CONTRIBUTIONS FETCHED: {len(self.contributions)}")
        logger.info("="*70)

    def print_summary(self):
        """Print summary statistics for each politician."""
        logger.info("")
        logger.info("="*70)
        logger.info("SUMMARY STATISTICS")
        logger.info("="*70)

        for politician_key, cycles_data in self.stats.items():
            logger.info(f"\n{politician_key}:")
            total = 0
            for cycle, stats in cycles_data.items():
                count = stats['count']
                unique = stats.get('unique_ids', 0)
                total += count

                if 'error' in stats:
                    logger.info(f"  {cycle}: ERROR - {stats['error']}")
                else:
                    logger.info(f"  {cycle}: {count} contributions ({unique} unique)")

            logger.info(f"  TOTAL: {total} contributions")

        logger.info("")

    def check_for_duplicates(self):
        """Check if contributions are duplicated across politicians."""
        logger.info("="*70)
        logger.info("CHECKING FOR DUPLICATE CONTRIBUTIONS")
        logger.info("="*70)

        # Group by contribution ID
        id_to_politicians = {}
        for contrib in self.contributions:
            contrib_id = contrib.id
            bioguide = contrib.bioguide_id

            if contrib_id not in id_to_politicians:
                id_to_politicians[contrib_id] = set()
            id_to_politicians[contrib_id].add(bioguide)

        # Find duplicates
        duplicates = {
            contrib_id: bioguides
            for contrib_id, bioguides in id_to_politicians.items()
            if len(bioguides) > 1
        }

        if duplicates:
            logger.warning(f"Found {len(duplicates)} contribution IDs shared across multiple politicians!")
            logger.warning("This could explain why they all show the same contributions.")
            logger.warning("")

            # Show first 10 examples
            for i, (contrib_id, bioguides) in enumerate(list(duplicates.items())[:10]):
                logger.warning(f"  {contrib_id}: {', '.join(sorted(bioguides))}")

            if len(duplicates) > 10:
                logger.warning(f"  ... and {len(duplicates) - 10} more duplicates")
        else:
            logger.info("✓ No duplicate contribution IDs found across politicians")

        logger.info("")

    def save_to_csv(self, filename: str = "utah_contributions_debug.csv"):
        """Save all contributions to CSV file."""
        if not self.contributions:
            logger.warning("No contributions to save")
            return

        output_file = DATA_DIR / filename
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Define CSV columns with extra debug info
        fieldnames = [
            'id', 'bioguide_id', 'recipient_name',
            'contributor_name', 'contributor_type',
            'contributor_employer', 'contributor_occupation',
            'contributor_city', 'contributor_state', 'contributor_zip',
            'amount', 'contribution_date', 'cycle',
            'source', 'last_updated'
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

        logger.info(f"✓ Saved {len(self.contributions)} contributions to {output_file}")
        logger.info("")


async def main():
    parser = argparse.ArgumentParser(
        description='Troubleshoot Utah contributions - fetch ALL contributions for 6 Utah politicians'
    )
    parser.add_argument(
        '--cycles',
        type=int,
        nargs='+',
        default=[2024],
        help='Election cycles to fetch (default: 2024). Example: --cycles 2024 2022 2020'
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        help='Maximum pages to fetch per politician/cycle (100 contributions per page). Default: unlimited'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Fetch ALL contributions with no page limit (same as not specifying --max-pages)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='utah_contributions_debug.csv',
        help='Output CSV filename (default: utah_contributions_debug.csv)'
    )

    args = parser.parse_args()

    # If --all is specified, set max_pages to None
    max_pages = None if args.all else args.max_pages

    debugger = UtahContributionsDebugger()

    # Fetch contributions
    await debugger.fetch_all_contributions(
        cycles=args.cycles,
        max_pages=max_pages
    )

    # Print summary
    debugger.print_summary()

    # Check for duplicates
    debugger.check_for_duplicates()

    # Save to CSV
    debugger.save_to_csv(filename=args.output)

    logger.info("="*70)
    logger.info("DONE! Check the CSV file for detailed contribution data.")
    logger.info("="*70)


if __name__ == "__main__":
    asyncio.run(main())
