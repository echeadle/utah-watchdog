"""
Test the research agent with debug output to see tool calls.

Usage:
    uv run python scripts/test_agent_debug.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.research_agent import research_agent
from src.agents.dependencies import get_agent_deps


async def test_with_debug():
    """Test with tool call visibility"""
    
    print("\n" + "="*60)
    print("🤖 TESTING RESEARCH AGENT (DEBUG MODE)")
    print("="*60)
    
    deps = await get_agent_deps()
    
    # Single focused query
    query = "Who are the senators from Utah?"
    
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print("="*60)
    
    try:
        result = await research_agent.run(query, deps=deps)
        
        print(f"\n🔧 Tools Used:")
        
        # Access tool calls from the result
        if hasattr(result, '_all_messages'):
            for msg in result._all_messages:
                # Check if it's a tool call
                if hasattr(msg, 'parts'):
                    for part in msg.parts:
                        if hasattr(part, 'tool_name'):
                            print(f"  ✓ Called: {part.tool_name}")
                            if hasattr(part, 'args'):
                                print(f"    Args: {part.args}")
        
        # Simpler approach - just show the final output and if tools were called
        print(f"\n📊 Total Messages: {len(result.all_messages())}")
        print(f"   (This includes user message, tool calls, and responses)")
        
        print(f"\n{'='*60}")
        print("Final Response:")
        print("="*60)
        print(result.output)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_with_debug())
