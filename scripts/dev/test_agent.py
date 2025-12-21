"""
Test script for the research agent.

This script tests all agent tools with real queries to verify everything works
before deploying to the Streamlit UI.

Usage:
    uv run python test_agent.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.research_agent import research_agent
from src.agents.dependencies import get_agent_deps


# ============================================================================
# Test Queries
# ============================================================================

TEST_QUERIES = [
    # Politician lookups
    {
        "category": "Politician Lookup",
        "query": "Who is Mike Lee?",
        "expected": "Should find Mike Lee (R-UT), Senator"
    },
    {
        "category": "Politician Lookup",
        "query": "Who is Terri Sewell?",
        "expected": "Should find Terri A. Sewell (D-AL), Representative"
    },
    {
        "category": "Politician Lookup",
        "query": "Show me politicians from Utah",
        "expected": "Should list Utah delegation"
    },
    {
        "category": "Politician Lookup",
        "query": "Find Republican senators",
        "expected": "Should list Republican senators"
    },
    
    # Bill searches - keyword
    {
        "category": "Bill Search (Keyword)",
        "query": "Find HR 6787",
        "expected": "Should find specific bill by number"
    },
    {
        "category": "Bill Search (Keyword)",
        "query": "Search for HR. 1491",
        "expected": "Should handle bill number with period"
    },
    {
        "category": "Bill Search (Keyword)",
        "query": "Find bills about infrastructure",
        "expected": "Should find infrastructure-related bills"
    },
    
    # Bill searches - semantic
    {
        "category": "Bill Search (Semantic)",
        "query": "What bills are about climate change?",
        "expected": "Should use semantic search for topic"
    },
    {
        "category": "Bill Search (Semantic)",
        "query": "Show me healthcare legislation",
        "expected": "Should find healthcare-related bills"
    },
    
    # Sponsored bills
    {
        "category": "Sponsored Bills",
        "query": "What bills has Mike Lee sponsored?",
        "expected": "Should show Mike Lee's sponsored bills"
    },
    {
        "category": "Sponsored Bills",
        "query": "Show me bills sponsored by Eric Crawford",
        "expected": "Should find bills or say no data if politician not found"
    },
    
    # Campaign finance
    {
        "category": "Campaign Finance",
        "query": "Who is funding Mike Lee?",
        "expected": "Should show contribution data"
    },
    {
        "category": "Campaign Finance",
        "query": "Show me contributions from California",
        "expected": "Should filter by state"
    },
    {
        "category": "Campaign Finance",
        "query": "What are the top employers donating to Mike Lee?",
        "expected": "Should show employer breakdown"
    },
    {
        "category": "Campaign Finance",
        "query": "Find contributions over $1000",
        "expected": "Should filter by amount"
    },
    
    # Votes
    {
        "category": "Votes",
        "query": "Show me votes on HR 3684",
        "expected": "Should find vote record or say no votes found"
    },
    
    # Recent activity
    {
        "category": "Recent Activity",
        "query": "What bills were introduced recently?",
        "expected": "Should show recent bills"
    },
]


# ============================================================================
# Test Runner
# ============================================================================

async def run_test(query_info: dict, deps) -> dict:
    """
    Run a single test query.
    
    Args:
        query_info: Test query dictionary
        deps: Agent dependencies
        
    Returns:
        Test result with success/failure info
    """
    query = query_info["query"]
    category = query_info["category"]
    
    try:
        # Run the agent
        result = await research_agent.run(
            query,
            deps=deps
        )

        # Extract response
        response = result.data if hasattr(result, 'data') else str(result)

        # Count tool calls
        tool_calls = []
        if hasattr(result, 'all_messages'):
            for msg in result.all_messages():
                if hasattr(msg, 'kind') and msg.kind == 'response':  # Changed from 'request' to 'response'
                    if hasattr(msg, 'parts'):
                        for part in msg.parts:
                            if hasattr(part, 'part_kind') and part.part_kind == 'tool-call':
                                tool_calls.append(part.tool_name)
        
        return {
            "success": True,
            "query": query,
            "category": category,
            "response": response,
            "tool_calls": tool_calls,
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "query": query,
            "category": category,
            "response": None,
            "tool_calls": [],
            "error": str(e)
        }


async def run_all_tests():
    """Run all test queries and display results."""
    
    print("=" * 80)
    print("UTAH WATCHDOG - RESEARCH AGENT TEST SUITE")
    print("=" * 80)
    print()
    
    # Get dependencies
    print("🔌 Connecting to database...")
    deps = await get_agent_deps()
    print("✅ Connected!")
    print()
    
    # Run tests
    results = []
    categories = {}
    
    for i, query_info in enumerate(TEST_QUERIES, 1):
        category = query_info["category"]
        query = query_info["query"]
        expected = query_info["expected"]
        
        # Print test header
        print(f"[{i}/{len(TEST_QUERIES)}] {category}")
        print(f"📝 Query: {query}")
        print(f"🎯 Expected: {expected}")
        
        # Run test
        result = await run_test(query_info, deps)
        results.append(result)
        
        # Track by category
        if category not in categories:
            categories[category] = {"passed": 0, "failed": 0}
        
        if result["success"]:
            categories[category]["passed"] += 1
            print(f"✅ SUCCESS")
            print(f"🔧 Tools used: {', '.join(result['tool_calls']) if result['tool_calls'] else 'None'}")
            
            # Show first 200 chars of response
            response_preview = result["response"][:200]
            if len(result["response"]) > 200:
                response_preview += "..."
            print(f"💬 Response: {response_preview}")
        else:
            categories[category]["failed"] += 1
            print(f"❌ FAILED")
            print(f"⚠️  Error: {result['error']}")
        
        print()
        
        # Small delay between queries to avoid rate limits
        await asyncio.sleep(0.5)
    
    # Print summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    
    total_passed = sum(cat["passed"] for cat in categories.values())
    total_failed = sum(cat["failed"] for cat in categories.values())
    total = total_passed + total_failed
    
    print(f"Total Tests: {total}")
    print(f"✅ Passed: {total_passed}")
    print(f"❌ Failed: {total_failed}")
    print(f"Success Rate: {(total_passed/total*100):.1f}%")
    print()
    
    # Category breakdown
    print("By Category:")
    for category, stats in categories.items():
        total_cat = stats["passed"] + stats["failed"]
        print(f"  {category}: {stats['passed']}/{total_cat} passed")
    print()
    
    # Show failures if any
    if total_failed > 0:
        print("Failed Tests:")
        for result in results:
            if not result["success"]:
                print(f"  ❌ {result['query']}")
                print(f"     Error: {result['error']}")
        print()
    
    # Tool usage summary
    print("Tool Usage Summary:")
    tool_counts = {}
    for result in results:
        for tool in result.get("tool_calls", []):
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
    
    for tool, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {tool}: {count} times")
    
    print()
    print("=" * 80)
    
    # Return overall success
    return total_failed == 0


# ============================================================================
# Interactive Mode
# ============================================================================

async def interactive_mode():
    """
    Interactive mode - ask questions and see responses.
    """
    print("=" * 80)
    print("INTERACTIVE MODE - Ask questions about legislators")
    print("=" * 80)
    print()
    print("Type 'exit' or 'quit' to end")
    print("Type 'help' for example questions")
    print()
    
    deps = await get_agent_deps()
    
    while True:
        try:
            query = input("\n🤔 Your question: ").strip()
            
            if not query:
                continue
            
            if query.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if query.lower() == 'help':
                print("\n💡 Example questions:")
                print("  - Who is Mike Lee?")
                print("  - What bills has Mike Lee sponsored?")
                print("  - Find HR 6787")
                print("  - Show me bills about climate change")
                print("  - Who is funding Mike Lee?")
                print("  - Show me contributions from California")
                continue
            
            print("\n🤖 Thinking...")
            result = await research_agent.run(
                query,
                deps=deps
            )

            print("\n💬 Response:")
            print(result.data if hasattr(result, 'data') else str(result))

            # Show tools used
            tool_calls = []
            if hasattr(result, 'all_messages'):
                for msg in result.all_messages():
                    if hasattr(msg, 'kind') and msg.kind == 'response':  # Changed from 'request' to 'response'
                        if hasattr(msg, 'parts'):
                            for part in msg.parts:
                                if hasattr(part, 'part_kind') and part.part_kind == 'tool-call':
                                    tool_calls.append(part.tool_name)
            
            if tool_calls:
                print(f"\n🔧 Tools used: {', '.join(set(tool_calls))}")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


# ============================================================================
# Main
# ============================================================================

async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test the research agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  uv run python test_agent.py
  
  # Interactive mode
  uv run python test_agent.py --interactive
  
  # Test specific query
  uv run python test_agent.py --query "Who is Mike Lee?"
        """
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Run in interactive mode'
    )
    
    parser.add_argument(
        '--query', '-q',
        type=str,
        help='Test a single query'
    )
    
    args = parser.parse_args()
    
    if args.interactive:
        await interactive_mode()
    elif args.query:
        # Single query mode
        deps = await get_agent_deps()
        result = await research_agent.run(args.query, deps=deps)
        print(result.data if hasattr(result, 'data') else str(result))
    else:
        # Run full test suite
        success = await run_all_tests()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
