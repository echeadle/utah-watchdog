"""
Fix database indexes - drop old conflicting indexes.

Run with: uv run python scripts/fix_indexes.py
"""

from src.database import get_sync_database, close_sync_client


def main():
    print("Fixing database indexes...")
    
    db = get_sync_database()
    politician_votes_coll = db["politician_votes"]
    
    # List current indexes
    print("\nCurrent indexes:")
    for index in politician_votes_coll.list_indexes():
        print(f"   - {index['name']}: {index['key']}")
    
    # Drop all indexes except _id
    print("\nDropping non-_id indexes...")
    politician_votes_coll.drop_indexes()
    print("✅ Dropped indexes")
    
    # Also clear the collection since data might be inconsistent
    print("\nClearing politician_votes collection...")
    result = politician_votes_coll.delete_many({})
    print(f"✅ Deleted {result.deleted_count} documents")
    
    # List indexes again
    print("\nRemaining indexes:")
    for index in politician_votes_coll.list_indexes():
        print(f"   - {index['name']}: {index['key']}")
    
    close_sync_client()
    print("\n✅ Done! Now run fetch_votes.py again.")


if __name__ == "__main__":
    main()