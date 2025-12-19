"""
Query politicians from MongoDB.

Usage:
    uv run python scripts/query_politicians.py                # All politicians
    uv run python scripts/query_politicians.py --state UT     # Utah only
    uv run python scripts/query_politicians.py --chamber senate  # Senate only
"""
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import get_sync_database


def query_politicians(state=None, chamber=None, party=None):
    """Query politicians from MongoDB."""
    db = get_sync_database()
    collection = db.politicians
    
    # Build query filter
    query = {}
    if state:
        query["state"] = state
    if chamber:
        query["chamber"] = chamber
    if party:
        query["party"] = party
    
    # Get politicians
    politicians = list(collection.find(query).sort("last_name", 1))
    
    if not politicians:
        print("No politicians found matching criteria.")
        return
    
    print(f"\n{'='*80}")
    print(f"Found {len(politicians)} politician(s)")
    print(f"{'='*80}\n")
    
    for pol in politicians:
        print(f"📋 {pol['full_name']}")
        print(f"   Party: {pol.get('party', 'Unknown')}")
        print(f"   Title: {pol.get('title', 'Unknown')}")
        print(f"   State: {pol.get('state', 'Unknown')}", end="")
        if pol.get('district'):
            print(f", District {pol['district']}")
        else:
            print()
        print(f"   Chamber: {pol.get('chamber', 'Unknown')}")
        print(f"   Bioguide ID: {pol.get('bioguide_id', 'Unknown')}")
        if pol.get('website'):
            print(f"   Website: {pol['website']}")
        print()
    
    # Summary stats
    print(f"{'='*80}")
    print("Summary:")
    
    # Count by party
    parties = {}
    for pol in politicians:
        party = pol.get('party', 'Unknown')
        parties[party] = parties.get(party, 0) + 1
    
    for party, count in sorted(parties.items()):
        print(f"  • {party}: {count}")
    
    # Count by chamber
    chambers = {}
    for pol in politicians:
        chamber = pol.get('chamber', 'Unknown')
        chambers[chamber] = chambers.get(chamber, 0) + 1
    
    print(f"\nBy Chamber:")
    for chamber, count in sorted(chambers.items()):
        print(f"  • {chamber.title()}: {count}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Query politicians from MongoDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # All politicians
  uv run python scripts/query_politicians.py
  
  # Utah delegation only
  uv run python scripts/query_politicians.py --state Utah
  
  # All senators
  uv run python scripts/query_politicians.py --chamber senate
  
  # Utah House members
  uv run python scripts/query_politicians.py --state Utah --chamber house
  
  # Republicans only
  uv run python scripts/query_politicians.py --party R
        """
    )
    
    parser.add_argument(
        "--state",
        type=str,
        help="Filter by state (e.g., Utah, California)"
    )
    
    parser.add_argument(
        "--chamber",
        choices=["senate", "house"],
        help="Filter by chamber"
    )
    
    parser.add_argument(
        "--party",
        choices=["D", "R", "I"],
        help="Filter by party (D=Democrat, R=Republican, I=Independent)"
    )
    
    args = parser.parse_args()
    
    try:
        query_politicians(
            state=args.state,
            chamber=args.chamber,
            party=args.party
        )
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
