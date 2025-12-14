"""
Application settings using Pydantic Settings.

Environment variables are loaded from .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    
    Create a .env file in the project root with these values.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ========================================================================
    # Database - Using your existing variable names
    # ========================================================================
    MONGODB_URI: str
    MONGODB_DATABASE: str
    
    # ========================================================================
    # External APIs
    # ========================================================================
    
    # Congress.gov API (get key at: https://api.congress.gov/sign-up/)
    CONGRESS_GOV_API_KEY: str
    
    # OpenAI (for embeddings and agent LLM) - OPTIONAL for now
    OPENAI_API_KEY: Optional[str] = None
    
    # FEC API (optional, for real-time campaign finance)
    FEC_API_KEY: Optional[str] = None
    
    # ProPublica Congress API (optional, being sunsetted)
    PROPUBLICA_API_KEY: Optional[str] = None
    
    # ========================================================================
    # Task Queue (Celery + Redis)
    # ========================================================================
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # ========================================================================
    # API Configuration
    # ========================================================================
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True  # Set to False in production
    
    # CORS Origins (comma-separated for multiple)
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8501"
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins into a list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # ========================================================================
    # Embeddings Configuration
    # ========================================================================
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    
    # LLM for agents
    AGENT_MODEL: str = "openai:gpt-4o"
    
    # ========================================================================
    # Logging
    # ========================================================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # ========================================================================
    # Application
    # ========================================================================
    APP_NAME: str = "Utah Watchdog"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # Environment (development, staging, production)
    ENVIRONMENT: str = "development"


# Singleton instance
settings = Settings()