# Data Registry

This directory contains manually curated data registries that define which politicians and entities to track.

## Purpose

The registries solve critical problems with automated data collection:

1. **Politicians disappearing**: When someone leaves office, they disappear from APIs but we still need their historical data
2. **Office transitions**: Politicians moving from House to Senate (like John Curtis) can fall through the cracks
3. **ID management**: Different systems use different IDs (FEC, OpenSecrets, GovTrack, etc.)
4. **Historical tracking**: We want to keep data for retired politicians for historical analysis

## Files

### `tracked_politicians.json`

**Purpose**: Canonical list of Utah federal politicians to always track, regardless of current office status.

**Use cases**:
- Ensures campaign finance data is never orphaned
- Tracks politicians through office transitions
- Maintains historical records for retired politicians
- Provides a single source of truth for Utah delegation

**Structure**:
```json
{
  "politicians": [
    {
      "bioguide_id": "C001114",
      "full_name": "John Curtis",
      "identifiers": {
        "fec_candidate_id": "H8UT03132",
        "fec_senate_candidate_id": "S4UT00322",
        "opensecrets_id": "N00041091"
      },
      "tracking_reason": "Representative UT-03 (2017-2025), Senator-elect (2025-)",
      "priority": "high"
    }
  ]
}
```

**Priority levels**:
- `high`: Current officeholders, update frequently
- `medium`: Recently retired, keep updated
- `low`: Historical figures, archive only

## Usage

### Ensure Tracked Politicians Exist

Run this script to sync the registry to the database:

```bash
# Verify what would change (dry run)
uv run python scripts/maintenance/ensure_tracked_politicians.py --verify-only

# Apply changes
uv run python scripts/maintenance/ensure_tracked_politicians.py

# Only sync high-priority politicians
uv run python scripts/maintenance/ensure_tracked_politicians.py --priority high
```

### Adding a New Politician

1. Edit `tracked_politicians.json`
2. Add the politician with their bioguide_id and identifiers
3. Run the sync script
4. The politician will be created in the database and marked as "tracked"

### When to Add Someone

**Always add**:
- All current Utah federal legislators
- Politicians in transition (like John Curtis, House → Senate)
- Recent retirees whose campaign finance data is still relevant

**Consider adding**:
- Historical figures for research purposes
- Candidates running for federal office from Utah

**Don't add**:
- Politicians from other states (unless specifically tracking them)
- Failed candidates with no office history

## Integration with Data Pipeline

### How It Works

1. **Manual Registry** (`tracked_politicians.json`): You maintain the list
2. **Sync Script** (`ensure_tracked_politicians.py`): Ensures database matches registry
3. **Database** (MongoDB): Stores full politician records with `tracked: true` flag
4. **Ingesters**: Update tracked politicians but never delete them

### Data Flow

```
tracked_politicians.json
         ↓
   [Sync Script]
         ↓
    MongoDB Politicians
         ↓
  ┌──────┴──────┐
  ↓             ↓
FEC Ingester  Congress API
  ↓             ↓
Contributions  Office History
```

### Protected Fields

When a politician is marked `tracked: true`:
- ✅ **Can be updated**: party, chamber, in_office, contact info
- ✅ **Can be appended**: office_history, committees
- ❌ **Cannot be deleted**: Record stays in database forever
- ❌ **Cannot remove tracking**: Once tracked, always tracked

## Enhanced Politician Model

Tracked politicians support enhanced data:

```python
{
  "bioguide_id": "C001114",
  "full_name": "John Curtis",

  # Current office
  "chamber": "senate",
  "state": "UT",
  "in_office": true,

  # Office history (automatically populated)
  "office_history": [
    {
      "chamber": "house",
      "state": "UT",
      "district": 3,
      "term_start": "2017-11-13",
      "term_end": "2025-01-03",
      "party": "R",
      "election_type": "special"
    }
  ],

  # Cross-system identifiers
  "identifiers": {
    "bioguide_id": "C001114",
    "fec_candidate_id": "H8UT03132",
    "fec_senate_candidate_id": "S4UT00322",
    "opensecrets_id": "N00041091",
    "govtrack_id": "412740"
  },

  # Tracking metadata
  "tracked": true,
  "tracking_reason": "Utah Senator",
  "priority": "high"
}
```

## Maintenance

### Regular Tasks

**Monthly**:
- Update identifiers if politicians get new FEC IDs (office changes)
- Adjust priority levels based on relevance

**After Elections**:
- Add newly elected Utah politicians
- Update office transitions (House → Senate, etc.)
- Adjust priorities (winners → high, losers → low)

**After Retirements**:
- Keep politicians in registry (downgrade to medium/low priority)
- Update with final term dates
- Add notes about retirement

### Schema Validation

The registry uses JSON Schema for validation (`tracked_politicians_schema.json`). Validate before committing:

```bash
# If you have a JSON schema validator
jsonschema -i data/tracked_politicians.json data/tracked_politicians_schema.json
```

## Best Practices

1. **Always use bioguide_id**: This is the canonical identifier across all systems
2. **Document transitions**: Use notes field for office changes
3. **Keep identifiers updated**: Especially FEC IDs when politicians run for different offices
4. **Don't delete**: Lower priority instead of removing
5. **Commit with care**: Changes affect production data

## Troubleshooting

### "Politician not showing up in searches"

1. Check if they're in `tracked_politicians.json`
2. Run the sync script: `ensure_tracked_politicians.py`
3. Check database: `db.politicians.find({bioguide_id: "..."})`
4. Verify `tracked: true` field is set

### "Campaign finance data orphaned"

1. Find the bioguide_id in contribution records
2. Add politician to `tracked_politicians.json`
3. Run sync script
4. Re-run campaign finance ingester for that politician

### "John Curtis not appearing"

John Curtis is a special case (House → Senate transition):
- Has TWO FEC candidate IDs (one for House, one for Senate)
- Both are in the registry
- Marked as high priority
- Campaign finance should link to bioguide_id (not FEC ID)

## See Also

- `/src/models/politician.py` - Enhanced politician data model
- `/scripts/maintenance/ensure_tracked_politicians.py` - Sync script
- `/src/ingestion/congress_members.py` - How we fetch current members
- `/src/ingestion/fec.py` - How we link campaign finance
