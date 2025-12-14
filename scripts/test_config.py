"""
Test script to verify configuration is working.

Run with: uv run python scripts/test_config.py
"""

from src.config import settings, UTAH_DELEGATION, CURRENT_CONGRESS


def main():
    print("=" * 50)
    print("Configuration Test")
    print("=" * 50)
    
    # Check MongoDB URI (hide most of it for security)
    uri = settings.MONGODB_URI
    if uri:
        # Show just the beginning to confirm it loaded
        visible_part = uri[:30] + "..." if len(uri) > 30 else uri
        print(f"✅ MONGODB_URI loaded: {visible_part}")
    else:
        print("❌ MONGODB_URI not found!")
    
    # Check database name
    print(f"✅ Database name: {settings.MONGODB_DATABASE}")
    
    # Check Congress.gov API key (just confirm it exists)
    if settings.CONGRESS_GOV_API_KEY:
        key_preview = settings.CONGRESS_GOV_API_KEY[:8] + "..."
        print(f"✅ CONGRESS_GOV_API_KEY loaded: {key_preview}")
    else:
        print("❌ CONGRESS_GOV_API_KEY not found!")
    
    # Show Utah delegation
    print(f"\n📍 Current Congress: {CURRENT_CONGRESS}th")
    print(f"\n👥 Utah's Federal Delegation ({len(UTAH_DELEGATION)} members):")
    for member in UTAH_DELEGATION:
        district = f" (District {member['district']})" if 'district' in member else " (Senator)"
        print(f"   - {member['name']}{district}")
    
    print("\n" + "=" * 50)
    print("✅ Configuration loaded successfully!")
    print("=" * 50)


if __name__ == "__main__":
    main()