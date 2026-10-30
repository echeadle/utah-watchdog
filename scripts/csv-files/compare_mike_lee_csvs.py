#!/usr/bin/env python3
"""
Compare Mike Lee contributions between two CSV files.

This script checks if all Mike Lee contributions from utah_contributions_debug.csv
are present in mike_lee_contributions.csv (from MongoDB).

Usage:
    python scripts/csv-files/compare_mike_lee_csvs.py
"""
import csv
import logging
from pathlib import Path
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"


def load_csv_contributions(filepath: Path, bioguide_filter: str = None):
    """
    Load contributions from CSV file.

    Args:
        filepath: Path to CSV file
        bioguide_filter: Optional bioguide_id to filter by

    Returns:
        dict: {contribution_id: row_dict}
    """
    contributions = {}

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Filter by bioguide_id if specified
            if bioguide_filter and row.get('bioguide_id') != bioguide_filter:
                continue

            contrib_id = row['id']
            contributions[contrib_id] = row

    return contributions


def compare_contributions():
    """Compare Mike Lee contributions between the two CSV files."""

    logger.info("="*70)
    logger.info("COMPARING MIKE LEE CONTRIBUTIONS")
    logger.info("="*70)

    # File paths
    mongodb_file = DATA_DIR / "mike_lee_contributions.csv"
    debug_file = DATA_DIR / "utah_contributions_debug.csv"

    # Check if files exist
    if not mongodb_file.exists():
        logger.error(f"MongoDB export file not found: {mongodb_file}")
        return

    if not debug_file.exists():
        logger.error(f"Debug file not found: {debug_file}")
        return

    logger.info(f"MongoDB export: {mongodb_file}")
    logger.info(f"Debug file: {debug_file}")
    logger.info("")

    # Load contributions from both files
    logger.info("Loading MongoDB contributions...")
    mongodb_contribs = load_csv_contributions(mongodb_file)
    logger.info(f"  Loaded {len(mongodb_contribs)} contributions from MongoDB export")

    logger.info("Loading debug contributions for Mike Lee...")
    debug_contribs = load_csv_contributions(debug_file, bioguide_filter="L000577")
    logger.info(f"  Loaded {len(debug_contribs)} Mike Lee contributions from debug file")

    logger.info("")
    logger.info("="*70)
    logger.info("COMPARISON RESULTS")
    logger.info("="*70)

    # Find contributions in debug file but not in MongoDB
    mongodb_ids = set(mongodb_contribs.keys())
    debug_ids = set(debug_contribs.keys())

    missing_in_mongodb = debug_ids - mongodb_ids
    extra_in_mongodb = mongodb_ids - debug_ids
    common_ids = debug_ids & mongodb_ids

    logger.info(f"\nContribution IDs in both files: {len(common_ids)}")
    logger.info(f"Contribution IDs only in debug file: {len(missing_in_mongodb)}")
    logger.info(f"Contribution IDs only in MongoDB: {len(extra_in_mongodb)}")

    # Report missing contributions
    if missing_in_mongodb:
        logger.warning(f"\n⚠️  Found {len(missing_in_mongodb)} contributions in debug file that are NOT in MongoDB!")
        logger.warning("These contributions may not have been ingested:")

        # Show first 20 examples
        for i, contrib_id in enumerate(sorted(list(missing_in_mongodb))[:20]):
            row = debug_contribs[contrib_id]
            logger.warning(
                f"  {i+1}. {contrib_id}: ${row['amount']} from {row['contributor_name']} "
                f"on {row['contribution_date']} (cycle: {row['cycle']})"
            )

        if len(missing_in_mongodb) > 20:
            logger.warning(f"  ... and {len(missing_in_mongodb) - 20} more")

        # Analyze by cycle
        logger.warning("\nMissing contributions by cycle:")
        missing_by_cycle = defaultdict(int)
        for contrib_id in missing_in_mongodb:
            cycle = debug_contribs[contrib_id]['cycle']
            missing_by_cycle[cycle] += 1

        for cycle in sorted(missing_by_cycle.keys(), reverse=True):
            logger.warning(f"  {cycle}: {missing_by_cycle[cycle]} missing")

        # Analyze by date
        logger.warning("\nMissing contributions by contribution date (first 10):")
        missing_by_date = defaultdict(int)
        for contrib_id in missing_in_mongodb:
            date = debug_contribs[contrib_id]['contribution_date']
            missing_by_date[date] += 1

        for date in sorted(missing_by_date.keys(), reverse=True)[:10]:
            logger.warning(f"  {date}: {missing_by_date[date]} missing")
    else:
        logger.info("\n✓ All Mike Lee contributions from debug file ARE in MongoDB!")
        logger.info("  All contributions have been successfully ingested.")

    # Info about extra contributions in MongoDB
    if extra_in_mongodb:
        logger.info(f"\nℹ️  MongoDB has {len(extra_in_mongodb)} additional contributions not in the debug file")
        logger.info("  This is expected - MongoDB likely contains contributions from other fetch cycles")

        # Show some examples
        logger.info("\nExamples of MongoDB-only contributions (first 10):")
        for i, contrib_id in enumerate(sorted(list(extra_in_mongodb))[:10]):
            row = mongodb_contribs[contrib_id]
            logger.info(
                f"  {i+1}. {contrib_id}: ${row['amount']} from {row['contributor_name']} "
                f"on {row['contribution_date']} (cycle: {row['cycle']})"
            )

    # Summary
    logger.info("")
    logger.info("="*70)
    logger.info("SUMMARY")
    logger.info("="*70)
    logger.info(f"Debug file Mike Lee contributions: {len(debug_ids)}")
    logger.info(f"MongoDB file contributions: {len(mongodb_ids)}")
    logger.info(f"Contributions in both files: {len(common_ids)}")
    logger.info(f"Missing in MongoDB: {len(missing_in_mongodb)}")
    logger.info(f"Extra in MongoDB: {len(extra_in_mongodb)}")

    if len(missing_in_mongodb) == 0:
        logger.info("\n✅ RESULT: All debug contributions are in MongoDB!")
    else:
        logger.warning(f"\n❌ RESULT: {len(missing_in_mongodb)} debug contributions are missing from MongoDB")

    logger.info("="*70)


if __name__ == "__main__":
    compare_contributions()
