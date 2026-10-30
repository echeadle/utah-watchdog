#!/usr/bin/env python3
"""Test the fixed FEC ingester."""
import asyncio
from src.ingestion.fec import FECIngester

async def test():
    print("Testing fixed FEC ingester with Mike Lee...")
    print("=" * 70)

    ingester = FECIngester(
        candidate_name="Mike Lee",
        bioguide_id="L000577"
    )

    # Fetch first 2 "pages" worth of data
    page1_ids = []
    page2_ids = []

    count = 0
    async for raw_data in ingester.fetch_data(
        candidate_id="S0UT00165",  # Will auto-convert to committee_id
        cycle=2024,
        per_page=10,
        max_pages=2
    ):
        count += 1
        sub_id = raw_data.get('sub_id')

        if count <= 10:
            page1_ids.append(sub_id)
            print(f"Page 1, Item {count}: {sub_id} - {raw_data.get('contributor_name')} - ${raw_data.get('contribution_receipt_amount')}")
        else:
            page2_ids.append(sub_id)
            print(f"Page 2, Item {count-10}: {sub_id} - {raw_data.get('contributor_name')} - ${raw_data.get('contribution_receipt_amount')}")

    print("\n" + "=" * 70)
    print("RESULTS:")
    print(f"Total contributions fetched: {count}")
    print(f"Page 1 IDs: {page1_ids[:3]}...")
    print(f"Page 2 IDs: {page2_ids[:3]}...")

    if page1_ids == page2_ids:
        print("\n❌ FAILED: Still getting duplicates!")
    else:
        # Check for any overlap
        overlap = set(page1_ids) & set(page2_ids)
        if overlap:
            print(f"\n⚠️  WARNING: {len(overlap)} duplicate IDs found")
        else:
            print("\n✅ SUCCESS: No duplicates! Pagination is working correctly!")

asyncio.run(test())
