"""
Investigate why we're only getting 55 senators instead of 100.
Check multiple states to see if API returns 2 senators per state.
"""
import asyncio
import httpx
from src.config.settings import settings
from src.config.constants import CONGRESS_GOV_BASE_URL

async def check_senators_by_state():
    """Check how many senators the API returns for various states"""
    api_key = settings.CONGRESS_GOV_API_KEY
    base_url = CONGRESS_GOV_BASE_URL

    # Test a variety of states
    test_states = ["CA", "TX", "NY", "FL", "UT", "WY", "VT", "AL"]

    async with httpx.AsyncClient(timeout=30.0) as client:
        total_senators_found = 0

        for state in test_states:
            url = f"{base_url}/member/congress/119/{state}"
            params = {
                "currentMember": "true",
                "api_key": api_key,
                "format": "json",
                "limit": 250
            }

            response = await client.get(url, params=params)
            data = response.json()
            members = data.get("members", [])

            # Count senators
            senators = []
            for member in members:
                terms = member.get("terms", {}).get("item", [])
                if terms:
                    chamber = terms[0].get("chamber", "")
                    if "Senate" in chamber:
                        senators.append(member.get("name"))

            print(f"{state}: {len(senators)} senators")
            for senator in senators:
                print(f"  - {senator}")

            total_senators_found += len(senators)
            await asyncio.sleep(0.3)

        print(f"\nTotal senators found across {len(test_states)} test states: {total_senators_found}")
        print(f"Expected: {len(test_states) * 2} senators (2 per state)")

asyncio.run(check_senators_by_state())
