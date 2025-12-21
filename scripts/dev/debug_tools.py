"""
Debug script to check if tools are properly registered with the agent.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.research_agent import research_agent

def check_tools():
    """Check what tools are registered with the agent."""
    print("=" * 80)
    print("TOOL REGISTRATION DEBUG")
    print("=" * 80)
    print()

    # Check if agent has tools via _function_toolset
    if hasattr(research_agent, '_function_toolset'):
        toolset = research_agent._function_toolset
        print(f"✅ Agent has _function_toolset: {type(toolset)}")

        if hasattr(toolset, 'tools'):
            tools_dict = toolset.tools
            print(f"✅ Toolset has {len(tools_dict)} tools registered:")
            print()
            for name, tool_wrapper in tools_dict.items():
                print(f"  📦 {name}")
                # Try to get function from wrapper
                if hasattr(tool_wrapper, 'function'):
                    func = tool_wrapper.function
                    if hasattr(func, '__doc__') and func.__doc__:
                        desc = func.__doc__.strip().split('\n')[0][:100]
                        print(f"     {desc}")
                elif hasattr(tool_wrapper, '__doc__') and tool_wrapper.__doc__:
                    desc = tool_wrapper.__doc__.strip().split('\n')[0][:100]
                    print(f"     {desc}")
            print()
        else:
            print(f"   No 'tools' attribute found")
            print(f"   Toolset attributes: {[a for a in dir(toolset) if not a.startswith('_')]}")
    else:
        print("❌ Agent does not have _function_toolset attribute")

    # Try to access tools in different ways
    print("\nChecking alternative tool storage methods:")
    for attr in ['tools', '_tools', 'function_tools', '_model']:
        if hasattr(research_agent, attr):
            value = getattr(research_agent, attr)
            print(f"  ✅ {attr}: {type(value)}")
            if hasattr(value, '__len__'):
                try:
                    print(f"     Length: {len(value)}")
                except:
                    pass
        else:
            print(f"  ❌ {attr}: not found")

    print()
    print("=" * 80)

if __name__ == "__main__":
    check_tools()
