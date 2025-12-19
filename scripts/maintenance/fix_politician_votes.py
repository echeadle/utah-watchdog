"""
Fix Politician Votes with Null Bioguide IDs

This script removes politician_vote records that have null bioguide_ids.
These are invalid records - every politician vote must be linked to a politician.

Usage:
    uv run python scripts/fix_politician_votes.py --dry-run  # See what would be deleted
    uv run python scripts/fix_politician_votes.py            # Actually delete
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import MongoClient
from src.config.settings import settings


def analyze_null_bioguides(db):
    """Find politician_votes with null bioguide_id"""
    
    # Find votes with null bioguide_id
    null_votes = list(db.politician_votes.find({"bioguide_id": None}))
    
    print(f"\n📊 Analysis:")
    print(f"   Total politician_votes: {db.politician_votes.count_documents({})}")
    print(f"   Records with null bioguide_id: {len(null_votes)}")
    
    if null_votes:
        # Group by vote_id to see which votes are affected
        vote_ids = {}
        for vote in null_votes:
            vote_id = vote.get("vote_id", "unknown")
            vote_ids[vote_id] = vote_ids.get(vote_id, 0) + 1
        
        print(f"\n   Affected votes: {len(vote_ids)}")
        print(f"   Top affected vote_ids:")
        for vote_id, count in sorted(vote_ids.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"      - {vote_id}: {count} null bioguide_id records")
    
    return null_votes


def delete_null_bioguides(db, dry_run=True):
    """Delete politician_votes with null bioguide_id"""
    
    null_votes = list(db.politician_votes.find({"bioguide_id": None}))
    
    if not null_votes:
        print("\n✅ No politician_votes with null bioguide_id")
        return 0
    
    print(f"\n🗑️  Found {len(null_votes)} politician_votes with null bioguide_id")
    
    if dry_run:
        print("   [DRY RUN] Would delete these records:")
        for vote in null_votes[:10]:
            vote_id = vote.get("vote_id", "unknown")
            position = vote.get("position", "?")
            print(f"      - vote_id={vote_id}, position={position}")
        if len(null_votes) > 10:
            print(f"      ... and {len(null_votes) - 10} more")
        return 0
    else:
        result = db.politician_votes.delete_many({"bioguide_id": None})
        print(f"   ✅ Deleted {result.deleted_count} records with null bioguide_id")
        return result.deleted_count


def check_for_duplicates(db):
    """Check if there are other duplicate (bioguide_id, vote_id) pairs"""
    
    duplicates = list(db.politician_votes.aggregate([
        {
            "$group": {
                "_id": {
                    "bioguide_id": "$bioguide_id",
                    "vote_id": "$vote_id"
                },
                "count": {"$sum": 1},
                "ids": {"$push": "$_id"}
            }
        },
        {
            "$match": {
                "count": {"$gt": 1},
                "_id.bioguide_id": {"$ne": None}  # Exclude null bioguide_ids
            }
        }
    ]))
    
    if duplicates:
        print(f"\n⚠️  Found {len(duplicates)} other duplicate (bioguide_id, vote_id) pairs:")
        for dup in duplicates[:5]:
            bioguide = dup["_id"]["bioguide_id"]
            vote_id = dup["_id"]["vote_id"]
            count = dup["count"]
            print(f"      - {bioguide} on {vote_id}: {count} records")
        if len(duplicates) > 5:
            print(f"      ... and {len(duplicates) - 5} more")
    else:
        print(f"\n✅ No other duplicates found (excluding null bioguide_ids)")
    
    return duplicates


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix politician_votes with null bioguide_ids")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    
    args = parser.parse_args()
    
    print("🔧 Fix Politician Votes - Null Bioguide IDs")
    print("=" * 60)
    
    # Connect to database
    client = MongoClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    
    # Analyze the problem
    print("\n🔍 Analyzing politician_votes collection...")
    null_votes = analyze_null_bioguides(db)
    
    if not null_votes:
        print("\n✅ No politician_votes with null bioguide_id found!")
        print("\nYou can now run: uv run python scripts/setup_indexes.py --drop")
        return
    
    # Check for other duplicates
    check_for_duplicates(db)
    
    # Delete null bioguide records
    print("\n" + "=" * 60)
    
    if args.dry_run:
        print("🔍 DRY RUN - No changes will be made")
        print("   Remove --dry-run flag to actually delete records")
    else:
        print("⚠️  DELETING INVALID DATA")
    
    print("=" * 60)
    
    deleted = delete_null_bioguides(db, dry_run=args.dry_run)
    
    # Summary
    print("\n" + "=" * 60)
    if args.dry_run:
        print("✅ DRY RUN COMPLETE")
        print(f"   Would delete: {len(null_votes)} records with null bioguide_id")
        print("\nRun without --dry-run to actually delete")
    else:
        print("✅ CLEANUP COMPLETE")
        print(f"   Deleted: {deleted} records with null bioguide_id")
        print("\nYou can now run: uv run python scripts/setup_indexes.py --drop")
    print("=" * 60)


if __name__ == "__main__":
    main()
