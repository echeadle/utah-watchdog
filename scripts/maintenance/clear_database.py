"""
Clear all data from MongoDB database.

DANGER: This will delete ALL data! Use only for development.

Usage:
    uv run python scripts/clear_database.py                    # Interactive confirmation
    uv run python scripts/clear_database.py --yes              # Skip confirmation
    uv run python scripts/clear_database.py --collection votes # Clear specific collection only
    uv run python scripts/clear_database.py --drop-indexes     # Also drop all indexes
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import get_sync_database
from src.config.settings import settings


def clear_database(
    specific_collection: str = None,
    drop_indexes: bool = False,
    skip_confirmation: bool = False
):
    """
    Clear all data from MongoDB.
    
    Args:
        specific_collection: If provided, only clear this collection
        drop_indexes: If True, also drop all indexes (except _id)
        skip_confirmation: If True, skip the confirmation prompt
    """
    db = get_sync_database()
    db_name = settings.MONGODB_DB_NAME
    
    print("🗑️  MongoDB Database Cleaner")
    print("=" * 60)
    print(f"Database: {db_name}")
    print()
    
    # Get list of collections
    collection_names = db.list_collection_names()
    
    if not collection_names:
        print("ℹ️  Database is already empty - no collections found.")
        return
    
    # Filter to specific collection if requested
    if specific_collection:
        if specific_collection in collection_names:
            collections_to_clear = [specific_collection]
            print(f"🎯 Target: {specific_collection} collection only")
        else:
            print(f"❌ Collection '{specific_collection}' not found!")
            print(f"Available collections: {', '.join(collection_names)}")
            sys.exit(1)
    else:
        collections_to_clear = collection_names
        print(f"🎯 Target: ALL collections ({len(collection_names)} total)")
    
    # Show what will be deleted
    print("\n📋 Collections to clear:")
    for coll_name in collections_to_clear:
        collection = db[coll_name]
        count = collection.count_documents({})
        indexes = list(collection.list_indexes())
        index_count = len(indexes) - 1  # Exclude _id index
        
        print(f"   • {coll_name}: {count:,} documents, {index_count} custom indexes")
    
    # Confirmation prompt
    if not skip_confirmation:
        print("\n" + "⚠️  " * 20)
        print("⚠️  WARNING: This will DELETE ALL DATA!")
        print("⚠️  " * 20)
        response = input("\nType 'DELETE' to confirm: ")
        
        if response != "DELETE":
            print("\n❌ Aborted - data preserved.")
            sys.exit(0)
    
    print("\n🧹 Clearing data...")
    print("-" * 60)
    
    total_deleted = 0
    total_indexes_dropped = 0
    
    for coll_name in collections_to_clear:
        collection = db[coll_name]
        
        # Delete all documents
        result = collection.delete_many({})
        deleted = result.deleted_count
        total_deleted += deleted
        
        print(f"   ✅ {coll_name}: deleted {deleted:,} documents")
        
        # Drop indexes if requested
        if drop_indexes:
            try:
                # Get all indexes except _id
                indexes = list(collection.list_indexes())
                indexes_to_drop = [idx['name'] for idx in indexes if idx['name'] != '_id_']
                
                for idx_name in indexes_to_drop:
                    collection.drop_index(idx_name)
                    total_indexes_dropped += 1
                
                if indexes_to_drop:
                    print(f"      🗑️  Dropped {len(indexes_to_drop)} indexes")
            except Exception as e:
                print(f"      ⚠️  Error dropping indexes: {e}")
    
    print("-" * 60)
    print(f"✅ Complete!")
    print(f"   • Total documents deleted: {total_deleted:,}")
    if drop_indexes:
        print(f"   • Total indexes dropped: {total_indexes_dropped}")
    print()
    print("💡 Tip: Run your sync scripts to repopulate data")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Clear all data from MongoDB (DESTRUCTIVE - dev only!)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive - asks for confirmation
  uv run python scripts/clear_database.py
  
  # Clear specific collection only
  uv run python scripts/clear_database.py --collection politician_votes
  
  # Skip confirmation (dangerous!)
  uv run python scripts/clear_database.py --yes
  
  # Clear data AND drop all custom indexes
  uv run python scripts/clear_database.py --drop-indexes --yes
        """
    )
    
    parser.add_argument(
        "--collection",
        "-c",
        type=str,
        help="Clear only this specific collection (default: all collections)"
    )
    
    parser.add_argument(
        "--drop-indexes",
        action="store_true",
        help="Also drop all custom indexes (keeps only _id index)"
    )
    
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt (DANGEROUS!)"
    )
    
    args = parser.parse_args()
    
    try:
        clear_database(
            specific_collection=args.collection,
            drop_indexes=args.drop_indexes,
            skip_confirmation=args.yes
        )
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
