"""
Check if removing currentMember=true filter gives us more senators.
"""
import asyncio
import httpx
from src.config.settings import settings
from src.config.constants import CONGRESS_GOV_BASE_URL

async def check_senators_without_filter():
    """Check senators WITHOUT the currentMember filter"""
    api_key = settings.CONGRESS_GOV_API_KEY
    base_url = CONGRESS_GOV_BASE_URL

    test_states = ["CA", "NY", "VT", "UT"]  # States that were missing senators

    async with httpx.AsyncClient(timeout=30.0) as client:
        for state in test_states:
            print(f"\n{'='*60}")
            print(f"State: {state}")
            print(f"{'='*60}")

            # With currentMember filter
            url = f"{base_url}/member/congress/119/{state}"
            params = {
                "currentMember": "true",
                "api_key": api_key,
                "format": "json",
                "limit": 250
            }

            response = await client.get(url, params=params)
            data = response.json()
            members_with_filter = data.get("members", [])

            senators_with = [m.get("name") for m in members_with_filter
                           if "Senate" in m.get("terms", {}).get("item", [{}])[0].get("chamber", "")]

            print(f"WITH currentMember=true: {len(senators_with)} senators")
            for s in senators_with:
                print(f"  - {s}")

            # WITHOUT currentMember filter
            params2 = {
                "api_key": api_key,
                "format": "json",
                "limit": 250
            }

            response2 = await client.get(url, params=params2)
            data2 = response2.json()
            members_without_filter = data2.get("members", [])

            senators_without = [m.get("name") for m in members_without_filter
                              if "Senate" in m.get("terms", {}).get("item", [{}])[0].get("chamber", "")]

            print(f"\nWITHOUT currentMember filter: {len(senators_without)} senators")
            for s in senators_without:
                print(f"  - {s}")

            await asyncio.sleep(0.3)

asyncio.run(check_senators_without_filter())
