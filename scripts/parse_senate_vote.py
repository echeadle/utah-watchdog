"""
Parse Senate vote XML to get individual votes.

Run with: uv run python scripts/parse_senate_vote.py
"""

import httpx
import xml.etree.ElementTree as ET


def fetch_senate_vote_xml(url: str) -> str | None:
    """Fetch the XML vote data from Senate.gov."""
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url)
        if response.status_code == 200:
            return response.text
        print(f"❌ Failed to fetch: {response.status_code}")
        return None


def parse_senate_vote(xml_text: str) -> dict:
    """
    Parse Senate vote XML into structured data.
    
    Returns dict with vote info and list of how each senator voted.
    """
    root = ET.fromstring(xml_text)
    
    # Get vote metadata
    vote_info = {
        "congress": root.findtext("congress"),
        "session": root.findtext("session"),
        "roll_call": root.findtext("vote_number"),
        "vote_date": root.findtext("vote_date"),
        "question": root.findtext("vote_question_text") or root.findtext("question"),
        "result": root.findtext("vote_result") or root.findtext("result"),
        "title": root.findtext("vote_title") or root.findtext("title"),
    }
    
    # Get vote counts
    count_elem = root.find("count")
    if count_elem is not None:
        vote_info["yeas"] = count_elem.findtext("yeas")
        vote_info["nays"] = count_elem.findtext("nays")
        vote_info["present"] = count_elem.findtext("present")
        vote_info["absent"] = count_elem.findtext("absent")
    
    # Get individual senator votes
    members = []
    
    # Find all member elements (structure varies)
    for member_elem in root.findall(".//member"):
        member = {
            "name": member_elem.findtext("member_full"),
            "first_name": member_elem.findtext("first_name"),
            "last_name": member_elem.findtext("last_name"),
            "party": member_elem.findtext("party"),
            "state": member_elem.findtext("state"),
            "vote": member_elem.findtext("vote_cast"),
            "lis_member_id": member_elem.findtext("lis_member_id"),
        }
        members.append(member)
    
    vote_info["members"] = members
    
    return vote_info


def main():
    print("=" * 60)
    print("Parsing Senate Vote XML")
    print("=" * 60)
    
    # The URL we found
    vote_url = "https://www.senate.gov/legislative/LIS/roll_call_votes/vote1182/vote_118_2_00327.xml"
    
    print(f"\n📥 Fetching: {vote_url}")
    xml_text = fetch_senate_vote_xml(vote_url)
    
    if not xml_text:
        return
    
    print("✅ Got XML data")
    
    # Parse it
    print("\n📊 Parsing vote data...")
    vote_data = parse_senate_vote(xml_text)
    
    # Display vote info
    print("\n" + "=" * 60)
    print("VOTE INFORMATION")
    print("=" * 60)
    print(f"Congress: {vote_data['congress']}, Session: {vote_data['session']}")
    print(f"Roll Call: {vote_data['roll_call']}")
    print(f"Date: {vote_data['vote_date']}")
    print(f"Question: {vote_data['question']}")
    print(f"Result: {vote_data['result']}")
    print(f"Yeas: {vote_data.get('yeas')}, Nays: {vote_data.get('nays')}")
    
    # Display all senators' votes
    print("\n" + "=" * 60)
    print("ALL SENATORS' VOTES")
    print("=" * 60)
    
    members = vote_data["members"]
    print(f"Total senators voting: {len(members)}")
    
    # Sort by state
    members_sorted = sorted(members, key=lambda x: (x.get("state", ""), x.get("last_name", "")))
    
    # Show first 10 for preview
    print("\nFirst 10 senators:")
    for m in members_sorted[:10]:
        print(f"   {m.get('state', '??'):2} - {m.get('name', 'Unknown'):25} ({m.get('party', '?')}): {m.get('vote', 'N/A')}")
    
    # Filter for Utah senators
    print("\n" + "=" * 60)
    print("🏔️ UTAH SENATORS")
    print("=" * 60)
    
    utah_senators = [m for m in members if m.get("state") == "UT"]
    
    if utah_senators:
        for senator in utah_senators:
            print(f"   {senator.get('name', 'Unknown')} ({senator.get('party', '?')})")
            print(f"   Vote: {senator.get('vote', 'N/A')}")
            print()
    else:
        print("   No Utah senators found in this vote")
        # Debug: show all states
        states = set(m.get("state", "??") for m in members)
        print(f"   States found: {sorted(states)}")
    
    print("=" * 60)
    print("✅ Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()