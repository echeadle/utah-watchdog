"""
Ingester for current members of Congress from Congress.gov API.

This keeps the politician database up-to-date with who's currently serving.
Handles transitions like retirements, special elections, and new terms.
"""
import asyncio
import httpx
from typing import AsyncGenerator
from datetime import date, datetime
import logging

from src.ingestion.base import BaseIngester
from src.models.politician import Politician, Chamber, Party
from src.config.settings import settings
from src.config.constants import CONGRESS_GOV_BASE_URL, US_STATES

logger = logging.getLogger(__name__)


class CongressMembersIngester(BaseIngester[Politician]):
    """
    Ingest current members of Congress from Congress.gov API.
    
    Uses the /member/congress/{congress}/{state} endpoint with 
    currentMember=true to get only active legislators.
    """
    
    def __init__(self, congress: int = 118):
        """
        Initialize the ingester.
        
        Args:
            congress: Congress number (e.g., 118 for 118th Congress, 2023-2025)
        """
        super().__init__()
        self.congress = congress
        self.api_key = settings.CONGRESS_GOV_API_KEY
        self.base_url = CONGRESS_GOV_BASE_URL
        
    async def fetch_data(self, **kwargs) -> AsyncGenerator[dict, None]:
        """
        Fetch current members from all states.
        
        Yields:
            Raw member data from Congress.gov API
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch for each state
            for state_code in US_STATES:
                try:
                    url = f"{self.base_url}/member/congress/{self.congress}/{state_code}"
                    params = {
                        "currentMember": "true",  # Only active members
                        "api_key": self.api_key,
                        "format": "json",
                        "limit": 250
                    }
                    
                    self.logger.info(f"Fetching members for {state_code}...")
                    response = await client.get(url, params=params)
                    
                    if response.status_code == 404:
                        # Some territories might not have data
                        self.logger.debug(f"No data for {state_code}")
                        continue
                        
                    response.raise_for_status()
                    data = response.json()
                    
                    members = data.get("members", [])
                    self.logger.info(f"Found {len(members)} members for {state_code}")
                    
                    for member in members:
                        # Add state code to the member data
                        member["state_code"] = state_code
                        yield member
                    
                    # Respect rate limits (5000/hour = ~1.4/second)
                    await asyncio.sleep(0.2)
                    
                except httpx.HTTPError as e:
                    self.logger.error(f"HTTP error fetching {state_code}: {e}")
                    self.stats["errors"] += 1
                except Exception as e:
                    self.logger.error(f"Error fetching {state_code}: {e}")
                    self.stats["errors"] += 1
                    
    
    async def transform(self, raw: dict) -> Politician:
        """
        Transform Congress.gov member data to our Politician model.
        
        Args:
            raw: Raw member data from API
            
        Returns:
            Politician model instance
        """
        # Determine chamber
        terms = raw.get("terms", {}).get("item", [])
        current_term = terms[0] if terms else {}
        
        chamber_str = current_term.get("chamber", "").lower()
        if chamber_str == "senate":
            chamber = Chamber.SENATE
            district = None
        else:  # House
            chamber = Chamber.HOUSE
            district_num = raw.get("district")
            district = int(district_num) if district_num else None
        
        # Map party
        party_name = raw.get("partyName", "")
        if "Republican" in party_name:
            party = Party.REPUBLICAN
        elif "Democrat" in party_name:
            party = Party.DEMOCRAT
        elif "Independent" in party_name:
            party = Party.INDEPENDENT
        else:
            party = Party.OTHER
        
        # Parse name - API returns "Last, First" or "Last, First Middle"
        full_name_raw = raw.get("name", "")
        if ", " in full_name_raw:
            parts = full_name_raw.split(", ", 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip()
            full_name = f"{first_name} {last_name}"
        else:
            # Fallback if format is different
            full_name = full_name_raw
            name_parts = full_name_raw.split()
            first_name = name_parts[0] if name_parts else ""
            last_name = name_parts[-1] if len(name_parts) > 1 else ""
        
        # Get bioguide ID (our primary key)
        bioguide_id = raw.get("bioguideId")
        if not bioguide_id:
            raise ValueError(f"Missing bioguideId for {full_name}")
        
        # Title
        if chamber == Chamber.SENATE:
            title = "Senator"
        else:
            title = "Representative"
        
        return Politician(
            bioguide_id=bioguide_id,
            first_name=first_name,
            last_name=last_name,
            full_name=full_name,
            party=party,
            state=raw.get("state_code"),
            chamber=chamber,
            district=district,
            title=title,
            in_office=True,
            website=raw.get("officialWebsiteUrl"),
            last_updated=datetime.utcnow()
        )
        
    async def load(self, politician: Politician) -> bool:
        """
        Upsert politician into MongoDB.
        
        Also handles marking old records as out of office when members change.
        
        Args:
            politician: Politician model to save
            
        Returns:
            True if this was a new insert, False if update
        """
        collection = self.db.politicians
        
        # First, check if this is a new member for this seat
        # If so, mark the old occupant as no longer in office
        if politician.chamber == Chamber.SENATE:
            # For Senate, match by state and chamber
            query = {
                "state": politician.state,
                "chamber": "senate",
                "in_office": True,
                "bioguide_id": {"$ne": politician.bioguide_id}  # Different person
            }
        else:
            # For House, match by state and district
            query = {
                "state": politician.state,
                "district": politician.district,
                "chamber": "house",
                "in_office": True,
                "bioguide_id": {"$ne": politician.bioguide_id}
            }
        
        # Mark old occupant as out of office
        update_result = await collection.update_many(
            query,
            {"$set": {"in_office": False, "last_updated": datetime.utcnow()}}
        )
        
        if update_result.modified_count > 0:
            self.logger.info(
                f"Marked {update_result.modified_count} old record(s) as out of office "
                f"for {politician.full_name}'s seat"
            )
        
        # Now upsert the current member
        result = await collection.update_one(
            {"bioguide_id": politician.bioguide_id},
            {"$set": politician.model_dump()},
            upsert=True
        )
        
        return result.upserted_id is not None
    
    async def run_full_sync(self) -> dict:
        """
        Run a complete sync of all current members.
        
        Returns:
            Statistics about the sync operation
        """
        self.logger.info(f"Starting full sync of Congress {self.congress} members...")
        stats = await self.run()
        
        self.logger.info("Sync complete!")
        return stats


async def main():
    """CLI entry point for testing"""
    logging.basicConfig(level=logging.INFO)
    
    ingester = CongressMembersIngester(congress=118)
    stats = await ingester.run_full_sync()
    
    print("\n=== Sync Complete ===")
    print(f"Processed: {stats['processed']}")
    print(f"Inserted: {stats['inserted']}")
    print(f"Updated: {stats['updated']}")
    print(f"Errors: {stats['errors']}")
    print(f"Duration: {stats['completed_at'] - stats['started_at']}")


if __name__ == "__main__":
    asyncio.run(main())