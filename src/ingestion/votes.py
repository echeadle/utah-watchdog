"""
Ingester for congressional roll call votes.

Fetches votes from Congress.gov and individual member positions
from House Clerk XML files.
"""
import asyncio
import httpx
import xml.etree.ElementTree as ET
from typing import AsyncGenerator, Optional
from datetime import date, datetime
import logging

from src.ingestion.base import BaseIngester
from src.models.legislation import Vote, PoliticianVote
from src.config.settings import settings
from src.config.constants import CONGRESS_GOV_BASE_URL, CURRENT_CONGRESS

logger = logging.getLogger(__name__)


class VotesIngester(BaseIngester[Vote]):
    """
    Ingest roll call votes from Congress.gov.
    
    Fetches vote events and individual member positions from House Clerk XML.
    """
    
    def __init__(self, congress: int = CURRENT_CONGRESS):
        super().__init__()
        self.congress = congress
        self.api_key = settings.CONGRESS_GOV_API_KEY
        self.base_url = CONGRESS_GOV_BASE_URL
        
    async def fetch_data(
        self,
        chamber: str = "house",  # Currently only "house" is supported
        session: int = None,  # 1 or 2, None = fetch both
        limit: Optional[int] = None
    ) -> AsyncGenerator[dict, None]:
        """
        Fetch roll call votes from Congress.gov.
        
        Args:
            chamber: "house" (senate not yet available in API)
            session: Session number (1 or 2), None = both sessions
            limit: Max votes to fetch total (None = all)
            
        Yields:
            Raw vote data from API with member votes
        """
        if chamber == "senate":
            self.logger.warning("Senate votes not yet available in Congress.gov API (beta)")
            return
        
        self.logger.info(f"Fetching {chamber} votes for Congress {self.congress}...")
        
        # Determine which sessions to fetch
        sessions_to_fetch = [session] if session else [1, 2]
        
        total_fetched = 0
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            for sess in sessions_to_fetch:
                self.logger.info(f"Fetching session {sess} votes...")
                
                offset = 0
                batch_size = 250
                
                while True:
                    try:
                        # Use the correct beta endpoint
                        url = f"{self.base_url}/house-vote/{self.congress}/{sess}"
                        params = {
                            "api_key": self.api_key,
                            "format": "json",
                            "limit": batch_size,
                            "offset": offset
                        }
                        
                        self.logger.info(f"Fetching session {sess} votes {offset}-{offset+batch_size}...")
                        response = await client.get(url, params=params)
                        
                        if response.status_code == 404:
                            self.logger.info(f"No more votes for session {sess}")
                            break
                        
                        response.raise_for_status()
                        data = response.json()
                        
                        votes = data.get("houseRollCallVotes", [])
                        if not votes:
                            self.logger.info(f"No more votes for session {sess}")
                            break
                        
                        self.logger.info(f"Found {len(votes)} votes in batch")
                        
                        # Process each vote
                        for vote_summary in votes:
                            try:
                                # Get full vote details from the URL
                                vote_url = vote_summary.get("url")
                                if vote_url:
                                    detail_params = {
                                        "api_key": self.api_key,
                                        "format": "json"
                                    }
                                    
                                    detail_response = await client.get(vote_url, params=detail_params)
                                    
                                    if detail_response.status_code == 200:
                                        vote_detail = detail_response.json().get("houseRollCallVote", {})
                                        
                                        # Fetch member votes from House Clerk XML
                                        source_xml_url = vote_detail.get("sourceDataURL")
                                        if source_xml_url:
                                            try:
                                                xml_response = await client.get(source_xml_url)
                                                if xml_response.status_code == 200:
                                                    # Parse XML to extract member votes
                                                    member_votes = self._parse_house_clerk_xml(xml_response.text)
                                                    vote_detail["memberVotes"] = member_votes
                                                    self.logger.info(f"Fetched {len(member_votes)} member votes from XML")
                                            except Exception as e:
                                                self.logger.warning(f"Could not fetch member votes XML: {e}")
                                        
                                        yield vote_detail
                                        
                                        total_fetched += 1
                                        
                                        if limit and total_fetched >= limit:
                                            self.logger.info(f"Reached limit of {limit} votes")
                                            return
                                        
                                        await asyncio.sleep(0.3)
                                        
                            except Exception as e:
                                self.logger.error(f"Error fetching vote details: {e}")
                                self.stats["errors"] += 1
                        
                        offset += batch_size
                        await asyncio.sleep(0.5)
                        
                    except httpx.HTTPError as e:
                        self.logger.error(f"HTTP error: {e}")
                        self.stats["errors"] += 1
                        break
                    except Exception as e:
                        self.logger.error(f"Error: {e}")
                        self.stats["errors"] += 1
                        break
    
    async def transform(self, raw: dict) -> Vote:
        """
        Transform Congress.gov house-vote data to our Vote model.
        
        Args:
            raw: Raw vote data from API
            
        Returns:
            Vote model instance
        """
        # Build vote ID from identifier
        identifier = raw.get("identifier", "")
        congress = raw.get("congress")
        session = raw.get("sessionNumber", 1)
        roll_number = raw.get("rollCallNumber")
        
        vote_id = f"house-roll-{roll_number}-{congress}"
        
        # Get vote question and result
        question = raw.get("voteQuestion", "Unknown")
        result = raw.get("result", "Unknown")
        
        # Get vote date from startDate
        start_date_str = raw.get("startDate")
        vote_date = self._parse_date(start_date_str)
        
        # Get counts from party totals
        party_totals = raw.get("votePartyTotal", [])
        yea_count = 0
        nay_count = 0
        present_count = 0
        not_voting_count = 0
        
        for party_item in party_totals:
            yea_count += party_item.get("yeaTotal", 0)
            nay_count += party_item.get("nayTotal", 0)
            present_count += party_item.get("presentTotal", 0)
            not_voting_count += party_item.get("notVotingTotal", 0)
        
        # Try to link to a bill
        bill_id = None
        legislation_type = raw.get("legislationType")
        legislation_number = raw.get("legislationNumber")
        
        if legislation_type and legislation_number:
            bill_type = legislation_type.lower()
            bill_id = f"{bill_type}-{legislation_number}-{congress}"
        
        return Vote(
            vote_id=vote_id,
            bill_id=bill_id,
            chamber="house",
            congress=int(congress),
            session=int(session),
            roll_number=int(roll_number),
            question=question,
            result=result,
            vote_date=vote_date,
            yea_count=int(yea_count),
            nay_count=int(nay_count),
            present_count=int(present_count),
            not_voting_count=int(not_voting_count),
            congress_gov_url=raw.get("legislationUrl"),
            last_updated=datetime.utcnow()
        )
    
    async def load(self, vote: Vote) -> bool:
        """
        Save vote and individual politician positions.
        
        Args:
            vote: Vote model to save
            
        Returns:
            True if new insert, False if update
        """
        # Convert to dict and handle date objects
        vote_data = vote.model_dump()
        
        # Convert date to datetime for MongoDB
        if vote_data.get('vote_date'):
            vote_data['vote_date'] = datetime.combine(
                vote_data['vote_date'],
                datetime.min.time()
            )
        
        # Save the vote event
        collection = self.db.votes
        
        result = await collection.update_one(
            {"vote_id": vote.vote_id},
            {"$set": vote_data},
            upsert=True
        )
        
        return result.upserted_id is not None
    
    async def process_item(self, raw_data: dict) -> bool:
        """
        Override to also save individual politician votes.
        """
        # Transform and save the vote
        success = await super().process_item(raw_data)
        
        if success:
            # Now save individual member positions
            await self._save_member_positions(raw_data)
        
        return success
    
    async def _save_member_positions(self, raw_vote: dict):
        """
        Save how each member voted.
        
        Args:
            raw_vote: Raw vote data with member positions
        """
        roll_number = raw_vote.get("rollCallNumber")
        congress = raw_vote.get("congress")
        vote_id = f"house-roll-{roll_number}-{congress}"
        
        # Get member votes
        member_votes = raw_vote.get("memberVotes", [])
        
        if not member_votes:
            self.logger.debug(f"No member positions found for {vote_id}")
            return
        
        collection = self.db.politician_votes
        
        for member_vote in member_votes:
            bioguide_id = member_vote.get("bioguideId")
            position = member_vote.get("voteCast")  # "Aye", "No", "Present", "Not Voting"
            
            if not bioguide_id or not position:
                continue
            
            politician_vote = PoliticianVote(
                vote_id=vote_id,
                bioguide_id=bioguide_id,
                position=position
            )
            
            await collection.update_one(
                {"vote_id": vote_id, "bioguide_id": bioguide_id},
                {"$set": politician_vote.model_dump()},
                upsert=True
            )
        
        self.logger.info(f"Saved {len(member_votes)} member votes for {vote_id}")
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            # Handle different date formats
            if "T" in date_str:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                return dt.date()
            return date.fromisoformat(date_str[:10])
        except:
            return None
    
    def _parse_house_clerk_xml(self, xml_text: str) -> list:
        """
        Parse House Clerk XML to extract member votes.
        
        Args:
            xml_text: XML content from clerk.house.gov
            
        Returns:
            List of dicts with bioguideId and voteCast
        """
        try:
            root = ET.fromstring(xml_text)
            
            member_votes = []
            
            # Find all recorded-vote elements
            for recorded_vote in root.findall('.//recorded-vote'):
                legislator = recorded_vote.find('legislator')
                vote_elem = recorded_vote.find('vote')
                
                if legislator is not None and vote_elem is not None:
                    bioguide_id = legislator.get('name-id')
                    vote_cast = vote_elem.text
                    
                    if bioguide_id and vote_cast:
                        member_votes.append({
                            'bioguideId': bioguide_id,
                            'voteCast': vote_cast  # "Aye", "No", "Present", "Not Voting"
                        })
            
            self.logger.debug(f"Parsed {len(member_votes)} member votes from XML")
            return member_votes
            
        except Exception as e:
            self.logger.error(f"Error parsing House Clerk XML: {e}")
            return []


async def main():
    """CLI entry point for testing"""
    logging.basicConfig(level=logging.INFO)
    
    ingester = VotesIngester(congress=CURRENT_CONGRESS)
    
    # Fetch 20 recent House votes for testing
    stats = await ingester.run(chamber="house", limit=5)
    
    print("\n=== Sync Complete ===")
    print(f"Processed: {stats['processed']}")
    print(f"Inserted: {stats['inserted']}")
    print(f"Updated: {stats['updated']}")
    print(f"Errors: {stats['errors']}")


if __name__ == "__main__":
    asyncio.run(main())