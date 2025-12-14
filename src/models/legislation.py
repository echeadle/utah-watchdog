"""
Legislation data models.

Defines structures for bills, resolutions, and votes.
"""
from datetime import date, datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class BillType(str, Enum):
    """Type of legislation."""
    HR = "hr"           # House Bill
    S = "s"             # Senate Bill
    HRES = "hres"       # House Resolution
    SRES = "sres"       # Senate Resolution
    HJRES = "hjres"     # House Joint Resolution
    SJRES = "sjres"     # Senate Joint Resolution
    HCONRES = "hconres" # House Concurrent Resolution
    SCONRES = "sconres" # Senate Concurrent Resolution


class BillStatus(str, Enum):
    """Current status of a bill."""
    INTRODUCED = "introduced"
    IN_COMMITTEE = "in_committee"
    PASSED_HOUSE = "passed_house"
    PASSED_SENATE = "passed_senate"
    TO_PRESIDENT = "to_president"
    BECAME_LAW = "became_law"
    VETOED = "vetoed"
    FAILED = "failed"


class Bill(BaseModel):
    """
    A piece of federal legislation.
    
    Represents bills, resolutions, and other legislative documents.
    """
    
    # Unique identifier (e.g., "hr-1234-119")
    bill_id: str = Field(..., description="Unique ID: {type}-{number}-{congress}")
    
    # Basic info
    bill_type: BillType
    number: int
    congress: int
    
    # Content
    title: str
    short_title: Optional[str] = None
    summary: Optional[str] = None
    
    # Status
    status: BillStatus = BillStatus.INTRODUCED
    introduced_date: date
    latest_action_date: Optional[date] = None
    latest_action_text: Optional[str] = None
    
    # Sponsorship
    sponsor_bioguide_id: Optional[str] = None  # Primary sponsor
    cosponsor_bioguide_ids: List[str] = Field(default_factory=list)
    
    # Categorization
    policy_area: Optional[str] = None  # Main topic
    subjects: List[str] = Field(default_factory=list)  # All topics
    
    # Links
    congress_gov_url: Optional[str] = None
    full_text_url: Optional[str] = None
    
    # Metadata
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    def __str__(self) -> str:
        """Human-readable representation."""
        return f"{self.bill_type.upper()}. {self.number} ({self.congress}th Congress): {self.title[:60]}..."


class BillSummary(BaseModel):
    """
    Abbreviated bill info for lists.
    """
    bill_id: str
    bill_type: BillType
    number: int
    congress: int
    title: str
    status: BillStatus
    sponsor_bioguide_id: Optional[str] = None
    introduced_date: date
    
    def __str__(self) -> str:
        return f"{self.bill_type.upper()}. {self.number}: {self.title[:50]}..."


class Vote(BaseModel):
    """
    A recorded vote on legislation.
    """
    
    # Unique identifier (e.g., "h-roll-123-119")
    vote_id: str = Field(..., description="Unique ID: {chamber}-roll-{number}-{congress}")
    
    # What was voted on
    bill_id: Optional[str] = None  # Link to Bill
    chamber: str  # "house" or "senate"
    congress: int
    session: int  # 1 or 2
    roll_number: int
    
    # Vote details
    question: str  # "On Passage", "On the Motion", etc.
    result: str    # "Passed", "Failed", "Agreed to"
    vote_date: date
    
    # Counts
    yea_count: int
    nay_count: int
    present_count: int = 0
    not_voting_count: int = 0
    
    # Link
    congress_gov_url: Optional[str] = None
    
    # Metadata
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class PoliticianVote(BaseModel):
    """
    How a specific politician voted.
    """
    vote_id: str  # Links to Vote
    bioguide_id: str  # Links to Politician
    position: str  # "Yea", "Nay", "Present", "Not Voting"