#!/usr/bin/env python3
"""
Ensure all tracked politicians are in the database.

This script reads from data/tracked_politicians.json and ensures:
1. All tracked politicians exist in the database
2. Their identifiers are up-to-date
3. They're never accidentally deleted
4. Historical politicians are preserved

Usage:
    # Verify and sync all tracked politicians
    uv run python scripts/maintenance/ensure_tracked_politicians.py
    uv run python scripts/maintenance/ensure_tracked_politicians.py --verify-only

    # Add a new politician (interactive)
    uv run python scripts/maintenance/ensure_tracked_politicians.py --add

    # Add a new politician (non-interactive)
    uv run python scripts/maintenance/ensure_tracked_politicians.py --add \
        --bioguide-id C001114 \
        --name "John Curtis" \
        --fec-id H8UT03132 \
        --reason "Current Representative UT-03" \
        --priority high
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import logging
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_registry_path():
    """Get path to the tracked politicians registry."""
    return Path(__file__).parent.parent.parent / "data" / "tracked_politicians.json"


async def load_tracked_politicians():
    """Load the tracked politicians registry."""
    registry_path = get_registry_path()

    if not registry_path.exists():
        raise FileNotFoundError(f"Tracked politicians registry not found: {registry_path}")

    with open(registry_path, 'r') as f:
        data = json.load(f)

    return data["politicians"]


def save_tracked_politicians(politicians: list):
    """Save the tracked politicians registry."""
    registry_path = get_registry_path()

    # Load existing data to preserve metadata
    with open(registry_path, 'r') as f:
        data = json.load(f)

    # Update politicians list and timestamp
    data["politicians"] = politicians
    data["last_updated"] = datetime.now().strftime("%Y-%m-%d")

    # Write back with nice formatting
    with open(registry_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')  # Add trailing newline

    logger.info(f"✅ Saved {len(politicians)} politicians to registry")


def validate_bioguide_id(bioguide_id: str) -> bool:
    """Validate bioguide ID format (e.g., C001114)."""
    pattern = r'^[A-Z]\d{6}$'
    return bool(re.match(pattern, bioguide_id))


def prompt_for_politician():
    """Interactively prompt for politician information."""
    print("\n" + "=" * 80)
    print("ADD NEW POLITICIAN TO REGISTRY")
    print("=" * 80)
    print()

    # Bioguide ID (required)
    while True:
        bioguide_id = input("Bioguide ID (e.g., C001114): ").strip().upper()
        if not bioguide_id:
            print("❌ Bioguide ID is required")
            continue
        if not validate_bioguide_id(bioguide_id):
            print("❌ Invalid format. Should be: Letter + 6 digits (e.g., C001114)")
            continue
        break

    # Full name (required)
    while True:
        full_name = input("Full Name (e.g., John Curtis): ").strip()
        if not full_name:
            print("❌ Name is required")
            continue
        break

    # Tracking reason (required)
    while True:
        tracking_reason = input("Tracking Reason (e.g., Current Representative UT-03): ").strip()
        if not tracking_reason:
            print("❌ Tracking reason is required")
            continue
        break

    # Priority (optional, default medium)
    while True:
        priority = input("Priority (high/medium/low) [medium]: ").strip().lower()
        if not priority:
            priority = "medium"
        if priority not in ["high", "medium", "low"]:
            print("❌ Priority must be: high, medium, or low")
            continue
        break

    # Identifiers (optional)
    print("\nOptional Identifiers (press Enter to skip):")
    identifiers = {}

    fec_id = input("  FEC Candidate ID (e.g., H8UT03132): ").strip()
    if fec_id:
        identifiers["fec_candidate_id"] = fec_id

    opensecrets_id = input("  OpenSecrets ID (e.g., N00041091): ").strip()
    if opensecrets_id:
        identifiers["opensecrets_id"] = opensecrets_id

    govtrack_id = input("  GovTrack ID (e.g., 412740): ").strip()
    if govtrack_id:
        identifiers["govtrack_id"] = govtrack_id

    # Notes (optional)
    notes = input("\nNotes (optional): ").strip()

    # Build politician dict
    politician = {
        "bioguide_id": bioguide_id,
        "full_name": full_name,
        "tracking_reason": tracking_reason,
        "priority": priority
    }

    if identifiers:
        politician["identifiers"] = identifiers

    if notes:
        politician["notes"] = notes

    # Confirm
    print("\n" + "=" * 80)
    print("CONFIRM NEW POLITICIAN")
    print("=" * 80)
    print(json.dumps(politician, indent=2))
    print()

    confirm = input("Add this politician to registry? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Cancelled")
        return None

    return politician


async def add_politician_to_registry(politician_data: dict):
    """
    Add a new politician to the tracked politicians registry.

    Args:
        politician_data: Dictionary with politician info

    Returns:
        True if added, False if already exists
    """
    # Load current registry
    registry_path = get_registry_path()

    with open(registry_path, 'r') as f:
        data = json.load(f)

    politicians = data["politicians"]

    # Check if already exists
    bioguide_id = politician_data["bioguide_id"]
    existing = next((p for p in politicians if p["bioguide_id"] == bioguide_id), None)

    if existing:
        logger.warning(f"❌ Politician {bioguide_id} already exists in registry")
        logger.info(f"   Existing: {existing['full_name']}")
        logger.info(f"   Use manual edit to update")
        return False

    # Add to list
    politicians.append(politician_data)

    # Sort by bioguide_id for consistency
    politicians.sort(key=lambda p: p["bioguide_id"])

    # Save back
    save_tracked_politicians(politicians)

    logger.info(f"✅ Added {politician_data['full_name']} ({bioguide_id}) to registry")
    return True


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


async def handle_add_politician(args):
    """
    Handle adding a politician via command line args or interactively.

    Args:
        args: Parsed command line arguments
    """
    # Check if non-interactive (all required args provided)
    if args.bioguide_id and args.name and args.reason:
        # Non-interactive mode
        bioguide_id = args.bioguide_id.upper().strip()

        # Validate bioguide ID
        if not validate_bioguide_id(bioguide_id):
            logger.error("❌ Invalid bioguide ID format. Should be: Letter + 6 digits (e.g., C001114)")
            sys.exit(1)

        # Build politician data
        politician_data = {
            "bioguide_id": bioguide_id,
            "full_name": args.name.strip(),
            "tracking_reason": args.reason.strip(),
            "priority": args.priority if args.priority else "medium"
        }

        # Add identifiers if provided
        identifiers = {}
        if args.fec_id:
            identifiers["fec_candidate_id"] = args.fec_id.strip()
        if args.opensecrets_id:
            identifiers["opensecrets_id"] = args.opensecrets_id.strip()
        if args.govtrack_id:
            identifiers["govtrack_id"] = args.govtrack_id.strip()

        if identifiers:
            politician_data["identifiers"] = identifiers

        if args.notes:
            politician_data["notes"] = args.notes.strip()

        logger.info("Adding politician:")
        logger.info(json.dumps(politician_data, indent=2))

    else:
        # Interactive mode
        if args.bioguide_id or args.name or args.reason:
            logger.warning("⚠️  Some args provided but not all required ones.")
            logger.warning("   Required for non-interactive: --bioguide-id, --name, --reason")
            logger.warning("   Switching to interactive mode...\n")

        politician_data = prompt_for_politician()

        if not politician_data:
            return

    # Add to registry
    added = await add_politician_to_registry(politician_data)

    if added:
        logger.info("\n" + "=" * 80)
        logger.info("✅ Politician added to registry!")
        logger.info("=" * 80)
        logger.info("\nNext steps:")
        logger.info("  1. Run sync to add to database:")
        logger.info("     uv run python scripts/maintenance/ensure_tracked_politicians.py")
        logger.info("  2. Commit the change:")
        logger.info("     git add data/tracked_politicians.json")
        logger.info(f"     git commit -m 'Add {politician_data['full_name']} to tracked politicians'")


async def main():
    """Main execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Ensure tracked politicians are in the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sync all tracked politicians to database
  uv run python scripts/maintenance/ensure_tracked_politicians.py

  # Add a new politician (interactive)
  uv run python scripts/maintenance/ensure_tracked_politicians.py --add

  # Add a new politician (non-interactive)
  uv run python scripts/maintenance/ensure_tracked_politicians.py --add \\
      --bioguide-id M001221 \\
      --name "Blake Moore" \\
      --fec-id H0UT01133 \\
      --reason "Current Representative UT-01" \\
      --priority high
        """
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

    # Add politician arguments
    parser.add_argument(
        "--add",
        action="store_true",
        help="Add a new politician to the registry"
    )
    parser.add_argument(
        "--bioguide-id",
        type=str,
        help="Bioguide ID (e.g., C001114)"
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Full name (e.g., 'John Curtis')"
    )
    parser.add_argument(
        "--fec-id",
        type=str,
        help="FEC candidate ID (e.g., H8UT03132)"
    )
    parser.add_argument(
        "--opensecrets-id",
        type=str,
        help="OpenSecrets ID (e.g., N00041091)"
    )
    parser.add_argument(
        "--govtrack-id",
        type=str,
        help="GovTrack ID (e.g., 412740)"
    )
    parser.add_argument(
        "--reason",
        type=str,
        help="Tracking reason (e.g., 'Current Representative UT-01')"
    )
    parser.add_argument(
        "--notes",
        type=str,
        help="Additional notes"
    )

    args = parser.parse_args()

    # Handle --add mode
    if args.add:
        await handle_add_politician(args)
        return

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
