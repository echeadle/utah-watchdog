# Files to Add to Your Repo

Complete checklist of what to add to get current politician data from Congress.gov API.

## ✅ Step-by-Step Checklist

### 1. Create New Files (Copy from artifacts)

- [ ] `src/ingestion/base.py` - Base ingester class
- [ ] `src/ingestion/congress_members.py` - Congress member ingester  
- [ ] `src/config/constants.py` - Application constants
- [ ] `scripts/sync_members.py` - Manual sync script
- [ ] `.env.example` - Environment variable template
- [ ] `SETUP_INSTRUCTIONS.md` - Setup guide
- [ ] `IMPLEMENTATION_SUMMARY.md` - What was built and why
- [ ] `frontend/pages/1_🏛️_Politicians.py` - Example Streamlit page (optional)

### 2. Update Existing Files

#### `src/config/settings.py`
Add these fields:
```python
# Congress.gov API
CONGRESS_GOV_API_KEY: str

# API Configuration  
API_HOST: str = "0.0.0.0"
API_PORT: int = 8000
CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8501"

@property
def cors_origins_list(self) -> list[str]:
    return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
```

#### `src/ingestion/scheduler.py`
Add this task to `beat_schedule`:
```python
'sync-congress-members-daily': {
    'task': 'src.ingestion.tasks.sync_congress_members',
    'schedule': crontab(hour=5, minute=0),
    'args': (CURRENT_CONGRESS,),
}
```

And add this task function:
```python
@celery_app.task(name='src.ingestion.tasks.sync_congress_members')
def sync_congress_members(congress: int):
    from src.ingestion.congress_members import CongressMembersIngester
    
    async def run():
        ingester = CongressMembersIngester(congress=congress)
        return await ingester.run_full_sync()
    
    return asyncio.run(run())
```

### 3. Create Your .env File

```bash
# Copy the example
cp .env.example .env

# Edit and add your keys
nano .env
```

Required:
- `CONGRESS_GOV_API_KEY` - Get at https://api.congress.gov/sign-up/
- `OPENAI_API_KEY` - Your existing OpenAI key
- `MONGODB_URL` - Your MongoDB connection string

### 4. Install Dependencies

```bash
# Core dependencies
uv add httpx motor pymongo

# For background tasks (optional)
uv add celery redis
```

### 5. Run Your First Sync

```bash
# Populate database with current members
uv run python scripts/sync_members.py

# Watch the output - should see ~541 members processed
```

### 6. Verify It Worked

```python
# Quick verification script
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def check():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.utah_watchdog
    
    # Check Utah delegation
    utah = await db.politicians.find({
        "state": "UT",
        "jurisdiction": "federal",
        "in_office": True
    }).to_list(10)
    
    print("Utah Federal Delegation:")
    for m in utah:
        print(f"  - {m['full_name']} ({m['party']}) - {m['title']}")

asyncio.run(check())
```

Expected output:
```
Utah Federal Delegation:
  - Mike Lee (R) - Senator
  - John Curtis (R) - Senator
  - Blake Moore (R) - Representative
  - Celeste Maloy (R) - Representative
  - Burgess Owens (R) - Representative
```

### 7. Update Your Streamlit App (Optional)

Replace any hardcoded politician data with database queries. See `frontend/pages/1_🏛️_Politicians.py` for a complete example.

Key changes:
```python
# OLD (hardcoded)
politicians = [{"name": "Mitt Romney", ...}]

# NEW (from database)
async def get_politicians():
    db = get_db()
    return await db.politicians.find({
        "state": "UT",
        "in_office": True
    }).to_list()

politicians = asyncio.run(get_politicians())
```

---

## 📁 File Organization

Your repo should look like:

