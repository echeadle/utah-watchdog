"""
Research Agent - Main AI agent for government watchdog queries.

This agent uses Pydantic AI to coordinate multiple tools for researching
politicians, legislation, voting records, and campaign finance.
"""
# Load environment variables FIRST before any other imports
from dotenv import load_dotenv
load_dotenv()

import os
from pydantic_ai import Agent, RunContext
from typing import List, Optional

from src.agents.dependencies import AgentDependencies
from src.agents.prompts import RESEARCH_AGENT_PROMPT

# Get model name from environment variable
model_name = os.getenv('MODEL_NAME', 'claude-sonnet-4-5-20250929')  # Default to Claude if not set

# Import tool functions - Politicians
from src.agents.tools.politician import (
    lookup_politician,
    get_politician_details
)

# Import tool functions - Legislation
from src.agents.tools.legislation import (
    search_legislation,
    get_bill_details,
    get_bill_votes,
    get_politician_sponsored_bills,
    get_recent_legislation,
    semantic_search_legislation
)

# Import tool functions - Finance
from src.agents.tools.finance import (
    get_politician_contributions,
    get_top_donors_by_industry,
    search_contributions
)

# Create the agent
research_agent = Agent(
    model=model_name,
    deps_type=AgentDependencies,
    system_prompt=RESEARCH_AGENT_PROMPT,
)


# ============================================================================
# POLITICIAN TOOLS
# ============================================================================

@research_agent.tool
async def find_politician(
    ctx: RunContext[AgentDependencies],
    name: Optional[str] = None,
    state: Optional[str] = None,
    party: Optional[str] = None,
    chamber: Optional[str] = None
) -> List[dict]:
    """
    Look up politicians by name, state, party, or chamber.
    
    Args:
        name: Full or partial name to search (e.g., "Mike Lee", "Romney")
        state: State in ANY format - name or abbreviation, any capitalization (e.g., "Utah", "UT", "utah", "UTAH")
        party: Party affiliation ("D", "R", "I")
        chamber: "senate", "house"
    
    Returns:
        List of matching politicians with basic info
    
    Example:
        politicians = await find_politician(name="Lee", state="UT")
    """
    return await lookup_politician(
        db=ctx.deps.db,
        name=name,
        state=state,
        party=party,
        chamber=chamber
    )


@research_agent.tool
async def get_politician_info(
    ctx: RunContext[AgentDependencies],
    bioguide_id: str
) -> dict:
    """
    Get comprehensive details about a specific politician.
    
    Args:
        bioguide_id: The politician's bioguide identifier (e.g., "L000577" for Mike Lee)
    
    Returns:
        Full politician profile
    
    Example:
        details = await get_politician_info(bioguide_id="L000577")
    """
    result = await get_politician_details(
        db=ctx.deps.db,
        bioguide_id=bioguide_id
    )
    
    if result is None:
        return {"error": f"Politician not found: {bioguide_id}"}
    
    return result


# ============================================================================
# LEGISLATION TOOLS
# ============================================================================

@research_agent.tool
async def search_bills(
    ctx: RunContext[AgentDependencies],
    query: str,
    jurisdiction: str = "all",
    status: Optional[str] = None,
    congress: Optional[int] = None,
    limit: int = 10
) -> List[dict]:
    """
    Search for legislation by keyword or topic using keyword search.
    
    Use this for specific bill numbers or exact keyword matches.
    For topic/concept searches, use semantic_search_bills instead.
    
    Args:
        query: Search text (searches title, summary, subjects)
        jurisdiction: Filter by "federal", "utah", or "all"
        status: Filter by status (e.g., "introduced", "passed_senate")
        congress: Filter by congress number (e.g., 119)
        limit: Maximum results to return
    
    Returns:
        List of matching bills
    
    Example:
        bills = await search_bills("HR 1491", congress=119)
    """
    return await search_legislation(
        query=query,
        jurisdiction=jurisdiction,
        status=status,
        congress=congress,
        limit=limit,
        ctx=ctx
    )


@research_agent.tool
async def semantic_search_bills(
    ctx: RunContext[AgentDependencies],
    query: str,
    limit: int = 10
) -> List[dict]:
    """
    Search for legislation using semantic/meaning-based search.
    
    This is better than keyword search for finding bills by topic or concept.
    Use this when the user asks about bills on a subject, theme, or policy area.
    
    Args:
        query: Natural language description of what to search for
        limit: Maximum results to return
    
    Returns:
        List of relevant bills with similarity scores
    
    Example:
        bills = await semantic_search_bills("climate change policy", limit=5)
    """
    return await semantic_search_legislation(
        query=query,
        limit=limit,
        ctx=ctx
    )


@research_agent.tool
async def get_bill_info(
    ctx: RunContext[AgentDependencies],
    bill_id: str
) -> dict:
    """
    Get detailed information about a specific bill.
    
    Args:
        bill_id: The bill identifier (e.g., "hr-1491-119")
    
    Returns:
        Full bill details including summary, sponsor, status
    
    Example:
        bill = await get_bill_info("hr-1491-119")
    """
    return await get_bill_details(
        bill_id=bill_id,
        ctx=ctx
    )


@research_agent.tool
async def get_votes_on_bill(
    ctx: RunContext[AgentDependencies],
    bill_id: str
) -> dict:
    """
    Get voting record for a specific bill.
    
    Args:
        bill_id: The bill identifier (e.g., "hr-3684-117")
    
    Returns:
        Vote details including how each politician voted
    
    Note: Vote data is primarily from 118th Congress
    
    Example:
        votes = await get_votes_on_bill("hr-3684-117")
    """
    return await get_bill_votes(
        bill_id=bill_id,
        ctx=ctx
    )


