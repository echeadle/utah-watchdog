"""
Agent tools for searching and querying legislation.

These tools allow the AI agent to:
- Search bills by keyword/topic
- Get detailed bill information
- Find votes on bills
- Get bills sponsored by a politician
"""
from typing import Optional, List
from datetime import datetime


async def search_legislation(
    query: str,
    jurisdiction: str = "all",
    status: Optional[str] = None,
    sponsor_bioguide_id: Optional[str] = None,
    congress: Optional[int] = None,
    limit: int = 10,
    ctx = None
) -> List[dict]:
    """
    Search for legislation using keyword search.
    
    Args:
        query: Search text (searches title, summary, subjects)
        jurisdiction: Filter by "federal", "utah", or "all"
        status: Filter by status (e.g., "introduced", "passed_senate")
        sponsor_bioguide_id: Filter by sponsor's bioguide ID
        congress: Filter by congress number (e.g., 118)
        limit: Maximum results to return
    
    Returns:
        List of matching bills with basic info
    
    Example:
        bills = await search_legislation("infrastructure", status="passed_senate")
    """
    db = ctx.deps.db
    
    # Build MongoDB query
    filters = {}
    
    # Text search across title, summary, subjects
    if query:
        filters["$or"] = [
            {"title": {"$regex": query, "$options": "i"}},
            {"short_title": {"$regex": query, "$options": "i"}},
            {"summary": {"$regex": query, "$options": "i"}},
            {"subjects": {"$regex": query, "$options": "i"}},
            {"policy_area": {"$regex": query, "$options": "i"}}
        ]
    
    # Apply filters
    if jurisdiction != "all":
        if jurisdiction == "federal":
            filters["congress"] = {"$exists": True}
        elif jurisdiction == "utah":
            # Utah bills would have a different structure
            # For now, we only have federal bills
            filters["jurisdiction"] = "utah"
    
    if status:
        filters["status"] = status
    
    if sponsor_bioguide_id:
        filters["sponsor_bioguide_id"] = sponsor_bioguide_id
    
    if congress:
        filters["congress"] = congress
    
    # Execute query
    cursor = db.legislation.find(filters).limit(limit)
    bills = await cursor.to_list(length=limit)
    
    # Format results
    results = []
    for bill in bills:
        results.append({
            "bill_id": bill.get("bill_id"),
            "bill_type": bill.get("bill_type"),
            "number": bill.get("number"),
            "congress": bill.get("congress"),
            "title": bill.get("title"),
            "short_title": bill.get("short_title"),
            "status": bill.get("status"),
            "sponsor_bioguide_id": bill.get("sponsor_bioguide_id"),
            "introduced_date": bill.get("introduced_date"),
            "latest_action": bill.get("latest_action_text"),
            "url": bill.get("congress_gov_url"),
            "subjects": bill.get("subjects", [])[:5]  # First 5 subjects
        })
    
    return results


async def get_bill_details(
    bill_id: str,
    ctx = None
) -> dict:
    """
    Get comprehensive details about a specific bill.
    
    Args:
        bill_id: The bill identifier (e.g., "hr-1234-118")
    
    Returns:
        Full bill details including summary, sponsors, status, and actions
    
    Example:
        bill = await get_bill_details("hr-3684-117")
    """
    db = ctx.deps.db
    
    # Find bill by bill_id
    bill = await db.legislation.find_one({"bill_id": bill_id})
    
    if not bill:
        return {"error": f"Bill not found: {bill_id}"}
    
    # Get sponsor details if available
    sponsor_info = None
    if bill.get("sponsor_bioguide_id"):
        sponsor = await db.politicians.find_one({
            "bioguide_id": bill["sponsor_bioguide_id"]
        })
        if sponsor:
            sponsor_info = {
                "name": sponsor.get("full_name"),
                "party": sponsor.get("party"),
                "state": sponsor.get("state")
            }
    
    # Get cosponsor count
    cosponsors = bill.get("cosponsor_bioguide_ids", [])
    
    return {
        "bill_id": bill.get("bill_id"),
        "bill_type": bill.get("bill_type"),
        "number": bill.get("number"),
        "congress": bill.get("congress"),
        "title": bill.get("title"),
        "short_title": bill.get("short_title"),
        "summary": bill.get("summary"),
        "status": bill.get("status"),
        "introduced_date": bill.get("introduced_date"),
        "latest_action": {
            "date": bill.get("latest_action_date"),
            "text": bill.get("latest_action_text")
        },
        "sponsor": sponsor_info,
        "cosponsor_count": len(cosponsors),
        "policy_area": bill.get("policy_area"),
        "subjects": bill.get("subjects", []),
        "urls": {
            "congress_gov": bill.get("congress_gov_url"),
            "full_text": bill.get("full_text_url")
        },
        "last_updated": bill.get("last_updated")
    }


