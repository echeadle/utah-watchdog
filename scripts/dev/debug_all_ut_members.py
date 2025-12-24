import asyncio
import httpx
from src.config.settings import settings
from src.config.constants import CONGRESS_GOV_BASE_URL

async def check_all_utah_members():
    """Check ALL Utah members (not just current)"""
    api_key = settings.CONGRESS_GOV_API_KEY
    base_url = CONGRESS_GOV_BASE_URL

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch ALL Utah members (remove currentMember filter)
        url = f"{base_url}/member/congress/119/UT"
        params = {
            # "currentMember": "true",  # REMOVED to see all members
            "api_key": api_key,
            "format": "json",
            "limit": 250
        }

        response = await client.get(url, params=params)
        data = response.json()
        members = data.get("members", [])

        print(f"Total Utah members in 119th Congress (all): {len(members)}\n")

        # Filter senators
        senators = []
        for member in members:
            name = member.get("name", "Unknown")
            terms = member.get("terms", {}).get("item", [])
            if terms:
                chamber = terms[0].get("chamber", "")
                if "Senate" in chamber:
                    senators.append((name, member.get("bioguideId")))
                    print(f"Senator: {name} ({member.get('bioguideId')})")

        print(f"\nTotal senators found: {len(senators)}")

asyncio.run(check_all_utah_members())
