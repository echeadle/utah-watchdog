"""
Agent tools for querying politician data.

These functions are used by the AI agent to answer questions about politicians.
"""
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)


async def lookup_politician(
    db: AsyncIOMotorDatabase,
    name: Optional[str] = None,
    state: Optional[str] = None,
    party: Optional[str] = None,
    chamber: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Look up politicians by name, state, party, or chamber.
    
    This is a flexible search function that the AI agent can use to find
    politicians based on various criteria.
    
    Args:
        db: MongoDB database connection
        name: Full or partial name to search (case-insensitive)
        state: State name or abbreviation (e.g., "Utah" or "UT")
        party: Party affiliation ("D", "R", "I")
        chamber: "senate" or "house"
        limit: Maximum number of results to return (default: 10)
    
    Returns:
        List of politician dictionaries with their key information
    
    Examples:
        # Find politicians by name
        await lookup_politician(db, name="Mike Lee")
        
        # Find all Utah politicians
        await lookup_politician(db, state="Utah")
        
        # Find all Republican senators
        await lookup_politician(db, party="R", chamber="senate")
    """
    collection = db.politicians
    
    # Build the query filter
    query = {}
    
    # Name search (case-insensitive, partial match)
    if name:
        query["$or"] = [
            {"full_name": {"$regex": name, "$options": "i"}},
            {"first_name": {"$regex": name, "$options": "i"}},
            {"last_name": {"$regex": name, "$options": "i"}}
        ]
    
    # State filter (handle both full name and abbreviation)
    if state:
        # Try to match both the full state name and abbreviation
        query["state"] = {"$regex": f"^{state}$", "$options": "i"}
    
    # Party filter
    if party:
        query["party"] = party.upper()
    
    # Chamber filter
    if chamber:
        query["chamber"] = chamber.lower()
    
    # Only return currently serving politicians
    query["in_office"] = True
    
    logger.info(f"Searching politicians with query: {query}")
    
    # Execute query
    cursor = collection.find(query).limit(limit).sort("last_name", 1)
    results = await cursor.to_list(length=limit)
    
    # Transform results to a cleaner format for the agent
    politicians = []
    for doc in results:
        politician = {
            "bioguide_id": doc.get("bioguide_id"),
            "full_name": doc.get("full_name"),
            "party": doc.get("party"),
            "state": doc.get("state"),
            "chamber": doc.get("chamber"),
            "title": doc.get("title"),
            "district": doc.get("district"),
            "website": doc.get("website"),
            "photo_url": doc.get("photo_url")
        }
        
        # Remove None values to keep response clean
        politician = {k: v for k, v in politician.items() if v is not None}
        politicians.append(politician)
    
    logger.info(f"Found {len(politicians)} politicians")
    return politicians


async def get_politician_details(
    db: AsyncIOMotorDatabase,
    bioguide_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get comprehensive details about a specific politician.
    
    Args:
        db: MongoDB database connection
        bioguide_id: The politician's unique bioguide identifier
    
    Returns:
        Full politician profile, or None if not found
    
    Example:
        await get_politician_details(db, "L000577")  # Mike Lee
    """
    collection = db.politicians
    
    politician = await collection.find_one({"bioguide_id": bioguide_id})
    
    if not politician:
        logger.warning(f"Politician not found: {bioguide_id}")
        return None
    
    # Remove MongoDB's internal _id field
    politician.pop("_id", None)
    
    # TODO: In the future, this would also fetch:
    # - Recent votes
    # - Sponsored bills
    # - Committee assignments
    # - Top contributors
    # - Recent stock trades
    
    return politician


async def search_politicians_by_criteria(
    db: AsyncIOMotorDatabase,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Advanced search with any field criteria.
    
    This is a more flexible function that allows searching by any field
    in the politician document.
    
    Args:
        db: MongoDB database connection
        **kwargs: Any field to search by (e.g., jurisdiction="federal", in_office=True)
    
    Returns:
        List of matching politicians
    
    Example:
        # Find all federal politicians in office
        await search_politicians_by_criteria(db, jurisdiction="federal", in_office=True)
    """
    collection = db.politicians
    
    # Build query from kwargs
    query = {k: v for k, v in kwargs.items() if v is not None}
    
    logger.info(f"Advanced search with criteria: {query}")
    
    cursor = collection.find(query).limit(50).sort("last_name", 1)
    results = await cursor.to_list(length=50)
    
    # Clean up results
    politicians = []
    for doc in results:
        doc.pop("_id", None)
        politicians.append(doc)
    
    return politicians


# Synchronous versions for testing/CLI
def lookup_politician_sync(
    db,
    name: Optional[str] = None,
    state: Optional[str] = None,
    party: Optional[str] = None,
    chamber: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Synchronous version of lookup_politician for testing.
    
    Same as lookup_politician but works with synchronous MongoDB client.
    """
    collection = db.politicians
    
    # Build query
    query = {}
    
    if name:
        query["$or"] = [
            {"full_name": {"$regex": name, "$options": "i"}},
            {"first_name": {"$regex": name, "$options": "i"}},
            {"last_name": {"$regex": name, "$options": "i"}}
        ]
    
    if state:
        query["state"] = {"$regex": f"^{state}$", "$options": "i"}
    
    if party:
        query["party"] = party.upper()
    
    if chamber:
        query["chamber"] = chamber.lower()
    
    query["in_office"] = True
    
    # Execute query
    results = list(collection.find(query).limit(limit).sort("last_name", 1))
    
    # Transform results
    politicians = []
    for doc in results:
        doc.pop("_id", None)
        politician = {
            "bioguide_id": doc.get("bioguide_id"),
            "full_name": doc.get("full_name"),
            "party": doc.get("party"),
            "state": doc.get("state"),
            "chamber": doc.get("chamber"),
            "title": doc.get("title"),
            "district": doc.get("district"),
            "website": doc.get("website")
        }
        politician = {k: v for k, v in politician.items() if v is not None}
        politicians.append(politician)
    
    return politicians
