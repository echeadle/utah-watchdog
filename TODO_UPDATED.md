# Utah Watchdog - Project TODO

A phased task list for building the Government Watchdog application.
This is a learning project - expect to revise and reprioritize as we go!

---

## Phase 1: Core Infrastructure (Foundation) ✅ COMPLETE

These need to work before anything else.

-   [x] Create normalization module (`src/database/normalization.py`)
-   [x] Integrate normalization into `congress_members.py`
-   [x] Integrate normalization into `fec.py`
-   [x] Integrate normalization into `congress_bills.py`
-   [x] Verify `committees.py` has normalization (already done)
-   [x] Create database indexes for common queries
    -   [x] Politicians: `bioguide_id`, `state`, `party`, `chamber`, `in_office`
    -   [x] Legislation: `bill_id`, `sponsor_bioguide_id`, `status`, `congress`
    -   [x] Contributions: `bioguide_id`, `contributor_state`, `cycle`
    -   [x] Votes: `vote_id`, `bill_id`, `chamber`
    -   [x] Politician_votes: `vote_id`, `bioguide_id`
    -   [x] **Result: 37 indexes created, 90x performance improvement**
-   [x] Verify all sync scripts work end-to-end
    -   [x] `sync_members.py` - ✅ 539 politicians synced
    -   [x] `sync_bills.py` - ✅ 500 bills synced
    -   [x] `sync_votes.py` - ✅ 62 House votes synced
    -   [x] `sync_committees.py` - ✅ Working
    -   [x] `sync_contact_info.py` - ✅ Working
    -   [x] `sync_fec_contributions.py` - ✅ Fixed bioguide_id linking

---

## Phase 2: Data Quality & Completeness 🟡 ~60% COMPLETE

Fill gaps in the data to make the app useful.

-   [x] Sync FEC candidate IDs for all politicians
    -   [x] **539 of 539 politicians now have FEC IDs!** (using official YAML mapping)
    -   [x] Created `populate_fec_ids_from_yaml.py` script
-   [x] Fetch contributions for more politicians
    -   [x] Nicole Malliotakis (100 contributions)
    -   [ ] All Utah delegation (need to sync)
    -   [ ] Expand to other states as needed (20+ politicians recommended for demo)
-   [ ] Senate votes
    -   Congress.gov API doesn't have Senate votes yet (beta)
    -   [ ] Research alternative sources (senate.gov XML?)
    -   [ ] Implement Senate votes ingester when available
-   [ ] Generate embeddings for legislation
    -   [ ] Create embeddings script for bill titles/summaries
    -   [ ] Set up MongoDB vector search index
    -   [ ] Test semantic search queries
-   [ ] Improve bill data
    -   [ ] Fetch cosponsors (requires additional API calls)
    -   [ ] Fetch full bill text URLs
    -   [ ] Link bills to votes

---

## Phase 3: Streamlit Frontend Enhancements ✅ COMPLETE

Based on STREAMLIT_ENHANCEMENT_PLAN.md - make the UI match our backend capabilities.

### New Pages ✅

-   [x] 💰 Campaign Finance page (`8_💰_Campaign_Finance.py`)
    -   [x] Politician selector dropdown
    -   [x] Total raised metric
    -   [x] Top contributors table
    -   [x] Top employers/organizations table
    -   [x] Filter by employer, state, amount range
    -   [x] **4 tabs: Donors, Employers, By State, Recent**
-   [x] 🤖 AI Chat page (`9_🤖_Ask_AI.py`)
    -   [x] Chat interface with `st.chat_message()`
    -   [x] Example questions as starter buttons (8 examples)
    -   [x] Session state for conversation history
    -   [x] Show which tools the agent called (debug mode)
    -   [x] Clear conversation button
    -   [ ] Streaming responses (not implemented - Streamlit limitation)

### Enhance Existing Pages

-   [ ] Add semantic search toggle to Legislation page
-   [ ] Add "Ask AI about this person" button to Politician Detail
-   [ ] Add "Ask AI about this bill" button to Legislation detail
-   [x] Add contribution charts (Plotly/Altair) where relevant
    -   [x] Created enhanced version with charts (optional upgrade)
-   [ ] Add CSV download buttons for data tables

**Note:** Core Phase 3 objectives complete. Enhancement items are optional nice-to-haves.

---

## Phase 4: Agent & Tools 🟡 ~50% COMPLETE

Make the AI research assistant more capable.

