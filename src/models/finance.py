"""
Pydantic models for campaign finance data.

These models represent contributions, expenditures, and related financial data
from sources like OpenSecrets and FEC.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from decimal import Decimal
from enum import Enum


class ContributionType(str, Enum):
    """Type of contribution"""
    INDIVIDUAL = "individual"
    PAC = "pac"
    PARTY = "party"
    CANDIDATE = "candidate"
    OTHER = "other"


class Contribution(BaseModel):
    """
    Individual or PAC contribution to a candidate.
    
    Maps to OpenSecrets 'indivs' and 'pacs' data.
    """
    # Unique identifier
    id: str = Field(..., description="Unique contribution ID (FEC transaction ID or generated)")
    
    # Recipient information
    recipient_name: str = Field(..., description="Candidate name")
    recipient_id: Optional[str] = Field(None, description="OpenSecrets CRP ID (e.g., N00031696)")
    bioguide_id: Optional[str] = Field(None, description="Bioguide ID if matched to politician")
    committee_id: Optional[str] = Field(None, description="FEC Committee ID")
    
    # Contributor information
    contributor_name: str = Field(..., description="Name of contributor")
    contributor_type: ContributionType = Field(..., description="Type of contributor")
    contributor_employer: Optional[str] = Field(None, description="Employer name")
    contributor_occupation: Optional[str] = Field(None, description="Occupation")
    contributor_city: Optional[str] = Field(None, description="City")
    contributor_state: Optional[str] = Field(None, description="State")
    contributor_zip: Optional[str] = Field(None, description="ZIP code")
    
    # Contribution details
    amount: Decimal = Field(..., description="Contribution amount in dollars")
    contribution_date: date = Field(..., description="Date of contribution")
    
    # Categorization (OpenSecrets industry/sector codes)
    industry_code: Optional[str] = Field(None, description="Industry code (e.g., K01)")
    industry_name: Optional[str] = Field(None, description="Industry name (e.g., Lawyers/Law Firms)")
    sector_code: Optional[str] = Field(None, description="Sector code")
    sector_name: Optional[str] = Field(None, description="Sector name (e.g., Lawyers & Lobbyists)")
    
    # Election cycle
    cycle: str = Field(..., description="Election cycle year (e.g., '2024')")
    
    # Source tracking
    source: str = Field(..., description="Data source: 'opensecrets', 'fec', etc.")
    fec_transaction_id: Optional[str] = Field(None, description="FEC transaction ID if available")
    
    # Metadata
    last_updated: date = Field(default_factory=date.today)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "fec_C00401224_SA11AI_12345",
                "recipient_name": "Lee, Mike",
                "bioguide_id": "L000577",
                "contributor_name": "Smith, John",
                "contributor_type": "individual",
                "contributor_employer": "Tech Corp",
                "contributor_occupation": "Software Engineer",
                "contributor_city": "Salt Lake City",
                "contributor_state": "UT",
                "amount": "2500.00",
                "contribution_date": "2024-03-15",
                "industry_code": "B12",
                "industry_name": "Computer Software",
                "cycle": "2024",
                "source": "opensecrets"
            }
        }


class ContributionSummary(BaseModel):
    """
    Aggregated contribution summary for a politician.
    
    This can be pre-computed or calculated on-demand.
    """
    bioguide_id: str
    politician_name: str
    cycle: str
    
    # Totals
    total_raised: Decimal
    individual_total: Decimal
    pac_total: Decimal
    party_total: Decimal
    
    # Counts
    num_contributions: int
    num_individual_contributors: int
    
    # Top industries/sectors
    top_industries: list[dict] = Field(
        default_factory=list,
        description="List of {industry_name, amount} dicts"
    )
    top_contributors: list[dict] = Field(
        default_factory=list,
        description="List of {contributor_name, amount} dicts"
    )
    
    last_updated: date = Field(default_factory=date.today)


class IndustryCode(BaseModel):
    """
    OpenSecrets industry/sector code mapping.
    
    Used to categorize contributions by industry.
    """
    code: str = Field(..., description="Industry code (e.g., K01)")
    name: str = Field(..., description="Industry name")
    sector_code: Optional[str] = Field(None, description="Parent sector code")
    sector_name: Optional[str] = Field(None, description="Parent sector name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "K01",
                "name": "Lawyers/Law Firms",
                "sector_code": "K",
                "sector_name": "Lawyers & Lobbyists"
            }
        }


class CandidateMapping(BaseModel):
    """
    Maps OpenSecrets CRP IDs to bioguide IDs.
    
    From OpenSecrets CRP_IDs.xls file.
    """
    crp_id: str = Field(..., description="OpenSecrets CRP ID (e.g., N00031696)")
    bioguide_id: Optional[str] = Field(None, description="Bioguide ID")
    fec_id: Optional[str] = Field(None, description="FEC Candidate ID")
    candidate_name: str
    party: Optional[str] = None
    office: Optional[str] = Field(None, description="S=Senate, H=House")
    state: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "crp_id": "N00031696",
                "bioguide_id": "L000577",
                "fec_id": "S2UT00106",
                "candidate_name": "Lee, Mike",
                "party": "R",
                "office": "S",
                "state": "UT"
            }
        }