#!/usr/bin/env python3
"""Test filtering by committee_id instead of candidate_id."""
import httpx
import asyncio
from src.config.settings import settings

async def test():
    api_key = settings.FEC_API_KEY
    endpoint = 'https://api.open.fec.gov/v1/schedules/schedule_a/'

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test with committee_id instead of candidate_id
        print("Testing with committee_id (Mike Lee's principal campaign committee)...")
        response = await client.get(endpoint, params={
            'api_key': api_key,
            'committee_id': 'C00473827',  # FRIENDS OF MIKE LEE INC
            'two_year_transaction_period': 2024,
            'per_page': 5,
            'page': 1
        })
        data = response.json()
        results = data.get('results', [])

        pagination = data.get('pagination', {})
        print(f'Total results: {pagination.get("count")}')
        print(f'Total pages: {pagination.get("pages")}')
        print(f'Results on this page: {len(results)}')
        print()

        for i, r in enumerate(results[:3], 1):
            print(f'{i}. Committee: {r.get("committee_name")}')
            print(f'   Committee ID: {r.get("committee_id")}')
            print(f'   Contributor: {r.get("contributor_name")}')
            print(f'   Amount: ${r.get("contribution_receipt_amount")}')
            print(f'   Date: {r.get("contribution_receipt_date")}')
            print()

        # Test pagination
        print("\n--- Testing Pagination ---")
        print("Fetching page 2...")
        response2 = await client.get(endpoint, params={
            'api_key': api_key,
            'committee_id': 'C00473827',
            'two_year_transaction_period': 2024,
            'per_page': 5,
            'page': 2
        })
        data2 = response2.json()
        results2 = data2.get('results', [])

        ids1 = [r.get('sub_id') for r in results]
        ids2 = [r.get('sub_id') for r in results2]

        print(f'Page 1 IDs: {ids1}')
        print(f'Page 2 IDs: {ids2}')

        if ids1 == ids2:
            print("\n❌ ERROR: Still getting duplicate results!")
        else:
            print("\n✓ SUCCESS: Pagination works with committee_id!")

asyncio.run(test())
