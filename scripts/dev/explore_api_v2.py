"""
Deeper dive into Congress.gov API to find votes.

Run with: uv run python scripts/explore_api_v2.py
"""

import httpx
from src.config import settings, CONGRESS_GOV_BASE_URL, CURRENT_CONGRESS


def fetch(endpoint: str, params: dict = None):
    """Fetch from API."""
    url = f"{CONGRESS_GOV_BASE_URL}{endpoint}"
    base_params = {"api_key": settings.CONGRESS_GOV_API_KEY, "format": "json"}
    if params:
        base_params.update(params)
    
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, params=base_params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ {response.status_code} for {endpoint}")
            return None


def main():
    print("=" * 60)
    print("Deep Dive: Finding Vote Data")
    print("=" * 60)
    
    # 1. Look at Mike Lee's member details more closely
    print("\n1️⃣ Checking Mike Lee's member record...")
    member_data = fetch("/member/L000577")
    
    if member_data and "member" in member_data:
        member = member_data["member"]
        print(f"   All keys in member record:")
        for key in sorted(member.keys()):
            value = member[key]
            if isinstance(value, dict) and "url" in value:
                print(f"   📎 {key}: has URL -> {value.get('url', '')[:60]}...")
            elif isinstance(value, dict) and "count" in value:
                print(f"   📊 {key}: count = {value.get('count')}")
            elif isinstance(value, str) and len(value) < 50:
                print(f"   📝 {key}: {value}")
            else:
                print(f"   📦 {key}: {type(value).__name__}")
    
    # 2. Check if sponsored legislation leads to votes
    print("\n2️⃣ Checking sponsored legislation...")
    sponsored_data = fetch("/member/L000577/sponsored-legislation", {"limit": 3})
    
    if sponsored_data:
        print(f"   Keys: {list(sponsored_data.keys())}")
        bills = sponsored_data.get("sponsoredLegislation", [])
        if bills:
            print(f"   Found {len(bills)} sponsored bills")
            bill = bills[0]
            print(f"   First bill keys: {list(bill.keys())}")
            print(f"   Bill: {bill.get('title', 'N/A')[:60]}...")
            
            # Get the bill number and type to fetch details
            if "number" in bill and "type" in bill:
                bill_type = bill["type"].lower()
                bill_num = bill["number"]
                print(f"\n   Fetching bill details for {bill_type}{bill_num}...")
                
                bill_detail = fetch(f"/bill/{CURRENT_CONGRESS}/{bill_type}/{bill_num}")
                if bill_detail and "bill" in bill_detail:
                    detail = bill_detail["bill"]
                    print(f"   Bill detail keys: {list(detail.keys())}")
                    
                    # Check for actions (votes are often in actions)
                    if "actions" in detail:
                        print(f"   📋 Has 'actions' key!")
                        actions_url = detail["actions"].get("url") if isinstance(detail["actions"], dict) else None
                        if actions_url:
                            print(f"      Actions URL: {actions_url[:60]}...")
    
    # 3. Check the bill actions endpoint directly
    print("\n3️⃣ Checking bill actions...")
    # Let's try a known bill that likely had votes
    actions_data = fetch(f"/bill/{CURRENT_CONGRESS}/s/1/actions")
    if actions_data:
        print(f"   Keys: {list(actions_data.keys())}")
        actions = actions_data.get("actions", [])
        print(f"   Found {len(actions)} actions")
        for action in actions[:5]:
            action_type = action.get("type", "N/A")
            text = action.get("text", "N/A")[:60]
            print(f"   - [{action_type}] {text}...")
            
            # Check if this action has recordedVotes
            if "recordedVotes" in action:
                print(f"     🗳️ HAS RECORDED VOTES!")
                print(f"     {action['recordedVotes']}")
    
    # 4. Let's try the roll call vote endpoint format
    print("\n4️⃣ Trying roll call vote endpoints...")
    
    # Try different URL patterns for votes
    test_patterns = [
        "/rollcall",
        "/roll-call", 
        f"/congress/{CURRENT_CONGRESS}/votes",
        f"/vote",
        f"/votes",
    ]
    
    for pattern in test_patterns:
        data = fetch(pattern, {"limit": 1})
        if data:
            print(f"   ✅ {pattern} works! Keys: {list(data.keys())}")
        else:
            print(f"   ❌ {pattern} - not found")
    
    print("\n" + "=" * 60)
    print("Exploration Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()