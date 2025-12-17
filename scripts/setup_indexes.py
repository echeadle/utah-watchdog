"""
Setup Database Indexes

Run this script to create all MongoDB indexes for optimal query performance.

Usage:
    # Create all indexes (synchronous - default)
    uv run python scripts/setup_indexes.py
    
    # Drop existing and recreate
    uv run python scripts/setup_indexes.py --drop
    
    # Just list existing indexes
    uv run python scripts/setup_indexes.py --list
    
    # Use async version (requires motor package)
    uv run python scripts/setup_indexes.py --async
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.indexes import (
    create_all_indexes_sync,
    create_all_indexes_async,
    list_existing_indexes_sync,
    get_database_sync,
    get_database_async
)


async def main_async(args):
    """Async version of main"""
    db = await get_database_async()
    
    if args.list:
        from src.database.indexes import list_existing_indexes
        await list_existing_indexes(db)
    else:
        await create_all_indexes_async(drop_existing=args.drop)


def main_sync(args):
    """Synchronous version of main"""
    db = get_database_sync()
    
    if args.list:
        list_existing_indexes_sync(db)
    else:
        create_all_indexes_sync(db, drop_existing=args.drop)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create MongoDB indexes for Utah Watchdog"
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing indexes before creating new ones"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List existing indexes only (don't create)"
    )
    parser.add_argument(
        "--async",
        dest="use_async",
        action="store_true",
        help="Use async version (requires motor package)"
    )
    
    args = parser.parse_args()
    
    print("🔧 Utah Watchdog - Database Index Setup")
    print("=" * 60)
    print()
    
    if args.list:
        print("📋 Listing existing indexes...")
    else:
        print("⚙️  Creating database indexes...")
        if args.drop:
            print("⚠️  Will drop existing indexes first!")
    
    print()
    
    try:
        if args.use_async:
            print("Using async connection (motor)...")
            asyncio.run(main_async(args))
        else:
            print("Using synchronous connection (pymongo)...")
            main_sync(args)
        
        print()
        print("✅ Index setup complete!")
        print()
        print("💡 Tips:")
        print("   • Indexes are now optimized for common queries")
        print("   • Vector search index must be created in Atlas UI")
        print("   • Run --list to verify indexes were created")
        print("   • Queries on indexed fields will be much faster")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()