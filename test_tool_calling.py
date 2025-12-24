"""
Minimal test to verify tool calling works with Pydantic AI and Claude.
"""
import asyncio
from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv

load_dotenv()

# Create a simple agent
agent = Agent(
    'claude-sonnet-4-5-20250929',
    system_prompt='You are a helpful assistant. ALWAYS use your tools to answer questions.'
)

@agent.tool
async def get_current_time(ctx: RunContext) -> str:
    """Get the current time. Use this tool whenever asked about the time."""
    from datetime import datetime
    return datetime.now().strftime("%H:%M:%S")

async def main():
    print("Testing tool calling with Pydantic AI + Claude...\n")

    result = await agent.run("What time is it?")

    response = result.data if hasattr(result, 'data') else result.output
    print(f"Response: {response}\n")

    # Check if tools were called
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
        print("\nDebugging - all messages:")
        if hasattr(result, 'all_messages'):
            for i, msg in enumerate(result.all_messages()):
                print(f"\nMessage {i}: {type(msg)}")
                print(f"  {msg}")

if __name__ == "__main__":
    asyncio.run(main())
