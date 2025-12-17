"""
Agent dependencies - provides database and other resources to agent tools.

This follows the Pydantic AI pattern for dependency injection.
"""
from motor.motor_asyncio import AsyncIOMotorDatabase
from dataclasses import dataclass


@dataclass
class AgentDependencies:
    """
    Dependencies that are passed to agent tools via context.
    
    Attributes:
        db: MongoDB database connection (Motor async)
    """
    db: AsyncIOMotorDatabase


async def get_agent_deps() -> AgentDependencies:
    """
    Factory function to create agent dependencies.
    
    This would typically be called when initializing the agent
    or handling an API request.
    
    Returns:
        AgentDependencies with database connection
    """
    from motor.motor_asyncio import AsyncIOMotorClient
    from src.config.settings import settings
    
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    
    return AgentDependencies(db=db)
