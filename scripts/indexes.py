"""
Database Indexes Module

Creates MongoDB indexes for optimal query performance.
Run this script after initial data load or schema changes.

Usage:
    # From command line (async)
    uv run python scripts/setup_indexes.py
    
    # From async Python
    from src.database.indexes import create_all_indexes_async
    await create_all_indexes_async()
    
    # From sync Python (e.g., Streamlit)
    from src.database.indexes import create_all_indexes_sync
    create_all_indexes_sync(db)
"""
import asyncio
import logging
from typing import Union

try:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
    MOTOR_AVAILABLE = True
except ImportError:
    MOTOR_AVAILABLE = False
    AsyncIOMotorDatabase = None  # Type hint only

from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.database import Database
from pymongo.errors import OperationFailure

from src.config.settings import settings

logger = logging.getLogger(__name__)


def get_database_sync() -> Database:
    """Get synchronous MongoDB database connection"""
    client = MongoClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DATABASE]


async def get_database_async() -> 'AsyncIOMotorDatabase':
    """Get async MongoDB database connection (requires motor)"""
    if not MOTOR_AVAILABLE:
        raise ImportError("motor package required for async operations. Install with: uv add motor")
    
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DATABASE]


# ============================================================================
# SYNCHRONOUS INDEX FUNCTIONS (for Streamlit, scripts, etc.)
# ============================================================================

def create_politicians_indexes_sync(db: Database):
    """Synchronous version - create indexes for politicians collection"""
    collection = db.politicians
    
    logger.info("Creating politicians indexes...")
    
    collection.create_index(
        [("bioguide_id", ASCENDING)],
        unique=True,
        name="idx_bioguide_id"
    )
    
    collection.create_index(
        [
            ("state", ASCENDING),
            ("party", ASCENDING),
            ("chamber", ASCENDING),
            ("in_office", ASCENDING)
        ],
        name="idx_state_party_chamber_office"
    )
    
    collection.create_index(
        [("in_office", ASCENDING)],
        name="idx_in_office"
    )
    
    collection.create_index(
        [("state", ASCENDING), ("in_office", ASCENDING)],
        name="idx_state_office"
    )
    
    collection.create_index(
        [("last_name", ASCENDING), ("first_name", ASCENDING)],
        name="idx_name_sort"
    )
    
    collection.create_index(
        [("full_name", TEXT), ("last_name", TEXT), ("first_name", TEXT)],
        name="idx_name_text_search"
    )
    
    collection.create_index(
        [("fec_candidate_id", ASCENDING)],
        name="idx_fec_candidate_id",
        sparse=True
    )
    
    collection.create_index(
        [("opensecrets_id", ASCENDING)],
        name="idx_opensecrets_id",
        sparse=True
    )
    
    logger.info("✅ Politicians indexes created")


def create_legislation_indexes_sync(db: Database):
    """Synchronous version - create indexes for legislation collection"""
    collection = db.legislation
    
    logger.info("Creating legislation indexes...")
    
    collection.create_index(
        [("bill_id", ASCENDING)],
        unique=True,
        name="idx_bill_id"
    )
    
    collection.create_index(
        [
            ("congress", DESCENDING),
            ("status", ASCENDING),
            ("introduced_date", DESCENDING)
        ],
        name="idx_congress_status_date"
    )
    
    collection.create_index(
        [("sponsor_bioguide_id", ASCENDING), ("introduced_date", DESCENDING)],
        name="idx_sponsor_date"
    )
    
    collection.create_index(
        [("status", ASCENDING)],
        name="idx_status"
    )
    
    collection.create_index(
        [("policy_area", ASCENDING)],
        name="idx_policy_area",
        sparse=True
    )
    
    collection.create_index(
        [("subjects", ASCENDING)],
        name="idx_subjects"
    )
    
    collection.create_index(
        [("title", TEXT), ("summary", TEXT)],
        name="idx_title_summary_text",
        weights={"title": 10, "summary": 5}
    )
    
    collection.create_index(
        [("bill_type", ASCENDING), ("introduced_date", DESCENDING)],
        name="idx_type_date"
    )
    
    logger.info("✅ Legislation indexes created")


