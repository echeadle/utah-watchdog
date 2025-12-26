#!/usr/bin/env python3
"""
Ensure all tracked politicians are in the database.

This script reads from data/tracked_politicians.json and ensures:
1. All tracked politicians exist in the database
2. Their identifiers are up-to-date
3. They're never accidentally deleted
4. Historical politicians are preserved

Usage:
    uv run python scripts/maintenance/ensure_tracked_politicians.py
    uv run python scripts/maintenance/ensure_tracked_politicians.py --verify-only
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def load_tracked_politicians():
    """Load the tracked politicians registry."""
    registry_path = Path(__file__).parent.parent.parent / "data" / "tracked_politicians.json"

    if not registry_path.exists():
        raise FileNotFoundError(f"Tracked politicians registry not found: {registry_path}")

    with open(registry_path, 'r') as f:
        data = json.load(f)

    return data["politicians"]


async def ensure_politician_exists(db, tracked_pol: dict, verify_only: bool = False):
    """
    Ensure a tracked politician exists in the database.

    Args:
        db: MongoDB database
        tracked_pol: Politician data from registry
        verify_only: If True, only report issues without fixing

    Returns:
        Tuple of (exists, needs_update, action_taken)
    """
    bioguide_id = tracked_pol["bioguide_id"]

    # Check if politician exists
    existing = await db.politicians.find_one({"bioguide_id": bioguide_id})

    if not existing:
        logger.warning(f"❌ {tracked_pol['full_name']} ({bioguide_id}) NOT in database")

        if verify_only:
            return False, True, "would_create"

        # Create minimal record - will be filled in by ingesters
        new_politician = {
            "bioguide_id": bioguide_id,
            "full_name": tracked_pol["full_name"],
            "first_name": tracked_pol["full_name"].split()[-1],  # Simple split
            "last_name": tracked_pol["full_name"].split()[0],
            "party": "?",  # Unknown, will be filled by ingester
            "state": "UT",
            "chamber": None,
            "district": None,
            "in_office": False,  # Will be updated by ingester
            "identifiers": tracked_pol.get("identifiers", {}),
            "tracked": True,  # Mark as manually tracked
            "tracking_reason": tracked_pol.get("tracking_reason"),
            "priority": tracked_pol.get("priority", "medium"),
            "last_updated": datetime.utcnow()
        }

        await db.politicians.insert_one(new_politician)
        logger.info(f"✅ Created record for {tracked_pol['full_name']}")
        return False, True, "created"

    # Check if identifiers need updating
    existing_ids = existing.get("identifiers", {})
    tracked_ids = tracked_pol.get("identifiers", {})

    needs_update = False
    updates = {}

    # Update identifiers if new ones are available
    for id_type, id_value in tracked_ids.items():
        if id_type not in existing_ids or existing_ids[id_type] != id_value:
            needs_update = True
            if "identifiers" not in updates:
                updates["identifiers"] = existing_ids.copy()
            updates["identifiers"][id_type] = id_value

    # Always mark as tracked
    if not existing.get("tracked"):
        needs_update = True
        updates["tracked"] = True
        updates["tracking_reason"] = tracked_pol.get("tracking_reason")
        updates["priority"] = tracked_pol.get("priority", "medium")

    if needs_update:
        if verify_only:
            logger.warning(f"⚠️  {tracked_pol['full_name']} ({bioguide_id}) needs identifier updates")
            return True, True, "would_update"

        updates["last_updated"] = datetime.utcnow()
        await db.politicians.update_one(
            {"bioguide_id": bioguide_id},
            {"$set": updates}
        )
        logger.info(f"📝 Updated identifiers for {tracked_pol['full_name']}")
        return True, True, "updated"

    logger.info(f"✅ {tracked_pol['full_name']} ({bioguide_id}) OK")
    return True, False, "ok"


async def main():
    """Main execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Ensure tracked politicians are in the database"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify, don't make changes"
    )
    parser.add_argument(
        "--priority",
        choices=["high", "medium", "low"],
        help="Only process politicians with this priority"
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("TRACKED POLITICIANS VERIFICATION")
    logger.info("=" * 80)

    # Load registry
    logger.info("Loading tracked politicians registry...")
    tracked_politicians = await load_tracked_politicians()
    logger.info(f"Found {len(tracked_politicians)} tracked politicians")

    # Filter by priority if specified
    if args.priority:
        tracked_politicians = [
            p for p in tracked_politicians
            if p.get("priority") == args.priority
        ]
        logger.info(f"Filtered to {len(tracked_politicians)} with priority={args.priority}")

    # Connect to database
    logger.info("Connecting to database...")
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]

    # Process each politician
    stats = {
        "exists": 0,
        "created": 0,
        "updated": 0,
        "would_create": 0,
        "would_update": 0,
        "ok": 0
    }

    for tracked_pol in tracked_politicians:
        exists, needs_update, action = await ensure_politician_exists(
            db,
            tracked_pol,
            verify_only=args.verify_only
        )

        stats[action] += 1

    # Close connection
    client.close()

    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)

    if args.verify_only:
        logger.info(f"Already in database: {stats['ok'] + stats['would_update']}")
        logger.info(f"Would create: {stats['would_create']}")
        logger.info(f"Would update: {stats['would_update']}")
        logger.info(f"Up to date: {stats['ok']}")

        if stats['would_create'] > 0 or stats['would_update'] > 0:
            logger.info("\n⚠️  Run without --verify-only to apply changes")
            sys.exit(1)
    else:
        logger.info(f"Already existed: {stats['ok'] + stats['updated']}")
        logger.info(f"Created: {stats['created']}")
        logger.info(f"Updated: {stats['updated']}")
        logger.info(f"No changes needed: {stats['ok']}")

        if stats['created'] > 0 or stats['updated'] > 0:
            logger.info("\n✅ All tracked politicians are now in database")
        else:
            logger.info("\n✅ All tracked politicians were already up-to-date")

    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
