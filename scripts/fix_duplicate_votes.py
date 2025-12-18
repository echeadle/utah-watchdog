"""
Fix Duplicate Votes

This script finds and removes duplicate vote records before creating indexes.
The unique index on (chamber, congress, roll_number) requires these to be unique.

Usage:
    uv run python scripts/fix_duplicate_votes.py --dry-run  # See what would be deleted
    uv run python scripts/fix_duplicate_votes.py            # Actually delete duplicates
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import MongoClient
from src.config.settings import settings


def find_duplicate_votes(db):
    """Find votes with duplicate (chamber, congress, roll_number)"""
    
    # Find votes with null roll_number
    null_roll_votes = list(db.votes.find({"roll_number": None}))
    
    print(f"\n📊 Analysis:")
    print(f"   Votes with null roll_number: {len(null_roll_votes)}")
    
    # Find duplicate (chamber, congress, roll_number) combinations
    duplicates = list(db.votes.aggregate([
        {
            "$group": {
                "_id": {
                    "chamber": "$chamber",
                    "congress": "$congress",
                    "roll_number": "$roll_number"
                },
                "count": {"$sum": 1},
                "ids": {"$push": "$_id"},
                "vote_ids": {"$push": "$vote_id"}
            }
        },
        {
            "$match": {
                "count": {"$gt": 1}
            }
        }
    ]))
    
    print(f"   Duplicate vote groups: {len(duplicates)}")
    
    return null_roll_votes, duplicates


def show_duplicates(duplicates):
    """Display duplicate vote details"""
    
    if not duplicates:
        print("\n✅ No duplicates found!")
        return
    
    print(f"\n⚠️  Found {len(duplicates)} groups of duplicate votes:")
    print("=" * 80)
    
    for dup in duplicates:
        group = dup["_id"]
        chamber = group.get("chamber", "unknown")
        congress = group.get("congress", "?")
        roll_num = group.get("roll_number", "NULL")
        count = dup["count"]
        
        print(f"\n   {chamber.upper()} - {congress}th Congress - Roll #{roll_num}")
        print(f"   Duplicates: {count} records")
        print(f"   Vote IDs: {dup['vote_ids'][:3]}{'...' if len(dup['vote_ids']) > 3 else ''}")


def fix_null_roll_numbers(db, dry_run=True):
    """Delete votes with null roll_number"""
    
    null_votes = list(db.votes.find({"roll_number": None}))
    
    if not null_votes:
        print("\n✅ No votes with null roll_number")
        return 0
    
    print(f"\n🗑️  Found {len(null_votes)} votes with null roll_number")
    
    if dry_run:
        print("   [DRY RUN] Would delete these votes:")
        for vote in null_votes[:5]:
            print(f"      - {vote.get('vote_id', 'unknown')} ({vote.get('chamber', '?')})")
        if len(null_votes) > 5:
            print(f"      ... and {len(null_votes) - 5} more")
        return 0
    else:
        result = db.votes.delete_many({"roll_number": None})
        print(f"   ✅ Deleted {result.deleted_count} votes with null roll_number")
        return result.deleted_count


def keep_latest_duplicate(db, duplicates, dry_run=True):
    """For each duplicate group, keep the most recent and delete others"""
    
    total_deleted = 0
    
    for dup in duplicates:
        group = dup["_id"]
        ids = dup["ids"]
        
        if len(ids) <= 1:
            continue
        
        # Get full documents to find most recent
        docs = list(db.votes.find({"_id": {"$in": ids}}))
        
        # Skip if documents were already deleted (e.g., null roll_number cleanup)
        if not docs:
            continue
        
        # If only one document left, no need to delete
        if len(docs) == 1:
            continue
        
        # Sort by last_updated or vote_date
        docs_sorted = sorted(
            docs,
            key=lambda x: x.get("last_updated") or x.get("vote_date") or "",
            reverse=True
        )
        
        # Keep first (most recent), delete rest
        keep_id = docs_sorted[0]["_id"]
        delete_ids = [d["_id"] for d in docs_sorted[1:]]
        
        chamber = group.get("chamber", "?")
        congress = group.get("congress", "?")
        roll_num = group.get("roll_number", "?")
        
        if dry_run:
            print(f"\n   {chamber} {congress}-{roll_num}:")
            print(f"      Keep: {docs_sorted[0].get('vote_id')}")
            print(f"      Delete: {len(delete_ids)} duplicates")
        else:
            result = db.votes.delete_many({"_id": {"$in": delete_ids}})
            total_deleted += result.deleted_count
            print(f"   ✅ {chamber} {congress}-{roll_num}: Deleted {result.deleted_count} duplicates")
    
    return total_deleted


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix duplicate votes before creating indexes")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    
    args = parser.parse_args()
    
    print("🔧 Fix Duplicate Votes")
    print("=" * 60)
    
    # Connect to database
    client = MongoClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    
    # Find duplicates
    print("\n🔍 Searching for duplicate votes...")
    null_votes, duplicates = find_duplicate_votes(db)
    
    # Show what we found
    show_duplicates(duplicates)
    
    if not null_votes and not duplicates:
        print("\n✅ No duplicates found! Database is clean.")
        print("\nYou can now run: uv run python scripts/setup_indexes.py --drop")
        return
    
    # Fix the issues
    print("\n" + "=" * 60)
    
    if args.dry_run:
        print("🔍 DRY RUN - No changes will be made")
        print("   Remove --dry-run flag to actually delete duplicates")
    else:
        print("⚠️  DELETING DUPLICATE DATA")
    
    print("=" * 60)
    
    # Fix null roll numbers first
    deleted_null = fix_null_roll_numbers(db, dry_run=args.dry_run)
    
    # Fix duplicate groups
    deleted_dupes = 0
    if duplicates:
        print(f"\n🗑️  Processing {len(duplicates)} duplicate groups...")
        deleted_dupes = keep_latest_duplicate(db, duplicates, dry_run=args.dry_run)
    
    # Summary
    print("\n" + "=" * 60)
    if args.dry_run:
        print("✅ DRY RUN COMPLETE")
        print(f"   Would delete: {deleted_null} null roll_number votes")
        print(f"   Would delete: {len(duplicates)} duplicate vote groups")
        print("\nRun without --dry-run to actually delete duplicates")
    else:
        print("✅ CLEANUP COMPLETE")
        print(f"   Deleted: {deleted_null} null roll_number votes")
        print(f"   Deleted: {deleted_dupes} duplicate votes")
        print("\nYou can now run: uv run python scripts/setup_indexes.py --drop")
    print("=" * 60)


if __name__ == "__main__":
    main()