def create_contributions_indexes_sync(db: Database):
    """Synchronous version - create indexes for contributions collection"""
    collection = db.contributions
    
    logger.info("Creating contributions indexes...")
    
    collection.create_index(
        [
            ("bioguide_id", ASCENDING),
            ("cycle", DESCENDING),
            ("contribution_date", DESCENDING)
        ],
        name="idx_politician_cycle_date"
    )
    
    collection.create_index(
        [("bioguide_id", ASCENDING), ("industry_code", ASCENDING), ("cycle", DESCENDING)],
        name="idx_politician_industry_cycle"
    )
    
    collection.create_index(
        [("bioguide_id", ASCENDING), ("contributor_employer", ASCENDING)],
        name="idx_politician_employer"
    )
    
    collection.create_index(
        [("contributor_state", ASCENDING), ("bioguide_id", ASCENDING)],
        name="idx_state_politician"
    )
    
    collection.create_index(
        [("amount", DESCENDING)],
        name="idx_amount"
    )
    
    collection.create_index(
        [("contribution_date", DESCENDING)],
        name="idx_contribution_date"
    )
    
    collection.create_index(
        [("cycle", DESCENDING)],
        name="idx_cycle"
    )
    
    logger.info("✅ Contributions indexes created")


def create_votes_indexes_sync(db: Database):
    """Synchronous version - create indexes for votes collection"""
    collection = db.votes
    
    logger.info("Creating votes indexes...")
    
    collection.create_index(
        [("vote_id", ASCENDING)],
        unique=True,
        name="idx_vote_id"
    )
    
    collection.create_index(
        [
            ("chamber", ASCENDING),
            ("congress", DESCENDING),
            ("vote_date", DESCENDING)
        ],
        name="idx_chamber_congress_date"
    )
    
    collection.create_index(
        [("bill_id", ASCENDING)],
        name="idx_bill_id",
        sparse=True
    )
    
    collection.create_index(
        [("result", ASCENDING), ("vote_date", DESCENDING)],
        name="idx_result_date"
    )
    
    collection.create_index(
        [("chamber", ASCENDING), ("congress", ASCENDING), ("roll_number", ASCENDING)],
        name="idx_chamber_congress_roll",
        unique=True
    )
    
    logger.info("✅ Votes indexes created")


def create_politician_votes_indexes_sync(db: Database):
    """Synchronous version - create indexes for politician_votes collection"""
    collection = db.politician_votes
    
    logger.info("Creating politician_votes indexes...")
    
    collection.create_index(
        [("bioguide_id", ASCENDING), ("vote_id", DESCENDING)],
        name="idx_politician_vote"
    )
    
    collection.create_index(
        [("vote_id", ASCENDING), ("position", ASCENDING)],
        name="idx_vote_position"
    )
    
    collection.create_index(
        [("position", ASCENDING)],
        name="idx_position"
    )
    
    collection.create_index(
        [("bioguide_id", ASCENDING), ("vote_id", ASCENDING)],
        unique=True,
        name="idx_unique_politician_vote"
    )
    
    logger.info("✅ Politician_votes indexes created")


def list_existing_indexes_sync(db: Database):
    """Synchronous version - list all existing indexes"""
    collections = ["politicians", "legislation", "contributions", "votes", "politician_votes"]
    
    print("\n📊 Existing Indexes:")
    print("=" * 80)
    
    for coll_name in collections:
        collection = db[coll_name]
        
        try:
            indexes = collection.index_information()
            
            print(f"\n{coll_name} ({len(indexes)} indexes):")
            for idx_name, idx_info in indexes.items():
                keys = idx_info.get("key", [])
                unique = " [UNIQUE]" if idx_info.get("unique") else ""
                sparse = " [SPARSE]" if idx_info.get("sparse") else ""
                print(f"  • {idx_name}: {keys}{unique}{sparse}")
        
        except Exception as e:
            print(f"  ⚠️  Error listing indexes: {e}")
    
    print("\n" + "=" * 80)


def drop_all_indexes_sync(db: Database, confirm: bool = False):
    """Synchronous version - drop all indexes"""
    if not confirm:
        logger.warning("⚠️  Dropping indexes requires confirm=True")
        return
    
    collections = ["politicians", "legislation", "contributions", "votes", "politician_votes"]
    
    logger.info("🗑️  Dropping all indexes...")
    
    for coll_name in collections:
        collection = db[coll_name]
        
        try:
            collection.drop_indexes()
            logger.info(f"   ✅ Dropped indexes for {coll_name}")
        
        except Exception as e:
            logger.error(f"   ❌ Error dropping indexes for {coll_name}: {e}")


