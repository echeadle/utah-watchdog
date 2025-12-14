"""
Ingester for federal legislation from Congress.gov API.

Fetches bills, resolutions, and their metadata.
"""
import asyncio
import httpx
from typing import AsyncGenerator, Optional
from datetime import date, datetime
import logging

from src.ingestion.base import BaseIngester
from src.models.legislation import Bill, BillType, BillStatus
from src.config.settings import settings
from src.config.constants import CONGRESS_GOV_BASE_URL, CURRENT_CONGRESS

logger = logging.getLogger(__name__)


class CongressBillsIngester(BaseIngester[Bill]):
    """
    Ingest bills from Congress.gov API.
    
    Fetches recent bills for a given Congress and bill type.
    """
    
    def __init__(self, congress: int = CURRENT_CONGRESS):
        super().__init__()
        self.congress = congress
        self.api_key = settings.CONGRESS_GOV_API_KEY
        self.base_url = CONGRESS_GOV_BASE_URL
        
    async def fetch_data(
        self, 
        bill_type: str = "hr",
        limit_per_request: int = 250,
        max_bills: Optional[int] = None
    ) -> AsyncGenerator[dict, None]:
        """
        Fetch bills from Congress.gov API.
        
        Args:
            bill_type: Type of bill to fetch (hr, s, etc.)
            limit_per_request: Results per API call
            max_bills: Maximum total bills to fetch (None = all)
            
        Yields:
            Raw bill data from API
        """
        offset = 0
        total_fetched = 0
        
        self.logger.info(f"Fetching {bill_type.upper()} bills for Congress {self.congress}...")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                try:
                    url = f"{self.base_url}/bill/{self.congress}/{bill_type}"
                    params = {
                        "api_key": self.api_key,
                        "format": "json",
                        "limit": limit_per_request,
                        "offset": offset
                    }
                    
                    self.logger.info(f"Fetching bills {offset}-{offset+limit_per_request}...")
                    response = await client.get(url, params=params)
                    
                    if response.status_code == 404:
                        self.logger.info(f"No more bills found")
                        break
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    bills = data.get("bills", [])
                    if not bills:
                        self.logger.info("No more bills to fetch")
                        break
                    
                    self.logger.info(f"Found {len(bills)} bills in this batch")
                    
                    # Fetch full details for each bill
                    for bill_summary in bills:
                        try:
                            # Get detailed bill info
                            detail_url = bill_summary.get("url")
                            if detail_url:
                                detail_params = {
                                    "api_key": self.api_key,
                                    "format": "json"
                                }
                                detail_response = await client.get(detail_url, params=detail_params)
                                
                                if detail_response.status_code == 200:
                                    detail_data = detail_response.json()
                                    bill_data = detail_data.get("bill", {})
                                    yield bill_data
                                    
                                    total_fetched += 1
                                    
                                    # Check if we've hit max_bills limit
                                    if max_bills and total_fetched >= max_bills:
                                        self.logger.info(f"Reached max_bills limit of {max_bills}")
                                        return
                                    
                                    # Small delay to respect rate limits
                                    await asyncio.sleep(0.3)
                                else:
                                    self.logger.warning(f"Failed to fetch details for bill: {detail_url}")
                            
                        except Exception as e:
                            self.logger.error(f"Error fetching bill details: {e}")
                            self.stats["errors"] += 1
                    
                    offset += limit_per_request
                    
                    # Respect rate limits
                    await asyncio.sleep(0.5)
                    
                except httpx.HTTPError as e:
                    self.logger.error(f"HTTP error: {e}")
                    self.stats["errors"] += 1
                    break
                except Exception as e:
                    self.logger.error(f"Unexpected error: {e}")
                    self.stats["errors"] += 1
                    break
    
    async def transform(self, raw: dict) -> Bill:
        """
        Transform Congress.gov bill data to our Bill model.
        
        Args:
            raw: Raw bill data from API
            
        Returns:
            Bill model instance
        """
        # Build bill ID
        bill_type = raw.get("type", "").lower()
        number = raw.get("number")
        congress = raw.get("congress")
        bill_id = f"{bill_type}-{number}-{congress}"
        
        # Parse status
        status = self._parse_status(raw)
        
        # Get sponsor
        sponsors = raw.get("sponsors", [])
        sponsor_bioguide_id = None
        if sponsors:
            sponsor_bioguide_id = sponsors[0].get("bioguideId")
        
        # Get cosponsors
        cosponsors_data = raw.get("cosponsors", {})
        cosponsor_ids = []
        if isinstance(cosponsors_data, dict):
            count = cosponsors_data.get("count", 0)
            if count > 0:
                # Note: Full cosponsor list requires separate API call
                # For now, we just note they exist
                pass
        
        # Get latest action
        latest_action = raw.get("latestAction", {})
        latest_action_date = self._parse_date(latest_action.get("actionDate"))
        latest_action_text = latest_action.get("text")
        
        # Get subjects
        subjects_data = raw.get("subjects", {})
        policy_area = subjects_data.get("legislativeSubjects", [{}])[0].get("name") if subjects_data.get("legislativeSubjects") else None
        subjects = [s.get("name") for s in subjects_data.get("legislativeSubjects", []) if s.get("name")]
        
        # Get summary
        summaries = raw.get("summaries", {})
        summary = None
        if isinstance(summaries, dict):
            summary_items = summaries.get("billSummaries", [])
            if summary_items:
                summary = summary_items[0].get("text")
        
        return Bill(
            bill_id=bill_id,
            bill_type=BillType(bill_type),
            number=int(number),
            congress=int(congress),
            title=raw.get("title", ""),
            short_title=raw.get("shortTitle"),
            summary=summary,
            status=status,
            introduced_date=self._parse_date(raw.get("introducedDate")),
            latest_action_date=latest_action_date,
            latest_action_text=latest_action_text,
            sponsor_bioguide_id=sponsor_bioguide_id,
            cosponsor_bioguide_ids=cosponsor_ids,
            policy_area=policy_area,
            subjects=subjects,
            congress_gov_url=raw.get("url"),
            full_text_url=raw.get("textVersions", {}).get("url") if raw.get("textVersions") else None,
            last_updated=datetime.utcnow()
        )
    
    async def load(self, bill: Bill) -> bool:
        """
        Upsert bill into MongoDB.
        
        Args:
            bill: Bill model to save
            
        Returns:
            True if new insert, False if update
        """
        collection = self.db.legislation
    
        # Convert to dict and handle date objects
        bill_data = bill.model_dump()
        
        # Convert date objects to datetime for MongoDB
        if bill_data.get('introduced_date'):
            bill_data['introduced_date'] = datetime.combine(
                bill_data['introduced_date'], 
                datetime.min.time()
            )
        
        if bill_data.get('latest_action_date'):
            bill_data['latest_action_date'] = datetime.combine(
                bill_data['latest_action_date'],
                datetime.min.time()
            )
        
        # Convert enum values to strings
        if 'bill_type' in bill_data:
            bill_data['bill_type'] = bill_data['bill_type'].value if hasattr(bill_data['bill_type'], 'value') else bill_data['bill_type']
        
        if 'status' in bill_data:
            bill_data['status'] = bill_data['status'].value if hasattr(bill_data['status'], 'value') else bill_data['status']
        
        result = await collection.update_one(
            {"bill_id": bill.bill_id},
            {"$set": bill_data},
            upsert=True
        )
        
        return result.upserted_id is not None
    
    def _parse_status(self, raw: dict) -> BillStatus:
        """Map Congress.gov status to our enum."""
        # This is simplified - real logic would check multiple fields
        latest_action_text = raw.get("latestAction", {}).get("text", "").lower()
        
        if "became public law" in latest_action_text or "signed by president" in latest_action_text:
            return BillStatus.BECAME_LAW
        elif "passed senate" in latest_action_text and "passed house" in latest_action_text:
            return BillStatus.TO_PRESIDENT
        elif "passed senate" in latest_action_text:
            return BillStatus.PASSED_SENATE
        elif "passed house" in latest_action_text:
            return BillStatus.PASSED_HOUSE
        elif "referred to" in latest_action_text or "committee" in latest_action_text:
            return BillStatus.IN_COMMITTEE
        elif "vetoed" in latest_action_text:
            return BillStatus.VETOED
        else:
            return BillStatus.INTRODUCED
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            return date.fromisoformat(date_str[:10])
        except:
            return None


async def main():
    """CLI entry point for testing"""
    logging.basicConfig(level=logging.INFO)
    
    ingester = CongressBillsIngester(congress=CURRENT_CONGRESS)
    
    # Fetch just House bills, limit to 50 for testing
    stats = await ingester.run(bill_type="hr", max_bills=50)
    
    print("\n=== Sync Complete ===")
    print(f"Processed: {stats['processed']}")
    print(f"Inserted: {stats['inserted']}")
    print(f"Updated: {stats['updated']}")
    print(f"Errors: {stats['errors']}")
    print(f"Duration: {stats['completed_at'] - stats['started_at']}")


if __name__ == "__main__":
    asyncio.run(main())