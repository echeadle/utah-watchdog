"""
Fetch recent Senate votes and store in MongoDB.

This script:
1. Finds bills with recorded votes from Congress.gov
2. Fetches vote XML from Senate.gov
3. Parses and stores the data

Run with: uv run python scripts/fetch_votes.py
"""

import time
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from src.config import settings, CONGRESS_GOV_BASE_URL, CURRENT_CONGRESS
from src.database import get_sync_database, close_sync_client
from src.config.constants import COLLECTION_VOTES


def fetch_congress_api(endpoint: str, params: dict = None) -> dict | None:
    """Fetch from Congress.gov API."""
    url = f"{CONGRESS_GOV_BASE_URL}{endpoint}"
    base_params = {"api_key": settings.CONGRESS_GOV_API_KEY, "format": "json"}
    if params:
        base_params.update(params)
    
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, params=base_params)
        if response.status_code == 200:
            return response.json()
        return None


def fetch_senate_vote_xml(url: str) -> str | None:
    """Fetch vote XML from Senate.gov."""
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url)
        if response.status_code == 200:
            return response.text
        print(f"   ❌ Failed to fetch XML: {response.status_code}")
        return None


def parse_senate_vote_xml(xml_text: str) -> dict | None:
    """Parse Senate vote XML into structured data."""
    try:
        root = ET.fromstring(xml_text)
        
        # Vote metadata
        vote_data = {
            "congress": int(root.findtext("congress") or CURRENT_CONGRESS),
            "session": int(root.findtext("session") or 1),
            "roll_call": int(root.findtext("vote_number") or 0),
            "chamber": "senate",
            "vote_date": root.findtext("vote_date"),
            "question": root.findtext("vote_question_text") or root.findtext("question"),
            "result": root.findtext("vote_result") or root.findtext("result"),
            "title": root.findtext("vote_title"),
        }
        
        # Create unique vote_id
        vote_data["vote_id"] = f"senate-{vote_data['congress']}-{vote_data['session']}-{vote_data['roll_call']}"
        
        # Vote counts
        count_elem = root.find("count")
        if count_elem is not None:
            vote_data["yeas"] = int(count_elem.findtext("yeas") or 0)
            vote_data["nays"] = int(count_elem.findtext("nays") or 0)
            vote_data["present"] = int(count_elem.findtext("present") or 0)
            vote_data["absent"] = int(count_elem.findtext("absent") or 0)
        
        # Individual senator votes
        members = []
        for member_elem in root.findall(".//member"):
            member = {
                "name": member_elem.findtext("member_full"),
                "first_name": member_elem.findtext("first_name"),
                "last_name": member_elem.findtext("last_name"),
                "party": member_elem.findtext("party"),
                "state": member_elem.findtext("state"),
                "vote": member_elem.findtext("vote_cast"),
                "lis_member_id": member_elem.findtext("lis_member_id"),
            }
            members.append(member)
        
        vote_data["members"] = members
        vote_data["last_updated"] = datetime.now(timezone.utc)
        
        return vote_data
        
    except Exception as e:
        print(f"   ❌ Error parsing XML: {e}")
        return None


def find_bills_with_votes(limit: int = 50) -> list[dict]:
    """
    Find recent bills that have recorded votes.
    
    Returns list of vote info (chamber, roll number, url, etc.)
    """
    votes_found = []
    seen_rolls = set()  # Avoid duplicates
    
    # Check recent Senate bills
    print("🔍 Searching for bills with recorded votes...")
    
    for bill_type in ["s", "hr", "sjres", "hjres"]:
        print(f"   Checking {bill_type.upper()} bills...")
        
        data = fetch_congress_api(
            f"/bill/{CURRENT_CONGRESS}/{bill_type}",
            {"limit": 50, "sort": "updateDate+desc"}
        )
        
        if not data:
            continue
        
        bills = data.get("bills", [])
        
        for bill in bills:
            bill_num = bill.get("number")
            
            # Fetch bill actions to find votes
            actions_data = fetch_congress_api(
                f"/bill/{CURRENT_CONGRESS}/{bill_type}/{bill_num}/actions",
                {"limit": 100}
            )
            
            if not actions_data:
                continue
            
            for action in actions_data.get("actions", []):
                recorded_votes = action.get("recordedVotes", [])
                
                for rv in recorded_votes:
                    roll = rv.get("rollNumber")
                    chamber = rv.get("chamber")
                    
                    # Only process Senate votes for now (we have that parser working)
                    # Skip duplicates
                    if chamber == "Senate" and roll not in seen_rolls:
                        seen_rolls.add(roll)
                        votes_found.append({
                            "bill_type": bill_type,
                            "bill_number": bill_num,
                            "bill_title": bill.get("title"),
                            "chamber": chamber,
                            "roll_number": roll,
                            "congress": rv.get("congress"),
                            "session": rv.get("sessionNumber"),
                            "date": rv.get("date"),
                            "url": rv.get("url"),
                        })
                        
                        print(f"      Found vote: Roll #{roll}")
            
            # Rate limiting
            time.sleep(0.1)
            
            # Stop if we have enough
            if len(votes_found) >= limit:
                return votes_found
    
    return votes_found


