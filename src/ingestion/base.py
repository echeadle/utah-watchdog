"""
Base ingester class for all data pipelines.

Provides common ETL (Extract, Transform, Load) patterns and error handling.
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, TypeVar, Generic, Any
from datetime import datetime
import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.config.settings import settings

T = TypeVar('T')


class BaseIngester(ABC, Generic[T]):
    """
    Abstract base class for all data ingesters.
    
    Implements the ETL pattern:
    1. Fetch - Get data from external source
    2. Transform - Convert to our data models
    3. Load - Save to MongoDB
    
    All ingester implementations should inherit from this class.
    """
    
    def __init__(self):
        """Initialize the ingester with empty state"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.db: AsyncIOMotorDatabase | None = None
        self.client: AsyncIOMotorClient | None = None
        
        # Statistics tracking
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
        
        This should be implemented as an async generator that yields
        raw data records one at a time.
        
        Args:
            **kwargs: Implementation-specific parameters
            
        Yields:
            Raw data records (usually dicts from APIs or files)
        """
        pass
    
    @abstractmethod
    async def transform(self, raw_data: dict) -> T:
        """
        Transform raw data to our data model.
        
        Args:
            raw_data: Raw record from external source
            
        Returns:
            Pydantic model instance
            
        Raises:
            ValueError: If data is invalid or missing required fields
        """
        pass
    
    @abstractmethod
    async def load(self, item: T) -> bool:
        """
        Load item into database.
        
        Should handle upsert logic to make ingestion idempotent.
        
        Args:
            item: Pydantic model instance to save
            
        Returns:
            True if this was a new insert, False if update
            
        Raises:
            Exception: If database operation fails
        """
        pass
    
    async def process_item(self, raw_data: dict) -> bool:
        """
        Process a single item through the ETL pipeline.
        
        Args:
            raw_data: Raw data record
            
        Returns:
            True if item was processed successfully
        """
        try:
            self.stats["processed"] += 1
            
            # Transform
            item = await self.transform(raw_data)
            
            # Load
            was_insert = await self.load(item)
            
            if was_insert:
                self.stats["inserted"] += 1
            else:
                self.stats["updated"] += 1
            
            # Log progress every 50 items
            if self.stats["processed"] % 50 == 0:
                self.logger.info(
                    f"Progress: {self.stats['processed']} processed, "
                    f"{self.stats['inserted']} inserted, "
                    f"{self.stats['updated']} updated"
                )
            
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error(f"Error processing item: {e}")
            self.logger.debug(f"Raw data: {raw_data}")
            return False
    
    async def run(self, **kwargs) -> dict:
        """
        Execute the full ETL pipeline.
        
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
            async for raw_item in self.fetch_data(**kwargs):
                await self.process_item(raw_item)
            
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
            
            # Close connection
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