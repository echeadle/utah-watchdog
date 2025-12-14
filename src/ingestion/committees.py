"""
Ingester for congressional committee assignments.

Fetches committee membership from Congress.gov API.
"""
import asyncio
import httpx
from typing import AsyncGenerator
from datetime import datetime
import logging

from src.ingestion.base import BaseIngester
from src.config.settings import settings
from src.config.constants import CONGRESS_GOV_BASE_URL, CURRENT_CONGRESS

logger = logging.getLogger(__name__)


class CommitteeIngester(BaseIngester[dict]):
    """
    Ingest committee assignments for current Congress.
    """
    
    def __init__(self, congress: int = CURRENT_CONGRESS):
        super().__init__()
        self.congress = congress
        self.api_key = settings.CONGRESS_GOV_API_KEY
        self.base_url = CONGRESS_GOV_BASE_URL
        
    async def fetch_data(self, **kwargs) -> AsyncGenerator[dict, None]:
        """
        Fetch committees and their members.
        
        Yields:
            Committee data with member assignments
        """
        self.logger.info(f"Fetching committees for Congress {self.congress}...")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Get list of committees
            for chamber in ["house", "senate"]:
                try:
                    url = f"{self.base_url}/committee/{chamber}"
                    params = {
                        "api_key": self.api_key,
                        "format": "json",
                        "limit": 250
                    }
                    
                    self.logger.info(f"Fetching {chamber} committees...")
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    
                    data = response.json()
                    committees = data.get("committees", [])
                    
                    self.logger.info(f"Found {len(committees)} {chamber} committees")
                    
                    # For each committee, fetch members
                    for committee in committees:
                        committee_code = committee.get("systemCode")
                        committee_name = committee.get("name")
                        
                        if not committee_code:
                            continue
                        
                        # Fetch committee members
                        member_url = committee.get("url")
                        if member_url:
                            try:
                                member_response = await client.get(
                                    member_url,
                                    params={"api_key": self.api_key, "format": "json"}
                                )
                                
                                if member_response.status_code == 200:
                                    member_data = member_response.json()
                                    committee_detail = member_data.get("committee", {})
                                    
                                    # Get current members
                                    members = committee_detail.get("members", [])
                                    
                                    yield {
                                        "committee_code": committee_code,
                                        "committee_name": committee_name,
                                        "chamber": chamber,
                                        "congress": self.congress,
                                        "members": members
                                    }
                                    
                                    await asyncio.sleep(0.3)
                                    
                            except Exception as e:
                                self.logger.error(f"Error fetching members for {committee_code}: {e}")
                                self.stats["errors"] += 1
                    
                    await asyncio.sleep(0.5)
                    
                except httpx.HTTPError as e:
                    self.logger.error(f"HTTP error fetching {chamber} committees: {e}")
                    self.stats["errors"] += 1
                except Exception as e:
                    self.logger.error(f"Error fetching {chamber} committees: {e}")
                    self.stats["errors"] += 1
    
    async def transform(self, raw: dict) -> dict:
        """
        Transform committee data.
        
        Returns dict as we're updating multiple politician records.
        """
        return raw
    
    async def load(self, committee_data: dict) -> bool:
        """
        Update politician records with committee assignments.
        
        Args:
            committee_data: Committee with member list
            
        Returns:
            False (always update, not insert)
        """
        committee_code = committee_data["committee_code"]
        committee_name = committee_data["committee_name"]
        chamber = committee_data["chamber"]
        members = committee_data["members"]
        
        if not members:
            return False
        
        # Update each member's record
        for member in members:
            bioguide_id = member.get("bioguideId")
            if not bioguide_id:
                continue
            
            # Determine role
            role = "Member"
            if member.get("rank") == 1:
                # Check if chair or ranking member
                party_name = member.get("partyName", "")
                # Simplified logic - would need to check majority party
                if "Chair" in member.get("title", ""):
                    role = "Chair"
                elif "Ranking" in member.get("title", ""):
                    role = "Ranking Member"
            
            # Add committee to politician's record
            await self.db.politicians.update_one(
                {"bioguide_id": bioguide_id},
                {
                    "$addToSet": {
                        "committees": {
                            "code": committee_code,
                            "name": committee_name,
                            "chamber": chamber,
                            "role": role
                        }
                    },
                    "$set": {
                        "last_updated": datetime.utcnow()
                    }
                }
            )
        
        return False


async def main():
    """CLI entry point"""
    logging.basicConfig(level=logging.INFO)
    
    ingester = CommitteeIngester(congress=CURRENT_CONGRESS)
    stats = await ingester.run()
    
    print("\n=== Committee Sync Complete ===")
    print(f"Processed: {stats['processed']}")
    print(f"Errors: {stats['errors']}")


if __name__ == "__main__":
    asyncio.run(main())