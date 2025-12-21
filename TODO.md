# Utah Watchdog - Project TODO

A phased task list for building the Government Watchdog application.
This is a learning project - expect to revise and reprioritize as we go!

---

## Phase 1: Core Infrastructure (Foundation) ✅ COMPLETE!

These need to work before anything else.

-   ✅ Create normalization module (`src/database/normalization.py`)
-   ✅ Integrate normalization into `congress_members.py`
-   ✅ Integrate normalization into `fec.py`
-   ✅ Integrate normalization into `congress_bills.py`
-   ✅ Verify `committees.py` has normalization (already done)
-   ✅ Create database indexes for common queries
    -   ✅ Politicians: `bioguide_id`, `state`, `party`, `chamber`, `in_office`
    -   ✅ Legislation: `bill_id`, `sponsor_bioguide_id`, `status`, `congress`
    -   ✅ Contributions: `bioguide_id`, `contributor_state`, `cycle`
    -   ✅ Votes: `vote_id`, `bill_id`, `chamber`
    -   ✅ Politician_votes: `vote_id`, `bioguide_id`
-   ✅ Verify all sync scripts work end-to-end
    -   ✅ `sync_members.py` - Working with native filtering!
    -   ✅ `sync_bills.py` - Working, fixed policy_area extraction
    -   ✅ `sync_votes.py` - Working
    -   ✅ `sync_committees.py` - Working
    -   ✅ `sync_fec_contributions.py` - Working
    -   ✅ `generate_embeddings.py` - Working (1,116 bills embedded!)
-   ✅ **NEW: Create `sync_all.py` master orchestration script**
-   ✅ **NEW: Reorganized scripts into pipelines/dev/maintenance**
-   ✅ **NEW: Enhanced CongressMembersIngester with native filtering (50x faster for state queries!)**

---

## Phase 2: Data Quality & Completeness 🔄 IN PROGRESS

Fill gaps in the data to make the app useful.

-   [ ] Sync FEC candidate IDs for all politicians
    -   Currently only 87 of 539 politicians have FEC IDs
    -   Need a script to match bioguide_id → fec_candidate_id
-   🔄 Fetch contributions for more politicians
    -   ✅ Mike Lee (100 contributions)
    -   ✅ Script supports multiple politicians (limit 10 for now)
    -   [ ] All Utah delegation
    -   [ ] Expand to other states as needed
