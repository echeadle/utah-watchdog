# CSV-Based Development Workflow

This directory contains utilities for developing and testing data ingestion without repeatedly hitting the Congress.gov API.

## Workflow

```
API → CSV Files → Database
     ↑           ↓
     └── Verify ─┘
```

## Directory Structure

```
scripts/
  csv-files/          # Scripts for CSV workflow
    update_csv_from_api.py   # Fetch from API → Save to CSV
    ingest_from_csv.py       # Load CSV → Database
    verify_database.py       # Compare Database ↔ CSV
  data/               # CSV data files
    politicians.csv
    bills.csv
```

## Scripts

### 1. update_csv_from_api.py

Fetches fresh data from the Congress.gov API and saves it to CSV files.

**Usage:**

```bash
# Fetch all politicians (all states)
python scripts/csv-files/update_csv_from_api.py --politicians

# Fetch only Utah politicians
python scripts/csv-files/update_csv_from_api.py --politicians --state UT

# Fetch bills (default: House bills, 119th Congress)
python scripts/csv-files/update_csv_from_api.py --bills

# Fetch Senate bills
python scripts/csv-files/update_csv_from_api.py --bills --bill-type s

# Limit number of bills
python scripts/csv-files/update_csv_from_api.py --bills --max-bills 100

# Fetch everything
python scripts/csv-files/update_csv_from_api.py --all

# Specify Congress number
python scripts/csv-files/update_csv_from_api.py --all --congress 118
```

**Output:**
- `scripts/data/politicians.csv`
- `scripts/data/bills.csv`

### 2. ingest_from_csv.py

Reads CSV files and populates the database using the same models and validation as the API ingesters.

**Usage:**

```bash
# Ingest politicians from CSV
python scripts/csv-files/ingest_from_csv.py --politicians

# Ingest bills from CSV
python scripts/csv-files/ingest_from_csv.py --bills

# Ingest everything
python scripts/csv-files/ingest_from_csv.py --all
```

**Benefits:**
- Fast: No API rate limits
- Reproducible: Same data every time
- Safe: Test ingestion logic without affecting "live" API data

### 3. verify_database.py

Compares database records with CSV files to verify ingestion accuracy.

**Usage:**

```bash
# Verify politicians
python scripts/csv-files/verify_database.py --politicians

# Verify bills
python scripts/csv-files/verify_database.py --bills

# Verify everything
python scripts/csv-files/verify_database.py --all
```

**Output:**
- Lists records missing from database
- Lists extra records in database (not in CSV)
- Reports field mismatches between CSV and database

## Common Workflows

### Initial Setup: Create Reference Data

```bash
# 1. Fetch fresh data from API and save to CSV (one-time or occasional)
python scripts/csv-files/update_csv_from_api.py --all --congress 119

# 2. Verify CSV files were created
ls -lh scripts/data/
```

### Development: Test Ingestion Logic

```bash
# 1. Make changes to your ingestion code
# 2. Test with CSV data (fast, no API calls)
python scripts/csv-files/ingest_from_csv.py --all

# 3. Verify ingestion worked correctly
python scripts/csv-files/verify_database.py --all
```

### Debugging: Compare Expected vs Actual

```bash
# 1. Ingest from CSV (known good data)
python scripts/csv-files/ingest_from_csv.py --politicians

# 2. Run your API ingester
python -m src.ingestion.congress_members

# 3. Verify database matches CSV
python scripts/csv-files/verify_database.py --politicians
```

## CSV File Formats

### politicians.csv

Columns:
- `bioguide_id`: Unique identifier
- `first_name`, `last_name`, `full_name`
- `party`: D, R, I, or O
- `state`: Two-letter code (e.g., UT)
- `chamber`: senate or house
- `district`: House district number (empty for senators)
- `title`: Senator or Representative
- `in_office`: True/False
- `website`, `phone`, `office`: Contact info
- `last_updated`: ISO timestamp

### bills.csv

Columns:
- `bill_id`: Unique identifier (e.g., hr-1234-119)
- `bill_type`, `number`, `congress`
- `title`, `short_title`, `summary`
- `status`: introduced, in_committee, passed_house, etc.
- `introduced_date`, `latest_action_date`, `latest_action_text`
- `sponsor_bioguide_id`: Primary sponsor
- `policy_area`: Main topic
- `subjects`: Pipe-separated topics (e.g., "Health|Medicare")
- `congress_gov_url`: Link to bill
- `last_updated`: ISO timestamp

## Benefits of This Approach

1. **Faster Development**: No API rate limits during testing
2. **Reproducible**: Same dataset every time you run tests
3. **Offline Work**: Can develop without network access
4. **Easy Debugging**: CSV files are human-readable
5. **Historical Snapshots**: Track how API data changes over time
6. **Verification**: Compare ingestion results against known good data

## Tips

- Update CSV files weekly/monthly to keep data fresh
- Commit CSV files to git for team collaboration (optional)
- Use `--max-bills` to create smaller test datasets
- Use `--state UT` to work with just Utah's delegation
- Keep old CSV files to test data migration scenarios
