"""
Test script to verify MongoDB connection.

Run with: uv run python scripts/test_database.py
"""

from src.database import test_connection, get_sync_database, close_sync_client
from src.config import settings


def main():
    print("=" * 50)
    print("MongoDB Connection Test")
    print("=" * 50)
    
    print(f"\n📦 Database: {settings.MONGODB_DATABASE}")
    
    # Test basic connectivity
    print("\n🔌 Testing connection...")
    try:
        if test_connection():
            print("✅ Successfully connected to MongoDB!")
        else:
            print("❌ Connection test returned unexpected result")
            return
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return
    
    # Get database and show some info
    db = get_sync_database()
    
    # List existing collections (if any)
    collections = db.list_collection_names()
    print(f"\n📁 Existing collections: {len(collections)}")
    for coll in collections:
        count = db[coll].count_documents({})
        print(f"   - {coll}: {count} documents")
    
    if not collections:
        print("   (none yet - that's expected for a new database!)")
    
    # Test a simple write and read
    print("\n🧪 Testing write/read...")
    test_collection = db["_connection_test"]
    
    # Write
    test_doc = {"test": True, "message": "Hello from Utah Watchdog!"}
    result = test_collection.insert_one(test_doc)
    print(f"   ✅ Wrote test document (id: {result.inserted_id})")
    
    # Read
    found = test_collection.find_one({"test": True})
    print(f"   ✅ Read back: {found['message']}")
    
    # Clean up
    test_collection.delete_one({"test": True})
    print("   ✅ Cleaned up test document")
    
    # Close connection
    close_sync_client()
    
    print("\n" + "=" * 50)
    print("✅ All database tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    main()