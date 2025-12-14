"""
Utah Watchdog - Main Streamlit Application

Track Utah and Federal legislators - votes, money, and legislation.
"""
import streamlit as st
from pymongo import MongoClient
from datetime import datetime

from src.config.settings import settings


# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="Utah Watchdog",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================================
# Database Connection (cached, synchronous)
# ============================================================================

@st.cache_resource
def get_db():
    """Get MongoDB database connection (cached for performance)"""
    client = MongoClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DATABASE]


# ============================================================================
# Data Fetching Functions (now synchronous)
# ============================================================================

def get_utah_delegation():
    """Get Utah's current federal delegation (Senators + Representatives)"""
    db = get_db()
    
    members = list(db.politicians.find(
        {
            "state": "UT",
            "in_office": True
        }
    ).sort([
        ("chamber", 1),     # Senate first
        ("district", 1)     # Then House by district
    ]).limit(10))
    
    return members


def get_politician_count():
    """Get total count of politicians in database"""
    db = get_db()
    
    total = db.politicians.count_documents({"in_office": True})
    federal = db.politicians.count_documents({
        "in_office": True,
        "state": {"$exists": True}
    })
    utah_count = db.politicians.count_documents({
        "state": "UT",
        "in_office": True
    })
    
    return {
        "total": total,
        "federal": federal,
        "utah": utah_count
    }


def get_last_sync_time():
    """Get when politician data was last updated"""
    db = get_db()
    
    latest = db.politicians.find_one(
        {},
        sort=[("last_updated", -1)]
    )
    
    if latest and "last_updated" in latest:
        return latest["last_updated"]
    return None


# ============================================================================
# UI Components
# ============================================================================

def display_politician_card(politician: dict):
    """Display a politician in a card format"""
    
    # Chamber emoji
    if politician["chamber"] == "senate":
        emoji = "🏛️"
        position = "U.S. Senator"
    else:
        emoji = "🏢"
        district = politician.get("district", "?")
        position = f"U.S. Representative, District {district}"
    
    # Party color
    party_colors = {
        "R": "🔴",
        "D": "🔵",
        "I": "🟣",
        "O": "⚪"
    }
    party_emoji = party_colors.get(politician["party"], "⚪")
    
    # Create card
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f"### {emoji} {politician['full_name']}")
            st.caption(position)
        
        with col2:
            st.metric("Party", f"{party_emoji} {politician['party']}")
        
        with col3:
            if politician.get("website"):
                st.link_button("Website", politician["website"], use_container_width=True)
        
        # Expandable details
        with st.expander("More Information"):
            details_col1, details_col2 = st.columns(2)
            
            with details_col1:
                st.write("**Bioguide ID:**", politician.get("bioguide_id", "N/A"))
                st.write("**Chamber:**", politician["chamber"].title())
                st.write("**State:**", politician["state"])
            
            with details_col2:
                st.write("**Office:**", politician.get("office", "N/A"))
                st.write("**Phone:**", politician.get("phone", "N/A"))
                if politician.get("last_updated"):
                    st.write("**Last Updated:**", politician["last_updated"].strftime("%Y-%m-%d"))
        
        st.divider()


# ============================================================================
# Main Application
# ============================================================================

def main():
    """Main application"""
    
    # Header
    st.title("🏛️ Utah Government Watchdog")
    st.markdown("**Track what your legislators are doing** - votes, campaign finance, and legislation")
    
    # Show last sync time
    last_sync = get_last_sync_time()
    if last_sync:
        if isinstance(last_sync, datetime):
            sync_str = last_sync.strftime("%B %d, %Y at %I:%M %p")
        else:
            sync_str = str(last_sync)
        st.caption(f"📅 Data last updated: {sync_str}")
    
    st.divider()
    
    # ========================================================================
    # Main Content - Utah Delegation
    # ========================================================================
    
    st.header("Utah's Congressional Delegation")
    st.markdown("Current members representing Utah in the U.S. Congress")
    
    # Fetch delegation
    with st.spinner("Loading Utah's delegation from database..."):
        try:
            members = get_utah_delegation()
        except Exception as e:
            st.error(f"Error loading data: {e}")
            st.info("💡 Make sure you've run: `uv run python scripts/sync_members.py`")
            return
    
    if not members:
        st.warning("⚠️ No members found in database.")
        st.info("Run the sync script to populate data: `uv run python scripts/sync_members.py`")
        return
    
    # Separate by chamber
    senators = [m for m in members if m["chamber"] == "senate"]
    representatives = [m for m in members if m["chamber"] == "house"]
    
    # Display Senators
    if senators:
        st.subheader("🏛️ U.S. Senators")
        for senator in senators:
            display_politician_card(senator)
    
    # Display Representatives
    if representatives:
        st.subheader("🏢 U.S. Representatives")
        for rep in sorted(representatives, key=lambda x: x.get("district") or 0):
            display_politician_card(rep)
    
    # ========================================================================
    # Footer with Stats
    # ========================================================================
    
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    
    try:
        counts = get_politician_count()
        
        with col1:
            st.metric("Total Officials in DB", counts["total"])
        
        with col2:
            st.metric("Federal Officials", counts["federal"])
        
        with col3:
            st.metric("Utah Delegation", counts["utah"])
    
    except Exception as e:
        st.caption(f"Could not load statistics: {e}")


# ============================================================================
# Sidebar
# ============================================================================

with st.sidebar:
    st.markdown("## 📊 Navigation")
    
    st.markdown("### Current Features")
    st.markdown("✅ **Politicians** - View current legislators")
    
    st.markdown("### Coming Soon")
    st.markdown("⏳ Legislation tracking")
    st.markdown("⏳ Campaign finance data")
    st.markdown("⏳ Voting records")
    st.markdown("⏳ AI-powered research")
    
    st.divider()
    
    st.markdown("## 🔄 Data Updates")
    st.markdown("Data syncs automatically daily at 5 AM UTC")
    
    if st.button("📖 How to Manual Sync"):
        st.code("uv run python scripts/sync_members.py", language="bash")
    
    st.divider()
    
    st.markdown("## ℹ️ About")
    st.markdown("Track Utah and Federal legislators using AI agents and official government data sources.")
    
    st.caption("Built with Streamlit + MongoDB + Congress.gov API")


# ============================================================================
# Run Application
# ============================================================================

if __name__ == "__main__":
    main()