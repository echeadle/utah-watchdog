"""
Data Normalization Module

Centralized functions to transform raw data into our standardized database format.
All ingestion scripts should use these functions to ensure consistency.

Usage:
    from src.database.normalization import normalize_politician, normalize_state, normalize_party
    
    # In your ingester:
    raw_data = fetch_from_api()
    politician = normalize_politician(raw_data)
    db.politicians.insert_one(politician)
"""
from typing import Optional, Dict, Any
from datetime import datetime


# ============================================================================
# State Normalization
# ============================================================================

STATE_NAME_TO_CODE = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY",
    "District of Columbia": "DC", "Puerto Rico": "PR"
}

# Reverse mapping for validation
STATE_CODE_TO_NAME = {v: k for k, v in STATE_NAME_TO_CODE.items()}


def normalize_state(state: Optional[str]) -> Optional[str]:
    """
    Normalize state to 2-letter code.
    
    Args:
        state: State name or code (e.g., "Utah", "UT", "ut")
        
    Returns:
        2-letter uppercase state code (e.g., "UT") or None if invalid
        
    Examples:
        >>> normalize_state("Utah")
        "UT"
        >>> normalize_state("UT")
        "UT"
        >>> normalize_state("ut")
        "UT"
        >>> normalize_state("California")
        "CA"
    """
    if not state:
        return None
    
    state_clean = state.strip()
    
    # Already a 2-letter code?
    if len(state_clean) == 2:
        code = state_clean.upper()
        # Validate it's a real state code
        if code in STATE_CODE_TO_NAME:
            return code
        return None
    
    # Full state name?
    if state_clean in STATE_NAME_TO_CODE:
        return STATE_NAME_TO_CODE[state_clean]
    
    # Try case-insensitive match
    for full_name, code in STATE_NAME_TO_CODE.items():
        if full_name.lower() == state_clean.lower():
            return code
    
    # Invalid state
    return None


# ============================================================================
# Party Normalization
# ============================================================================

# Known party mappings
PARTY_MAPPINGS = {
    "Republican": "R",
    "Democrat": "D",
    "Democratic": "D",
    "Independent": "I",
    "Libertarian": "L",
    "Green": "G",
    "R": "R",
    "D": "D",
    "I": "I",
    "L": "L",
    "G": "G",
}


def normalize_party(
    party: Optional[str],
    default: str = "I"
) -> str:
    """
    Normalize party affiliation to single-letter code.
    
    Args:
        party: Raw party string (e.g., "Republican", "Democrat", "Unknown")
        default: Default party if unknown (default: "I" for Independent)
        
    Returns:
        Single-letter party code: "R", "D", "I", "L", "G", or default
        
    Examples:
        >>> normalize_party("Republican")
        "R"
        >>> normalize_party("Democrat")
        "D"
        >>> normalize_party("Unknown")
        "I"
        
    Note:
        If you're getting "Unknown" parties, fix your data ingestion source!
        The API should provide the correct party affiliation.
    """
    if not party:
        return default
    
    party_clean = party.strip()
    
    # Direct lookup
    if party_clean in PARTY_MAPPINGS:
        return PARTY_MAPPINGS[party_clean]
    
    # Case-insensitive lookup
    for key, code in PARTY_MAPPINGS.items():
        if key.lower() == party_clean.lower():
            return code
    
    # Unknown party - this is a data quality issue!
    if party_clean.lower() in ["unknown", "other", "none", ""]:
        return default
    
    # If we get here, it's an unexpected party value
    # Log it so you can investigate
    print(f"⚠️  Warning: Unexpected party value '{party_clean}', using default '{default}'")
    return default


# ============================================================================
# Chamber Normalization
# ============================================================================

CHAMBER_MAPPINGS = {
    "Senate": "senate",
    "House": "house",
    "House of Representatives": "house",
    "senate": "senate",
    "house": "house",
    "SENATE": "senate",
    "HOUSE": "house",
}


def normalize_chamber(chamber: Optional[str]) -> Optional[str]:
    """
    Normalize chamber to lowercase standard format.
    
    Args:
        chamber: Raw chamber string
        
    Returns:
        "senate" or "house" or None
        
    Examples:
        >>> normalize_chamber("Senate")
        "senate"
        >>> normalize_chamber("House of Representatives")
        "house"
    """
    if not chamber:
        return None
    
    chamber_clean = chamber.strip()
    
    if chamber_clean in CHAMBER_MAPPINGS:
        return CHAMBER_MAPPINGS[chamber_clean]
    
    # Case-insensitive fallback
    for key, value in CHAMBER_MAPPINGS.items():
        if key.lower() == chamber_clean.lower():
            return value
    
    return None


# ============================================================================
# Full Politician Normalization
# ============================================================================

