"""
Try the general /member endpoint instead of /member/congress/119/{state}
"""
import asyncio
import httpx
from src.config.settings import settings
from src.config.constants import CONGRESS_GOV_BASE_URL

async def check_general_member_endpoint():
    """Check the general member endpoint"""
    api_key = settings.CONGRESS_GOV_API_KEY
    base_url = CONGRESS_GOV_BASE_URL

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Try general member endpoint
        url = f"{base_url}/member"
        params = {
            "currentMember": "true",
            "api_key": api_key,
            "format": "json",
            "limit": 250  # Get first page
        }

        print("Fetching from /member endpoint...")
        response = await client.get(url, params=params)
        data = response.json()

        members = data.get("members", [])
        print(f"\nTotal members in first page: {len(members)}")

        # Count senators
        senators = []
        for member in members:
            terms = member.get("terms", {})
            if isinstance(terms, dict):
                items = terms.get("item", [])
            else:
                items = terms

            if items and isinstance(items, list):
                chamber = items[0].get("chamber", "")
                if "Senate" in chamber:
                    state = member.get("state")
                    senators.append((member.get("name"), state))

        print(f"Senators in first page: {len(senators)}")
        print("\nFirst 10 senators:")
        for name, state in senators[:10]:
            print(f"  {state}: {name}")

        # Check pagination
        pagination = data.get("pagination", {})
        print(f"\nPagination info:")
        print(f"  Count: {pagination.get('count')}")
        print(f"  Next: {pagination.get('next')}")

        # Check if NY and VT senators are in this list
        ny_senators = [s for s in senators if s[1] == "NY"]
        vt_senators = [s for s in senators if s[1] == "VT"]
        ca_senators = [s for s in senators if s[1] == "CA"]
        ut_senators = [s for s in senators if s[1] == "UT"]

        print(f"\nSpecific states:")
        print(f"  NY: {len(ny_senators)} - {[s[0] for s in ny_senators]}")
        print(f"  VT: {len(vt_senators)} - {[s[0] for s in vt_senators]}")
        print(f"  CA: {len(ca_senators)} - {[s[0] for s in ca_senators]}")
        print(f"  UT: {len(ut_senators)} - {[s[0] for s in ut_senators]}")

asyncio.run(check_general_member_endpoint())
