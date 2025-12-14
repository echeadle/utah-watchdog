"""
Politician data models.

Defines the structure for federal and state legislators.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional, List


from pydantic import BaseModel, Field


class Chamber(str, Enum):
    """Legislative chamber."""
    SENATE = "senate"
    HOUSE = "house"


class Party(str, Enum):
    """Political party affiliation."""
    DEMOCRAT = "D"
    REPUBLICAN = "R"
    INDEPENDENT = "I"
    OTHER = "O"


class Politician(BaseModel):
    """
    A federal legislator (Senator or Representative).
    
    For MVP, we focus on Utah's federal delegation.
    State legislators can be added later with additional fields.
    """
    
    # Unique identifier (bioguide_id from Congress.gov)
    bioguide_id: str = Field(..., description="Unique ID from Congress.gov")
    
    # Basic info
    first_name: str
    last_name: str
    full_name: str
    
    # Political info
    party: Party
    state: str = Field(..., min_length=2, max_length=2, description="Two-letter state code")
    chamber: Chamber
    district: Optional[int] = Field(None, description="House district number (None for Senators)")
    
    # Status
    in_office: bool = True
    
    # Optional details (we'll populate these as we get more data)
    title: Optional[str] = None  # "Senator", "Representative"
    website: Optional[str] = None
    phone: Optional[str] = None
    office: Optional[str] = None
    committees: List[dict] = Field(default_factory=list, description="Committee memberships")
    
    # Metadata
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    def __str__(self) -> str:
        """Human-readable representation."""
        chamber_title = "Sen." if self.chamber == Chamber.SENATE else "Rep."
        district_str = f" (District {self.district})" if self.district else ""
        return f"{chamber_title} {self.full_name} ({self.party.value}-{self.state}){district_str}"


class PoliticianSummary(BaseModel):
    """
    Abbreviated politician info for lists and search results.
    
    Lighter weight than full Politician model.
    """
    bioguide_id: str
    full_name: str
    party: Party
    state: str
    chamber: Chamber
    district: Optional[int] = None
    
    def __str__(self) -> str:
        chamber_title = "Sen." if self.chamber == Chamber.SENATE else "Rep."
        return f"{chamber_title} {self.full_name} ({self.party.value}-{self.state})"