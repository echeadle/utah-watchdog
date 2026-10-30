#!/usr/bin/env python3
"""Test if candidate_id filter is working."""
import httpx
import asyncio
from src.config.settings import settings

async def test():
    api_key = settings.FEC_API_KEY
    endpoint = 'https://api.open.fec.gov/v1/schedules/schedule_a/'

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(endpoint, params={
            'api_key': api_key,
            'candidate_id': 'S0UT00165',  # Mike Lee
            'two_year_transaction_period': 2024,
            'per_page': 5,
            'page': 1
        })
        data = response.json()
        results = data.get('results', [])

        print(f'Total results in API: {data.get("pagination", {}).get("count")}')
        print(f'Results on this page: {len(results)}')
        print()

        candidates = set()
        for i, r in enumerate(results[:5], 1):
            cand_name = r.get("candidate_name", "N/A")
            cand_id = r.get("candidate_id", "N/A")
            candidates.add(f"{cand_name} ({cand_id})")

            print(f'{i}. Candidate: {cand_name} (ID: {cand_id})')
            print(f'   Contributor: {r.get("contributor_name")}')
            print(f'   Amount: ${r.get("contribution_receipt_amount")}')
            print(f'   Date: {r.get("contribution_receipt_date")}')
            print()

        print(f"Unique candidates in results: {len(candidates)}")
        for c in candidates:
            print(f"  - {c}")

asyncio.run(test())