-   🔄 Senate votes
    -   ✅ House votes working (180 new votes synced)
    -   [ ] Senate votes (Congress.gov API doesn't have them yet - beta)
    -   [ ] Research alternative sources (senate.gov XML?)
-   ✅ Generate embeddings for legislation
    -   ✅ Create embeddings script for bill titles/summaries
    -   ✅ Generated embeddings for 1,116 bills!
    -   ✅ Set up MongoDB vector search index
    -   [ ] Test semantic search queries in Streamlit
-   🔄 Improve bill data
    -   ✅ **FIXED: Policy area extraction** (63 bills now have policy areas)
    -   [ ] Fetch cosponsors (requires additional API calls)
    -   [ ] Fetch full bill text URLs
    -   [ ] Link bills to votes

---

## Phase 3: Streamlit Frontend Enhancements 🔄 IN PROGRESS

Based on STREAMLIT_ENHANCEMENT_PLAN.md - make the UI match our backend capabilities.

### Existing Pages Enhanced ✅

-   ✅ **Legislation page** (`2___Legislation.py`)
    -   ✅ Congress filter (118th, 119th, etc.)
    -   ✅ Bill number search (e.g., "HR 6849")
    -   ✅ Bill type filter
    -   ✅ Advanced sorting (by date, number, last updated)
    -   ✅ Policy area display (shows real data when available)
    -   ✅ Active filters display
    -   ✅ Statistics by Congress in sidebar
-   ✅ **Politician Detail page** (fixed datetime import bug)
-   ✅ **All pages** - Updated script paths for reorganized structure

### New Pages - Still TODO

-   [ ] 💰 Campaign Finance page (`8_💰_Campaign_Finance.py`)
    -   [ ] Politician selector dropdown
    -   [ ] Total raised metric
    -   [ ] Top contributors table
    -   [ ] Top employers/organizations table
    -   [ ] Filter by employer, state, amount range
-   [ ] 🤖 AI Chat page (`9_🤖_Ask_AI.py`)
    -   [ ] Chat interface with `st.chat_message()`
    -   [ ] Example questions as starter buttons
    -   [ ] Session state for conversation history
    -   [ ] Show which tools the agent called (debug mode)
    -   [ ] Streaming responses (if possible with Streamlit)

### Enhance Existing Pages - Still TODO

-   [ ] Add semantic search toggle to Legislation page
-   [ ] Add "Ask AI about this person" button to Politician Detail
-   [ ] Add "Ask AI about this bill" button to Legislation detail
-   [ ] Add contribution charts (Plotly/Altair) where relevant
-   [ ] Add CSV download buttons for data tables

---

## Phase 4: Agent & Tools 📝 READY TO TEST

Make the AI research assistant more capable.

-   [ ] Test all agent tools work correctly
    -   [ ] `search_knowledge_base()`
    -   [ ] `lookup_politician()`
    -   [ ] `get_politician_details()`
    -   [ ] `search_bills()` / `semantic_search_bills()`
    -   [ ] `get_bill_details()`
    -   [ ] `get_bill_votes()`
    -   [ ] `get_campaign_contributions()`
    -   [ ] `get_top_donors()`
    -   [ ] `search_campaign_contributions()`
    -   [ ] `compare_politicians()`
    -   [ ] Others as applicable
-   [ ] Improve agent system prompts
    -   [ ] Test with real user questions
    -   [ ] Refine prompts based on failure cases
    -   [ ] Add examples to prompts if needed
-   [ ] Add new tools as needed
    -   [ ] `get_politician_voting_record()` - summary of votes
    -   [ ] `find_bills_by_topic()` - semantic search wrapper
    -   [ ] `get_recent_activity()` - latest votes/bills for a politician

**Note:** Agent exists with 13 tools but no Streamlit UI yet!

---

## Phase 5: Production Readiness 🚫 NOT STARTED

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

## 🎉 Major Accomplishments Today (Dec 19-20, 2024)

### Data Pipeline
1. ✅ **Fixed policy area extraction** - 63 bills now have real policy areas
2. ✅ **Created sync_all.py** - Master orchestration script with dependency management
3. ✅ **Ran full sync successfully** - 16 minutes, zero errors:
   - 539 politicians (119th Congress)
   - 200 bills (11 new, 189 updated)
   - 1,116 embeddings generated
   - 500 committee assignments
   - 200 votes (180 new)
   - 1,000 contributions

### Code Organization
4. ✅ **Reorganized scripts/** into:
   - `scripts/pipelines/` - Production data ingestion
   - `scripts/dev/` - Development & debugging tools
   - `scripts/maintenance/` - One-off fixes
5. ✅ **Enhanced CongressMembersIngester** - Native state/chamber filtering (50x faster!)
6. ✅ **Archived obsolete files** - Cleaned up duplicates

### Frontend
7. ✅ **Enhanced Legislation page** with:
   - Congress filter (119th, 118th, etc.)
   - Bill number search (e.g., "HR 6849")
   - Advanced sorting options
   - Policy area display
   - Active filters display
8. ✅ **Fixed all Streamlit script paths** after reorganization
9. ✅ **Fixed datetime import bug** in Politician Detail page

### Debugging Tools
10. ✅ **Created check_policy_area.py** - Diagnostic script for data quality

---

## Notes

-   **Last updated**: December 20, 2024
-   **Current focus**: Phase 2 (data quality) → Phase 3 (Campaign Finance & AI Chat pages)
-   **Current data status** (as of Dec 20, 2024):
    - 539 politicians (119th Congress)
    - 1,616 bills with 1,116 embeddings
    - 63 bills with policy areas (17 categories)
    - 1,000 contributions
    - ~380 votes with ~23,000 individual politician votes

---

## 🎯 Recommended Next Steps

### Priority 1: Campaign Finance Page
- Build `8_💰_Campaign_Finance.py`
- Show contributions for politicians with FEC IDs
- Use existing 1,000 contributions data

### Priority 2: AI Chat Page
- Build `9_🤖_Ask_AI.py`
- Connect to existing research agent (13 tools ready!)
- Enable semantic search on 1,116 embedded bills

### Priority 3: Expand Data Coverage
- Sync more bills from 118th Congress (better policy area coverage)
- Get FEC IDs for more politicians
- Expand campaign finance beyond current 10 politicians

---

_Check off items as completed. Revise priorities as needed!_
