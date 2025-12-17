"""
Test the research agent with semantic search queries.

Usage:
    uv run python scripts/test_agent_semantic.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.research_agent import research_agent, run_research_query
from src.agents.dependencies import get_agent_deps


async def test_queries():
    """Test the agent with semantic search queries"""
    
    print("\n" + "="*60)
    print("🤖 TESTING AGENT WITH SEMANTIC SEARCH")
    print("="*60)
    
    # Get dependencies
    deps = await get_agent_deps()
    
    # Test queries that should use semantic search
    queries = [
        "What bills are about climate change?",
        "Find legislation related to healthcare reform",
        "Show me bills about education funding",
        "Are there any bills about environmental protection?",
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'='*60}")
        print(f"Query {i}: {query}")
        print("="*60)
        
        try:
            response = await run_research_query(query, deps)
            print(f"\n{response}")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_queries())
