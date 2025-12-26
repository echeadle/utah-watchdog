# Tracked Politicians System - Quick Start Guide

## The Problem You Had

**John Curtis disappeared from the list** because he transitioned from Representative (UT-03) to Senator-elect. The automated systems only track "current" officeholders, so when someone changes offices or retires, they fall through the cracks and their campaign finance data becomes orphaned.

## The Solution

I've created a **Tracked Politicians Registry** system that ensures Utah politicians are never lost, even when they:
- Leave office
- Transition between positions (House → Senate)
- Retire
- Lose elections

## How It Works

### 1. Manual Registry (`data/tracked_politicians.json`)

This is YOUR canonical list of who to track. It includes:

- **All current Utah federal legislators**
- **John Curtis** (with both House and Senate FEC IDs)
- **Historical figures** (like Orrin Hatch) for research
- **Cross-system identifiers** (FEC, OpenSecrets, GovTrack, etc.)

Example entry:
```json
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
```

### 2. Enhanced Politician Model

Politicians now have:
- `office_history[]` - Track all positions ever held
- `identifiers{}` - All IDs across different systems
- `tracked: true` - Flag preventing deletion
- `priority` - Update frequency (high/medium/low)

### 3. Sync Script

Ensures the database matches your registry:

```bash
# See what would change (dry run)
uv run python scripts/maintenance/ensure_tracked_politicians.py --verify-only

# Apply changes
uv run python scripts/maintenance/ensure_tracked_politicians.py
```

## Fixing the John Curtis Issue

### Immediate Fix

1. **Run the sync script**:
   ```bash
   uv run python scripts/maintenance/ensure_tracked_politicians.py
   ```

2. **John Curtis will be restored** with:
   - ✅ Marked as `tracked: true` (never deleted)
   - ✅ Both FEC IDs (House H8UT03132 + Senate S4UT00322)
   - ✅ High priority for updates
   - ✅ Notes about his transition

3. **His campaign finance data is preserved** because contributions link to `bioguide_id`, not office

### Going Forward

**After each election or office change**:
1. Update `data/tracked_politicians.json` with new information
2. Run the sync script
3. Politicians are automatically protected from deletion

## Usage Examples

### Add a New Politician

Edit `data/tracked_politicians.json`:
```json
{
  "bioguide_id": "X000123",
  "full_name": "New Politician",
  "identifiers": {
    "fec_candidate_id": "H4UT01234"
  },
  "tracking_reason": "Current Representative UT-01",
  "priority": "high"
}
```

Then run:
```bash
uv run python scripts/maintenance/ensure_tracked_politicians.py
```

### Update Existing Politician

Just edit their entry in `tracked_politicians.json` and run the script. The database will be updated automatically.

### Handle Office Transitions

When someone transitions (like John Curtis):
1. Add their new FEC ID to `identifiers`
2. Update `tracking_reason` to note both offices
3. Keep priority as `high`
4. The system handles the rest!

## Priority Levels

- **`high`**: Current officeholders → Update frequently
- **`medium`**: Recent retirees → Keep updated
- **`low`**: Historical figures → Archive only

You can sync only high-priority:
```bash
uv run python scripts/maintenance/ensure_tracked_politicians.py --priority high
```

## Current Tracked Politicians

I've pre-populated the registry with:

✅ **Current Senators**:
- Mike Lee
- Mitt Romney (retiring 2025)

✅ **Current Representatives**:
- Blake Moore (UT-01)
- Celeste Maloy (UT-02)
- Burgess Owens (UT-04)

✅ **Transitioning**:
- John Curtis (UT-03 House → Senate)

✅ **Historical**:
- Orrin Hatch (Former Senator)
- Jason Chaffetz (Former Rep UT-03)

## Integration Points

### 1. Campaign Finance
- Contributions link to `bioguide_id` (permanent)
- Never orphaned even if politician changes office
- John Curtis's House contributions stay linked

### 2. Congress API Sync
- Updates current office info
- Adds to `office_history` when office changes
- Never deletes tracked politicians

### 3. FEC Sync
- Uses identifiers to find correct FEC ID
- Handles multiple IDs (House vs Senate)
- Links via bioguide_id

## Recommendations

### For Your Use Case

1. **JSON format is perfect** for your needs because:
   - ✅ Human-readable and editable
   - ✅ Version control friendly (git diff)
   - ✅ Schema validation
   - ✅ Easy to parse programmatically
   - ✅ Industry standard for configuration

2. **Keep it in git** so you have:
   - Full history of changes
   - Who added/removed politicians
   - When transitions occurred

3. **Update quarterly** or after elections:
   - Add new winners
   - Downgrade losers to low priority
   - Update office transitions

### Alternative Approaches Considered

❌ **Database-only**: Loses manual curation, no version history
❌ **CSV**: Harder to handle nested data (identifiers, office_history)
❌ **YAML**: Less tooling support, more whitespace issues
✅ **JSON with schema**: Best balance of human-editable + validated

## Maintenance Workflow

### After an Election

```bash
# 1. Edit the registry
vim data/tracked_politicians.json

# 2. Add winners, update transitions
# Example: New senator elected

# 3. Validate (if you have jsonschema tool)
jsonschema -i data/tracked_politicians.json data/tracked_politicians_schema.json

# 4. Sync to database
uv run python scripts/maintenance/ensure_tracked_politicians.py

# 5. Commit changes
git add data/tracked_politicians.json
git commit -m "Update registry after 2024 election"
```

### Monthly Check

```bash
# Verify everything is in sync
uv run python scripts/maintenance/ensure_tracked_politicians.py --verify-only
```

## Files Created

- `data/tracked_politicians.json` - Your registry
- `data/tracked_politicians_schema.json` - Validation schema
- `data/README.md` - Detailed documentation
- `scripts/maintenance/ensure_tracked_politicians.py` - Sync script
- `src/models/politician.py` - Enhanced data model (updated)

## Questions?

**Q: What if I forget to run the sync script?**
A: No problem! Run it anytime. It's idempotent (safe to run multiple times).

**Q: Will this affect existing data?**
A: No, it only adds/updates. Never deletes. Your existing politicians are safe.

**Q: Can I track politicians from other states?**
A: Yes! Just add them to the registry. The system works for any federal politician.

**Q: What about state legislators?**
A: The model supports it, but you'd need state-level data sources. Start with federal for now.

## Next Steps

1. **Run the sync script now** to protect your current data
2. **Review the registry** - add/remove as needed
3. **Set up a quarterly reminder** to update after elections
4. **Update your campaign finance workflow** to use bioguide_id consistently

---

**Bottom Line**: John Curtis and all Utah politicians are now permanently tracked. They'll never disappear from your system again, even when they change offices or retire. 🎉