async def get_bill_votes(
    bill_id: str,
    ctx = None
) -> dict:
    """
    Get all votes on a specific bill.
    
    NOTE: This requires the votes collection to be populated.
    Currently returns placeholder until vote ingestion is complete.
    
    Args:
        bill_id: The bill identifier (e.g., "hr-3684-117")
    
    Returns:
        Vote details including how each politician voted
    
    Example:
        votes = await get_bill_votes("hr-3684-117")
    """
    db = ctx.deps.db
    
    # Check if bill exists
    bill = await db.legislation.find_one({"bill_id": bill_id})
    if not bill:
        return {"error": f"Bill not found: {bill_id}"}
    
    # Look for votes on this bill
    votes = []
    cursor = db.votes.find({"bill_id": bill_id})
    async for vote in cursor:
        votes.append({
            "vote_id": vote.get("vote_id"),
            "chamber": vote.get("chamber"),
            "question": vote.get("question"),
            "result": vote.get("result"),
            "date": vote.get("vote_date"),
            "yea_count": vote.get("yea_count"),
            "nay_count": vote.get("nay_count"),
            "not_voting_count": vote.get("not_voting_count")
        })
    
    if not votes:
        return {
            "bill_id": bill_id,
            "bill_title": bill.get("title"),
            "votes": [],
            "message": "No votes found for this bill yet. Vote data may not be ingested."
        }
    
    return {
        "bill_id": bill_id,
        "bill_title": bill.get("title"),
        "votes": votes
    }


async def get_politician_sponsored_bills(
    politician_id: Optional[str] = None,
    bioguide_id: Optional[str] = None,
    congress: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 10,
    ctx = None
) -> List[dict]:
    """
    Get bills sponsored by a specific politician.
    
    Args:
        politician_id: The politician's ID (will look up bioguide_id)
        bioguide_id: The bioguide ID directly (faster)
        congress: Filter by congress number
        status: Filter by bill status
        limit: Maximum results to return
    
    Returns:
        List of bills sponsored by the politician
    
    Example:
        bills = await get_politician_sponsored_bills(bioguide_id="L000577")
    """
    db = ctx.deps.db
    
    # If politician_id provided, look up bioguide_id
    if politician_id and not bioguide_id:
        politician = await db.politicians.find_one({"id": politician_id})
        if politician:
            bioguide_id = politician.get("bioguide_id")
    
    if not bioguide_id:
        return {"error": "Could not find politician's bioguide_id"}
    
    # Build query
    filters = {"sponsor_bioguide_id": bioguide_id}
    
    if congress:
        filters["congress"] = congress
    
    if status:
        filters["status"] = status
    
    # Execute query
    cursor = db.legislation.find(filters).sort("introduced_date", -1).limit(limit)
    bills = await cursor.to_list(length=limit)
    
    # Format results
    results = []
    for bill in bills:
        results.append({
            "bill_id": bill.get("bill_id"),
            "bill_type": bill.get("bill_type"),
            "number": bill.get("number"),
            "congress": bill.get("congress"),
            "title": bill.get("title"),
            "short_title": bill.get("short_title"),
            "status": bill.get("status"),
            "introduced_date": bill.get("introduced_date"),
            "cosponsor_count": len(bill.get("cosponsor_bioguide_ids", [])),
            "url": bill.get("congress_gov_url")
        })
    
    return results