def main():
    print("=" * 60)
    print("Fetching Senate Votes")
    print("=" * 60)
    
    db = get_sync_database()
    votes_coll = db[COLLECTION_VOTES]
    politician_votes_coll = db["politician_votes"]
    
    # Create indexes
    votes_coll.create_index("vote_id", unique=True)
    politician_votes_coll.create_index([("vote_id", 1), ("state", 1), ("last_name", 1)], unique=True)
    politician_votes_coll.create_index("state")
    print("✅ Created indexes\n")
    
    # Find bills with votes
    votes_info = find_bills_with_votes(limit=15)
    print(f"\n📋 Found {len(votes_info)} Senate votes to process\n")
    
    if not votes_info:
        print("No votes found. Try running again later.")
        close_sync_client()
        return
    
    votes_stored = 0
    utah_votes_stored = 0
    
    for vote_info in votes_info:
        roll = vote_info["roll_number"]
        url = vote_info["url"]
        
        print(f"📥 Processing Roll Call #{roll}...")
        print(f"   Bill: {vote_info.get('bill_title', 'N/A')[:50]}...")
        
        # Fetch XML
        xml_text = fetch_senate_vote_xml(url)
        if not xml_text:
            continue
        
        # Parse XML
        vote_data = parse_senate_vote_xml(xml_text)
        if not vote_data:
            continue
        
        # Add bill info
        vote_data["bill_type"] = vote_info.get("bill_type")
        vote_data["bill_number"] = vote_info.get("bill_number")
        vote_data["bill_title"] = vote_info.get("bill_title")
        vote_data["source_url"] = url
        
        # Extract members before storing (we'll store them separately)
        members = vote_data.pop("members", [])
        
        # Store the vote
        votes_coll.update_one(
            {"vote_id": vote_data["vote_id"]},
            {"$set": vote_data},
            upsert=True
        )
        votes_stored += 1
        
        # Store individual politician votes
        for member in members:
            politician_vote = {
                "vote_id": vote_data["vote_id"],
                "state": member.get("state"),
                "last_name": member.get("last_name"),
                "first_name": member.get("first_name"),
                "full_name": member.get("name"),
                "party": member.get("party"),
                "position": member.get("vote"),
                "last_updated": datetime.now(timezone.utc),
            }
            
            politician_votes_coll.update_one(
                {
                    "vote_id": vote_data["vote_id"],
                    "state": member.get("state"),
                    "last_name": member.get("last_name"),
                },
                {"$set": politician_vote},
                upsert=True
            )
            
            # Count Utah votes
            if member.get("state") == "UT":
                utah_votes_stored += 1
        
        print(f"   ✅ Stored: {vote_data.get('question', 'N/A')[:50]}...")
        print(f"      Result: {vote_data.get('result')} ({vote_data.get('yeas', 0)}-{vote_data.get('nays', 0)})")
        
        # Be nice to Senate.gov
        time.sleep(0.3)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"   Votes stored: {votes_stored}")
    print(f"   Utah senator votes stored: {utah_votes_stored}")
    print(f"   Total votes in DB: {votes_coll.count_documents({})}")
    print(f"   Total politician votes in DB: {politician_votes_coll.count_documents({})}")
    
    # Show Utah's recent votes
    print("\n" + "=" * 60)
    print("🏔️ UTAH SENATORS' RECENT VOTES")
    print("=" * 60)
    
    utah_votes = list(politician_votes_coll.find({"state": "UT"}).sort("vote_id", -1).limit(10))
    
    for uv in utah_votes:
        # Get vote details
        vote = votes_coll.find_one({"vote_id": uv["vote_id"]})
        if vote:
            print(f"\n   {uv.get('full_name')}: {uv.get('position')}")
            print(f"   Question: {vote.get('question', 'N/A')[:60]}...")
            print(f"   Result: {vote.get('result')}")
    
    close_sync_client()
    
    print("\n" + "=" * 60)
    print("✅ Vote fetching complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()