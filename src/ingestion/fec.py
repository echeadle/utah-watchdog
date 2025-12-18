"""
FEC API Ingester - Fetch campaign contributions from the FEC.

The FEC (Federal Election Commission) API provides real-time campaign finance data.
API docs: https://api.open.fec.gov/developers/

Usage:
    ingester = FECIngester()
    await ingester.run(candidate_id="S2UT00106")  # Mike Lee
"""
import httpx
from typing import AsyncGenerator, Optional
from datetime import date, datetime
from decimal import Decimal
import logging

from src.ingestion.base import BaseIngester
from src.models.finance import Contribution, ContributionType
from src.config.settings import settings
from src.database.normalization import normalize_contribution

logger = logging.getLogger(__name__)


class FECIngester(BaseIngester[Contribution]):
    """
    Ingest campaign contributions from FEC API.
    
    The FEC API provides itemized individual contributions to candidates.
    We'll fetch contributions for specific candidates (by FEC candidate ID).
    """
    
    BASE_URL = "https://api.open.fec.gov/v1"
    
    def __init__(self, candidate_name: Optional[str] = None, bioguide_id: Optional[str] = None):
        super().__init__()
        self.api_key = settings.FEC_API_KEY
        if not self.api_key:
            raise ValueError("FEC_API_KEY not found in settings")
        self.candidate_name = candidate_name  # Cache candidate name
        self.bioguide_id = bioguide_id  # Store bioguide_id for linking
    
    async def fetch_candidate_name(self, candidate_id: str) -> str:
        """
        Look up candidate name from FEC API.
        
        Args:
            candidate_id: FEC candidate ID
            
        Returns:
            Candidate name
        """
        if self.candidate_name:
            return self.candidate_name
        
        endpoint = f"{self.BASE_URL}/candidate/{candidate_id}/"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    endpoint,
                    params={"api_key": self.api_key}
                )
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                if results:
                    name = results[0].get("name", "Unknown Candidate")
                    self.candidate_name = name
                    return name
                    
            except Exception as e:
                self.logger.error(f"Error fetching candidate name: {e}")
        
        return "Unknown Candidate"
    
    async def fetch_data(
        self,
        candidate_id: Optional[str] = None,
        committee_id: Optional[str] = None,
        cycle: int = 2024,
        per_page: int = 100,
        max_pages: Optional[int] = 10
    ) -> AsyncGenerator[dict, None]:
        """
        Fetch individual contributions from FEC API.
        
        Args:
            candidate_id: FEC candidate ID (e.g., "S2UT00106" for Mike Lee)
            committee_id: FEC committee ID (alternative to candidate_id)
            cycle: Election cycle year (e.g., 2024)
            per_page: Results per page (max 100)
            max_pages: Maximum pages to fetch (None = unlimited, but be careful!)
        
        Yields:
            Raw contribution dictionaries from FEC API
        """
        if not candidate_id and not committee_id:
            raise ValueError("Must provide either candidate_id or committee_id")
        
        # Look up candidate name once
        if candidate_id and not self.candidate_name:
            self.candidate_name = await self.fetch_candidate_name(candidate_id)
            self.logger.info(f"Fetching contributions for: {self.candidate_name}")
        
        endpoint = f"{self.BASE_URL}/schedules/schedule_a/"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            page = 1
            
            while True:  # Changed from while page <= max_pages
                # Check max_pages limit
                if max_pages is not None and page > max_pages:
                    self.logger.info(f"Reached max_pages limit ({max_pages})")
                    break
                params = {
                    "api_key": self.api_key,
                    "two_year_transaction_period": cycle,
                    "per_page": per_page,
                    "page": page,
                    "sort": "-contribution_receipt_date"
                }
                
                # Filter by candidate or committee
                if candidate_id:
                    params["candidate_id"] = candidate_id
                elif committee_id:
                    params["committee_id"] = committee_id
                
                self.logger.info(
                    f"Fetching FEC contributions: "
                    f"candidate={candidate_id}, cycle={cycle}, page={page}"
                )
                
                try:
                    response = await client.get(endpoint, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    results = data.get("results", [])
                    if not results:
                        self.logger.info("No more results")
                        break
                    
                    for item in results:
                        yield item
                    
                    # Check if there are more pages
                    pagination = data.get("pagination", {})
                    total_pages = pagination.get("pages", 0)
                    
                    if page >= total_pages:
                        self.logger.info(f"Reached last page ({total_pages})")
                        break
                    
                    page += 1
                    
                except httpx.HTTPError as e:
                    self.logger.error(f"HTTP error fetching FEC data: {e}")
                    break
    
    async def transform(self, raw: dict) -> Contribution:
        """
        Transform FEC API response to Contribution model.
        
        FEC API returns Schedule A (itemized receipts) data.
        Field mapping: https://api.open.fec.gov/developers/
        
        Args:
            raw: Raw FEC API contribution dict
        
        Returns:
            Contribution model
        """
        # Parse date (FEC returns ISO format: "2024-03-15T00:00:00")
        date_str = raw.get("contribution_receipt_date")
        contrib_date = datetime.fromisoformat(date_str.replace("Z", "")).date() if date_str else date.today()
        
        # Amount - FIXED: handle None/empty values properly
        amount_raw = raw.get("contribution_receipt_amount")
        if amount_raw is None or amount_raw == "":
            amount = Decimal("0")
            self.logger.debug(f"Missing amount for contribution, using 0")
        else:
            try:
                amount = Decimal(str(amount_raw))
            except (ValueError, TypeError, decimal.InvalidOperation) as e:
                self.logger.warning(f"Invalid amount '{amount_raw}': {e}, using 0")
                amount = Decimal("0")
        
        # Determine contribution type
        entity_type = raw.get("entity_type", "")
        if entity_type == "IND":
            contrib_type = ContributionType.INDIVIDUAL
        elif entity_type in ["PAC", "COM"]:
            contrib_type = ContributionType.PAC
        elif entity_type == "PTY":
            contrib_type = ContributionType.PARTY
        elif entity_type == "CAN":
            contrib_type = ContributionType.CANDIDATE
        else:
            contrib_type = ContributionType.OTHER
        
        # Build unique ID
        sub_id = raw.get("sub_id", "")
        contrib_id = f"fec_{sub_id}" if sub_id else f"fec_{raw.get('line_number')}_{raw.get('file_number')}"
        
        # Get recipient name (use cached name if not in record)
        recipient_name = raw.get("candidate_name") or self.candidate_name or "Unknown Candidate"
        
        return Contribution(
            id=contrib_id,
            recipient_name=recipient_name,
            recipient_id=None,  # FEC doesn't provide CRP ID
            bioguide_id=self.bioguide_id,  # FIXED: Use the bioguide_id passed to constructor
            committee_id=raw.get("committee_id"),
            contributor_name=raw.get("contributor_name") or "Unknown",
            contributor_type=contrib_type,
            contributor_employer=raw.get("contributor_employer"),
            contributor_occupation=raw.get("contributor_occupation"),
            contributor_city=raw.get("contributor_city"),
            contributor_state=raw.get("contributor_state"),
            contributor_zip=raw.get("contributor_zip"),
            amount=amount,
            contribution_date=contrib_date,
            industry_code=None,  # FEC doesn't categorize by industry
            industry_name=None,
            sector_code=None,
            sector_name=None,
            cycle=str(raw.get("two_year_transaction_period", "")),
            source="fec",
            fec_transaction_id=raw.get("transaction_id"),
            last_updated=date.today()
        )
    
    async def load(self, contribution: Contribution) -> bool:
        """
        Upsert contribution into MongoDB.
        
        Args:
            contribution: Contribution model
        
        Returns:
            True if new insert, False if update
        """
        collection = self.db.contributions
        
        # Convert to dict
        contrib_data = contribution.model_dump()
        
        # Convert Decimal to float for MongoDB
        if isinstance(contrib_data.get('amount'), Decimal):
            contrib_data['amount'] = float(contrib_data['amount'])
        
        # Convert date objects to datetime for MongoDB
        if contrib_data.get('contribution_date'):
            contrib_data['contribution_date'] = datetime.combine(
                contrib_data['contribution_date'],
                datetime.min.time()
            )
        if contrib_data.get('last_updated'):
            contrib_data['last_updated'] = datetime.combine(
                contrib_data['last_updated'],
                datetime.min.time()
            )
        
        # Convert enums to strings
        if contrib_data.get('contributor_type'):
            contrib_type = contrib_data['contributor_type']
            contrib_data['contributor_type'] = contrib_type.value if hasattr(contrib_type, 'value') else str(contrib_type)
        
        # ✨ NORMALIZE the contribution data before saving
        # This ensures consistent formats for contributor_state
        normalized_data = normalize_contribution(contrib_data)
        
        # Upsert by contribution ID
        result = await collection.update_one(
            {"id": contribution.id},
            {"$set": normalized_data},
            upsert=True
        )
        
        return result.upserted_id is not None


async def get_candidate_fec_id(bioguide_id: str, db) -> Optional[str]:
    """
    Helper: Get FEC candidate ID from bioguide ID.
    
    This looks up the politician's FEC ID from the politicians collection.
    
    Args:
        bioguide_id: Bioguide ID (e.g., "L000577")
        db: MongoDB database
    
    Returns:
        FEC candidate ID or None
    """
    politician = await db.politicians.find_one({"bioguide_id": bioguide_id})
    if politician:
        return politician.get("fec_candidate_id")
    return None
