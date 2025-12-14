"""
Find bills that actually had floor votes.

Run with: uv run python scripts/find_votes.py
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
        return None


def main():
    print("=" * 60)
    print("Finding Bills with Floor Votes")
    print("=" * 60)
    
    # Get recently updated bills - these are more likely to have activity
    print("\n1️⃣ Fetching recent Senate bills...")
    bills_data = fetch(f"/bill/{CURRENT_CONGRESS}/s", {"limit": 20, "sort": "updateDate+desc"})
    
    if not bills_data:
        print("   ❌ Failed to fetch bills")
        return
    
    bills = bills_data.get("bills", [])
    print(f"   Found {len(bills)} bills")
    
    # Check each bill's actions for recorded votes
    print("\n2️⃣ Checking bills for recorded votes...")
    
    for bill in bills:
        bill_type = bill.get("type", "").lower()
        bill_num = bill.get("number")
        title = bill.get("title", "N/A")[:50]
        latest_action = bill.get("latestAction", {}).get("text", "")[:40]
        
        # Skip if clearly not voted on
        if "Introduced" in latest_action or "Referred" in latest_action:
            continue
        
        print(f"\n   📋 {bill_type.upper()}{bill_num}: {title}...")
        print(f"      Latest: {latest_action}...")
        
        # Fetch the bill's actions
        actions_data = fetch(f"/bill/{CURRENT_CONGRESS}/{bill_type}/{bill_num}/actions", {"limit": 50})
        
        if actions_data:
            actions = actions_data.get("actions", [])
            
            for action in actions:
                # Check if this action has recordedVotes
                if "recordedVotes" in action and action["recordedVotes"]:
                    print(f"      🗳️ FOUND RECORDED VOTE!")
                    print(f"         Action: {action.get('text', 'N/A')[:60]}")
                    print(f"         Recorded votes: {action['recordedVotes']}")
                    
                    # This is what we're looking for!
                    # The recordedVotes typically contains URLs to the actual vote data
                    for rv in action["recordedVotes"]:
                        print(f"         📎 {rv}")
                    return  # Found one, let's stop and examine
                
                # Also check for vote-related action types
                action_type = action.get("type", "")
                action_text = action.get("text", "").lower()
                
                if any(word in action_text for word in ["passed", "agreed", "roll no", "yea-nay", "recorded vote"]):
                    print(f"      🔍 Possible vote action: [{action_type}]")
                    print(f"         {action.get('text', 'N/A')[:80]}")
                    print(f"         Keys: {list(action.keys())}")
    
    # Let's also try laws (enacted bills definitely had votes)
    print("\n3️⃣ Checking enacted laws...")
    laws_data = fetch(f"/law/{CURRENT_CONGRESS}", {"limit": 5})
    
    if laws_data:
        laws = laws_data.get("laws", [])
        print(f"   Found {len(laws)} laws")
        
        for law in laws[:3]:
            print(f"\n   📜 Law: {law}")
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()