#!/usr/bin/env python3
"""Check what pagination fields the FEC API returns."""
import httpx
import asyncio
import json
from src.config.settings import settings

async def test():
    api_key = settings.FEC_API_KEY
    endpoint = 'https://api.open.fec.gov/v1/schedules/schedule_a/'

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(endpoint, params={
            'api_key': api_key,
            'committee_id': 'C00473827',  # Mike Lee
            'two_year_transaction_period': 2024,
            'per_page': 5,
            'sort': '-contribution_receipt_date'
        })
        data = response.json()

        print("Full pagination structure:")
        print(json.dumps(data.get('pagination', {}), indent=2))

asyncio.run(test())
