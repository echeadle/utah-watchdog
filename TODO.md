# Utah Watchdog - Project TODO

A phased task list for building the Government Watchdog application.
This is a learning project - expect to revise and reprioritize as we go!

---

## Phase 1: Core Infrastructure (Foundation)

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
-   [ ] Verify all sync scripts work end-to-end
    -   ✅ `sync_members.py`
    -   ✅ `sync_bills.py`
    -   ✅ `sync_votes.py` - ⚠️ House only (Senate API not available yet)
    -   ✅ `sync_committees.py`
    -   ✅ `enrich_contact_info.py` (enriches existing politicians)
    -   ✅ `sync_fec.py` (if exists)

---

## Phase 2: Data Quality & Completeness

Fill gaps in the data to make the app useful.

-   ✅ Sync FEC candidate IDs for all politicians
    -   Currently only 87 of 539 politicians have FEC IDs
    -   Need a script to match bioguide_id → fec_candidate_id
-   ✅ Fetch contributions for more politicians (not just Mike Lee)
    -   [ ] All Utah delegation
    -   [ ] Expand to other states as needed
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

## Phase 3: Streamlit Frontend Enhancements

Based on STREAMLIT_ENHANCEMENT_PLAN.md - make the UI match our backend capabilities.

### New Pages

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

### Enhance Existing Pages

-   [ ] Add semantic search toggle to Legislation page
-   [ ] Add "Ask AI about this person" button to Politician Detail
-   [ ] Add "Ask AI about this bill" button to Legislation detail
-   [ ] Add contribution charts (Plotly/Altair) where relevant
-   [ ] Add CSV download buttons for data tables

---

## Phase 4: Agent & Tools

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

## Notes

-   **Last updated**: December 2024
-   **Current focus**: Phase 1 completion, then Phase 3 (Streamlit pages)
-   **Data status**: 539 politicians, 500 bills, 100 contributions, 62 votes

---

_Check off items as completed. Revise priorities as needed!_
