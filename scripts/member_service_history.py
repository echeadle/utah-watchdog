"""
Get Congressional service history for a House or Senate member.

Uses the Congress.gov API to fetch a member's complete service record
including all terms they served.

Usage:
    uv run python scripts/member_service_history.py "Mike Lee"
    uv run python scripts/member_service_history.py "Mitt Romney"
    uv run python scripts/member_service_history.py "Chris Stewart" --verbose
    uv run python scripts/member_service_history.py "Nancy Pelosi"
"""
import asyncio
import httpx
import sys
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings
from src.config.constants import CONGRESS_GOV_BASE_URL


async def search_member(name: str, current_only: bool = True, verbose: bool = False) -> Optional[str]:
    """
    Search for a member by name and return their bioguide ID.
    
    Args:
        name: Member's name (first, last, or full name)
        current_only: If True, only search current members. If False, search all members.
        verbose: Print detailed search results
        
    Returns:
        Bioguide ID if found, None otherwise
    """
    if verbose:
        print(f"🔍 Searching for: {name}")
        member_type = "current" if current_only else "all"
        print(f"   Searching: {member_type} members")
        print()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch all members (need to paginate)
        url = f"{CONGRESS_GOV_BASE_URL}/member"
        params = {
            "api_key": settings.CONGRESS_GOV_API_KEY,
            "format": "json",
            "limit": 250,  # Max per request
        }
        
        # Only add currentMember filter if searching current only
        if current_only:
            params["currentMember"] = "true"
        
        if verbose:
            print("📥 Fetching member list from Congress.gov...")
        
        all_members = []
        offset = 0
        
        # Fetch all pages
        while True:
            params["offset"] = offset
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            members = data.get("members", [])
            if not members:
                break
            
            all_members.extend(members)
            
            # Check if there are more pages
            pagination = data.get("pagination", {})
            if pagination.get("next") is None:
                break
            
            offset += 250
            await asyncio.sleep(0.2)  # Be nice to the API
        
        if verbose:
            member_type = "current" if current_only else "total"
            print(f"   Found {len(all_members)} {member_type} members")
            print()
        
        # Normalize search term - split into parts and lowercase
        search_parts = [part.strip().lower() for part in name.replace(',', ' ').split()]
        
        matches = []
        
        for member in all_members:
            member_name = member.get("name", "").lower()
            direct_name = member.get("directOrderName", "").lower()
            
            # Check if ALL search parts are in either name format
            # This allows "Mike Lee", "Lee Mike", "Lee, Mike", "Lee" or "Mike" to all work
            name_match = all(part in member_name for part in search_parts)
            direct_match = all(part in direct_name for part in search_parts)
            
            if name_match or direct_match:
                matches.append({
                    "name": member.get("name", ""),
                    "directOrderName": member.get("directOrderName", ""),
                    "bioguideId": member.get("bioguideId"),
                    "state": member.get("state"),
                    "party": member.get("partyName"),
                    "district": member.get("district"),
                    "url": member.get("url")
                })
        
        if not matches:
            member_type = "current" if current_only else ""
            print(f"❌ No {member_type} members found matching: {name}".strip())
            print()
            print("💡 Tips:")
            print("   • Try different name formats:")
            print("     - 'Mike Lee' or 'Lee Mike' or 'Lee, Mike'")
            print("     - Just 'Lee' or just 'Mike'")
            print("   • Check spelling")
            if current_only:
                print("   • Member must be currently serving")
                print("   • Try with --all flag to search former members too")
            return None
        
        if len(matches) > 1:
            print(f"⚠️  Found {len(matches)} matches:")
            for i, m in enumerate(matches, 1):
                district = f", District {m['district']}" if m.get('district') else ""
                print(f"   {i}. {m['name']} ({m['party']}, {m['state']}{district})")
            print()
            print("💡 Be more specific with the name to narrow results:")
            print("   • Use first and last name: 'Mike Lee'")
            print("   • Or add state: try searching 'Lee Utah' (not yet supported)")
            return None
        
        # Single match found
        match = matches[0]
        if verbose:
            print(f"✅ Found: {match['name']}")
            print(f"   Party: {match['party']}")
            district = f", District {match['district']}" if match.get('district') else ""
            print(f"   Location: {match['state']}{district}")
            print(f"   Bioguide ID: {match['bioguideId']}")
            print()
        
        return match["bioguideId"]


