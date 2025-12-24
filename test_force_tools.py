"""
Test forcing tool use with model_settings.
"""
import asyncio
from pydantic_ai import ModelSettings
from src.agents.research_agent import research_agent
from src.agents.dependencies import get_agent_deps

async def main():
    print("Testing forced tool usage...\n")

    deps = await get_agent_deps()

    query = "Who is Mike Lee?"

    # Try with tool_choice in model_settings
    try:
        model_settings = ModelSettings(
            tool_choice='required'  # Force tool use
        )

        print(f"Query: {query}")
        print("Model settings: tool_choice='required'\n")

        result = await research_agent.run(
            query,
            deps=deps,
            model_settings=model_settings
        )

        response = result.data if hasattr(result, 'data') else result.output
        print(f"Response: {response[:200]}...\n")

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

    except Exception as e:
        print(f"Error with tool_choice='required': {e}")
        print("\nTrying with tool_choice='auto'...")

        model_settings = ModelSettings(tool_choice='auto')

        result = await research_agent.run(
            query,
            deps=deps,
            model_settings=model_settings
        )

        response = result.data if hasattr(result, 'data') else result.output
        print(f"Response: {response[:200]}...")

if __name__ == "__main__":
    asyncio.run(main())
