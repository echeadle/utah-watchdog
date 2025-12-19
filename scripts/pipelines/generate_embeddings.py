"""
Generate embeddings for all bills in the database.

This enables semantic search - finding bills by meaning, not just keywords.

Usage:
    uv run python scripts/generate_embeddings.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
from src.config.settings import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def generate_embeddings():
    """Generate embeddings for all bills without them"""
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DATABASE]
    
    # Initialize OpenAI client
    openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    # Find bills without embeddings
    bills_without_embeddings = await db.legislation.find(
        {'embedding': {'$exists': False}}
    ).to_list(None)
    
    total = len(bills_without_embeddings)
    print(f"📊 Found {total} bills without embeddings")
    
    if total == 0:
        print("✅ All bills already have embeddings!")
        client.close()
        return
    
    # Process in batches
    processed = 0
    errors = 0
    
    for bill in bills_without_embeddings:
        try:
            # Create text to embed: title + summary
            title = bill.get('title', '')
            summary = bill.get('summary', '')
            short_title = bill.get('short_title', '')
            
            # Combine text (prioritize short_title if available)
            text_to_embed = f"{short_title or title}"
            if summary:
                text_to_embed += f"\n\n{summary}"
            
            # Truncate if too long (embeddings have token limits)
            text_to_embed = text_to_embed[:8000]  # ~2000 tokens
            
            if not text_to_embed.strip():
                logger.warning(f"Bill {bill.get('bill_id')} has no text to embed, skipping")
                continue
            
            # Generate embedding
            response = await openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text_to_embed
            )
            
            embedding = response.data[0].embedding
            
            # Update the bill with embedding
            await db.legislation.update_one(
                {'_id': bill['_id']},
                {'$set': {'embedding': embedding}}
            )
            
            processed += 1
            
            if processed % 10 == 0:
                print(f"✅ Processed {processed}/{total} bills...")
            
        except Exception as e:
            errors += 1
            logger.error(f"Error processing bill {bill.get('bill_id')}: {e}")
    
    print(f"\n{'='*60}")
    print(f"✅ Embedding generation complete!")
    print(f"   Processed: {processed}")
    print(f"   Errors: {errors}")
    print(f"   Total: {total}")
    print("="*60)
    
    client.close()


if __name__ == "__main__":
    asyncio.run(generate_embeddings())
