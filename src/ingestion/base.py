"""
Base ingester class with fixed connection management.

The key fix: Ensure all async operations complete before disconnecting.
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, TypeVar, Generic, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import logging

from src.config.settings import settings

T = TypeVar('T')


class BaseIngester(ABC, Generic[T]):
    """
    Base class for all data ingesters with proper async connection handling.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.stats = {
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "errors": 0,
            "started_at": None,
            "completed_at": None
        }
    
    async def connect(self):
        """
        Initialize database connection.
        
        Override this if you need custom connection logic.
        """
        if self.db is None:
            self.client = AsyncIOMotorClient(settings.MONGODB_URI)
            self.db = self.client[settings.MONGODB_DATABASE]
            self.logger.info(f"Connected to MongoDB: {settings.MONGODB_DATABASE}")
    
    async def disconnect(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            self.logger.info("Disconnected from MongoDB")
    
    @abstractmethod
    async def fetch_data(self, **kwargs) -> AsyncGenerator[dict, None]:
        """
        Fetch data from external source.
        
        This should be an async generator that yields raw data items.
        
        Args:
            **kwargs: Parameters for fetching data
            
        Yields:
            Raw data dictionaries from the source
        """
        pass
    
    @abstractmethod
    async def transform(self, raw_data: dict) -> T:
        """
        Transform raw data to our model.
        
        Args:
            raw_data: Raw data dictionary from source
            
        Returns:
            Transformed data model
        """
        pass
    
    @abstractmethod
    async def load(self, item: T) -> bool:
        """
        Load item into database (upsert).
        
        Args:
            item: Transformed data item
            
        Returns:
            True if new insert, False if update
        """
        pass
    
    async def process_item(self, raw_item: dict):
        """
        Process a single item through the ETL pipeline.
        
        Args:
            raw_item: Raw data from source
        """
        try:
            self.stats["processed"] += 1
            
            # Transform
            item = await self.transform(raw_item)
            
            # Load (and wait for it to complete!)
            was_insert = await self.load(item)
            
            if was_insert:
                self.stats["inserted"] += 1
            else:
                self.stats["updated"] += 1
                
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(f"Error processing item: {e}", exc_info=True)
    
    async def run(self, **kwargs) -> dict:
        """
        Execute the full ETL pipeline with proper async handling.
        
        Args:
            **kwargs: Passed to fetch_data()
            
        Returns:
            Statistics dict with counts and timing
        """
        self.logger.info(f"Starting {self.__class__.__name__}...")
        self.stats["started_at"] = datetime.utcnow()
        
        try:
            # Connect to database
            await self.connect()
            
            # Process each item from the data source
            # IMPORTANT: Await each process_item to ensure completion
            async for raw_item in self.fetch_data(**kwargs):
                await self.process_item(raw_item)
            
            # Give a moment for any pending operations to complete
            import asyncio
            await asyncio.sleep(0.1)
            
        except KeyboardInterrupt:
            self.logger.warning("Ingestion interrupted by user")
            raise
            
        except Exception as e:
            self.logger.error(f"Fatal error during ingestion: {e}")
            raise
            
        finally:
            # Record completion time
            self.stats["completed_at"] = datetime.utcnow()
            
            # Log final statistics
            duration = self.stats["completed_at"] - self.stats["started_at"]
            self.logger.info(
                f"Ingestion complete. "
                f"Processed: {self.stats['processed']}, "
                f"Inserted: {self.stats['inserted']}, "
                f"Updated: {self.stats['updated']}, "
                f"Errors: {self.stats['errors']}, "
                f"Duration: {duration}"
            )
            
            # Close connection (now safe - all operations completed)
            await self.disconnect()
        
        return self.stats
    
    def reset_stats(self):
        """Reset statistics counters"""
        self.stats = {
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "errors": 0,
            "started_at": None,
            "completed_at": None
        }