```
utah-watchdog/
├── .env                              ← Create (don't commit!)
├── .env.example                      ← NEW
├── SETUP_INSTRUCTIONS.md             ← NEW
├── IMPLEMENTATION_SUMMARY.md         ← NEW
├── pyproject.toml
├── src/
│   ├── config/
│   │   ├── settings.py              ← UPDATE
│   │   └── constants.py             ← NEW
│   ├── ingestion/
│   │   ├── base.py                  ← NEW
│   │   ├── congress_members.py      ← NEW
│   │   └── scheduler.py             ← UPDATE
│   └── ...
├── scripts/
│   └── sync_members.py               ← NEW
└── frontend/
    └── pages/
        └── 1_🏛️_Politicians.py      ← NEW/UPDATE
```

---

## 🚀 What This Gives You

After completing these steps, you'll have:

1. ✅ **Current Data**: Always-accurate politician information from Congress.gov
2. ✅ **Automatic Updates**: Daily sync at 5 AM UTC (via Celery)
3. ✅ **Manual Control**: Run sync anytime with the script
4. ✅ **Transition Handling**: Automatically marks retired politicians as `in_office=False`
5. ✅ **Foundation**: Base ingester pattern for all future data sources
6. ✅ **Production Ready**: Error handling, logging, statistics

---

## 🔍 Quick Verification Commands

```bash
# 1. Check Python imports work
uv run python -c "from src.ingestion.congress_members import CongressMembersIngester; print('✅ Imports OK')"

# 2. Verify database connection
uv run python -c "from motor.motor_asyncio import AsyncIOMotorClient; c = AsyncIOMotorClient('mongodb://localhost:27017'); print('✅ MongoDB OK')"

# 3. Test API key
uv run python -c "from src.config.settings import settings; print('✅ API key:', settings.CONGRESS_GOV_API_KEY[:10] + '...')"

# 4. Run sync
uv run python scripts/sync_members.py

# 5. Check count
uv run python -c "
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def count():
    c = AsyncIOMotorClient('mongodb://localhost:27017')
    n = await c.utah_watchdog.politicians.count_documents({'in_office': True})
    print(f'✅ Found {n} current politicians')

asyncio.run(count())
"
```

---

## 🆘 Getting Help

If something doesn't work:

1. **Check logs**: Look for error messages in the sync output
2. **Verify .env**: Make sure `CONGRESS_GOV_API_KEY` is set correctly
3. **Test API key**: Visit `https://api.congress.gov/v3/member?api_key=YOUR_KEY` in browser
4. **Check MongoDB**: Make sure it's running and connection string is correct
5. **Read docs**: See `SETUP_INSTRUCTIONS.md` for detailed troubleshooting

Common issues:
- `ModuleNotFoundError` → Run `uv add <module_name>`
- `Missing API key` → Check `.env` file exists and has `CONGRESS_GOV_API_KEY=...`
- `Empty results` → Run sync script first: `uv run python scripts/sync_members.py`
- `Old data` → Check `CURRENT_CONGRESS` in constants.py (should be 118)

---

## 🎯 Next Steps After This Works

1. **Add more data sources**:
   - Voting records from Congress.gov
   - Campaign finance from OpenSecrets
   - Committee assignments
   - Stock trades

2. **Build API endpoints**:
   - `/api/politicians/utah`
   - `/api/politicians/search`
   - `/api/politicians/{id}`

3. **Create agent tools**:
   - `lookup_politician(name="Mike Lee")`
   - `get_utah_delegation()`
   - `compare_politicians([id1, id2])`

4. **Enhance UI**:
   - Politician detail pages
   - Voting record visualizations
   - Campaign finance charts
   - Committee membership

---

## 📋 Commit Message Suggestion

```
feat: Add Congress.gov API integration for current members

- Create base ingester pattern for all data pipelines
- Add Congress member sync from Congress.gov API
- Implement automatic daily sync via Celery
- Add manual sync script for on-demand updates
- Include configuration for API keys and constants
- Add comprehensive setup documentation

Fixes #<issue_number>: Hardcoded politician data
```

---

Good luck! 🚀 You're now pulling real, current data instead of hardcoded values.