async def get_member_service_history(bioguide_id: str) -> Dict:
    """
    Get complete service history for a member.
    
    Args:
        bioguide_id: The member's bioguide identifier
        
    Returns:
        Dict with member info and service terms
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{CONGRESS_GOV_BASE_URL}/member/{bioguide_id}"
        params = {
            "api_key": settings.CONGRESS_GOV_API_KEY,
            "format": "json"
        }
        
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        return data.get("member", {})


def format_congress_range(start: int, end: Optional[int] = None) -> str:
    """Format a congress range like '112th-115th' or '118th-Present'"""
    if end is None:
        return f"{start}th-Present"
    elif start == end:
        return f"{start}th"
    else:
        return f"{start}th-{end}th"


def display_service_history(member_data: Dict):
    """
    Display formatted service history.
    
    Args:
        member_data: Member data from Congress.gov API
    """
    # Basic info
    name = member_data.get("directOrderName", member_data.get("name", "Unknown"))
    state = member_data.get("state", "")
    party = member_data.get("partyHistory", [{}])[0].get("partyName", "")
    
    print("=" * 70)
    print(f"📋 Congressional Service History")
    print("=" * 70)
    print(f"Name:  {name}")
    print(f"State: {state}")
    print(f"Party: {party}")
    print()
    
    # Get terms - handle both list and dict formats
    terms_data = member_data.get("terms", [])
    
    # Terms might be a list directly, or a dict with "item" key
    if isinstance(terms_data, dict):
        terms = terms_data.get("item", [])
    else:
        terms = terms_data
    
    if not terms:
        print("ℹ️  No service terms found.")
        return
    
    # Group by chamber
    house_terms = []
    senate_terms = []
    
    for term in terms:
        chamber = term.get("chamber")
        congress = term.get("congress")
        start_year = term.get("startYear")
        end_year = term.get("endYear")
        
        term_info = {
            "congress": congress,
            "start_year": start_year,
            "end_year": end_year,
            "chamber": chamber
        }
        
        if chamber == "House of Representatives":
            house_terms.append(term_info)
        elif chamber == "Senate":
            senate_terms.append(term_info)
    
    # Display House terms
    if house_terms:
        print("🏛️  House of Representatives")
        print("-" * 70)
        
        # Sort by congress number
        house_terms.sort(key=lambda x: x["congress"])
        
        # Group consecutive terms
        if house_terms:
            current_group = [house_terms[0]]
            
            for term in house_terms[1:]:
                if term["congress"] == current_group[-1]["congress"] + 1:
                    current_group.append(term)
                else:
                    # Print the group
                    start = current_group[0]
                    end = current_group[-1]
                    congress_range = format_congress_range(start["congress"], end["congress"])
                    year_range = f"{start['start_year']}-{end['end_year']}"
                    print(f"   {congress_range:15} Congress    ({year_range})")
                    
                    # Start new group
                    current_group = [term]
            
            # Print final group
            start = current_group[0]
            end = current_group[-1]
            congress_range = format_congress_range(start["congress"], end["congress"])
            year_range = f"{start['start_year']}-{end['end_year']}"
            print(f"   {congress_range:15} Congress    ({year_range})")
        
        print()
    
    # Display Senate terms
    if senate_terms:
        print("🏛️  Senate")
        print("-" * 70)
        
        # Sort by congress number
        senate_terms.sort(key=lambda x: x["congress"])
        
        # Group consecutive terms
        if senate_terms:
            current_group = [senate_terms[0]]
            
            for term in senate_terms[1:]:
                if term["congress"] == current_group[-1]["congress"] + 1:
                    current_group.append(term)
                else:
                    # Print the group
                    start = current_group[0]
                    end = current_group[-1]
                    congress_range = format_congress_range(start["congress"], end["congress"])
                    year_range = f"{start['start_year']}-{end['end_year']}"
                    print(f"   {congress_range:15} Congress    ({year_range})")
                    
                    # Start new group
                    current_group = [term]
            
            # Print final group
            start = current_group[0]
            end = current_group[-1]
            congress_range = format_congress_range(start["congress"], end["congress"])
            year_range = f"{start['start_year']}-{end['end_year']}"
            print(f"   {congress_range:15} Congress    ({year_range})")
        
        print()
    
    # Summary
    total_congresses = len(house_terms) + len(senate_terms)
    print("📊 Summary")
    print("-" * 70)
    print(f"   Total Congresses Served: {total_congresses}")
    if house_terms:
        print(f"   House Terms: {len(house_terms)}")
    if senate_terms:
        print(f"   Senate Terms: {len(senate_terms)}")
    print()


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Get Congressional service history for a member",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/member_service_history.py "Mike Lee"
  uv run python scripts/member_service_history.py "Mitt Romney" --all
  uv run python scripts/member_service_history.py "Chris Stewart" --all --verbose
  uv run python scripts/member_service_history.py "Nancy Pelosi"
  uv run python scripts/member_service_history.py "John Curtis"
        """
    )
    
    parser.add_argument(
        "name",
        type=str,
        help="Member name (first, last, or full name)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output"
    )
    
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Search all members (including former members, not just current)"
    )
    
    args = parser.parse_args()
    
    try:
        # Step 1: Search for member
        bioguide_id = await search_member(args.name, current_only=not args.all, verbose=args.verbose)
        
        if not bioguide_id:
            sys.exit(1)
        
        # Step 2: Get service history
        if args.verbose:
            print("📥 Fetching service history...")
            print()
        
        member_data = await get_member_service_history(bioguide_id)
        
        # Step 3: Display results
        display_service_history(member_data)
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
