"""
Check Policy Area Data in Legislation Collection

This script analyzes the policy_area field in your bills to see:
1. How many bills have policy_area data
2. What values exist
3. Sample bills with and without policy_area

Usage:
    uv run python scripts/dev/check_policy_area.py
"""
import sys
from pathlib import Path
from pymongo import MongoClient

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import settings


def check_policy_area_data():
    """Analyze policy_area field in legislation collection"""
    
    print("="*70)
    print("POLICY AREA DATA CHECK")
    print("="*70)
    print()
    
    # Connect to MongoDB
    client = MongoClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    
    # Total bills
    total_bills = db.legislation.count_documents({})
    print(f"📊 Total bills in database: {total_bills}")
    print()
    
    # ========================================================================
    # Check 1: Bills with policy_area field
    # ========================================================================
    
    print("="*70)
    print("CHECK 1: Field Existence")
    print("="*70)
    
    # Has field (exists, even if None)
    has_field = db.legislation.count_documents({
        "policy_area": {"$exists": True}
    })
    
    # Missing field entirely
    missing_field = db.legislation.count_documents({
        "policy_area": {"$exists": False}
    })
    
    print(f"✅ Bills WITH policy_area field:    {has_field:,} ({has_field/total_bills*100:.1f}%)")
    print(f"❌ Bills WITHOUT policy_area field: {missing_field:,} ({missing_field/total_bills*100:.1f}%)")
    print()
    
    # ========================================================================
    # Check 2: Bills with actual data (not None, not empty)
    # ========================================================================
    
    print("="*70)
    print("CHECK 2: Data Quality")
    print("="*70)
    
    # Has actual data (not None, not empty string)
    has_data = db.legislation.count_documents({
        "policy_area": {"$exists": True, "$ne": None, "$ne": ""}
    })
    
    # Is None
    is_none = db.legislation.count_documents({
        "policy_area": None
    })
    
    # Is empty string
    is_empty = db.legislation.count_documents({
        "policy_area": ""
    })
    
    print(f"✅ Bills with ACTUAL data:  {has_data:,} ({has_data/total_bills*100:.1f}%)")
    print(f"⚪ Bills with None:         {is_none:,} ({is_none/total_bills*100:.1f}%)")
    print(f"⚪ Bills with empty string: {is_empty:,} ({is_empty/total_bills*100:.1f}%)")
    print()
    
    # ========================================================================
    # Check 3: What policy areas exist?
    # ========================================================================
    
    if has_data > 0:
        print("="*70)
        print("CHECK 3: Policy Area Values")
        print("="*70)
        
        # Aggregate to get unique values and counts
        pipeline = [
            {"$match": {"policy_area": {"$exists": True, "$ne": None, "$ne": ""}}},
            {"$group": {"_id": "$policy_area", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 20}
        ]
        
        policy_areas = list(db.legislation.aggregate(pipeline))
        
        print(f"Found {len(policy_areas)} unique policy areas:")
        print()
        
        for i, pa in enumerate(policy_areas, 1):
            policy_name = pa['_id'] if pa['_id'] is not None else "(None)"
            print(f"  {i:2}. {policy_name:<40} ({pa['count']:,} bills)")
        
        print()
    
    # ========================================================================
    # Check 4: Sample bills
    # ========================================================================
    
    print("="*70)
    print("CHECK 4: Sample Bills")
    print("="*70)
    print()
    
    # Sample with data
    if has_data > 0:
        print("📄 Sample bill WITH policy_area data:")
        print("-"*70)
        
        # Explicitly find one with a known policy area (not None)
        sample_with = db.legislation.find_one({
            "policy_area": "Public Lands and Natural Resources"
        })
        
        # If that specific one doesn't exist, try to find ANY non-None
        if not sample_with:
            sample_with = db.legislation.find_one({
                "$and": [
                    {"policy_area": {"$exists": True}},
                    {"policy_area": {"$ne": None}},
                    {"policy_area": {"$ne": ""}}
                ]
            })
        
        if sample_with:
            print(f"  Bill ID: {sample_with.get('bill_id')}")
            print(f"  Title: {sample_with.get('title', 'N/A')[:70]}...")
            print(f"  Policy Area: {sample_with.get('policy_area')}")
            print(f"  Congress: {sample_with.get('congress')}")
        else:
            print("  ERROR: Could not find a bill with policy_area data!")
            print("  (This shouldn't happen if has_data > 0)")
        print()
    
    # Sample without data
    print("📄 Sample bill WITHOUT policy_area data:")
    print("-"*70)
    
    sample_without = db.legislation.find_one({
        "$or": [
            {"policy_area": {"$exists": False}},
            {"policy_area": None},
            {"policy_area": ""}
        ]
    })
    
    if sample_without:
        print(f"  Bill ID: {sample_without.get('bill_id')}")
        print(f"  Title: {sample_without.get('title', 'N/A')[:70]}...")
        print(f"  Policy Area: {sample_without.get('policy_area', 'MISSING FIELD')}")
        print(f"  Congress: {sample_without.get('congress')}")
    print()
    
    # ========================================================================
    # Check 5: By Congress
    # ========================================================================
    
    print("="*70)
    print("CHECK 5: Policy Area Data by Congress")
    print("="*70)
    print()
    
    # Get congress numbers
    congresses = db.legislation.distinct("congress")
    
    for congress in sorted([c for c in congresses if c], reverse=True):
        total_in_congress = db.legislation.count_documents({"congress": congress})
        with_data_in_congress = db.legislation.count_documents({
            "congress": congress,
            "policy_area": {"$exists": True, "$ne": None, "$ne": ""}
        })
        
        percentage = (with_data_in_congress / total_in_congress * 100) if total_in_congress > 0 else 0
        
        print(f"  {congress}th Congress: {with_data_in_congress:,}/{total_in_congress:,} "
              f"({percentage:.1f}%) have policy_area data")
    
    print()
    
    # ========================================================================
    # Summary & Recommendation
    # ========================================================================
    
    print("="*70)
    print("SUMMARY & RECOMMENDATIONS")
    print("="*70)
    print()
    
    if has_data == 0:
        print("❌ NO POLICY AREA DATA FOUND")
        print()
        print("Possible reasons:")
        print("  1. Congress.gov API doesn't return this field")
        print("  2. The field isn't being extracted during ingestion")
        print("  3. The field name in the API is different")
        print()
        print("Next steps:")
        print("  1. Check Congress.gov API response to see if field exists")
        print("  2. Check src/ingestion/congress_bills.py transform() method")
        print("  3. May need to add policy_area extraction code")
    
    elif has_data < total_bills * 0.5:
        print("⚠️  PARTIAL POLICY AREA DATA")
        print()
        print(f"Only {has_data/total_bills*100:.1f}% of bills have policy_area data.")
        print()
        print("This might be normal if:")
        print("  - Newer bills haven't been categorized yet")
        print("  - Some bill types don't get policy areas")
    
    else:
        print("✅ GOOD POLICY AREA COVERAGE")
        print()
        print(f"{has_data/total_bills*100:.1f}% of bills have policy_area data.")
    
    print()
    print("="*70)
    
    client.close()


if __name__ == "__main__":
    try:
        check_policy_area_data()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)