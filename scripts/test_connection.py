"""
Test script to verify your .env configuration works.

Run this before doing the full sync to catch configuration issues early.

Usage:
    uv run python scripts/test_connection.py
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from src.config.settings import settings
import httpx


async def test_mongodb():
    """Test MongoDB connection"""
    print("🔍 Testing MongoDB connection...")
    print(f"   URI: {settings.MONGODB_URI}")
    print(f"   Database: {settings.MONGODB_DATABASE}")  # Changed from MONGO_DATABASE
    
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URI)
        db = client[settings.MONGODB_DATABASE]  # Changed from MONGO_DATABASE
        
        # Try to ping
        await client.admin.command('ping')
        
        # Check if politicians collection exists
        collections = await db.list_collection_names()
        
        print("   ✅ MongoDB connection successful!")
        print(f"   📊 Found {len(collections)} collections")
        
        if "politicians" in collections:
            count = await db.politicians.count_documents({})
            print(f"   👥 Politicians collection has {count} documents")
        else:
            print("   ℹ️  No 'politicians' collection yet (will be created on first sync)")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"   ❌ MongoDB connection failed: {e}")
        return False


async def test_congress_api():
    """Test Congress.gov API key"""
    print("\n🔍 Testing Congress.gov API key...")
    print(f"   Key: {settings.CONGRESS_GOV_API_KEY[:10]}...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test with a simple member query
            url = "https://api.congress.gov/v3/member"
            params = {
                "api_key": settings.CONGRESS_GOV_API_KEY,
                "limit": 1,
                "format": "json"
            }
            
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                print("   ✅ Congress.gov API key is valid!")
                print(f"   📊 API responded with member data")
                return True
            elif response.status_code == 401:
                print("   ❌ API key is invalid (401 Unauthorized)")
                return False
            elif response.status_code == 403:
                print("   ❌ API key lacks permissions (403 Forbidden)")
                return False
            else:
                print(f"   ⚠️  Unexpected response: {response.status_code}")
                return False
                
    except httpx.TimeoutException:
        print("   ❌ Request timed out - check your internet connection")
        return False
    except Exception as e:
        print(f"   ❌ API test failed: {e}")
        return False


async def test_openai():
    """Test OpenAI API key (optional check)"""
    print("\n🔍 Testing OpenAI API key...")
    
    if settings.OPENAI_API_KEY:
        print(f"   Key: {settings.OPENAI_API_KEY[:10]}...")
        
        try:
            # Just check if key is set - don't make actual API call
            if len(settings.OPENAI_API_KEY) > 20:
                print("   ✅ OpenAI API key is set (not validated)")
                return True
            else:
                print("   ⚠️  OpenAI API key seems too short")
                return False
        except Exception as e:
            print(f"   ⚠️  Could not check OpenAI key: {e}")
            return False
    else:
        print("   ℹ️  OpenAI API key not set (optional for member sync)")
        return True


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Utah Watchdog - Configuration Test")
    print("=" * 60)
    
    # Test each component
    mongo_ok = await test_mongodb()
    congress_ok = await test_congress_api()
    openai_ok = await test_openai()
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"MongoDB:       {'✅ PASS' if mongo_ok else '❌ FAIL'}")
    print(f"Congress.gov:  {'✅ PASS' if congress_ok else '❌ FAIL'}")
    print(f"OpenAI:        {'✅ PASS' if openai_ok else '⚠️  WARNING'}")
    
    if mongo_ok and congress_ok:
        print("\n🎉 All critical tests passed!")
        print("You're ready to run: uv run python scripts/sync_members.py")
        return 0
    else:
        print("\n❌ Some tests failed. Please check your .env file.")
        print("\nYour .env should have:")
        print("  MONGODB_URI=<your_connection_string>")
        print("  MONGODB_DATABASE=utah_watchdog")
        print("  CONGRESS_GOV_API_KEY=<your_api_key>")
        print("  OPENAI_API_KEY=<your_api_key> (optional)")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)