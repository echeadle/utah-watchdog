"""
Test research agent with direct tool call.
"""
import asyncio
from src.agents.research_agent import research_agent
from src.agents.dependencies import get_agent_deps

async def main():
    print("Testing research agent tool calling...\n")

    deps = await get_agent_deps()

    # Very specific query that requires database lookup
    query = "Use the find_politician tool to search for politicians from Utah"

    print(f"Query: {query}\n")

    result = await research_agent.run(query, deps=deps)

    response = result.data if hasattr(result, 'data') else result.output
    print(f"Response: {response[:300]}...\n")

    # Check tool usage
    tool_calls = []
    if hasattr(result, 'all_messages'):
        for msg in result.all_messages():
            if hasattr(msg, 'parts'):
                for part in msg.parts:
                    if hasattr(part, 'part_kind') and part.part_kind == 'tool-call':
                        tool_calls.append(part.tool_name)

    if tool_calls:
        print(f"✅ Tools called: {', '.join(tool_calls)}")
    else:
        print("❌ No tools were called!")

        # Debug: print message types
        print("\nDebug - Message structure:")
        if hasattr(result, 'all_messages'):
            for i, msg in enumerate(result.all_messages()):
                print(f"  Message {i}: kind={getattr(msg, 'kind', 'unknown')}, "
                      f"parts={len(getattr(msg, 'parts', []))}")

if __name__ == "__main__":
    asyncio.run(main())
