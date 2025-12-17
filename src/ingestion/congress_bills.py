Utah Government Watchdog
/

I need to add normalization to my sync scripts. I've already created src/database/normalization.py and the pattern is to call normalize_politician() before inserting/updating. Here's the first script to fix:

Please add normalization to this script and return the complete fixed file
12:52 PM

I'll look at the uploaded sync_members.py file and add normalization to it. First, let me check the current implementation and understand how it works.
Failed to viewSync Members

The file content is already in the document you provided. Looking at sync_members.py, I can see it calls CongressMembersIngester which does the actual work. The normalization should happen in the ingester itself, not in this sync script.

Let me check if there's a congress_members.py ingester file that we need to modify:

plaintext
Here are the files and directories up to 2 levels deep in /mnt/project, excluding hidden items and node_modules:
153K	/mnt/project
9.0K	/mnt/project/2___Legislation.py
3.5K	/mnt/project/3___Bills_by_Politician.py
5.0K	/mnt/project/4___Search_Politicians.py
9.5K	/mnt/project/5___Politician_Detail.py
5.5K	/mnt/project/6____Votes.py
11K	/mnt/project/7___Vote_Detail.py
7.0K	/mnt/project/STREAMLIT_ENHANCEMENT_PLAN.md
8.5K	/mnt/project/app.py
72K	/mnt/project/government-watchdog-project-outline.md
14K	/mnt/project/normalization.py
4.0K	/mnt/project/sync_votes_py__Fixed_Import_.txt

I see the project files. Looking at the sync script you provided, it imports from src.ingestion.congress_members, which is where the actual data transformation happens. The sync_members.py script itself is just a CLI wrapper that calls the ingester.

There are two approaches:

    Add normalization to the ingester (congress_members.py) - this is the proper place
    Add normalization to the sync script - this would be a workaround

Since you asked to fix sync_members.py, I'll create a version that applies normalization as a post-processing step. However, I'll also note that the ideal fix would be in the ingester itself.

Please review all the ingestion files and determine which need to be normalize.  Print out a summary of what you find and then we will take things step by step
12:56 PM

I'll review all the ingestion files to identify which ones need normalization added.

Now I have a clear picture. Let me summarize what I found:
📋 Ingestion Files Normalization Summary
Available Normalization Functions
Function	Purpose
normalize_politician()	Normalizes state, party, chamber, last_updated
normalize_contribution()	Normalizes contributor_state, last_updated
normalize_legislation()	Normalizes status, last_updated
normalize_state()	Converts "Utah" → "UT"
normalize_party()	Converts "Republican" → "R"
normalize_chamber()	Converts "Senate" → "senate"
validate_politician()	Validates required fields and formats
Files Analysis
File	Writes To	Needs Normalization?	Current Status
congress_members.py	politicians	✅ YES	Uses Pydantic model with enums, but load() saves raw model_dump() without normalization
committees.py	politicians	✅ ALREADY DONE	Has normalize_politician() import and uses it in load()
contact_info.py	politicians	⚠️ PARTIAL	Only updates contact fields (office, phone, website) - doesn't touch state/party/chamber, so NO normalization needed
congress_bills.py	legislation	✅ YES	Should use normalize_legislation() in load()
votes.py	votes, politician_votes	❌ NO	Doesn't write politician data with state/party/chamber fields
fec.py	contributions	✅ YES	Should use normalize_contribution() in load() to normalize contributor_state
congress_gov.py	N/A (client only)	❌ NO	This is an API client, not an ingester - doesn't write to DB
base.py	N/A	❌ NO	Abstract base class, no data transformation
🔧 Files That Need Changes

    congress_members.py - Add normalize_politician() call in load() method
    congress_bills.py - Add normalize_legislation() call in load() method
    fec.py - Add normalize_contribution() call in load() method

✅ Files Already Done

    committees.py - Already imports and uses normalize_politician()

❌ Files That Don't Need Changes

    base.py - Abstract base class
    congress_gov.py - API client only, no DB writes
    contact_info.py - Only updates contact fields, not normalized fields
    votes.py - Writes vote data, not politician metadata

Recommended Order of Changes

    congress_members.py (most important - this is the primary source of politician data)
    fec.py (contributor state normalization)
    congress_bills.py (legislation status normalization)

Ready to proceed? Let me know which file you'd like me to update first, or if you want me to do all three in sequence.

please update  the first file
1:15 PM

I'll update congress_members.py to add normalization. Let me create the fixed version:

Here's the updated congress_members.py with normalization added.
Changes Made

1. Added import (line 14):
python

from src.database.normalization import normalize_politician

2. Updated load() method (lines 168-173):
python

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

What the Normalization Does

When normalize_politician() is called, it ensures:

    state: Already "UT" format (from state_code), but validates it
    party: Converts enum value to single letter ("R", "D", "I")
    chamber: Converts enum value to lowercase ("senate", "house")
    last_updated: Ensures timestamp is set

Ready for the next file (fec.py)?
Congress members
PY 

Yes, please do the next file
2:04 PM

I'll update fec.py to add normalization for contributions:

Here's the updated fec.py with normalization added.
Changes Made

1. Added import (line 19):
python

from src.database.normalization import normalize_contribution

2. Updated load() method (lines 250-254):
python

# ✨ NORMALIZE the contribution data before saving
# This ensures consistent formats for contributor_state
normalized_data = normalize_contribution(contrib_data)

# Upsert by contribution ID
result = await collection.update_one(
    {"id": contribution.id},
    {"$set": normalized_data},
    upsert=True
)

What the Normalization Does

When normalize_contribution() is called, it ensures:

    contributor_state: Converts full state names to 2-letter codes (e.g., "California" → "CA", "utah" → "UT")
    last_updated: Ensures timestamp is set

This is important because FEC data typically has 2-letter state codes already, but normalization ensures consistency if any edge cases slip through.

Ready for the last file (congress_bills.py)?
Fec
PY 

Yes
2:06 PM

I'll update congress_bills.py to add normalization for legislation:

Here's the updated congress_bills.py with normalization added.
Changes Made

1. Added import (line 15):
python

from src.database.normalization import normalize_legislation

2. Updated load() method (lines 230-234):
python

# ✨ NORMALIZE the legislation data before saving
# This ensures consistent formats for status field
normalized_data = normalize_legislation(bill_data)

result = await collection.update_one(
    {"bill_id": bill.bill_id},
    {"$set": normalized_data},
    upsert=True
)

What the Normalization Does

When normalize_legislation() is called, it ensures:

    status: Normalizes to lowercase with underscores (e.g., "Passed House" → "passed_house", "enacted" → "became_law")
    last_updated: Ensures timestamp is set

✅ Summary - All Files Updated
File	Normalization Function	Status
congress_members.py	normalize_politician()	✅ Done
fec.py	normalize_contribution()	✅ Done
congress_bills.py	normalize_legislation()	✅ Done
committees.py	normalize_politician()	✅ Already had it

All three ingester files now have normalization integrated. Your data will be consistent across all ingestion pipelines!
Congress bills
PY 


Claude is AI and can make mistakes. Please double-check responses.
Congress bills · PY
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
from src.database.normalization import normalize_legislation

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
        
        # ✨ NORMALIZE the legislation data before saving
        # This ensures consistent formats for status field
        normalized_data = normalize_legislation(bill_data)
        
        result = await collection.update_one(
            {"bill_id": bill.bill_id},
            {"$set": normalized_data},
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

