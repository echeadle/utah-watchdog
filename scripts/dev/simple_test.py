"""
Simple test to verify tools are actually being called.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.research_agent import research_agent
from src.agents.dependencies import get_agent_deps


async def test_tool_usage():
    """Test if agent uses tools."""
    print("=" * 80)
    print("SIMPLE TOOL USAGE TEST")
    print("=" * 80)
    print()

    # Get dependencies
    deps = await get_agent_deps()

    # Test query that SHOULD use tools
    query = "Who is Mike Lee?"
    print(f"Query: {query}")
    print("Running agent...")
    print()

    result = await research_agent.run(query, deps=deps)

    # Print result
    print("Response:")
    print(result.data if hasattr(result, 'data') else str(result))
    print()

    # Check for tool calls
    print("=" * 80)
    print("CHECKING TOOL CALLS")
    print("=" * 80)

    tool_calls_found = []

    if hasattr(result, 'all_messages'):
        print(f"\nFound {len(list(result.all_messages()))} messages")
        for i, msg in enumerate(result.all_messages()):
            print(f"\nMessage {i+1}:")
            print(f"  Type: {type(msg)}")
            print(f"  Has 'kind': {hasattr(msg, 'kind')}")

            if hasattr(msg, 'kind'):
                print(f"  Kind: {msg.kind}")

                if hasattr(msg, 'parts'):
                    print(f"  Parts count: {len(msg.parts)}")
                    for j, part in enumerate(msg.parts):
                        print(f"    Part {j+1}: {type(part)}")
                        if hasattr(part, 'part_kind'):
                            print(f"      part_kind: {part.part_kind}")
                            if part.part_kind == 'tool-call':
                                tool_name = part.tool_name if hasattr(part, 'tool_name') else 'unknown'
                                tool_calls_found.append(tool_name)
                                print(f"      ✅ TOOL CALL: {tool_name}")
    else:
        print("\n❌ Result does not have 'all_messages' method")
        print(f"Result type: {type(result)}")
        print(f"Result attributes: {dir(result)}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    if tool_calls_found:
        print(f"✅ Found {len(tool_calls_found)} tool calls:")
        for tool in tool_calls_found:
            print(f"  - {tool}")
    else:
        print("❌ No tool calls found")
    print()


if __name__ == "__main__":
    asyncio.run(test_tool_usage())
