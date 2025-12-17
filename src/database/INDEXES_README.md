# Database Indexes

## Overview

This module creates optimized MongoDB indexes for the Utah Watchdog database. Indexes dramatically improve query performance by allowing MongoDB to quickly locate documents without scanning entire collections.

## Quick Start

```bash
# Create all indexes (recommended after initial data load)
uv run python scripts/setup_indexes.py

# List existing indexes
uv run python scripts/setup_indexes.py --list

# Drop and recreate indexes
uv run python scripts/setup_indexes.py --drop
```

## Indexes Created

### Politicians Collection

| Index Name                       | Fields                                  | Purpose                     |
| -------------------------------- | --------------------------------------- | --------------------------- |
| `idx_bioguide_id`                | bioguide_id (UNIQUE)                    | Primary key lookups         |
| `idx_state_party_chamber_office` | state, party, chamber, in_office        | Filter legislators          |
| `idx_in_office`                  | in_office                               | Current vs former officials |
| `idx_state_office`               | state, in_office                        | State-specific queries      |
| `idx_name_sort`                  | last_name, first_name                   | Alphabetical sorting        |
| `idx_name_text_search`           | full_name, last_name, first_name (TEXT) | Name search                 |
| `idx_fec_candidate_id`           | fec_candidate_id (SPARSE)               | Link to FEC data            |
| `idx_opensecrets_id`             | opensecrets_id (SPARSE)                 | Link to OpenSecrets         |

**Example queries optimized:**

```python
# Find Utah delegation
db.politicians.find({"state": "UT", "in_office": True})

# Search by name
db.politicians.find({"$text": {"$search": "Mike Lee"}})

# Link FEC data
db.politicians.find({"fec_candidate_id": "S2UT00106"})
```

### Legislation Collection

| Index Name                 | Fields                               | Purpose                |
| -------------------------- | ------------------------------------ | ---------------------- |
| `idx_bill_id`              | bill_id (UNIQUE)                     | Primary key lookups    |
| `idx_congress_status_date` | congress, status, introduced_date    | Recent bills by status |
| `idx_sponsor_date`         | sponsor_bioguide_id, introduced_date | Bills by politician    |
| `idx_status`               | status                               | Filter by status       |
| `idx_policy_area`          | policy_area (SPARSE)                 | Topic filtering        |
| `idx_subjects`             | subjects                             | Multi-tag search       |
| `idx_title_summary_text`   | title, summary (TEXT)                | Full-text search       |
| `idx_type_date`            | bill_type, introduced_date           | Bills by type          |

**Example queries optimized:**

```python
# Recent bills by status
db.legislation.find({
    "congress": 118,
    "status": "passed_house"
}).sort("introduced_date", -1)

# Bills sponsored by Mike Lee
db.legislation.find({
    "sponsor_bioguide_id": "L000577"
}).sort("introduced_date", -1)

# Search bills
db.legislation.find({"$text": {"$search": "climate change"}})
```

### Contributions Collection

| Index Name                      | Fields                                | Purpose                          |
| ------------------------------- | ------------------------------------- | -------------------------------- |
| `idx_politician_cycle_date`     | bioguide_id, cycle, contribution_date | Contributions by politician/year |
| `idx_politician_industry_cycle` | bioguide_id, industry_code, cycle     | Industry breakdown               |
| `idx_politician_employer`       | bioguide_id, contributor_employer     | Employer aggregation             |
| `idx_state_politician`          | contributor_state, bioguide_id        | Geographic analysis              |
| `idx_amount`                    | amount                                | Large contributions              |
| `idx_contribution_date`         | contribution_date                     | Time-based queries               |
| `idx_cycle`                     | cycle                                 | Election cycle filtering         |

**Example queries optimized:**

```python
# Mike Lee's 2024 contributions
db.contributions.find({
    "bioguide_id": "L000577",
    "cycle": "2024"
})

# Top industries for a politician
db.contributions.aggregate([
    {"$match": {"bioguide_id": "L000577"}},
    {"$group": {
        "_id": "$industry_code",
        "total": {"$sum": "$amount"}
    }},
    {"$sort": {"total": -1}}
])

# California contributors
db.contributions.find({"contributor_state": "CA"})
```

### Votes Collection

| Index Name                  | Fields                                  | Purpose                 |
| --------------------------- | --------------------------------------- | ----------------------- |
| `idx_vote_id`               | vote_id (UNIQUE)                        | Primary key lookups     |
| `idx_chamber_congress_date` | chamber, congress, vote_date            | Recent votes by chamber |
| `idx_bill_id`               | bill_id (SPARSE)                        | Link votes to bills     |
| `idx_result_date`           | result, vote_date                       | Passed/failed votes     |
| `idx_chamber_congress_roll` | chamber, congress, roll_number (UNIQUE) | Unique vote identifier  |