def normalize_politician(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a complete politician record.
    
    This ensures all fields follow our database standards:
    - state: 2-letter uppercase code
    - party: Single letter code
    - chamber: lowercase "senate" or "house"
    - last_updated: datetime object
    
    Args:
        raw_data: Raw politician data from any source
        
    Returns:
        Normalized politician data ready for database insertion
        
    Example:
        >>> raw = {
        ...     "full_name": "Lee, Mike",
        ...     "state": "Utah",
        ...     "party": "Republican",
        ...     "chamber": "Senate",
        ...     "bioguide_id": "L000577"
        ... }
        >>> normalized = normalize_politician(raw)
        >>> normalized["state"]
        "UT"
        >>> normalized["party"]
        "R"
    """
    normalized = raw_data.copy()
    
    # Normalize state
    if "state" in normalized:
        normalized["state"] = normalize_state(normalized["state"])
    
    # Normalize party
    if "party" in normalized:
        normalized["party"] = normalize_party(normalized["party"])
    
    # Normalize chamber
    if "chamber" in normalized:
        normalized["chamber"] = normalize_chamber(normalized["chamber"])
    
    # Ensure last_updated is set
    if "last_updated" not in normalized:
        normalized["last_updated"] = datetime.utcnow()
    
    # Ensure in_office has a default
    if "in_office" not in normalized:
        normalized["in_office"] = True  # Assume true unless specified
    
    return normalized


# ============================================================================
# Contribution Normalization
# ============================================================================

def normalize_contributor_state(state: Optional[str]) -> Optional[str]:
    """
    Normalize contributor state (same as politician state).
    
    Args:
        state: State from contribution record
        
    Returns:
        2-letter state code or None
    """
    return normalize_state(state)


def normalize_contribution(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a campaign contribution record.
    
    Args:
        raw_data: Raw contribution data
        
    Returns:
        Normalized contribution data
    """
    normalized = raw_data.copy()
    
    # Normalize contributor state
    if "contributor_state" in normalized:
        normalized["contributor_state"] = normalize_contributor_state(
            normalized["contributor_state"]
        )
    
    # Ensure last_updated
    if "last_updated" not in normalized:
        normalized["last_updated"] = datetime.utcnow()
    
    return normalized


# ============================================================================
# Bill/Legislation Normalization
# ============================================================================

def normalize_bill_status(status: Optional[str]) -> Optional[str]:
    """
    Normalize bill status to lowercase with underscores.
    
    Args:
        status: Raw status string
        
    Returns:
        Normalized status like "introduced", "passed_house", etc.
    """
    if not status:
        return None
    
    # Convert to lowercase and replace spaces with underscores
    normalized = status.lower().strip().replace(" ", "_").replace("-", "_")
    
    # Common status mappings
    status_map = {
        "intro": "introduced",
        "in_committee": "in_committee",
        "passed_house": "passed_house",
        "passed_senate": "passed_senate",
        "became_law": "became_law",
        "enacted": "became_law",
        "vetoed": "vetoed",
    }
    
    if normalized in status_map:
        return status_map[normalized]
    
    return normalized


def normalize_legislation(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a legislation/bill record.
    
    Args:
        raw_data: Raw legislation data
        
    Returns:
        Normalized legislation data
    """
    normalized = raw_data.copy()
    
    # Normalize status
    if "status" in normalized:
        normalized["status"] = normalize_bill_status(normalized["status"])
    
    # Ensure last_updated
    if "last_updated" not in normalized:
        normalized["last_updated"] = datetime.utcnow()
    
    return normalized


# ============================================================================
# Validation Functions
# ============================================================================

def validate_politician(data: Dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate that a politician record has all required fields in correct format.
    
    Args:
        data: Politician data to validate
        
    Returns:
        (is_valid, error_messages)
    """
    errors = []
    
    # Required fields
    required = ["bioguide_id", "full_name", "state", "party", "chamber"]
    for field in required:
        if field not in data or data[field] is None:
            errors.append(f"Missing required field: {field}")
    
    # Validate state format (should be 2-letter code)
    if "state" in data and data["state"]:
        if len(data["state"]) != 2:
            errors.append(f"State must be 2-letter code, got: {data['state']}")
        if data["state"] not in STATE_CODE_TO_NAME:
            errors.append(f"Invalid state code: {data['state']}")
    
    # Validate party format (should be single letter)
    if "party" in data and data["party"]:
        if len(data["party"]) != 1:
            errors.append(f"Party must be single letter, got: {data['party']}")
    
    # Validate chamber
    if "chamber" in data and data["chamber"]:
        if data["chamber"] not in ["senate", "house", "state_senate", "state_house"]:
            errors.append(f"Invalid chamber: {data['chamber']}")
    
    return len(errors) == 0, errors


# ============================================================================
# Utility Functions
# ============================================================================

def get_state_name(code: str) -> Optional[str]:
    """Get full state name from 2-letter code."""
    return STATE_CODE_TO_NAME.get(code.upper())


def get_party_name(code: str) -> str:
    """Get full party name from single-letter code."""
    party_names = {
        "R": "Republican",
        "D": "Democrat",
        "I": "Independent",
        "L": "Libertarian",
        "G": "Green",
        "O": "Other"
    }
    return party_names.get(code.upper(), "Unknown")


if __name__ == "__main__":
    # Test the functions
    print("Testing normalization functions...")
    print()
    
    # Test state normalization
    print("State normalization:")
    print(f"  'Utah' → '{normalize_state('Utah')}'")
    print(f"  'UT' → '{normalize_state('UT')}'")
    print(f"  'ut' → '{normalize_state('ut')}'")
    print(f"  'California' → '{normalize_state('California')}'")
    print()
    
    # Test party normalization
    print("Party normalization:")
    print(f"  'Republican' → '{normalize_party('Republican')}'")
    print(f"  'Democrat' → '{normalize_party('Democrat')}'")
    print(f"  'Unknown' → '{normalize_party('Unknown')}'")
    print()
    
    # Test full politician normalization
    print("Full politician normalization:")
    raw = {
        "full_name": "Lee, Mike",
        "state": "Utah",
        "party": "Unknown",
        "chamber": "Senate",
        "bioguide_id": "L000577",
        "in_office": True
    }
    normalized = normalize_politician(raw)
    print(f"  Input: {raw}")
    print(f"  Output: {normalized}")
    print()
    
    # Validation
    is_valid, errors = validate_politician(normalized)
    print(f"Valid: {is_valid}")
    if errors:
        print(f"Errors: {errors}")