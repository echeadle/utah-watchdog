"""
Check if bills have embeddings for semantic search.

Usage:
    uv run python scripts/check_embeddings.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from src.config.settings import settings


async def check():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    
    # Check if any bills have embeddings
    sample = await db.legislation.find_one({'embedding': {'$exists': True}})
    
    if sample:
        print('✅ Bills already have embeddings')
        print(f'   Embedding dimension: {len(sample["embedding"])}')
    else:
        print('❌ No embeddings found - need to generate them')
    
    total = await db.legislation.count_documents({})
    print(f'   Total bills: {total}')
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check())