def create_all_indexes_sync(db: Database = None, drop_existing: bool = False):
    """
    Synchronous version - create all database indexes.
    
    Args:
        db: MongoDB database connection (if None, creates new connection)
        drop_existing: If True, drop existing indexes first
    """
    if db is None:
        db = get_database_sync()
    
    logger.info("🔧 Creating database indexes...")
    logger.info("=" * 60)
    
    if drop_existing:
        drop_all_indexes_sync(db, confirm=True)
        logger.info("   Dropped existing indexes\n")
    
    try:
        create_politicians_indexes_sync(db)
        create_legislation_indexes_sync(db)
        create_contributions_indexes_sync(db)
        create_votes_indexes_sync(db)
        create_politician_votes_indexes_sync(db)
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ All indexes created successfully!")
        logger.info("=" * 60)
        
        list_existing_indexes_sync(db)
        
        # Document vector search config
        logger.info("\n📝 Vector search index must be created in Atlas UI:")
        logger.info("   Index name: legislation_vector_index")
        logger.info("   Field: embedding (1536 dimensions, cosine similarity)")
        logger.info("   Docs: https://www.mongodb.com/docs/atlas/atlas-vector-search/")
        
    except Exception as e:
        logger.error(f"\n❌ Error creating indexes: {e}")
        raise


# ============================================================================
# ASYNC INDEX FUNCTIONS (for FastAPI, async scripts, etc.)
# ============================================================================

    """
    Create indexes for politicians collection.
    
    Common queries:
    - Find by bioguide_id (unique lookups)
    - Filter by state, party, chamber, in_office (list views)
    - Search by name (text search)
    - Sort by last_name (alphabetical lists)
    """
    collection = db.politicians
    
    logger.info("Creating politicians indexes...")
    
    # Unique index on bioguide_id (primary key)
    await collection.create_index(
        [("bioguide_id", ASCENDING)],
        unique=True,
        name="idx_bioguide_id"
    )
    
    # Compound index for common filters (state + party + chamber + in_office)
    await collection.create_index(
        [
            ("state", ASCENDING),
            ("party", ASCENDING),
            ("chamber", ASCENDING),
            ("in_office", ASCENDING)
        ],
        name="idx_state_party_chamber_office"
    )
    
    # Index for filtering by in_office (current vs former)
    await collection.create_index(
        [("in_office", ASCENDING)],
        name="idx_in_office"
    )
    
    # Index for Utah-specific queries
    await collection.create_index(
        [("state", ASCENDING), ("in_office", ASCENDING)],
        name="idx_state_office"
    )
    
    # Index for sorting by last name
    await collection.create_index(
        [("last_name", ASCENDING), ("first_name", ASCENDING)],
        name="idx_name_sort"
    )
    
    # Text index for name search
    await collection.create_index(
        [("full_name", TEXT), ("last_name", TEXT), ("first_name", TEXT)],
        name="idx_name_text_search"
    )
    
    # Index for FEC candidate lookups
    await collection.create_index(
        [("fec_candidate_id", ASCENDING)],
        name="idx_fec_candidate_id",
        sparse=True  # Only index documents that have this field
    )
    
    # Index for OpenSecrets lookups
    await collection.create_index(
        [("opensecrets_id", ASCENDING)],
        name="idx_opensecrets_id",
        sparse=True
    )
    
    logger.info("✅ Politicians indexes created")


async def create_legislation_indexes(db: AsyncIOMotorDatabase):
    """
    Create indexes for legislation collection.
    
    Common queries:
    - Find by bill_id (unique lookups)
    - Filter by congress, status, sponsor (list views)
    - Sort by introduced_date (recent bills)
    - Search by title/summary (text search)
    - Filter by policy area/subjects
    """
    collection = db.legislation
    
    logger.info("Creating legislation indexes...")
    
    # Unique index on bill_id
    await collection.create_index(
        [("bill_id", ASCENDING)],
        unique=True,
        name="idx_bill_id"
    )
    
    # Compound index for filtering + sorting (most common query pattern)
    await collection.create_index(
        [
            ("congress", DESCENDING),
            ("status", ASCENDING),
            ("introduced_date", DESCENDING)
        ],
        name="idx_congress_status_date"
    )
    
    # Index for sponsor lookups (bills by politician)
    await collection.create_index(
        [("sponsor_bioguide_id", ASCENDING), ("introduced_date", DESCENDING)],
        name="idx_sponsor_date"
    )
    
    # Index for status filtering
    await collection.create_index(
        [("status", ASCENDING)],
        name="idx_status"
    )
    
    # Index for policy area filtering
    await collection.create_index(
        [("policy_area", ASCENDING)],
        name="idx_policy_area",
        sparse=True
    )
    
    # Index for subjects (array field)
    await collection.create_index(
        [("subjects", ASCENDING)],
        name="idx_subjects"
    )
    
    # Text index for title/summary search
    await collection.create_index(
        [("title", TEXT), ("summary", TEXT)],
        name="idx_title_summary_text",
        weights={"title": 10, "summary": 5}  # Title is more important
    )
    
    # Index for recent bills by type
    await collection.create_index(
        [("bill_type", ASCENDING), ("introduced_date", DESCENDING)],
        name="idx_type_date"
    )
    
    logger.info("✅ Legislation indexes created")


