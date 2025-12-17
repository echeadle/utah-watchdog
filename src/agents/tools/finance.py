"""
Agent tools for querying campaign finance data.

These functions allow the AI agent to answer questions about
campaign contributions, donors, and money in politics.
"""
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)


async def get_politician_contributions(
    db: AsyncIOMotorDatabase,
    bioguide_id: Optional[str] = None,
    recipient_name: Optional[str] = None,
    cycle: str = "2024",
    limit: int = 20
) -> Dict[str, Any]:
    """
    Get campaign contributions for a politician.
    
    Args:
        db: MongoDB database connection
        bioguide_id: Bioguide ID of the politician
        recipient_name: Name of the recipient (if bioguide_id not available)
        cycle: Election cycle (e.g., "2024")
        limit: Max number of individual contributions to return
    
    Returns:
        Dictionary with total raised, contribution breakdown, and top contributors
    """
    # Build query
    query = {"cycle": cycle}
    
    if bioguide_id:
        query["bioguide_id"] = bioguide_id
    elif recipient_name:
        query["recipient_name"] = {"$regex": recipient_name, "$options": "i"}
    else:
        return {"error": "Must provide either bioguide_id or recipient_name"}
    
    collection = db.contributions
    
    # Get total raised
    pipeline_total = [
        {"$match": query},
        {"$group": {
            "_id": None,
            "total": {"$sum": "$amount"}
        }}
    ]
    
    total_result = await collection.aggregate(pipeline_total).to_list(1)
    total_raised = total_result[0]["total"] if total_result else 0
    
    # Get contribution count
    count = await collection.count_documents(query)
    
    # Get top contributors
    pipeline_top = [
        {"$match": query},
        {"$group": {
            "_id": "$contributor_name",
            "total_amount": {"$sum": "$amount"},
            "num_contributions": {"$sum": 1},
            "employer": {"$first": "$contributor_employer"},
            "state": {"$first": "$contributor_state"}
        }},
        {"$sort": {"total_amount": -1}},
        {"$limit": 10}
    ]
    
    top_contributors = []
    async for contrib in collection.aggregate(pipeline_top):
        top_contributors.append({
            "name": contrib["_id"],
            "total": float(contrib["total_amount"]),
            "count": contrib["num_contributions"],
            "employer": contrib.get("employer"),
            "state": contrib.get("state")
        })
    
    # Get contributions by type
    pipeline_by_type = [
        {"$match": query},
        {"$group": {
            "_id": "$contributor_type",
            "total": {"$sum": "$amount"}
        }}
    ]
    
    by_type = {}
    async for item in collection.aggregate(pipeline_by_type):
        by_type[item["_id"]] = float(item["total"])
    
    # Get recent contributions
    recent = []
    cursor = collection.find(query).sort("contribution_date", -1).limit(limit)
    async for contrib in cursor:
        recent.append({
            "contributor": contrib.get("contributor_name"),
            "amount": float(contrib.get("amount", 0)),
            "date": contrib.get("contribution_date"),
            "employer": contrib.get("contributor_employer"),
            "occupation": contrib.get("contributor_occupation"),
            "city": contrib.get("contributor_city"),
            "state": contrib.get("contributor_state")
        })
    
    return {
        "cycle": cycle,
        "total_raised": float(total_raised),
        "total_contributions": count,
        "by_type": by_type,
        "top_contributors": top_contributors,
        "recent_contributions": recent
    }