**Example queries optimized:**

```python
# Recent House votes
db.votes.find({
    "chamber": "house",
    "congress": 118
}).sort("vote_date", -1)

# Votes on a specific bill
db.votes.find({"bill_id": "hr-4521-118"})
```

### Politician Votes Collection

| Index Name                   | Fields                        | Purpose            |
| ---------------------------- | ----------------------------- | ------------------ |
| `idx_politician_vote`        | bioguide_id, vote_id          | Voting history     |
| `idx_vote_position`          | vote_id, position             | Vote breakdown     |
| `idx_position`               | position                      | Aye/Nay filtering  |
| `idx_unique_politician_vote` | bioguide_id, vote_id (UNIQUE) | Prevent duplicates |

**Example queries optimized:**

```python
# How Mike Lee voted
db.politician_votes.find({
    "bioguide_id": "L000577"
}).sort("vote_id", -1)

# Who voted Aye on a specific vote
db.politician_votes.find({
    "vote_id": "house-118-2024-123",
    "position": "Aye"
})
```

## Vector Search Index (Atlas Only)

The legislation vector search index **must be created manually** in the MongoDB Atlas UI:

1. Go to Atlas → Your Cluster → Search
2. Click "Create Search Index"
3. Choose "JSON Editor"
4. Use this configuration:

```json
{
    "name": "legislation_vector_index",
    "type": "vectorSearch",
    "fields": [
        {
            "type": "vector",
            "path": "embedding",
            "numDimensions": 1536,
            "similarity": "cosine"
        },
        {
            "type": "filter",
            "path": "status"
        },
        {
            "type": "filter",
            "path": "congress"
        },
        {
            "type": "filter",
            "path": "policy_area"
        }
    ]
}
```

This enables semantic search on bill titles/summaries using OpenAI embeddings.

## Performance Impact

**Before indexes:**

-   Query: `db.politicians.find({"state": "UT"})` → Full collection scan (539 docs examined)
-   Time: 5-10ms

**After indexes:**

-   Query: Same → Index scan (6 docs examined)
-   Time: <1ms

**Compound index benefits:**

```python
# This query uses idx_state_party_chamber_office
db.politicians.find({
    "state": "UT",
    "party": "R",
    "chamber": "senate",
    "in_office": True
})
# Examines only matching documents, not entire collection
```

## Index Maintenance

### When to Rebuild

-   After schema changes
-   If queries seem slow
-   After large data imports
-   MongoDB recommends quarterly for active DBs

### Monitoring

```python
# Check index usage
db.politicians.aggregate([
    {"$indexStats": {}}
])

# Explain a query
db.politicians.find({"state": "UT"}).explain("executionStats")
```

### Removing Unused Indexes

```python
# Drop a specific index
db.politicians.drop_index("idx_name")

# Drop all except _id
db.politicians.drop_indexes()
```

## Common Issues

### Issue: "Index already exists"

**Solution:** Drop and recreate with `--drop` flag

```bash
uv run python scripts/setup_indexes.py --drop
```

### Issue: Text index not working

**Cause:** Only one text index per collection allowed
**Solution:** Drop conflicting text indexes first

### Issue: Unique constraint violation

**Cause:** Duplicate data in collection
**Solution:** Clean data before creating unique indexes

```python
# Find duplicates
db.politicians.aggregate([
    {"$group": {
        "_id": "$bioguide_id",
        "count": {"$sum": 1}
    }},
    {"$match": {"count": {"$gt": 1}}}
])
```

## Best Practices

1. **Create indexes before heavy querying** - Much faster than adding them later
2. **Use compound indexes** - MongoDB can use left-to-right prefixes
3. **Keep sparse indexes** - Don't index null/missing values unless needed
4. **Monitor index usage** - Remove unused indexes (they slow down writes)
5. **Test with explain()** - Verify indexes are actually being used

## Usage in Code

### Python (Sync)

```python
from src.database.indexes import create_all_indexes_sync, get_database_sync

db = get_database_sync()
create_all_indexes_sync(db)
```

### Python (Async)

```python
from src.database.indexes import create_all_indexes_async

await create_all_indexes_async()
```

### Streamlit (Cached)

```python
import streamlit as st
from src.database.indexes import create_all_indexes_sync

@st.cache_resource
def setup_indexes():
    from src.database.indexes import get_database_sync
    db = get_database_sync()
    create_all_indexes_sync(db)
    return True

# Run once on app start
setup_indexes()
```

## Additional Resources

-   [MongoDB Indexes Docs](https://www.mongodb.com/docs/manual/indexes/)
-   [Query Optimization](https://www.mongodb.com/docs/manual/core/query-optimization/)
-   [Atlas Vector Search](https://www.mongodb.com/docs/atlas/atlas-vector-search/)
