# Utah Watchdog - Scripts Reference

This directory contains utility scripts for managing data ingestion, database maintenance, and API queries.

---

## Table of Contents

- [Database Management](#database-management)
- [Data Ingestion](#data-ingestion)
- [API Queries](#api-queries)
- [Development Workflow](#development-workflow)

---

## Database Management

### Clear Database
Start fresh by clearing all data from MongoDB. Useful during development when you need to reset.

```bash
# Interactive - asks for confirmation
uv run python scripts/clear_database.py

# Skip confirmation (use with caution!)
uv run python scripts/clear_database.py --yes

# Clear only a specific collection
uv run python scripts/clear_database.py --collection politician_votes

# Clear data AND drop all custom indexes
uv run python scripts/clear_database.py --drop-indexes --yes
```

**Options:**
- `--yes, -y` - Skip confirmation prompt
- `--collection, -c NAME` - Clear only specific collection
- `--drop-indexes` - Also drop all custom indexes (keeps _id)

---

### Fix Politician Votes Index
Fix index issues in the `politician_votes` collection. Run this if you encounter duplicate key errors.

```bash
uv run python scripts/fix_politician_votes_index.py
```

**What it does:**
- Drops incorrect indexes
- Removes records with null bioguide_id
- Creates correct unique index on (vote_id + bioguide_id)

---

## Data Ingestion

### Sync Roll Call Votes
Import House and Senate roll call votes from official sources (Congress.gov, House Clerk XML).

```bash
# Sync House votes (default: 100 votes)
uv run python scripts/sync_votes.py --chamber house

# Sync more votes
uv run python scripts/sync_votes.py --chamber house --max 500

# Sync from specific Congress
uv run python scripts/sync_votes.py --chamber house --congress 118 --max 50

# Sync both chambers (House + Senate)
uv run python scripts/sync_votes.py --chamber both --max 100

# Verbose logging for debugging
uv run python scripts/sync_votes.py --chamber house --max 50 --verbose
```

**Options:**
- `--chamber` - Which chamber: `house`, `senate`, or `both` (default: both)
- `--congress NUMBER` - Congress number (default: 118)
- `--max NUMBER` - Maximum votes per chamber (default: 100)
- `--verbose, -v` - Enable detailed logging

**Note:** Currently only House votes are fully supported. Senate vote ingestion is in development.

---

## API Queries

### Member Service History
Look up any current House or Senate member's complete service record.

```bash
# Search by name (flexible - any format works)
uv run python scripts/member_service_history.py "Mike Lee"
uv run python scripts/member_service_history.py "Lee Mike"
uv run python scripts/member_service_history.py "Lee, Mike"

# Search by last name only
uv run python scripts/member_service_history.py "Romney"
uv run python scripts/member_service_history.py "Curtis"

# Verbose output for debugging
uv run python scripts/member_service_history.py "Mike Lee" --verbose
```

**Examples - Utah Delegation:**

```bash
# Current Utah Senators
uv run python scripts/member_service_history.py "Mike Lee"
uv run python scripts/member_service_history.py "Mitt Romney"

# Current Utah House Members
uv run python scripts/member_service_history.py "John Curtis"
uv run python scripts/member_service_history.py "Blake Moore"
uv run python scripts/member_service_history.py "Celeste Maloy"
uv run python scripts/member_service_history.py "Burgess Owens"
```

**Output includes:**
- Member's full name, party, state
- All terms served in House and/or Senate
- Congress numbers and year ranges
- Total summary of service

**Options:**
- `--verbose, -v` - Show detailed search and API call information

**Search Tips:**
- Works with any name order: "Mike Lee", "Lee Mike", "Lee, Mike"
- Can search by just first or last name: "Lee" or "Mike"
- If multiple matches, shows all and asks you to be more specific
- Only searches currently serving members

---

## Development Workflow

### Starting Fresh

When you need to reset your database and re-sync data:

```bash
# 1. Clear all data
uv run python scripts/clear_database.py --yes

# 2. Sync votes
uv run python scripts/sync_votes.py --chamber house --max 100

# 3. (Future) Sync politicians
# uv run python scripts/sync_politicians.py

# 4. (Future) Sync legislation
# uv run python scripts/sync_legislation.py
```

### Fixing Database Issues

If you encounter index errors:

```bash
# Fix politician_votes indexes
uv run python scripts/fix_politician_votes_index.py

# Or nuclear option - clear and start over
uv run python scripts/clear_database.py --drop-indexes --yes
```

### Testing Queries

Quick test to see if data is loading correctly:

```bash
# Check a member's service history
uv run python scripts/member_service_history.py "Mike Lee" --verbose

# Should show their complete Congressional service record
```

---

## Common Issues & Solutions

### Issue: "E11000 duplicate key error"

**Solution:** Fix indexes or clear collection
```bash
uv run python scripts/fix_politician_votes_index.py
# OR
uv run python scripts/clear_database.py --collection politician_votes --yes
```

### Issue: "No members found matching"

**Cause:** Member search is case-sensitive to spelling, or member is not currently serving

**Solution:** 
- Check spelling
- Try different name formats: "Lee Mike" vs "Mike Lee"
- Try just last name: "Lee"
- Verify member is currently in Congress

### Issue: Rate limiting from Congress.gov API

**Cause:** Too many API requests too quickly

**Solution:** 
- Use `--max` to limit requests
- The scripts have built-in rate limiting (0.3-0.5s delays)
- Get a Congress.gov API key if you don't have one

---

## Script Locations

All scripts are in the `scripts/` directory:

```
scripts/
├── README.md                       # This file
├── clear_database.py               # Database maintenance
├── fix_politician_votes_index.py   # Fix index issues
├── sync_votes.py                   # Import roll call votes
└── member_service_history.py       # Query member service records
```

---

## Environment Variables

Make sure these are set in your `.env` file:

```bash
# MongoDB
MONGODB_URI=mongodb+srv://your-connection-string
MONGODB_DB_NAME=utah_watchdog

# Congress.gov API
CONGRESS_GOV_API_KEY=your-api-key-here
```

Get a free Congress.gov API key at: https://api.congress.gov/sign-up/

---

## Future Scripts (Coming Soon)

- `sync_politicians.py` - Import politician data from Congress.gov
- `sync_legislation.py` - Import bills from Congress.gov and Utah Legislature
- `sync_finances.py` - Import campaign finance data from OpenSecrets/FEC
- `sync_stock_trades.py` - Import congressional stock trades

---

## Contributing

When adding new scripts:

1. Follow the naming convention: `action_noun.py`
2. Add comprehensive `--help` documentation
3. Include example usage in this README
4. Add proper error handling and logging
5. Use the project's coding conventions (see main README)

---

*Last updated: December 2024*
