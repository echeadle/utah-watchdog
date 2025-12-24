"""
Check page 2 of the member endpoint to find missing senators.
"""
import asyncio
import httpx
from src.config.settings import settings
from src.config.constants import CONGRESS_GOV_BASE_URL

async def check_page_2():
    """Check second page of members"""
    api_key = settings.CONGRESS_GOV_API_KEY
    base_url = CONGRESS_GOV_BASE_URL

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get page 2
        url = f"{base_url}/member"
        params = {
            "currentMember": "true",
            "api_key": api_key,
            "format": "json",
            "limit": 250,
            "offset": 250  # Second page
        }

        print("Fetching page 2...")
        response = await client.get(url, params=params)
        data = response.json()

        members = data.get("members", [])
        print(f"Total members on page 2: {len(members)}")

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

        print(f"Senators on page 2: {len(senators)}")

        # Check for our missing states
        ny_senators = [s for s in senators if s[1] == "NY"]
        vt_senators = [s for s in senators if s[1] == "VT"]
        ca_senators = [s for s in senators if s[1] == "CA"]
        ut_senators = [s for s in senators if s[1] == "UT"]

        print(f"\nMissing states found on page 2:")
        print(f"  NY: {len(ny_senators)} - {[s[0] for s in ny_senators]}")
        print(f"  VT: {len(vt_senators)} - {[s[0] for s in vt_senators]}")
        print(f"  CA: {len(ca_senators)} - {[s[0] for s in ca_senators]}")
        print(f"  UT: {len(ut_senators)} - {[s[0] for s in ut_senators]}")

        print(f"\nAll page 2 senators:")
        for name, state in sorted(senators, key=lambda x: (x[1], x[0])):
            print(f"  {state}: {name}")

asyncio.run(check_page_2())
