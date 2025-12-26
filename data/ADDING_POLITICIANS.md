# Adding Politicians to the Registry

Quick guide for adding new politicians to track.

## Method 1: Interactive Mode (Recommended)

Just run with `--add` and answer the prompts:

```bash
uv run python scripts/maintenance/ensure_tracked_politicians.py --add
```

You'll be prompted for:
- **Bioguide ID** (required) - e.g., C001114
- **Full Name** (required) - e.g., John Curtis
- **Tracking Reason** (required) - e.g., Current Representative UT-03
- **Priority** (optional, default: medium) - high/medium/low
- **FEC ID** (optional) - e.g., H8UT03132
- **OpenSecrets ID** (optional) - e.g., N00041091
- **GovTrack ID** (optional) - e.g., 412740
- **Notes** (optional) - Any additional info

The script will:
1. ✅ Validate the bioguide ID format
2. ✅ Show you a preview
3. ✅ Ask for confirmation
4. ✅ Add to registry and sort alphabetically
5. ✅ Update the timestamp

## Method 2: Command Line (For Automation)

Provide all required info on the command line:

```bash
uv run python scripts/maintenance/ensure_tracked_politicians.py --add \
    --bioguide-id M001221 \
    --name "Blake Moore" \
    --fec-id H0UT01133 \
    --opensecrets-id N00045426 \
    --reason "Current Representative UT-01" \
    --priority high \
    --notes "Elected 2020"
```

**Required args**:
- `--bioguide-id` - Congressional Bioguide ID
- `--name` - Full name
- `--reason` - Why tracking this politician

**Optional args**:
- `--priority` - high/medium/low (default: medium)
- `--fec-id` - FEC candidate ID
- `--opensecrets-id` - OpenSecrets ID
- `--govtrack-id` - GovTrack ID
- `--notes` - Additional notes

## Finding IDs

### Bioguide ID
**Most Important** - This is the canonical identifier

1. Go to https://bioguide.congress.gov/
2. Search for the politician
3. ID is in the URL: `bioguide.congress.gov/search/bio/C001114`
4. Format: One letter + 6 digits (e.g., `C001114`)

### FEC Candidate ID
For campaign finance tracking

1. Go to https://www.fec.gov/data/candidates/
2. Search for the politician
3. Click on their name
4. ID is in the candidate info (e.g., `H8UT03132`)

**Note**: Politicians who run for different offices get different FEC IDs!
- House: Starts with `H`
- Senate: Starts with `S`

### OpenSecrets ID
For campaign finance and lobbying data

1. Go to https://www.opensecrets.org/
2. Search for the politician
3. ID is in the URL (e.g., `N00041091`)

### GovTrack ID
For legislative tracking

1. Go to https://www.govtrack.us/
2. Search for the politician
3. ID is in the URL (e.g., `412740`)

## Examples

### Current Officeholder (High Priority)

```bash
uv run python scripts/maintenance/ensure_tracked_politicians.py --add \
    --bioguide-id M001221 \
    --name "Blake Moore" \
    --reason "Current Representative UT-01" \
    --priority high
```

### Recently Retired (Medium Priority)

```bash
uv run python scripts/maintenance/ensure_tracked_politicians.py --add \
    --bioguide-id R000615 \
    --name "Mitt Romney" \
    --reason "Senator 2019-2025, retiring" \
    --priority medium \
    --notes "Not seeking reelection in 2024"
```

### Historical Figure (Low Priority)

```bash
uv run python scripts/maintenance/ensure_tracked_politicians.py --add \
    --bioguide-id H001032 \
    --name "Orrin Hatch" \
    --reason "Senator 1977-2019, historical data" \
    --priority low
```

### Office Transition (Multiple FEC IDs)

For someone like John Curtis moving from House to Senate:

```bash
uv run python scripts/maintenance/ensure_tracked_politicians.py --add \
    --bioguide-id C001114 \
    --name "John Curtis" \
    --fec-id H8UT03132 \
    --reason "Representative UT-03 (2017-2025), Senator-elect (2025-)" \
    --priority high \
    --notes "Transitioning from House to Senate, also has Senate FEC ID S4UT00322"
```

**Note**: You can manually edit the JSON file later to add the second FEC ID under a different key like `fec_senate_candidate_id`.

## After Adding

The script will tell you next steps:

```
✅ Politician added to registry!

Next steps:
  1. Run sync to add to database:
     uv run python scripts/maintenance/ensure_tracked_politicians.py

  2. Commit the change:
     git add data/tracked_politicians.json
     git commit -m 'Add Blake Moore to tracked politicians'
```

### Step 1: Sync to Database

```bash
uv run python scripts/maintenance/ensure_tracked_politicians.py
```

This creates/updates the database record with `tracked: true`.

### Step 2: Commit the Change

```bash
git add data/tracked_politicians.json
git commit -m "Add [Name] to tracked politicians"
git push
```

## Troubleshooting

### "Politician already exists"

```
❌ Politician C001114 already exists in registry
   Existing: John Curtis
   Use manual edit to update
```

**Solution**: Edit `data/tracked_politicians.json` directly to update their info.

### "Invalid bioguide ID format"

```
❌ Invalid bioguide ID format. Should be: Letter + 6 digits (e.g., C001114)
```

**Solution**: Check the format. Must be exactly 1 letter + 6 numbers (e.g., `C001114`, not `c1114`).

### Accidentally added wrong person

1. Edit `data/tracked_politicians.json`
2. Remove the entry
3. Commit: `git commit -am "Remove incorrect entry"`

The database record won't be automatically deleted (by design), but you can manually remove it if needed.

## Quick Reference

| Task | Command |
|------|---------|
| Add (interactive) | `uv run python scripts/maintenance/ensure_tracked_politicians.py --add` |
| Add (command line) | `... --add --bioguide-id X000000 --name "Name" --reason "Reason"` |
| Sync to database | `uv run python scripts/maintenance/ensure_tracked_politicians.py` |
| Verify sync | `uv run python scripts/maintenance/ensure_tracked_politicians.py --verify-only` |
| Help | `uv run python scripts/maintenance/ensure_tracked_politicians.py --help` |

## Best Practices

1. **Always add current officeholders** with `priority: high`
2. **Include FEC IDs** if you plan to track campaign finance
3. **Document office transitions** in the tracking reason or notes
4. **Keep retired politicians** at medium/low priority rather than removing
5. **Commit after adding** to maintain version history
6. **Run sync immediately** so the database matches the registry
