#!/usr/bin/env python3
"""
Test FEC API pagination WITHOUT sort parameter.
"""
import httpx
import asyncio
from src.config.settings import settings

async def test_pagination():
    """Test if FEC API returns different results on different pages without sorting."""

    api_key = settings.FEC_API_KEY
    candidate_id = "S0UT00165"  # Mike Lee
    cycle = 2024

    endpoint = "https://api.open.fec.gov/v1/schedules/schedule_a/"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch page 1 WITHOUT sort
        print("Fetching page 1 (NO SORT)...")
        response1 = await client.get(endpoint, params={
            "api_key": api_key,
            "candidate_id": candidate_id,
            "two_year_transaction_period": cycle,
            "per_page": 10,
            "page": 1
            # NO sort parameter
        })
        data1 = response1.json()
        results1 = data1.get("results", [])

        print(f"Page 1: {len(results1)} results")
        print(f"First contribution sub_id: {results1[0].get('sub_id') if results1 else 'N/A'}")
        print(f"Last contribution sub_id: {results1[-1].get('sub_id') if results1 else 'N/A'}")

        # Fetch page 2 WITHOUT sort
        print("\nFetching page 2 (NO SORT)...")
        response2 = await client.get(endpoint, params={
            "api_key": api_key,
            "candidate_id": candidate_id,
            "two_year_transaction_period": cycle,
            "per_page": 10,
            "page": 2
            # NO sort parameter
        })
        data2 = response2.json()
        results2 = data2.get("results", [])

        print(f"Page 2: {len(results2)} results")
        print(f"First contribution sub_id: {results2[0].get('sub_id') if results2 else 'N/A'}")
        print(f"Last contribution sub_id: {results2[-1].get('sub_id') if results2 else 'N/A'}")

        # Check if they're the same
        ids1 = [r.get('sub_id') for r in results1]
        ids2 = [r.get('sub_id') for r in results2]

        print(f"\n=== COMPARISON ===")
        print(f"Page 1 IDs: {ids1}")
        print(f"Page 2 IDs: {ids2}")

        if ids1 == ids2:
            print("\n❌ ERROR: Page 1 and Page 2 return IDENTICAL results!")
        else:
            print("\n✓ SUCCESS: Pages return DIFFERENT results! Pagination works without sort.")

            # Check for any overlap
            overlap = set(ids1) & set(ids2)
            if overlap:
                print(f"⚠️  WARNING: {len(overlap)} IDs appear on both pages: {overlap}")
            else:
                print("✓ No duplicate IDs between pages")

        # Print pagination info
        pagination = data2.get("pagination", {})
        print(f"\nPagination info from API:")
        print(f"  Total pages: {pagination.get('pages')}")
        print(f"  Total count: {pagination.get('count')}")
        print(f"  Per page: {pagination.get('per_page')}")

if __name__ == "__main__":
    asyncio.run(test_pagination())
