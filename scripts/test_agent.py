"""
Test the research agent with sample queries.

Usage:
    uv run python scripts/test_agent.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.research_agent import research_agent, run_research_query
from src.agents.dependencies import get_agent_deps


async def test_queries():
    """Test the agent with various queries"""
    
    print("\n" + "="*60)
    print("🤖 TESTING RESEARCH AGENT")
    print("="*60)
    
    # Get dependencies
    deps = await get_agent_deps()
    
    # Test queries
    queries = [
        "Who are the senators from Utah?",
        "What bills has Mike Lee sponsored?",
        "Search for bills about infrastructure",
        "Tell me about HR 1491 in the 119th Congress",
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
