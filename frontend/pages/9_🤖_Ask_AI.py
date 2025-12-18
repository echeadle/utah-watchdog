"""
AI Chat page - Ask questions about legislators using natural language.

This page uses the research agent to answer questions about politicians,
bills, votes, and campaign finance using AI.
"""
import streamlit as st
import asyncio
from datetime import datetime

# Streamlit is synchronous, so we need to handle async agent calls
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="Ask AI",
    page_icon="🤖",
    layout="wide"
)


# ============================================================================
# Agent Integration
# ============================================================================

def query_agent(message: str, history: list = None) -> dict:
    """
    Query the research agent (synchronous wrapper for async agent).
    
    Args:
        message: User's question
        history: Previous conversation messages
        
    Returns:
        {
            "response": str,
            "tool_calls": list,
            "error": str (if error occurred)
        }
    """
    async def run_agent():
        try:
            # Import agent and dependencies
            from src.agents.research_agent import research_agent
            from src.agents.dependencies import get_agent_deps
            
            # Get agent dependencies (database connection, etc.)
            deps = await get_agent_deps()
            
            # Run the agent (Pydantic AI handles history automatically)
            result = await research_agent.run(
                message,
                deps=deps
            )
            
            # Extract response - Pydantic AI uses .output or .data depending on version
            response_text = None
            if hasattr(result, 'data'):
                response_text = result.data
            elif hasattr(result, 'output'):
                response_text = result.output
            else:
                # Try to get the string representation
                response_text = str(result)
            
            # Extract tool usage info from all_messages
            tool_calls = []
            if hasattr(result, 'all_messages'):
                for msg in result.all_messages():
                    # Pydantic AI message structure
                    if hasattr(msg, 'kind') and msg.kind == 'request':
                        if hasattr(msg, 'parts'):
                            for part in msg.parts:
                                if hasattr(part, 'part_kind') and part.part_kind == 'tool-call':
                                    tool_calls.append({
                                        "tool": part.tool_name,
                                        "args": part.args if hasattr(part, 'args') else {}
                                    })
            
            return {
                "response": response_text,
                "tool_calls": tool_calls,
                "error": None
            }
            
        except ImportError as e:
            return {
                "response": None,
                "tool_calls": [],
                "error": f"Agent import failed: {str(e)}. Make sure research_agent.py and dependencies.py exist."
            }
        except Exception as e:
            import traceback
            return {
                "response": None,
                "tool_calls": [],
                "error": f"Agent error: {str(e)}\n{traceback.format_exc()}"
            }
    
    # Run async function in sync context
    try:
        return asyncio.run(run_agent())
    except Exception as e:
        import traceback
        return {
            "response": None,
            "tool_calls": [],
            "error": f"Failed to run agent: {str(e)}\n{traceback.format_exc()}"
        }


# ============================================================================
# Example Questions
# ============================================================================

EXAMPLE_QUESTIONS = [
    "Who is funding Terri Sewell?",
    "What bills has Eric Crawford sponsored?",
    "Show me contributions from California donors",
    "Find bills about healthcare",
    "Who are the top employers donating to Steve Womack?",
    "Search for contributions over $1000",
    "What legislation was introduced recently?",
    "Show me politicians from Arkansas",
]


# ============================================================================
# UI Components
# ============================================================================

def display_tool_calls(tool_calls: list):
    """Display which tools the agent used"""
    if not tool_calls:
        return
    
    with st.expander(f"🔧 Tools Used ({len(tool_calls)})", expanded=False):
        for i, call in enumerate(tool_calls, 1):
            tool_name = call.get("tool", "Unknown")
            args = call.get("args", {})
            
            st.markdown(f"**{i}. {tool_name}**")
            
            if args:
                # Show key arguments (limit to important ones)
                key_args = {k: v for k, v in args.items() if k in ['query', 'bioguide_id', 'bill_id', 'state', 'party']}
                if key_args:
                    st.json(key_args)
            
            st.divider()


def display_example_questions():
    """Display example question buttons"""
    st.markdown("### 💡 Try asking:")
    
    cols = st.columns(2)
    
    for i, question in enumerate(EXAMPLE_QUESTIONS):
        col_idx = i % 2
        with cols[col_idx]:
            if st.button(question, key=f"example_{i}", use_container_width=True):
                # Add to chat history and trigger response
                st.session_state.messages.append({
                    "role": "user",
                    "content": question
                })
                st.rerun()


# ============================================================================
# Main Page
# ============================================================================

def main():
    st.title("🤖 Ask AI About Legislators")
    st.markdown("Ask questions in natural language - the AI will search votes, bills, and campaign finance data")
    
    # Check if agent is available
    try:
        from src.agents.research_agent import research_agent
        agent_available = True
    except ImportError:
        agent_available = False
    
    if not agent_available:
        st.error("❌ Research agent not found!")
        st.info("""
        The AI chat feature requires the research agent to be set up.
        
        Make sure you have:
        1. Created `src/agents/research_agent.py`
        2. Implemented the agent tools
        3. Installed Pydantic AI: `uv add pydantic-ai`
        """)
        return
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Sidebar with info
    with st.sidebar:
        st.markdown("## 💬 Chat Info")
        st.metric("Messages", len(st.session_state.messages))
        
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        st.divider()
        
        st.markdown("## 🔍 What Can I Ask?")
        st.markdown("""
        - **Politicians**: "Who is Mike Lee?"
        - **Bills**: "What bills are about climate?"
        - **Votes**: "How did Utah vote on HR 1234?"
        - **Money**: "Who funds my representative?"
        - **Comparisons**: "Compare Romney and Lee"
        """)
        
        st.divider()
        
        st.markdown("## 🛠️ How It Works")
        st.caption("The AI uses multiple tools to search:")
        st.caption("• 🔍 Semantic search for bills")
        st.caption("• 👤 Politician lookup")
        st.caption("• 🗳️ Vote records")
        st.caption("• 💰 Campaign finance data")
    
    # Display example questions if no messages yet
    if len(st.session_state.messages) == 0:
        display_example_questions()
        st.divider()
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show tool usage for assistant messages
            if message["role"] == "assistant" and "tool_calls" in message:
                display_tool_calls(message["tool_calls"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about legislators, bills, or campaign finance..."):
        # Add user message to chat
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Query the agent
                result = query_agent(
                    prompt,
                    history=st.session_state.messages[:-1]  # Don't include the message we just added
                )
                
                if result["error"]:
                    st.error(f"Error: {result['error']}")
                    response_text = "I encountered an error processing your request. Please try again or rephrase your question."
                    tool_calls = []
                else:
                    response_text = result["response"]
                    tool_calls = result["tool_calls"]
                
                # Display response
                st.markdown(response_text)
                
                # Show tools used
                if tool_calls:
                    display_tool_calls(tool_calls)
        
        # Add assistant response to chat history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "tool_calls": tool_calls
        })
    
    # Show helpful tips at bottom
    if len(st.session_state.messages) > 0:
        st.divider()
        st.caption("💡 Tip: Ask follow-up questions or try one of the example questions above!")


# ============================================================================
# Run
# ============================================================================

if __name__ == "__main__":
    main()
