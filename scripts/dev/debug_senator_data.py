import asyncio
import httpx
import json
from src.config.settings import settings
from src.config.constants import CONGRESS_GOV_BASE_URL

async def check_senator_data():
    """Check raw API data for Utah senators"""
    api_key = settings.CONGRESS_GOV_API_KEY
    base_url = CONGRESS_GOV_BASE_URL

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch Utah members from list endpoint
        url = f"{base_url}/member/congress/119/UT"
        params = {
            "currentMember": "true",
            "api_key": api_key,
            "format": "json",
            "limit": 250
        }

        response = await client.get(url, params=params)
        data = response.json()
        members = data.get("members", [])

        print(f"Total Utah members found: {len(members)}\n")

        # Check each member's chamber
        for member in members:
            name = member.get("name", "Unknown")
            bioguide = member.get("bioguideId", "Unknown")

            # Try to extract chamber from terms
            terms = member.get("terms", {})
            if isinstance(terms, dict):
                items = terms.get("item", [])
            else:
                items = terms

            print(f"Member: {name} ({bioguide})")
            print(f"  Terms structure type: {type(terms)}")
            print(f"  Number of terms: {len(items) if isinstance(items, list) else 'N/A'}")

            if isinstance(items, list) and items:
                first_term = items[0]
                print(f"  First term chamber: {first_term.get('chamber', 'NOT FOUND')}")
                print(f"  First term keys: {list(first_term.keys())[:5]}")

            print()

asyncio.run(check_senator_data())
