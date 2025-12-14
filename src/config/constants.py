"""
Application-wide constants.

API endpoints, state codes, and other magic numbers live here.
"""
from datetime import datetime

# API Base URLs
CONGRESS_GOV_BASE_URL = "https://api.congress.gov/v3"
FEC_BASE_URL = "https://api.open.fec.gov/v1"
PROPUBLICA_BASE_URL = "https://api.propublica.org/congress/v1"

# US State and Territory Codes
# Congress.gov uses these for the member endpoint
US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    # Territories with delegates
    "AS",  # American Samoa
    "DC",  # District of Columbia
    "GU",  # Guam
    "MP",  # Northern Mariana Islands
    "PR",  # Puerto Rico
    "VI",  # Virgin Islands
]

# Congress numbers - calculated dynamically
# Formula: Each Congress is 2 years, starting from 1st Congress in 1789
# Congress number = ((current_year - 1789) // 2) + 1
def _calculate_current_congress() -> int:
    """Calculate the current Congress number based on today's date."""
    current_year = datetime.now().year
    return ((current_year - 1789) // 2) + 1

CURRENT_CONGRESS = _calculate_current_congress()  # Auto-calculates (119 in 2025)
NEXT_CONGRESS = CURRENT_CONGRESS + 1

# MongoDB Collection Names
COLLECTION_POLITICIANS = "politicians"
COLLECTION_LEGISLATION = "legislation"
COLLECTION_VOTES = "votes"
COLLECTION_POLITICIAN_VOTES = "politician_votes"
COLLECTION_CONTRIBUTIONS = "contributions"
COLLECTION_STOCK_TRADES = "stock_trades"
COLLECTION_COMMITTEES = "committees"
COLLECTION_CHUNKS = "chunks"  # For RAG embeddings

# OpenSecrets Industry Codes (sample - full list in separate file)
OPENSECRETS_INDUSTRIES = {
    "A": "Agriculture",
    "B": "Communications/Electronics",
    "C": "Construction",
    "D": "Defense",
    "E": "Energy/Natural Resources",
    "F": "Finance/Insurance/Real Estate",
    "H": "Health",
    "K": "Lawyers & Lobbyists",
    "M": "Transportation",
    "N": "Misc Business",
    "Q": "Ideology/Single-Issue",
    "P": "Labor",
    "W": "Other",
}

# Rate Limiting
CONGRESS_GOV_RATE_LIMIT = 5000  # requests per hour
REQUESTS_PER_SECOND = 1.4  # To stay under rate limit
RATE_LIMIT_DELAY = 0.2  # seconds between requests

# Data Sync Schedule (in hours)
SYNC_MEMBERS_EVERY = 24  # Daily
SYNC_BILLS_EVERY = 6     # Every 6 hours during session
SYNC_CONTRIBUTIONS_EVERY = 168  # Weekly
SYNC_TRADES_EVERY = 24   # Daily

# Utah-specific
UTAH_STATE_CODE = "UT"
UTAH_LEGISLATURE_URL = "https://le.utah.gov"
UTAH_DISCLOSURES_URL = "https://disclosures.utah.gov"

# Bill Types
FEDERAL_BILL_TYPES = ["hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"]
UTAH_BILL_TYPES = ["hb", "sb", "hjr", "sjr", "hcr", "scr"]

# Embedding Configuration
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200