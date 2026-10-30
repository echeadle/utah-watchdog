#!/usr/bin/env python3
"""Find the committee IDs for a candidate."""
import httpx
import asyncio
from src.config.settings import settings

async def find_committees(candidate_id):
    api_key = settings.FEC_API_KEY
    endpoint = f'https://api.open.fec.gov/v1/candidate/{candidate_id}/committees/'

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(endpoint, params={
            'api_key': api_key
        })
        data = response.json()
        results = data.get('results', [])

        print(f"Committees for candidate {candidate_id}:")
        for committee in results:
            print(f"  - {committee.get('name')}")
            print(f"    Committee ID: {committee.get('committee_id')}")
            print(f"    Type: {committee.get('committee_type_full')}")
            print(f"    Designation: {committee.get('designation_full')}")
            print()

asyncio.run(find_committees('S0UT00165'))  # Mike Lee