@research_agent.tool
async def get_sponsored_bills(
    ctx: RunContext[AgentDependencies],
    politician_id: Optional[str] = None,
    bioguide_id: Optional[str] = None,
    congress: Optional[int] = None,
    limit: int = 10
) -> List[dict]:
    """
    Get bills sponsored by a specific politician.
    
    Args:
        politician_id: The politician's ID (will look up bioguide_id)
        bioguide_id: The bioguide ID directly (faster if you have it)
        congress: Filter by congress number
        limit: Maximum results to return
    
    Returns:
        List of sponsored bills
    
    Example:
        bills = await get_sponsored_bills(bioguide_id="L000577")
    """
    return await get_politician_sponsored_bills(
        politician_id=politician_id,
        bioguide_id=bioguide_id,
        congress=congress,
        limit=limit,
        ctx=ctx
    )


@research_agent.tool
async def get_recent_bills(
    ctx: RunContext[AgentDependencies],
    days: int = 30,
    jurisdiction: str = "all",
    limit: int = 20
) -> List[dict]:
    """
    Get recently introduced or updated legislation.
    
    Args:
        days: Number of days to look back
        jurisdiction: Filter by "federal", "utah", or "all"
        limit: Maximum results to return
    
    Returns:
        List of recent bills sorted by latest action
    
    Example:
        recent = await get_recent_bills(days=7)
    """
    return await get_recent_legislation(
        days=days,
        jurisdiction=jurisdiction,
        limit=limit,
        ctx=ctx
    )


# ============================================================================
# FINANCE TOOLS
# ============================================================================

@research_agent.tool
async def get_campaign_contributions(
    ctx: RunContext[AgentDependencies],
    bioguide_id: Optional[str] = None,
    politician_name: Optional[str] = None,
    cycle: str = "2024"
) -> dict:
    """
    Get campaign contribution data for a politician.
    
    Shows total raised, top contributors, contribution breakdown by type,
    and recent individual contributions.
    
    Args:
        bioguide_id: Bioguide ID of the politician (preferred)
        politician_name: Name of the politician (if bioguide_id not available)
        cycle: Election cycle year (default: 2024)
    
    Returns:
        Contribution summary with total raised, top donors, and recent contributions
    
    Example:
        contribs = await get_campaign_contributions(bioguide_id="L000577", cycle="2024")
    """
    return await get_politician_contributions(
        db=ctx.deps.db,
        bioguide_id=bioguide_id,
        recipient_name=politician_name,
        cycle=cycle
    )


@research_agent.tool
async def get_top_donors(
    ctx: RunContext[AgentDependencies],
    bioguide_id: Optional[str] = None,
    politician_name: Optional[str] = None,
    cycle: str = "2024",
    limit: int = 10
) -> List[dict]:
    """
    Get top contributing employers/organizations for a politician.
    
    This shows which companies' employees are donating the most.
    
    Args:
        bioguide_id: Bioguide ID of the politician
        politician_name: Name of the politician
        cycle: Election cycle year
        limit: Number of top employers to return
    
    Returns:
        List of top employers with contribution totals and number of contributors
    
    Example:
        donors = await get_top_donors(bioguide_id="L000577")
    """
    return await get_top_donors_by_industry(
        db=ctx.deps.db,
        bioguide_id=bioguide_id,
        recipient_name=politician_name,
        cycle=cycle,
        limit=limit
    )


@research_agent.tool
async def search_campaign_contributions(
    ctx: RunContext[AgentDependencies],
    contributor_name: Optional[str] = None,
    employer: Optional[str] = None,
    state: Optional[str] = None,
    min_amount: Optional[float] = None,
    cycle: str = "2024",
    limit: int = 50
) -> List[dict]:
    """
    Search campaign contributions by various criteria.
    
    Use this to find contributions from specific people, companies, states,
    or above certain amounts.
    
    Args:
        contributor_name: Name of contributor to search for
        employer: Employer/organization name to search for
        state: State code (e.g., "CA", "UT")
        min_amount: Minimum contribution amount in dollars
        cycle: Election cycle year
        limit: Maximum results to return
    
    Returns:
        List of matching contributions with contributor details
    
    Example:
        # Find all contributions from Applied Materials employees
        contribs = await search_campaign_contributions(employer="Applied Materials")
        
        # Find large contributions from California
        contribs = await search_campaign_contributions(state="CA", min_amount=1000)
    """
    return await search_contributions(
        db=ctx.deps.db,
        contributor_name=contributor_name,
        employer=employer,
        state=state,
        min_amount=min_amount,
        cycle=cycle,
        limit=limit
    )


# ============================================================================
# HELPER FUNCTION FOR RUNNING THE AGENT
# ============================================================================

async def run_research_query(query: str, deps: AgentDependencies) -> str:
    """
    Convenience function to run a query against the research agent.
    
    Args:
        query: The user's question
        deps: Agent dependencies (database connection)
    
    Returns:
        The agent's response as a string
    
    Example:
        deps = await get_agent_deps()
        response = await run_research_query("What bills has Mike Lee sponsored?", deps)
    """
    result = await research_agent.run(
        query,
        deps=deps
    )
    return result.output
    