"""
Ingester for current members of Congress from Congress.gov API.

This keeps the politician database up-to-date with who's currently serving.
Handles transitions like retirements, special elections, and new terms.

ENHANCED: Now supports native filtering by state and chamber to minimize API calls.
"""
import asyncio
import httpx
from typing import AsyncGenerator, Optional
from datetime import date, datetime
import logging

from src.ingestion.base import BaseIngester
from src.models.politician import Politician, Chamber, Party
from src.config.settings import settings
from src.config.constants import CONGRESS_GOV_BASE_URL, US_STATES
from src.database.normalization import normalize_politician

logger = logging.getLogger(__name__)


class CongressMembersIngester(BaseIngester[Politician]):
    """
    Ingest current members of Congress from Congress.gov API.
    
    Uses the /member/congress/{congress}/{state} endpoint with 
    currentMember=true to get only active legislators.
    
    Supports filtering by state and chamber to minimize API calls.
    """
    
    def __init__(
        self,
        congress: int = 118,
        state_filter: Optional[str] = None,
        chamber_filter: Optional[str] = None,
        fetch_details: bool = True
    ):
        """
        Initialize the ingester.

        Args:
            congress: Congress number (e.g., 118 for 118th Congress, 2023-2025)
            state_filter: Optional 2-letter state code to fetch (e.g., "UT")
                         If None, fetches all states
            chamber_filter: Optional chamber filter ("senate" or "house")
                           Applied during fetch, not just during transform
            fetch_details: If True, fetch detailed member data including contact info
                          (slower but more complete)
        """
        super().__init__()
        self.congress = congress
        self.state_filter = state_filter.upper() if state_filter else None
        self.chamber_filter = chamber_filter.lower() if chamber_filter else None
        self.fetch_details = fetch_details
        self.api_key = settings.CONGRESS_GOV_API_KEY
        self.base_url = CONGRESS_GOV_BASE_URL

        # Log filter configuration
        if self.state_filter:
            self.logger.info(f"State filter: {self.state_filter}")
        if self.chamber_filter:
            self.logger.info(f"Chamber filter: {self.chamber_filter}")
        if self.fetch_details:
            self.logger.info("Detailed member fetching enabled (includes contact info)")
        
    async def fetch_data(self, **kwargs) -> AsyncGenerator[dict, None]:
        """
        Fetch current members, optionally filtered by state.
        
        If state_filter is set, only fetches that state.
        Otherwise, fetches all states.
        
        Chamber filtering is applied during iteration to skip unwanted members.
        
        Yields:
            Raw member data from Congress.gov API
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Determine which states to fetch
            if self.state_filter:
                # Only fetch the specified state
                states_to_fetch = [self.state_filter]
                self.logger.info(f"Fetching only {self.state_filter} (state filter active)")
            else:
                # Fetch all states
                states_to_fetch = US_STATES
                self.logger.info(f"Fetching all {len(US_STATES)} states")
            
            # Fetch for each state
            for state_code in states_to_fetch:
                try:
                    url = f"{self.base_url}/member/congress/{self.congress}/{state_code}"
                    params = {
                        "currentMember": "true",  # Only active members
                        "api_key": self.api_key,
                        "format": "json",
                        "limit": 250
                    }
                    
                    self.logger.info(f"Fetching members for {state_code}...")
                    response = await client.get(url, params=params)
                    
                    if response.status_code == 404:
                        # Some territories might not have data
                        self.logger.debug(f"No data for {state_code}")
                        continue
                        
                    response.raise_for_status()
                    data = response.json()
                    
                    members = data.get("members", [])
                    self.logger.info(f"Found {len(members)} members for {state_code}")
                    
                    # Apply chamber filter if set
                    filtered_count = 0
                    for member in members:
                        # Add state code to the member data
                        member["state_code"] = state_code

                        # Apply chamber filter if specified
                        if self.chamber_filter:
                            member_chamber = self._extract_chamber(member)
                            if member_chamber != self.chamber_filter:
                                continue  # Skip this member

                        # Fetch detailed data if requested
                        if self.fetch_details:
                            bioguide_id = member.get("bioguideId")
                            if bioguide_id:
                                details = await self.fetch_member_details(bioguide_id, client)
                                if details:
                                    # Merge details into member data
                                    member["_details"] = details
                                # Small delay to respect rate limits
                                await asyncio.sleep(0.2)

                        filtered_count += 1
                        yield member
                    
                    if self.chamber_filter:
                        self.logger.info(
                            f"After chamber filter: {filtered_count}/{len(members)} members"
                        )
                    
                    # Respect rate limits (5000/hour = ~1.4/second)
                    await asyncio.sleep(0.2)
                    
                except httpx.HTTPError as e:
                    self.logger.error(f"HTTP error fetching {state_code}: {e}")
                    self.stats["errors"] += 1
                except Exception as e:
                    self.logger.error(f"Error fetching {state_code}: {e}")
                    self.stats["errors"] += 1
    
    def _extract_chamber(self, member: dict) -> Optional[str]:
        """
        Extract chamber from member data.

        Args:
            member: Raw member data from API

        Returns:
            "senate" or "house" or None if unknown
        """
        terms = member.get("terms", {}).get("item", [])
        if terms:
            current_term = terms[-1]  # Get LAST term (most recent)
            chamber_str = current_term.get("chamber", "").lower()
            if "senate" in chamber_str:
                return "senate"
            elif "house" in chamber_str:
                return "house"
        return None

    async def fetch_member_details(self, bioguide_id: str, client: httpx.AsyncClient) -> Optional[dict]:
        """
        Fetch detailed member information including contact info.

        Args:
            bioguide_id: The member's bioguide ID
            client: HTTP client to use

        Returns:
            Detailed member data or None if fetch fails
        """
        try:
            url = f"{self.base_url}/member/{bioguide_id}"
            params = {
                "api_key": self.api_key,
                "format": "json"
            }

            self.logger.debug(f"Fetching details for {bioguide_id}...")
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            return data.get("member", {})

        except httpx.HTTPError as e:
            self.logger.error(f"Error fetching details for {bioguide_id}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error fetching details for {bioguide_id}: {e}")
            return None
                    
    
    async def transform(self, raw: dict) -> Politician:
        """
        Transform Congress.gov member data to our Politician model.

        Args:
            raw: Raw member data from API

        Returns:
            Politician model instance
        """
        # Determine chamber - use MOST RECENT term (last in array)
        terms = raw.get("terms", {}).get("item", [])
        current_term = terms[-1] if terms else {}  # -1 gets last/most recent term

        chamber_str = current_term.get("chamber", "").lower()
        if chamber_str == "senate":
            chamber = Chamber.SENATE
            district = None
        else:  # House
            chamber = Chamber.HOUSE
            district_num = raw.get("district")
            district = int(district_num) if district_num else None

        # Map party
        party_name = raw.get("partyName", "")
        if "Republican" in party_name:
            party = Party.REPUBLICAN
        elif "Democrat" in party_name:
            party = Party.DEMOCRAT
        elif "Independent" in party_name:
            party = Party.INDEPENDENT
        else:
            party = Party.OTHER

        # Parse name - API returns "Last, First" or "Last, First Middle"
        full_name_raw = raw.get("name", "")
        if ", " in full_name_raw:
            parts = full_name_raw.split(", ", 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip()
            full_name = f"{first_name} {last_name}"
        else:
            # Fallback if format is different
            full_name = full_name_raw
            name_parts = full_name_raw.split()
            first_name = name_parts[0] if name_parts else ""
            last_name = name_parts[-1] if len(name_parts) > 1 else ""

        # Get bioguide ID (our primary key)
        bioguide_id = raw.get("bioguideId")
        if not bioguide_id:
            raise ValueError(f"Missing bioguideId for {full_name}")

        # Title
        if chamber == Chamber.SENATE:
            title = "Senator"
        else:
            title = "Representative"

        # Extract contact information from detailed data if available
        office = None
        phone = None
        details = raw.get("_details", {})
        if details:
            # Extract address information (typically DC office)
            address_info = details.get("addressInformation", {})
            if address_info:
                # Get office addresses - usually an array of offices
                offices = address_info.get("officeAddress") or address_info.get("offices", [])
                if isinstance(offices, list) and offices:
                    # Prefer DC office (first one is usually DC)
                    dc_office = offices[0]
                    if isinstance(dc_office, dict):
                        # Build office address string
                        office_parts = []
                        if dc_office.get("line1"):
                            office_parts.append(dc_office["line1"])
                        if dc_office.get("line2"):
                            office_parts.append(dc_office["line2"])
                        if dc_office.get("city"):
                            city_state_zip = dc_office["city"]
                            if dc_office.get("state"):
                                city_state_zip += f", {dc_office['state']}"
                            if dc_office.get("zip"):
                                city_state_zip += f" {dc_office['zip']}"
                            office_parts.append(city_state_zip)
                        office = ", ".join(office_parts) if office_parts else None

                        # Extract phone
                        phone = dc_office.get("phoneNumber") or dc_office.get("phone")
                elif isinstance(offices, str):
                    # Sometimes it's just a string
                    office = offices

                # Alternative: try phoneNumber at root level
                if not phone:
                    phone = address_info.get("phoneNumber")

        return Politician(
            bioguide_id=bioguide_id,
            first_name=first_name,
            last_name=last_name,
            full_name=full_name,
            party=party,
            state=raw.get("state_code"),
            chamber=chamber,
            district=district,
            title=title,
            in_office=True,
            website=raw.get("officialWebsiteUrl"),
            office=office,
            phone=phone,
            last_updated=datetime.utcnow()
        )
        
    async def load(self, politician: Politician) -> bool:
        """
        Upsert politician into MongoDB.
        
        Also handles marking old records as out of office when members change.
        
        Args:
            politician: Politician model to save
            
        Returns:
            True if this was a new insert, False if update
        """
        collection = self.db.politicians
        
        # Mark old occupant as out of office (House only)
        # Note: We only do this for House because each district has exactly 1 rep.
        # For Senate, states have 2 senators (different classes), so we can't
        # automatically determine which seat without Senate class info.
        if politician.chamber == Chamber.HOUSE:
            query = {
                "state": politician.state,
                "district": politician.district,
                "chamber": "house",
                "in_office": True,
                "bioguide_id": {"$ne": politician.bioguide_id}
            }

            update_result = await collection.update_many(
                query,
                {"$set": {"in_office": False, "last_updated": datetime.utcnow()}}
            )

            if update_result.modified_count > 0:
                self.logger.info(
                    f"Marked {update_result.modified_count} old record(s) as out of office "
                    f"for {politician.full_name}'s seat"
                )
        
        # Convert Pydantic model to dict
        politician_data = politician.model_dump()
        
        # ✨ NORMALIZE the politician data before saving
        # This ensures consistent formats for state, party, chamber
        normalized_data = normalize_politician(politician_data)
        
        # Now upsert the current member with normalized data
        result = await collection.update_one(
            {"bioguide_id": politician.bioguide_id},
            {"$set": normalized_data},
            upsert=True
        )
        
        return result.upserted_id is not None
    
    async def run_full_sync(self) -> dict:
        """
        Run a complete sync of all current members.
        
        Respects state_filter and chamber_filter if set during initialization.
        
        Returns:
            Statistics about the sync operation
        """
        if self.state_filter or self.chamber_filter:
            filters = []
            if self.state_filter:
                filters.append(f"state={self.state_filter}")
            if self.chamber_filter:
                filters.append(f"chamber={self.chamber_filter}")
            self.logger.info(
                f"Starting filtered sync of Congress {self.congress} members "
                f"({', '.join(filters)})"
            )
        else:
            self.logger.info(
                f"Starting full sync of Congress {self.congress} members..."
            )
        
        stats = await self.run()
        
        self.logger.info("Sync complete!")
        return stats


async def main():
    """CLI entry point for testing"""
    logging.basicConfig(level=logging.INFO)
    
    # Example: Sync only Utah senators
    ingester = CongressMembersIngester(
        congress=118,
        state_filter="UT",
        chamber_filter="senate"
    )
    stats = await ingester.run_full_sync()
    
    print("\n=== Sync Complete ===")
    print(f"Processed: {stats['processed']}")
    print(f"Inserted: {stats['inserted']}")
    print(f"Updated: {stats['updated']}")
    print(f"Errors: {stats['errors']}")
    print(f"Duration: {stats['completed_at'] - stats['started_at']}")


if __name__ == "__main__":
    asyncio.run(main())