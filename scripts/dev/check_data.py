from pymongo import MongoClient
from src.config.settings import settings

client = MongoClient(settings.MONGODB_URI)
db = client[settings.MONGODB_DATABASE]

print("📊 Current Data Status:")
print(f"Politicians: {db.politicians.count_documents({})}")
print(f"  - With FEC IDs: {db.politicians.count_documents({'fec_candidate_id': {'$exists': True, '$ne': None}})}")
print()
print(f"Bills: {db.legislation.count_documents({})}")
print(f"  - House (hr): {db.legislation.count_documents({'bill_type': 'hr'})}")
print(f"  - Senate (s): {db.legislation.count_documents({'bill_type': 's'})}")
print(f"  - By Status:")
for status in ['introduced', 'in_committee', 'passed_house', 'passed_senate', 'became_law']:
    count = db.legislation.count_documents({'status': status})
    if count > 0:
        print(f"    • {status}: {count}")
print()
print(f"Contributions: {db.contributions.count_documents({})}")
print(f"Votes: {db.votes.count_documents({})}")
print(f"Politician Votes: {db.politician_votes.count_documents({})}")