async def get_recent_legislation(
    days: int = 30,
    jurisdiction: str = "all",
    status: Optional[str] = None,
    limit: int = 20,
    ctx = None
) -> List[dict]:
    """
    Get recently introduced or updated legislation.
    
    Args:
        days: Number of days to look back
        jurisdiction: Filter by "federal", "utah", or "all"
        status: Filter by bill status
        limit: Maximum results to return
    
    Returns:
        List of recent bills sorted by latest action date
    
    Example:
        recent = await get_recent_legislation(days=7)
    """
    db = ctx.deps.db
    
    # Calculate cutoff date
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    # Build query
    filters = {
        "$or": [
            {"introduced_date": {"$gte": cutoff.isoformat()}},
            {"latest_action_date": {"$gte": cutoff.isoformat()}}
        ]
    }
    
    if jurisdiction != "all":
        if jurisdiction == "federal":
            filters["congress"] = {"$exists": True}
        else:
            filters["jurisdiction"] = jurisdiction
    
    if status:
        filters["status"] = status
    
    # Execute query
    cursor = db.legislation.find(filters).sort("latest_action_date", -1).limit(limit)
    bills = await cursor.to_list(length=limit)
    
    # Format results
    results = []
    for bill in bills:
        results.append({
            "bill_id": bill.get("bill_id"),
            "title": bill.get("short_title") or bill.get("title"),
            "status": bill.get("status"),
            "sponsor_bioguide_id": bill.get("sponsor_bioguide_id"),
            "introduced_date": bill.get("introduced_date"),
            "latest_action": {
                "date": bill.get("latest_action_date"),
                "text": bill.get("latest_action_text")
            },
            "url": bill.get("congress_gov_url")
        })
    
    return results


async def semantic_search_legislation(
    query: str,
    limit: int = 10,
    ctx = None
) -> List[dict]:
    """
    Search legislation using semantic/meaning-based search.
    
    This finds bills by their meaning, not just keywords. Better for
    queries like "climate change bills" or "healthcare reform".
    
    Args:
        query: Natural language search query
        limit: Maximum results to return
    
    Returns:
        List of relevant bills with similarity scores
    
    Example:
        bills = await semantic_search_legislation("environmental protection")
    """
    from openai import AsyncOpenAI
    from src.config.settings import settings
    
    db = ctx.deps.db
    
    # Generate embedding for the query
    openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )
    query_embedding = response.data[0].embedding
    
    # Vector search using MongoDB Atlas
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": 100,
                "limit": limit
            }
        },
        {
            "$project": {
                "bill_id": 1,
                "bill_type": 1,
                "number": 1,
                "congress": 1,
                "title": 1,
                "short_title": 1,
                "summary": 1,
                "status": 1,
                "sponsor_bioguide_id": 1,
                "introduced_date": 1,
                "subjects": 1,
                "congress_gov_url": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]
    
    # Execute search
    results = []
    async for doc in db.legislation.aggregate(pipeline):
        results.append({
            "bill_id": doc.get("bill_id"),
            "title": doc.get("short_title") or doc.get("title"),
            "status": doc.get("status"),
            "sponsor_bioguide_id": doc.get("sponsor_bioguide_id"),
            "introduced_date": doc.get("introduced_date"),
            "summary": doc.get("summary", "")[:200] if doc.get("summary") else None,
            "subjects": doc.get("subjects", [])[:3],  # First 3 subjects
            "relevance_score": round(doc.get("score", 0), 3),
            "url": doc.get("congress_gov_url")
        })
    
    return results
