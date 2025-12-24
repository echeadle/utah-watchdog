from pymongo import MongoClient
from src.config.settings import settings

client = MongoClient(settings.MONGODB_URI)
db = client[settings.MONGODB_DATABASE]

# Get all states with senators
pipeline = [
    {"$match": {"chamber": "senate", "in_office": True}},
    {"$group": {
        "_id": "$state",
        "count": {"$sum": 1},
        "senators": {"$push": "$full_name"}
    }},
    {"$sort": {"_id": 1}}
]

states_with_senators = list(db.politicians.aggregate(pipeline))

print(f"States with senators in database: {len(states_with_senators)}")
print(f"Expected: 50 states\n")

# Find states with only 1 senator
print("States with only 1 senator:")
for state in states_with_senators:
    if state["count"] == 1:
        print(f"  {state['_id']}: {state['senators'][0]}")

print(f"\nTotal senators in database: {sum(s['count'] for s in states_with_senators)}")
print("Expected: 100 senators (2 per state)")
