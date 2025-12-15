"""
Fix the politician_votes collection index.

This script:
1. Drops the incorrect index (vote_id + state + last_name)
2. Creates the correct unique index (vote_id + bioguide_id)
3. Cleans up any existing data that might cause issues

Usage:
    uv run python scripts/fix_politician_votes_index.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import get_sync_database


def fix_indexes():
    """Fix the politician_votes collection indexes."""
    print("🔧 Fixing politician_votes collection indexes...")
    print("=" * 60)
    
    db = get_sync_database()
    collection = db.politician_votes
    
    # Step 1: Show current indexes
    print("\n📋 Current indexes:")
    indexes = list(collection.list_indexes())
    for idx in indexes:
        print(f"   • {idx['name']}: {idx.get('key', {})}")
    
    # Step 2: Drop the incorrect index if it exists
    print("\n🗑️  Dropping incorrect indexes...")
    try:
        # This is the problematic index
        collection.drop_index("vote_id_1_state_1_last_name_1")
        print("   ✅ Dropped: vote_id_1_state_1_last_name_1")
    except Exception as e:
        if "index not found" in str(e).lower():
            print("   ℹ️  Index vote_id_1_state_1_last_name_1 doesn't exist (already dropped?)")
        else:
            print(f"   ⚠️  Error dropping index: {e}")
    
    # Step 3: Find and clean up records with null bioguide_id
    print("\n🔍 Checking for records with null bioguide_id...")
    null_bioguide_count = collection.count_documents({"bioguide_id": None})
    print(f"   Found {null_bioguide_count} records with null bioguide_id")
    
    if null_bioguide_count > 0:
        print("\n🧹 Cleaning up records with null bioguide_id...")
        result = collection.delete_many({"bioguide_id": None})
        print(f"   ✅ Deleted {result.deleted_count} records with null bioguide_id")
    
    # Optional: Clear ALL existing data (uncomment if you want a fresh start)
    # print("\n🧹 Clearing ALL existing data...")
    # result = collection.delete_many({})
    # print(f"   Deleted {result.deleted_count} total documents")
    
    # Step 4: Create the correct unique index
    print("\n✨ Creating correct unique index...")
    try:
        collection.create_index(
            [("vote_id", 1), ("bioguide_id", 1)],
            unique=True,
            name="vote_id_bioguide_id_unique"
        )
        print("   ✅ Created: vote_id_bioguide_id_unique (unique compound index)")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("   ℹ️  Index already exists")
        else:
            print(f"   ❌ Error creating index: {e}")
            raise
    
    # Step 5: Show final indexes
    print("\n📋 Final indexes:")
    indexes = list(collection.list_indexes())
    for idx in indexes:
        unique = " (unique)" if idx.get('unique', False) else ""
        print(f"   • {idx['name']}: {idx.get('key', {})}{unique}")
    
    print("\n" + "=" * 60)
    print("✅ Index fix complete!")
    print("\nYou can now run: uv run python scripts/sync_votes.py")


def main():
    try:
        fix_indexes()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
