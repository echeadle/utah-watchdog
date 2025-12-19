"""
Explore the Congress.gov API to find correct endpoints.

Run with: uv run python scripts/explore_api.py
"""

import httpx
from src.config import settings, CONGRESS_GOV_BASE_URL, CURRENT_CONGRESS


def test_endpoint(name: str, endpoint: str):
    """Test if an endpoint works."""
    url = f"{CONGRESS_GOV_BASE_URL}{endpoint}"
    params = {"api_key": settings.CONGRESS_GOV_API_KEY, "format": "json", "limit": 1}
    
    print(f"\n🔍 Testing: {name}")
    print(f"   URL: {url}")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS! Keys: {list(data.keys())}")
                # Show a preview of what's in the response
                for key, value in data.items():
                    if isinstance(value, list) and len(value) > 0:
                        print(f"   📦 {key}: {len(value)} items")
                        if isinstance(value[0], dict):
                            print(f"      First item keys: {list(value[0].keys())[:5]}...")
                    elif isinstance(value, dict):
                        print(f"   📦 {key}: {list(value.keys())[:5]}...")
                return data
            else:
                print(f"   ❌ {response.status_code}: {response.text[:100]}")
                return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def main():
    print("=" * 60)
    print("Exploring Congress.gov API")
    print("=" * 60)
    
    # Test various endpoints
    endpoints = [
        ("Member list", "/member"),
        ("Specific member (Mike Lee)", "/member/L000577"),
        ("Member votes (might not exist)", "/member/L000577/votes"),
        ("Senate votes", f"/vote/{CURRENT_CONGRESS}/senate"),
        ("House votes", f"/vote/{CURRENT_CONGRESS}/house"),
        ("Recent bills", f"/bill/{CURRENT_CONGRESS}"),
    ]
    
    results = {}
    for name, endpoint in endpoints:
        results[name] = test_endpoint(name, endpoint)
    
    # If senate votes worked, let's look at a specific vote
    print("\n" + "=" * 60)
    print("Checking vote structure...")
    print("=" * 60)
    
    senate_data = results.get("Senate votes")
    if senate_data and "votes" in senate_data:
        votes = senate_data["votes"]
        if votes:
            first_vote = votes[0]
            print(f"\n📋 Sample vote structure:")
            for key, value in first_vote.items():
                val_preview = str(value)[:50] + "..." if len(str(value)) > 50 else value
                print(f"   {key}: {val_preview}")
            
            # Try to get detailed vote info
            if "url" in first_vote:
                print(f"\n🔗 Vote has URL: {first_vote['url']}")
    
    print("\n" + "=" * 60)
    print("API Exploration Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
