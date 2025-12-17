"""
Test the research agent with campaign finance queries.

Usage:
    uv run python scripts/test_agent_with_finance.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.research_agent import research_agent, run_research_query
from src.agents.dependencies import get_agent_deps


async def test_queries():
    """Test the agent with finance queries"""
    
    print("\n" + "="*60)
    print("💰 TESTING AGENT WITH CAMPAIGN FINANCE")
    print("="*60)
    
    # Get dependencies
    deps = await get_agent_deps()
    
    # Test queries
    queries = [
        "Who are the top donors contributing to politicians in our database?",
        "Show me contributions from Applied Materials employees",
        "What contributions came from California?",
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