async def create_contributions_indexes(db: AsyncIOMotorDatabase):
    """
    Create indexes for contributions collection.
    
    Common queries:
    - Find by politician (aggregate contributions)
    - Filter by cycle, contributor_state
    - Group by employer, industry
    - Sort by amount, date
    """
    collection = db.contributions
    
    logger.info("Creating contributions indexes...")
    
    # Compound index for politician + cycle (most common query)
    await collection.create_index(
        [
            ("bioguide_id", ASCENDING),
            ("cycle", DESCENDING),
            ("contribution_date", DESCENDING)
        ],
        name="idx_politician_cycle_date"
    )
    
    # Index for aggregating by industry
    await collection.create_index(
        [("bioguide_id", ASCENDING), ("industry_code", ASCENDING), ("cycle", DESCENDING)],
        name="idx_politician_industry_cycle"
    )
    
    # Index for aggregating by employer
    await collection.create_index(
        [("bioguide_id", ASCENDING), ("contributor_employer", ASCENDING)],
        name="idx_politician_employer"
    )
    
    # Index for filtering by state
    await collection.create_index(
        [("contributor_state", ASCENDING), ("bioguide_id", ASCENDING)],
        name="idx_state_politician"
    )
    
    # Index for amount range queries
    await collection.create_index(
        [("amount", DESCENDING)],
        name="idx_amount"
    )
    
    # Index for date range queries
    await collection.create_index(
        [("contribution_date", DESCENDING)],
        name="idx_contribution_date"
    )
    
    # Index for cycle-based aggregations
    await collection.create_index(
        [("cycle", DESCENDING)],
        name="idx_cycle"
    )
    
    logger.info("✅ Contributions indexes created")


async def create_votes_indexes(db: AsyncIOMotorDatabase):
    """
    Create indexes for votes collection.
    
    Common queries:
    - Find by vote_id (unique lookups)
    - Filter by chamber, congress, result
    - Link to bills (bill_id)
    - Sort by vote_date (recent votes)
    """
    collection = db.votes
    
    logger.info("Creating votes indexes...")
    
    # Unique index on vote_id
    await collection.create_index(
        [("vote_id", ASCENDING)],
        unique=True,
        name="idx_vote_id"
    )
    
    # Compound index for chamber + congress + date
    await collection.create_index(
        [
            ("chamber", ASCENDING),
            ("congress", DESCENDING),
            ("vote_date", DESCENDING)
        ],
        name="idx_chamber_congress_date"
    )
    
    # Index for linking to bills
    await collection.create_index(
        [("bill_id", ASCENDING)],
        name="idx_bill_id",
        sparse=True  # Not all votes have associated bills
    )
    
    # Index for filtering by result
    await collection.create_index(
        [("result", ASCENDING), ("vote_date", DESCENDING)],
        name="idx_result_date"
    )
    
    # Index for roll call number lookups
    await collection.create_index(
        [("chamber", ASCENDING), ("congress", ASCENDING), ("roll_number", ASCENDING)],
        name="idx_chamber_congress_roll",
        unique=True
    )
    
    logger.info("✅ Votes indexes created")


async def create_politician_votes_indexes(db: AsyncIOMotorDatabase):
    """
    Create indexes for politician_votes collection.
    
    Common queries:
    - Find votes by politician (voting history)
    - Find politicians by vote_id (who voted how)
    - Filter by position (Aye/Nay)
    - Join with votes collection
    """
    collection = db.politician_votes
    
    logger.info("Creating politician_votes indexes...")
    
    # Compound index for politician voting history
    await collection.create_index(
        [("bioguide_id", ASCENDING), ("vote_id", DESCENDING)],
        name="idx_politician_vote"
    )
    
    # Compound index for vote breakdown
    await collection.create_index(
        [("vote_id", ASCENDING), ("position", ASCENDING)],
        name="idx_vote_position"
    )
    
    # Index for position filtering
    await collection.create_index(
        [("position", ASCENDING)],
        name="idx_position"
    )
    
    # Unique compound index (politician can only vote once per vote)
    await collection.create_index(
        [("bioguide_id", ASCENDING), ("vote_id", ASCENDING)],
        unique=True,
        name="idx_unique_politician_vote"
    )
    
    logger.info("✅ Politician_votes indexes created")


