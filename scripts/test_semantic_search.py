"""
Test semantic search on legislation.

Usage:
    uv run python scripts/test_semantic_search.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.tools.legislation import semantic_search_legislation


class MockContext:
    """Mock context for testing"""
    def __init__(self, db):
        self.deps = MockDeps(db)


class MockDeps:
    """Mock dependencies"""
    def __init__(self, db):
        self.db = db


async def test_semantic_search():
    """Test semantic search with various queries"""
    from motor.motor_asyncio import AsyncIOMotorClient
    from src.config.settings import settings
    
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    ctx = MockContext(db)
    
    queries = [
        "healthcare and medical policy",
        "environmental protection",
        "infrastructure and transportation",
        "education funding"
    ]
    
    print("\n" + "="*60)
    print("🔍 TESTING SEMANTIC SEARCH")
    print("="*60)
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print("="*60)
        
        try:
            results = await semantic_search_legislation(query, limit=3, ctx=ctx)
            
            if results:
                print(f"\n✅ Found {len(results)} relevant bills:")
                for i, bill in enumerate(results, 1):
                    print(f"\n{i}. {bill['title'][:80]}...")
                    print(f"   Bill ID: {bill['bill_id']}")
                    print(f"   Relevance: {bill['relevance_score']}")
                    print(f"   Status: {bill['status']}")
            else:
                print("❌ No results found")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETE")
    print("="*60)
    
    client.close()


if __name__ == "__main__":
    asyncio.run(test_semantic_search())

