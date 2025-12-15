"""
Script to sync politicians (current members of Congress) from Congress.gov.

Fetches comprehensive member profiles including:
- Basic info (name, party, state, district)
- Committee assignments
- Contact information
- External IDs for linking to other data sources

Usage:
    uv run python scripts/sync_politicians.py                    # All current members
    uv run python scripts/sync_politicians.py --chamber senate   # Senate only
    uv run python scripts/sync_politicians.py --state UT         # Utah only
    uv run python scripts/sync_politicians.py --verbose          # Detailed logging
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import get_sync_database
from src.config.settings import settings
from src.config.constants import CONGRESS_GOV_BASE_URL
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class PoliticianSyncer:
    """Sync politicians from Congress.gov API to MongoDB."""
    
    def __init__(self, verbose: bool = False):
        self.api_key = settings.CONGRESS_GOV_API_KEY
        self.base_url = CONGRESS_GOV_BASE_URL
        self.verbose = verbose
        self.db = None
        self.stats = {
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "errors": 0,
            "skipped": 0
        }
    
    def connect_db(self):
        """Connect to MongoDB."""
        self.db = get_sync_database()
        logger.info(f"Connected to MongoDB: {self.db.name}")
    
    async def fetch_all_members(
        self,
        chamber: Optional[str] = None,
        state: Optional[str] = None
    ) -> list:
        """
        Fetch all current members from Congress.gov.
        
        Args:
            chamber: Filter by chamber ("house" or "senate")
            state: Filter by state code (e.g., "UT")
            
        Returns:
            List of member data dicts
        """
        all_members = []
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            offset = 0
            limit = 250
            
            while True:
                url = f"{self.base_url}/member"
                params = {
                    "api_key": self.api_key,
                    "format": "json",
                    "limit": limit,
                    "offset": offset,
                    "currentMember": "true"
                }
                
                logger.info(f"Fetching members {offset}-{offset+limit}...")
                
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                members = data.get("members", [])
                if not members:
                    break
                
                if self.verbose:
                    logger.debug(f"Batch has {len(members)} members before filtering")
                
                # Apply filters
                filtered_count = 0
                for member in members:
                    # Get state from member (it should be present in the list endpoint)
                    member_state = member.get("state")
                    member_name = member.get("name", "Unknown")
                    
                    if self.verbose and state:
                        logger.debug(f"Checking {member_name}: state={member_state}, looking for {state}")
                    
                    # State filter - handle both full names and abbreviations
                    if state:
                        state_upper = state.upper()
                        # Check if it matches either the abbreviation OR full state name
                        if not (member_state == state_upper or member_state.upper() == self._state_abbrev_to_name(state_upper)):
                            continue
                    
                    # Chamber filter (check after state to be more efficient)
                    if chamber:
                        member_chamber = self._get_current_chamber(member)
                        if member_chamber != chamber:
                            continue
                    
                    filtered_count += 1
                    all_members.append(member)
                
                if self.verbose:
                    logger.debug(f"After filtering: {filtered_count} members match")
                
                # Check pagination
                pagination = data.get("pagination", {})
                if pagination.get("next") is None:
                    break
                
                offset += limit
                await asyncio.sleep(0.3)  # Rate limiting
        
        logger.info(f"Fetched {len(all_members)} members")
        return all_members
    
    async def fetch_member_details(self, bioguide_id: str) -> dict:
        """
        Fetch full details for a specific member.
        
        Args:
            bioguide_id: The member's bioguide identifier
            
        Returns:
            Complete member data dict
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{self.base_url}/member/{bioguide_id}"
            params = {
                "api_key": self.api_key,
                "format": "json"
            }
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return data.get("member", {})
    
    def _get_current_chamber(self, member: dict) -> Optional[str]:
        """Extract current chamber from member data."""
        terms = member.get("terms", {})
        if isinstance(terms, dict):
            items = terms.get("item", [])
        else:
            items = terms
        
        if items:
            # Get most recent term
            latest = items[-1]
            chamber = latest.get("chamber", "")
            if "House" in chamber:
                return "house"
            elif "Senate" in chamber:
                return "senate"
        
        return None
    
    def _state_abbrev_to_name(self, abbrev: str) -> str:
        """Convert state abbreviation to full name."""
        state_map = {
            "UT": "UTAH",
            "CA": "CALIFORNIA",
            "TX": "TEXAS",
            "NY": "NEW YORK",
            # Add more as needed, but API seems to use full names
        }
        return state_map.get(abbrev.upper(), abbrev)
    
    def _extract_committees(self, member_data: dict) -> list:
        """Extract committee assignments."""
        committees = []
        
        sponsored_legislation = member_data.get("sponsoredLegislation", {})
        # Note: Full committee data requires additional API calls
        # For now, we'll get basic info and can expand later
        
        return committees
    
    def _extract_contact_info(self, member_data: dict) -> dict:
        """Extract contact information."""
        contact = {}
        
        # Official URL from terms
        terms = member_data.get("terms", {})
        if isinstance(terms, dict):
            items = terms.get("item", [])
        else:
            items = terms
        
        if items:
            latest = items[-1]
            contact["website"] = latest.get("memberUrl")
        
        # Note: Phone, email, office addresses require scraping from website
        # or additional data sources - can add later
        
        return contact
    
    def _transform_member(self, member_summary: dict, member_detail: dict) -> dict:
        """
        Transform Congress.gov data to our politician schema.
        
        Args:
            member_summary: Basic member data from list
            member_detail: Full member data from detail endpoint
            
        Returns:
            Dict matching our Politician model
        """
        bioguide_id = member_detail.get("bioguideId") or member_summary.get("bioguideId")
        
        # Basic info
        direct_name = member_detail.get("directOrderName", "")
        name_parts = direct_name.split(", ", 1) if ", " in direct_name else ["", ""]
        last_name = name_parts[0]
        first_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # Get current term info
        terms = member_detail.get("terms", {})
        if isinstance(terms, dict):
            term_items = terms.get("item", [])
        else:
            term_items = terms
        
        current_term = term_items[-1] if term_items else {}
        
        chamber_str = current_term.get("chamber", "")
        if "House" in chamber_str:
            chamber = "house"
            title = "Representative"
        elif "Senate" in chamber_str:
            chamber = "senate"
            title = "Senator"
        else:
            chamber = "unknown"
            title = "Member"
        
        # Party - get from party history
        party_history = member_detail.get("partyHistory", [])
        current_party = party_history[0].get("partyCode", "Unknown") if party_history else "Unknown"
        
        # Map party codes
        party_map = {
            "D": "D",
            "R": "R",
            "I": "I",
            "ID": "I",  # Independent Democrat
            "Dem": "D",
            "Rep": "R"
        }
        party = party_map.get(current_party, current_party)
        
        # State and district
        state = member_summary.get("state")
        district = member_summary.get("district")
        
        # Build politician document
        politician = {
            "bioguide_id": bioguide_id,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": member_summary.get("name", direct_name),
            "party": party,
            "state": state,
            "district": str(district) if district else None,
            "chamber": chamber,
            "jurisdiction": "federal",
            "title": title,
            "in_office": True,
            "term_start": current_term.get("startYear"),
            "term_end": current_term.get("endYear"),
            
            # External IDs (for linking to other data sources)
            # These would need to come from mapping tables
            "fec_candidate_id": None,  # TODO: Add FEC mapping
            "opensecrets_id": None,    # TODO: Add OpenSecrets mapping
            "govtrack_id": None,       # TODO: Add GovTrack mapping
            "votesmart_id": None,      # TODO: Add VoteSmart mapping
            
            # Contact
            "website": current_term.get("memberUrl"),
            "phone": None,  # TODO: Scrape from website
            "twitter": None,  # TODO: Add from social media APIs
            
            # Metadata
            "photo_url": member_detail.get("depiction", {}).get("imageUrl"),
            "last_updated": datetime.utcnow(),
            
            # Store raw data for reference
            "_raw_congress_gov": {
                "bioguide_id": bioguide_id,
                "updated_at": member_detail.get("updateDate")
            }
        }
        
        return politician
    
    def save_politician(self, politician: dict) -> bool:
        """
        Save politician to MongoDB.
        
        Args:
            politician: Politician document
            
        Returns:
            True if new insert, False if update
        """
        collection = self.db.politicians
        
        result = collection.update_one(
            {"bioguide_id": politician["bioguide_id"]},
            {"$set": politician},
            upsert=True
        )
        
        return result.upserted_id is not None
    
    async def sync(
        self,
        chamber: Optional[str] = None,
        state: Optional[str] = None,
        limit: Optional[int] = None
    ):
        """
        Run the full sync process.
        
        Args:
            chamber: Filter by chamber
            state: Filter by state
            limit: Max members to process (for testing)
        """
        print("👥 Syncing Politicians from Congress.gov")
        print("=" * 60)
        
        if chamber:
            print(f"Chamber: {chamber.title()}")
        if state:
            print(f"State: {state}")
        if limit:
            print(f"Limit: {limit}")
        print()
        
        # Connect to database
        self.connect_db()
        
        # Fetch member list
        print("📥 Fetching member list...")
        members = await self.fetch_all_members(chamber=chamber, state=state)
        
        if limit:
            members = members[:limit]
        
        print(f"   Found {len(members)} members to sync")
        print()
        
        # Process each member
        print("🔄 Fetching detailed profiles...")
        print("-" * 60)
        
        for i, member_summary in enumerate(members, 1):
            bioguide_id = member_summary.get("bioguideId")
            name = member_summary.get("name", "Unknown")
            
            try:
                # Fetch full details
                logger.info(f"Processing {i}/{len(members)}: {name}")
                print(f"   {i}/{len(members)}: {name}...", end=" ")
                
                member_detail = await self.fetch_member_details(bioguide_id)
                
                # Transform to our schema
                politician = self._transform_member(member_summary, member_detail)
                
                # Save to database
                is_new = self.save_politician(politician)
                
                if is_new:
                    self.stats["inserted"] += 1
                    print("✅ inserted")
                else:
                    self.stats["updated"] += 1
                    print("✅ updated")
                
                self.stats["processed"] += 1
                
                # Rate limiting
                await asyncio.sleep(0.3)
                
            except Exception as e:
                self.stats["errors"] += 1
                print(f"❌ error: {e}")
                logger.error(f"Error processing {name} ({bioguide_id}): {e}")
        
        # Print summary
        print()
        print("=" * 60)
        print("✅ Sync Complete!")
        print("=" * 60)
        print(f"📊 Statistics:")
        print(f"   • Processed:  {self.stats['processed']}")
        print(f"   • Inserted:   {self.stats['inserted']} new records")
        print(f"   • Updated:    {self.stats['updated']} records")
        print(f"   • Errors:     {self.stats['errors']}")
        print()


async def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sync politicians from Congress.gov to MongoDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sync all current members
  uv run python scripts/sync_politicians.py
  
  # Sync only Senate
  uv run python scripts/sync_politicians.py --chamber senate
  
  # Sync only Utah delegation
  uv run python scripts/sync_politicians.py --state UT
  
  # Sync Utah House members only
  uv run python scripts/sync_politicians.py --state UT --chamber house
  
  # Test with first 10 members
  uv run python scripts/sync_politicians.py --limit 10 --verbose
        """
    )
    
    parser.add_argument(
        "--chamber",
        choices=["house", "senate"],
        help="Filter by chamber"
    )
    
    parser.add_argument(
        "--state",
        type=str,
        help="Filter by state (2-letter code, e.g., UT, CA)"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of members to process (for testing)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Log file with timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"sync_politicians_{timestamp}.log"
    
    # Configure logging to both file and console
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger.info(f"Logging to: {log_file}")
    print(f"📝 Log file: {log_file}")
    print()
    
    try:
        syncer = PoliticianSyncer(verbose=args.verbose)
        await syncer.sync(
            chamber=args.chamber,
            state=args.state,
            limit=args.limit
        )
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Sync interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