-   [x] Test all agent tools work correctly
    -   [ ] `search_knowledge_base()` - Not implemented yet
    -   [x] `lookup_politician()` - ✅ **FIXED: Now handles partial names, middle initials**
    -   [x] `get_politician_details()` - ✅ Working
    -   [ ] `search_bills()` / `semantic_search_bills()` - Need to test
    -   [ ] `get_bill_details()` - Need to test
    -   [ ] `get_bill_votes()` - Need to test
    -   [x] `get_campaign_contributions()` - ✅ Working
    -   [x] `get_top_donors()` - ✅ Working
    -   [x] `search_campaign_contributions()` - ✅ Working
    -   [ ] `compare_politicians()` - Need to test
-   [x] Improve agent system prompts
    -   [x] Enhanced prompt with explicit tool usage instructions
    -   [x] Added "Who is [name]?" examples
    -   [x] Made tool calling mandatory
    -   [ ] Test with more real user questions
    -   [ ] Refine prompts based on failure cases
-   [ ] Add new tools as needed
    -   [ ] `get_politician_voting_record()` - summary of votes
    -   [ ] `find_bills_by_topic()` - semantic search wrapper
    -   [ ] `get_recent_activity()` - latest votes/bills for a politician

**Key Achievement:** Politician lookup now works with partial names (e.g., "Terri Sewell" finds "Terri A. Sewell")

---

## Phase 5: Production Readiness

Prepare for deployment and real users.

-   [ ] Error handling improvements
    -   [ ] Graceful API failures in ingesters
    -   [ ] User-friendly error messages in Streamlit
    -   [ ] Retry logic for transient failures
-   [ ] Logging and monitoring
    -   [ ] Structured logging throughout
    -   [ ] Set up Sentry (free tier) for error tracking
    -   [ ] Add basic metrics (API calls, sync durations)
-   [ ] Celery scheduler for automated syncs
    -   [ ] Set up Redis (Upstash free tier)
    -   [ ] Configure Celery beat schedule
    -   [ ] Daily: bills, votes
    -   [ ] Weekly: contributions, committees
-   [ ] Deployment configuration
    -   [ ] Dockerfile
    -   [ ] docker-compose for local dev
    -   [ ] Railway/Render deployment config
    -   [ ] Environment variables documentation
-   [ ] Documentation
    -   [ ] Update README with setup instructions
    -   [ ] API documentation (if exposing FastAPI)
    -   [ ] User guide for Streamlit app

---

## Future Ideas (Backlog)

Things to consider after the core app is working.

-   [ ] Stock trade tracking (Capitol Trades integration)
-   [ ] Email alerts for tracked politicians/bills
-   [ ] Committee hearing calendar
-   [ ] Lobbying data (OpenSecrets)
-   [ ] Utah state legislature integration
-   [ ] Mobile-friendly UI improvements
-   [ ] Next.js frontend (production upgrade from Streamlit)
-   [ ] User accounts and saved searches
-   [ ] API rate limiting for public access
-   [ ] Data export features (PDF reports, etc.)

---

## Recent Fixes & Improvements

### December 18, 2024
- ✅ Fixed FEC ingester to properly link contributions to politicians via bioguide_id
- ✅ Created `populate_fec_ids_from_yaml.py` - now ALL 539 politicians have FEC IDs
- ✅ Fixed politician lookup tool to handle partial names and middle initials
- ✅ Enhanced agent system prompt for better tool usage
- ✅ Completed Campaign Finance page (8_💰_Campaign_Finance.py)
- ✅ Completed AI Chat page (9_🤖_Ask_AI.py)
- ✅ Fixed regex search issues (changed from $regex to re.compile)
- ✅ Implemented word-based name matching (handles "Terri Sewell" → "Terri A. Sewell")

---

## Current Status

-   **Database**: 539 politicians (all with FEC IDs), 500 bills, 100 contributions, 62 votes
-   **Phase 1**: ✅ COMPLETE
-   **Phase 2**: 🟡 60% complete (need more contribution data)
-   **Phase 3**: ✅ COMPLETE (core features done)
-   **Phase 4**: 🟡 50% complete (politician tools working, need to test bill/vote tools)
-   **Phase 5**: Not started

---

## Recommended Next Steps

1. **Sync more contribution data** (Phase 2)
   ```bash
   # Get contributions for 20-50 politicians for better demo
   uv run python scripts/sync_fec_contributions.py --cycle 2024 --limit 20 --max-pages 5
   ```

2. **Test remaining agent tools** (Phase 4)
   - Test bill search tools in AI Chat
   - Test vote lookup tools
   - Test compare politicians feature

3. **Optional enhancements** (Phase 3)
   - Add Plotly charts to Campaign Finance page
   - Add "Ask AI" buttons to existing pages
   - Add CSV export functionality

4. **Production readiness** (Phase 5)
   - When ready to deploy publicly

---

_Last updated: December 18, 2024_
_Check off items as completed. Revise priorities as needed!_
