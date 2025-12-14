"""
Congress.gov API client.

Handles fetching data from the Congress.gov API.
API Docs: https://api.congress.gov/
"""

import httpx
from datetime import date, datetime
from typing import Optional

from src.config import settings, CONGRESS_GOV_BASE_URL, CURRENT_CONGRESS
from src.models import Vote, PoliticianVote, VotePosition


class CongressGovClient:
    """
    Client for the Congress.gov API.
    
    Usage:
        client = CongressGovClient()
        votes = client.get_recent_votes(chamber="senate", limit=10)
    """
    
    def __init__(self):
        self.base_url = CONGRESS_GOV_BASE_URL
        self.api_key = settings.CONGRESS_GOV_API_KEY
    
    def _make_request(self, endpoint: str, params: dict = None) -> dict:
        """
        Make a request to the Congress.gov API.
        
        Args:
            endpoint: API endpoint (e.g., "/bill/118/hr")
            params: Query parameters
            
        Returns:
            JSON response as dict
        """
        url = f"{self.base_url}{endpoint}"
        
        # Always include API key and format
        request_params = {
            "api_key": self.api_key,
            "format": "json",
        }
        if params:
            request_params.update(params)
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=request_params)
            response.raise_for_status()
            return response.json()
    
    def get_member(self, bioguide_id: str) -> dict:
        """
        Get details about a specific member of Congress.
        
        Args:
            bioguide_id: The member's bioguide ID
            
        Returns:
            Member data from Congress.gov
        """
        endpoint = f"/member/{bioguide_id}"
        return self._make_request(endpoint)
    
    def get_member_votes(
        self, 
        bioguide_id: str, 
        limit: int = 20,
        offset: int = 0
    ) -> list[dict]:
        """
        Get recent votes for a specific member.
        
        Args:
            bioguide_id: The member's bioguide ID
            limit: Maximum number of votes to return
            offset: Offset for pagination
            
        Returns:
            List of vote records
        """
        endpoint = f"/member/{bioguide_id}/votes"
        params = {"limit": limit, "offset": offset}
        
        response = self._make_request(endpoint, params)
        return response.get("votes", [])
    
    def get_vote_details(
        self,
        congress: int,
        chamber: str,
        roll_call: int,
        session: int = 1
    ) -> dict:
        """
        Get detailed information about a specific vote.
        
        Args:
            congress: Congress number (e.g., 118)
            chamber: "senate" or "house"
            roll_call: Roll call number
            session: Session number (1 or 2)
            
        Returns:
            Vote details including how each member voted
        """
        endpoint = f"/vote/{congress}/{chamber}/{session}/{roll_call}"
        return self._make_request(endpoint)
    
    def parse_vote_to_model(self, vote_data: dict, bioguide_id: str) -> tuple[Optional[Vote], Optional[PoliticianVote]]:
        """
        Parse Congress.gov vote data into our models.
        
        Args:
            vote_data: Raw vote data from Congress.gov
            bioguide_id: The politician who cast this vote
            
        Returns:
            Tuple of (Vote, PoliticianVote) models
        """
        try:
            # Extract vote info - structure varies, so we handle both formats
            congress = vote_data.get("congress", CURRENT_CONGRESS)
            chamber = vote_data.get("chamber", "").lower()
            
            # Handle chamber naming inconsistencies
            if chamber in ["senate", "s"]:
                chamber = "senate"
            elif chamber in ["house", "house of representatives", "h"]:
                chamber = "house"
            
            roll_call = vote_data.get("rollCallNumber") or vote_data.get("rollNumber")
            if not roll_call:
                return None, None
            
            session = vote_data.get("session", 1)
            
            # Create vote_id
            vote_id = f"{chamber}-{congress}-{session}-{roll_call}"
            
            # Parse date
            date_str = vote_data.get("date") or vote_data.get("voteDate")
            if date_str:
                # Handle different date formats
                if "T" in date_str:
                    vote_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
                else:
                    vote_date = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
            else:
                vote_date = date.today()
            
            # Create Vote model
            vote = Vote(
                vote_id=vote_id,
                congress=int(congress),
                session=int(session),
                chamber=chamber,
                roll_call=int(roll_call),
                question=vote_data.get("question", vote_data.get("description", "Unknown")),
                description=vote_data.get("description"),
                result=vote_data.get("result", "Unknown"),
                vote_date=vote_date,
                source_url=vote_data.get("url"),
            )
            
            # Parse politician's position
            position_str = vote_data.get("memberVotes", vote_data.get("position", "Not Voting"))
            
            # Map to our enum
            position_map = {
                "yea": VotePosition.YEA,
                "aye": VotePosition.YEA,
                "yes": VotePosition.YEA,
                "nay": VotePosition.NAY,
                "no": VotePosition.NAY,
                "not voting": VotePosition.NOT_VOTING,
                "present": VotePosition.PRESENT,
            }
            position = position_map.get(position_str.lower(), VotePosition.NOT_VOTING)
            
            # Create PoliticianVote model
            politician_vote = PoliticianVote(
                vote_id=vote_id,
                bioguide_id=bioguide_id,
                position=position,
            )
            
            return vote, politician_vote
            
        except Exception as e:
            print(f"Error parsing vote: {e}")
            return None, None


# Convenience function
def get_congress_client() -> CongressGovClient:
    """Get a Congress.gov API client instance."""
    return CongressGovClient()