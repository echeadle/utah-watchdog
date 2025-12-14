"""
Ingester for politician contact information (office, phone, etc.)

Uses the unitedstates/congress-legislators GitHub repository, which is
a community-maintained dataset of legislator contact information.

Source: https://github.com/unitedstates/congress-legislators
"""
import asyncio
import httpx
import yaml
from typing import AsyncGenerator, Optional
from datetime import datetime
import logging

from src.ingestion.base import BaseIngester
from src.models.politician import Politician
from src.config.settings import settings

logger = logging.getLogger(__name__)


class ContactInfoIngester(BaseIngester[dict]):
    """
    Enrich existing politician records with contact information.
    
    This ingester does NOT create new politicians - it only updates
    existing records with office addresses and phone numbers.
    
    Data source: https://github.com/unitedstates/congress-legislators
    """
    
    # GitHub raw content URLs for legislator data
    #LEGISLATORS_CURRENT_URL = "https://theunitedstates.io/congress-legislators/legislators-current.yaml"
    LEGISLATORS_CURRENT_URL = "https://raw.githubusercontent.com/unitedstates/congress-legislators/main/legislators-current.yaml"
    def __init__(self):
        super().__init__()
        self.legislators_data = None
        
    async def fetch_data(self, **kwargs) -> AsyncGenerator[dict, None]:
        """
        Fetch current legislators from GitHub repository.
        
        Yields:
            Legislator records with contact information
        """
        self.logger.info("Fetching legislator data from unitedstates/congress-legislators...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.LEGISLATORS_CURRENT_URL)
                response.raise_for_status()
                
                # Parse YAML
                data = yaml.safe_load(response.text)
                
                self.logger.info(f"Loaded {len(data)} legislators from GitHub")
                
                # Yield each legislator
                for legislator in data:
                    yield legislator
                    
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error fetching legislator data: {e}")
            raise
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise
    
    async def transform(self, raw: dict) -> dict:
        """
        Extract contact information from legislator record.
        
        Args:
            raw: Raw legislator data from GitHub
            
        Returns:
            Dict with bioguide_id and contact fields to update
        """
        # Get bioguide ID
        bioguide_id = raw.get("id", {}).get("bioguide")
        if not bioguide_id:
            raise ValueError("Missing bioguide ID in legislator record")
        
        # Extract terms (current term has contact info)
        terms = raw.get("terms", [])
        if not terms:
            self.logger.warning(f"No terms found for {bioguide_id}")
            return {"bioguide_id": bioguide_id}
        
        # Get most recent term (last in list)
        current_term = terms[-1]
        
        # Extract contact information
        contact_info = {
            "bioguide_id": bioguide_id,
            "office": current_term.get("address"),
            "phone": current_term.get("phone"),
        }
        
        # Optional: Extract additional info if available
        # Some records have email, website, etc.
        if current_term.get("contact_form"):
            contact_info["website"] = current_term.get("contact_form")
        elif current_term.get("url"):
            contact_info["website"] = current_term.get("url")
        
        return contact_info
    
    async def load(self, contact_info: dict) -> bool:
        """
        Update existing politician record with contact information.
        
        Args:
            contact_info: Dict with bioguide_id and contact fields
            
        Returns:
            True if record was updated, False if not found
        """
        bioguide_id = contact_info.pop("bioguide_id")
        
        # Remove None values (don't overwrite with empty data)
        update_fields = {k: v for k, v in contact_info.items() if v is not None}
        
        if not update_fields:
            self.logger.debug(f"No contact info to update for {bioguide_id}")
            return False
        
        # Add last_updated timestamp
        update_fields["last_updated"] = datetime.utcnow()
        
        collection = self.db.politicians
        
        # Update only if politician exists
        result = await collection.update_one(
            {"bioguide_id": bioguide_id},
            {"$set": update_fields}
        )
        
        if result.matched_count == 0:
            self.logger.debug(f"Politician not found in DB: {bioguide_id}")
            return False
        
        if result.modified_count > 0:
            self.logger.debug(f"Updated contact info for {bioguide_id}")
            return False  # It's an update, not insert
        
        return False
    
    async def run_enrichment(self) -> dict:
        """
        Run the enrichment process.
        
        Returns:
            Statistics about the enrichment
        """
        self.logger.info("Starting contact information enrichment...")
        stats = await self.run()
        
        self.logger.info("Enrichment complete!")
        return stats


async def main():
    """CLI entry point for testing"""
    logging.basicConfig(level=logging.INFO)
    
    ingester = ContactInfoIngester()
    stats = await ingester.run_enrichment()
    
    print("\n=== Enrichment Complete ===")
    print(f"Processed: {stats['processed']}")
    print(f"Updated: {stats['updated']}")
    print(f"Errors: {stats['errors']}")
    print(f"Duration: {stats['completed_at'] - stats['started_at']}")


if __name__ == "__main__":
    asyncio.run(main())