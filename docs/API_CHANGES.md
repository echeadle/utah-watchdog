# API Changes and Deprecations

Important notices about external API availability and changes affecting this project.

## OpenSecrets API - DISCONTINUED ❌

**Effective Date:** April 15, 2025

**Notice:** "As of April 15, 2025, our API offerings have been discontinued."

**Source:** OpenSecrets (Center for Responsive Politics)

**Impact on Project:**
- Cannot use OpenSecrets API for new data collection
- OpenSecrets IDs in `tracked_politicians.json` are still useful for reference
- Alternative data sources needed for:
  - Campaign finance analysis
  - Lobbying data
  - Industry contributions
  - PAC contributions

### Current Usage in Project

OpenSecrets IDs are tracked in:
- `data/tracked_politicians.json` - `identifiers.opensecrets_id` field
- Used for linking to OpenSecrets.org profile pages (still available)

### Alternatives for Campaign Finance Data

Since OpenSecrets API is discontinued, use these alternatives:

#### 1. **FEC API (Primary Source)** ✅
- **Status:** Active and maintained
- **Endpoint:** https://api.open.fec.gov/
- **Documentation:** https://api.open.fec.gov/developers/
- **What we use it for:**
  - Individual contributions (Schedule A)
  - Committee information
  - Candidate data
  - Disbursements
- **Implementation:** `src/ingestion/fec.py`

#### 2. **ProPublica Congress API** ✅
- **Status:** Active
- **Endpoint:** https://projects.propublica.org/api-docs/congress-api/
- **What it provides:**
  - Member information
  - Votes
  - Bills
  - Committees
- **Limitation:** No campaign finance data

#### 3. **Direct FEC Bulk Downloads** ✅
- **Source:** https://www.fec.gov/data/browse-data/?tab=bulk-data
- **Format:** CSV files
- **Pros:** Complete data, no rate limits
- **Cons:** Requires more processing, larger files
- **Use case:** For comprehensive historical analysis

#### 4. **OpenSecrets.org Website** ⚠️
- **Status:** Website still available (as of documentation date)
- **Use:** Manual lookups, reference links
- **Limitation:** No programmatic access
- **Profile URLs:** Still work with opensecrets_id
  - Format: `https://www.opensecrets.org/members-of-congress/summary?cid={opensecrets_id}`

### Recommended Actions

- [x] **Keep OpenSecrets IDs** - Still useful for reference links and cross-referencing
- [x] **Use FEC API as primary source** - Already implemented in `src/ingestion/fec.py`
- [ ] **Consider ProPublica API** - For votes and legislative activity
- [ ] **Consider FEC bulk data** - For comprehensive historical analysis
- [ ] **Update documentation** - Remove references to OpenSecrets API functionality

### Migration Notes

If you were planning to use OpenSecrets API features:

**Instead of:**
```python
# OpenSecrets API (discontinued)
opensecrets.get_candidate_summary(opensecrets_id)
```

**Use:**
```python
# FEC API (active)
from src.ingestion.fec import FECIngester
ingester = FECIngester(candidate_id=fec_candidate_id, cycle=2024)
```

### References

- FEC API Docs: https://api.open.fec.gov/developers/
- ProPublica Congress API: https://projects.propublica.org/api-docs/congress-api/
- FEC Bulk Data: https://www.fec.gov/data/browse-data/?tab=bulk-data

---

## Other API Status

### Congress.gov API ✅ **Active**
- **Status:** Active and maintained by Library of Congress
- **Current usage:** `src/ingestion/congress_members.py`
- **Purpose:** Current member data, bill information
- **Rate limit:** 5,000 requests/hour

### GovTrack API ⚠️ **Status Unknown**
- **Note:** GovTrack closed in 2024, status of data unclear
- **Alternative:** Use Congress.gov API instead

---

**Last Updated:** 2025-12-26