async def create_vector_search_index(db: AsyncIOMotorDatabase):
    """
    Create vector search index for semantic search on legislation.
    
    Note: This uses MongoDB Atlas Search, not a standard index.
    It must be created through Atlas UI or Atlas Admin API.
    This function just documents the configuration.
    """
    logger.info("📝 Vector search index configuration for legislation:")
    
    config = {
        "name": "legislation_vector_index",
        "type": "vectorSearch",
        "definition": {
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": 1536,  # OpenAI text-embedding-3-small
                    "similarity": "cosine"
                },
                {
                    "type": "filter",
                    "path": "status"
                },
                {
                    "type": "filter",
                    "path": "congress"
                },
                {
                    "type": "filter",
                    "path": "policy_area"
                }
            ]
        }
    }
    
    logger.info(f"   Create this index in Atlas UI with config: {config}")
    logger.info("   Or use Atlas Admin API to create programmatically")
    logger.info("   Docs: https://www.mongodb.com/docs/atlas/atlas-vector-search/")


async def list_existing_indexes(db: AsyncIOMotorDatabase):
    """List all existing indexes for verification"""
    
    collections = ["politicians", "legislation", "contributions", "votes", "politician_votes"]
    
    print("\n📊 Existing Indexes:")
    print("=" * 80)
    
    for coll_name in collections:
        collection = db[coll_name]
        
        try:
            indexes = await collection.index_information()
            
            print(f"\n{coll_name} ({len(indexes)} indexes):")
            for idx_name, idx_info in indexes.items():
                keys = idx_info.get("key", [])
                unique = " [UNIQUE]" if idx_info.get("unique") else ""
                sparse = " [SPARSE]" if idx_info.get("sparse") else ""
                print(f"  • {idx_name}: {keys}{unique}{sparse}")
        
        except Exception as e:
            print(f"  ⚠️  Error listing indexes: {e}")
    
    print("\n" + "=" * 80)


async def drop_all_indexes(db: AsyncIOMotorDatabase, confirm: bool = False):
    """
    Drop all indexes (except _id) for clean slate.
    
    Args:
        confirm: Must be True to actually drop indexes (safety check)
    """
    if not confirm:
        logger.warning("⚠️  Dropping indexes requires confirm=True")
        return
    
    collections = ["politicians", "legislation", "contributions", "votes", "politician_votes"]
    
    logger.info("🗑️  Dropping all indexes...")
    
    for coll_name in collections:
        collection = db[coll_name]
        
        try:
            # Drop all except _id index
            await collection.drop_indexes()
            logger.info(f"   ✅ Dropped indexes for {coll_name}")
        
        except Exception as e:
            logger.error(f"   ❌ Error dropping indexes for {coll_name}: {e}")


async def create_all_indexes_async(drop_existing: bool = False):
    """
    Async version - create all database indexes.
    
    Args:
        drop_existing: If True, drop existing indexes first
    """
    db = await get_database_async()
    
    logger.info("🔧 Creating database indexes...")
    logger.info("=" * 60)
    
    # Optional: Drop existing indexes for clean slate
    if drop_existing:
        await drop_all_indexes(db, confirm=True)
        logger.info("   Dropped existing indexes\n")
    
    # Create indexes for each collection
    try:
        await create_politicians_indexes(db)
        await create_legislation_indexes(db)
        await create_contributions_indexes(db)
        await create_votes_indexes(db)
        await create_politician_votes_indexes(db)
        
        # Document vector search config
        await create_vector_search_index(db)
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ All indexes created successfully!")
        logger.info("=" * 60)
        
        # Show what was created
        await list_existing_indexes(db)
        
    except Exception as e:
        logger.error(f"\n❌ Error creating indexes: {e}")
        raise


async def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create MongoDB indexes")
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
        "--sync",
        action="store_true",
        help="Use synchronous connection (default: async)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.sync:
        # Use synchronous version
        db = get_database_sync()
        
        if args.list:
            list_existing_indexes_sync(db)
        else:
            create_all_indexes_sync(db, drop_existing=args.drop)
    else:
        # Use async version
        db = await get_database_async()
        
        if args.list:
            await list_existing_indexes(db)
        else:
            await create_all_indexes_async(drop_existing=args.drop)


if __name__ == "__main__":
    asyncio.run(main())