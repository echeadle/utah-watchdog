# Streamlit Frontend Enhancement Plan

## Current Status

### ✅ What's Built
- **Main app.py**: Displays Utah congressional delegation
- **7 functional pages**:
  1. 📜 Legislation - Browse bills with filters
  2. 🔗 Bills by Politician - See sponsored bills
  3. 🔍 Search Politicians - Find any legislator  
  4. 👤 Politician Detail - Full profile with tabs
  5. 🗳️ Votes - Browse roll call votes
  6. 📊 Vote Detail - Detailed vote breakdown with party analysis
  7. (Placeholder page 1)

### ✅ Backend Capabilities (Built Today)
- **Research Agent** with 13 tools (Pydantic AI + OpenAI GPT-4o)
- **Database**: 539 politicians, 500 bills, 100 contributions, 62 votes
- **Semantic Search**: OpenAI embeddings + MongoDB vector search
- **Campaign Finance**: FEC API integration, 100 contributions linked to Mike Lee
- **87 politicians** have FEC IDs populated

### ❌ What's Missing from Frontend
1. **No AI Chat Interface** - Agent exists but no UI to use it
2. **No Campaign Finance Page** - Have 100 contributions but nowhere to show them
3. **No Semantic Search UI** - Have embeddings but using keyword search only
4. **Direct DB Queries** - Pages query MongoDB directly instead of using agent tools

## Enhancement Goals

### Primary Goal
**Add 2 new pages that showcase the powerful backend we built:**

#### 1. 💰 Campaign Finance Page (NEW)
**Features:**
- View contributions by politician (dropdown selector)
- Top donors table with employer info
- Contribution charts (by amount, by state, by employer)
- Search contributions (by employer, state, amount range)
- Display Mike Lee's $12,134.88 raised from Applied Materials employees

**Uses these tools:**
- `get_campaign_contributions()`
- `get_top_donors()`
- `search_campaign_contributions()`

#### 2. 🤖 Ask AI Page (NEW)
**Features:**
- Chat interface with streaming responses
- Example questions to get started
- Shows tool usage (which tools the agent calls)
- Natural language queries about politicians, bills, finances
- Conversation history in session

**Example queries:**
- "Who is funding Mike Lee's campaign?"
- "What bills has Mike Lee sponsored about climate change?"
- "Show me contributions from tech companies"
- "Compare voting records of Utah's senators"

### Secondary Goal (Optional)
**Enhance existing pages with AI integration:**
- Add "Ask AI" buttons on politician detail pages
- Add "Ask AI about this bill" on legislation pages
- Use semantic search instead of keyword search where appropriate

## Technical Details

### Current Stack
- **Frontend**: Streamlit (synchronous PyMongo)
- **Backend**: FastAPI + Motor (async)
- **Agent**: Pydantic AI + OpenAI
- **Database**: MongoDB Atlas

### Key Files
- `frontend/app.py` - Main page
- `frontend/pages/*.py` - 7 existing pages
- `src/agents/research_agent.py` - Agent with 13 tools
- `src/agents/tools/politician.py` - Politician lookup tools
- `src/agents/tools/legislation.py` - Bill search tools (keyword + semantic)
- `src/agents/tools/finance.py` - Campaign finance query tools

### Database Collections
```
politicians: 539 records (87 with FEC IDs)
legislation: 500 records (all with embeddings)
contributions: 100 records (all linked to Mike Lee)
votes: 62 records (118th Congress)
politician_votes: 22,972 records
```

### Important Notes
1. **Streamlit is synchronous**, agent is async - need to use `asyncio.run()` or sync wrappers
2. **Agent requires AgentDependencies** - needs MongoDB connection
3. **Finance data is limited** - Only Mike Lee has contributions currently
4. **State names normalized** - "Utah" and "UT" both work in queries

## Implementation Plan

### Page 1: Campaign Finance (Priority 1)
**File**: `frontend/pages/8_💰_Campaign_Finance.py`

**Structure:**
1. Header with summary stats (total raised across all politicians)
2. Politician selector (dropdown)
3. For selected politician:
   - Total raised metric
   - Top 10 contributors table
   - Top 10 employers/organizations table
   - Recent contributions table
4. Search section:
   - Filter by employer, state, amount range
   - Results table with contributor details

**Data Source:**
- Use `src/agents/tools/finance.py` functions directly
- Or call agent with finance queries

### Page 2: AI Chat (Priority 1)
**File**: `frontend/pages/9_🤖_Ask_AI.py`

**Structure:**
1. Header: "Ask about Utah legislators"
2. Example questions (buttons that populate chat)
3. Chat interface:
   - `st.chat_message()` for messages
   - `st.chat_input()` for user input
   - Store in `st.session_state.messages`
4. Show which tools were called (optional debug info)
5. Streaming responses if possible

**Implementation:**
```python
# Sync wrapper for async agent
def query_agent(message: str) -> str:
    async def run():
        deps = await get_agent_deps()
        result = await research_agent.run(message, deps=deps)
        return result.data
    
    return asyncio.run(run())
```

### Optional Enhancements
1. **Semantic search toggle** on Legislation page
2. **"Ask AI" buttons** on detail pages
3. **Contribution charts** (Plotly/Altair)
4. **Download data** buttons (CSV export)

## Success Criteria

After implementation, users should be able to:

✅ View campaign contributions for any politician with FEC data  
✅ Search contributions by employer, state, or amount  
✅ Ask natural language questions and get intelligent answers  
✅ See who's funding their representatives  
✅ Find bills by topic using semantic search  
✅ Get comparisons between politicians  

## Next Steps

1. Create `8_💰_Campaign_Finance.py` page
2. Create `9_🤖_Ask_AI.py` page  
3. Test with real queries
4. Add to sidebar navigation
5. (Optional) Enhance existing pages with AI buttons

## Example User Flows

### Flow 1: Follow the Money
1. Go to "Campaign Finance" page
2. Select "Lee, Mike" from dropdown
3. See $12,134.88 total raised
4. See top employer: Applied Materials Inc ($12K from 100 employees)
5. Click to search contributions from "Applied Materials"
6. See list of individual contributors with amounts

### Flow 2: AI Research
1. Go to "Ask AI" page
2. Click example: "Who is funding Mike Lee?"
3. Agent calls `get_campaign_contributions(bioguide_id="L000577")`
4. Returns formatted answer with top donors
5. User asks follow-up: "What about contributions from California?"
6. Agent calls `search_campaign_contributions(state="CA")`
7. Shows CA contributors

### Flow 3: Bill Discovery
1. User asks AI: "What bills are about climate change?"
2. Agent uses `semantic_search_bills("climate change")`
3. Returns 10 relevant bills with descriptions
4. User clicks bill link to see details
5. User asks: "How did Utah's senators vote on this?"
6. Agent looks up votes (when available)

---

**Ready to build these 2 pages! Start with Campaign Finance since the data is already there.**
