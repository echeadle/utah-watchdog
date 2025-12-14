"""
Vote data models.

Defines the structure for roll call votes and how politicians voted.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class VotePosition(str, Enum):
    """How a legislator voted."""
    YEA = "Yea"
    NAY = "Nay"
    NOT_VOTING = "Not Voting"
    PRESENT = "Present"


class Vote(BaseModel):
    """
    A roll call vote in Congress.
    
    This represents the overall vote (the question being voted on),
    not individual politician positions.
    """
    
    # Unique identifier: "{chamber}-{congress}-{session}-{roll_call}"
    vote_id: str = Field(..., description="Unique vote identifier")
    
    # Congress info
    congress: int = Field(..., description="Congress number (e.g., 118)")
    session: int = Field(..., description="Session (1 or 2)")
    chamber: str = Field(..., description="senate or house")
    
    # Vote details
    roll_call: int = Field(..., description="Roll call number")
    question: str = Field(..., description="What was being voted on")
    description: Optional[str] = None
    vote_type: Optional[str] = None  # "YEA-AND-NAY", "RECORDED VOTE", etc.
    
    # Result
    result: str = Field(..., description="Passed, Failed, Agreed to, etc.")
    vote_date: date
    
    # Totals
    yea_total: int = 0
    nay_total: int = 0
    not_voting_total: int = 0
    present_total: int = 0
    
    # Related bill (if applicable)
    bill_id: Optional[str] = None  # e.g., "hr-1234-118"
    bill_title: Optional[str] = None
    
    # Source
    source_url: Optional[str] = None
    
    # Metadata
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class PoliticianVote(BaseModel):
    """
    How a specific politician voted on a specific roll call.
    
    Links a politician to a vote with their position.
    """
    
    # Compound key
    vote_id: str = Field(..., description="Reference to Vote.vote_id")
    bioguide_id: str = Field(..., description="Reference to Politician.bioguide_id")
    
    # Their vote
    position: VotePosition
    
    # Denormalized for easier queries
    politician_name: Optional[str] = None
    politician_party: Optional[str] = None
    politician_state: Optional[str] = None
    
    # Metadata
    last_updated: datetime = Field(default_factory=datetime.utcnow)