async def get_top_donors_by_industry(
    db: AsyncIOMotorDatabase,
    bioguide_id: Optional[str] = None,
    recipient_name: Optional[str] = None,
    cycle: str = "2024",
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get top contributing employers/organizations.
    
    Args:
        db: MongoDB database connection
        bioguide_id: Bioguide ID of the politician
        recipient_name: Name of the recipient
        cycle: Election cycle
        limit: Number of top employers to return
    
    Returns:
        List of top employers with contribution totals
    """
    query = {"cycle": cycle}
    
    if bioguide_id:
        query["bioguide_id"] = bioguide_id
    elif recipient_name:
        query["recipient_name"] = {"$regex": recipient_name, "$options": "i"}
    else:
        return []
    
    # Group by employer
    pipeline = [
        {"$match": query},
        {"$match": {"contributor_employer": {"$ne": None}}},  # Exclude null employers
        {"$group": {
            "_id": "$contributor_employer",
            "total_amount": {"$sum": "$amount"},
            "num_contributors": {"$sum": 1}
        }},
        {"$sort": {"total_amount": -1}},
        {"$limit": limit}
    ]
    
    results = []
    async for item in db.contributions.aggregate(pipeline):
        results.append({
            "employer": item["_id"],
            "total": float(item["total_amount"]),
            "num_contributors": item["num_contributors"]
        })
    
    return results


async def search_contributions(
    db: AsyncIOMotorDatabase,
    contributor_name: Optional[str] = None,
    employer: Optional[str] = None,
    state: Optional[str] = None,
    min_amount: Optional[float] = None,
    cycle: str = "2024",
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search contributions by various criteria.
    
    Args:
        db: MongoDB database connection
        contributor_name: Name of contributor to search for
        employer: Employer to search for
        state: State of contributor
        min_amount: Minimum contribution amount
        cycle: Election cycle
        limit: Max results
    
    Returns:
        List of matching contributions
    """
    query = {"cycle": cycle}
    
    if contributor_name:
        query["contributor_name"] = {"$regex": contributor_name, "$options": "i"}
    
    if employer:
        query["contributor_employer"] = {"$regex": employer, "$options": "i"}
    
    if state:
        query["contributor_state"] = state.upper()
    
    if min_amount:
        query["amount"] = {"$gte": min_amount}
    
    results = []
    cursor = db.contributions.find(query).sort("amount", -1).limit(limit)
    
    async for contrib in cursor:
        results.append({
            "recipient": contrib.get("recipient_name"),
            "contributor": contrib.get("contributor_name"),
            "amount": float(contrib.get("amount", 0)),
            "employer": contrib.get("contributor_employer"),
            "occupation": contrib.get("contributor_occupation"),
            "city": contrib.get("contributor_city"),
            "state": contrib.get("contributor_state"),
            "date": contrib.get("contribution_date")
        })
    
    return results


async def get_contribution_summary_stats(
    db: AsyncIOMotorDatabase,
    cycle: str = "2024"
) -> Dict[str, Any]:
    """
    Get overall contribution statistics for a cycle.
    
    Args:
        db: MongoDB database connection
        cycle: Election cycle
    
    Returns:
        Summary statistics
    """
    query = {"cycle": cycle}
    
    # Total raised across all candidates
    pipeline_total = [
        {"$match": query},
        {"$group": {
            "_id": None,
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }}
    ]
    
    total_result = await db.contributions.aggregate(pipeline_total).to_list(1)
    
    if not total_result:
        return {
            "cycle": cycle,
            "total_raised": 0,
            "total_contributions": 0
        }
    
    # Average contribution
    avg = total_result[0]["total"] / total_result[0]["count"] if total_result[0]["count"] > 0 else 0
    
    # Top recipients
    pipeline_recipients = [
        {"$match": query},
        {"$group": {
            "_id": "$recipient_name",
            "total": {"$sum": "$amount"}
        }},
        {"$sort": {"total": -1}},
        {"$limit": 10}
    ]
    
    top_recipients = []
    async for item in db.contributions.aggregate(pipeline_recipients):
        top_recipients.append({
            "name": item["_id"],
            "total": float(item["total"])
        })
    
    return {
        "cycle": cycle,
        "total_raised": float(total_result[0]["total"]),
        "total_contributions": total_result[0]["count"],
        "average_contribution": float(avg),
        "top_recipients": top_recipients
    }
