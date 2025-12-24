from pymongo import MongoClient
from src.config.settings import settings

client = MongoClient(settings.MONGODB_URI)
db = client[settings.MONGODB_DATABASE]

# Count Senate members
total_senate = db.politicians.count_documents({"chamber": "senate"})
in_office_senate = db.politicians.count_documents(
    {"chamber": "senate", "in_office": True}
)
not_in_office_senate = db.politicians.count_documents(
    {"chamber": "senate", "in_office": False}
)

print(f"Total Senate members in database: {total_senate}")
print(f"  - In office: {in_office_senate}")
print(f"  - Not in office: {not_in_office_senate}")
print()

# Check how many states are represented
states = db.politicians.distinct("state", {"chamber": "senate", "in_office": True})
print(f"States with senators: {len(states)}")
print("Expected: 100 senators (2 per state x 50 states)")
