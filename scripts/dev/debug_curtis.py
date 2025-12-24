import asyncio
import httpx
import json
from src.config.settings import settings
from src.config.constants import CONGRESS_GOV_BASE_URL

async def check_curtis():
    """Check John Curtis's member details"""
    api_key = settings.CONGRESS_GOV_API_KEY
    base_url = CONGRESS_GOV_BASE_URL

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch Curtis's details
        url = f"{base_url}/member/C001114"
        params = {
            "api_key": api_key,
            "format": "json"
        }

        response = await client.get(url, params=params)
        data = response.json()
        member = data.get("member", {})

        print(f"Name: {member.get('directOrderName')}")
        print(f"Bioguide ID: {member.get('bioguideId')}")
        print(f"\nTerms:")

        terms = member.get("terms", {}).get("item", [])
        for i, term in enumerate(terms):
            print(f"\nTerm {i+1}:")
            print(f"  Chamber: {term.get('chamber')}")
            print(f"  Start: {term.get('startYear')}")
            print(f"  End: {term.get('endYear', 'Current')}")
            print(f"  Congress: {term.get('congress', 'N/A')}")

asyncio.run(check_curtis())
