"""
Legislation page - displays bills and resolutions.

Shows federal legislation with filters and search.
"""
import streamlit as st
from pymongo import MongoClient
from datetime import datetime

from src.config.settings import settings


# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="Legislation",
    page_icon="📜",
    layout="wide"
)


# ============================================================================
# Database Connection
# ============================================================================

@st.cache_resource
def get_db():
    """Get MongoDB database connection"""
    client = MongoClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DATABASE]


# ============================================================================
# Data Fetching
# ============================================================================

def get_recent_bills(limit: int = 50, status: str = None, sponsor_id: str = None):
    """Get recent bills with optional filters"""
    db = get_db()
    
    # Build filter
    filter_dict = {}
    
    if status and status != "All":
        filter_dict["status"] = status.lower().replace(" ", "_")
    
    if sponsor_id:
        filter_dict["sponsor_bioguide_id"] = sponsor_id
    
    bills = list(db.legislation.find(filter_dict)
                 .sort("introduced_date", -1)
                 .limit(limit))
    
    return bills


def get_bill_by_id(bill_id: str):
    """Get a specific bill"""
    db = get_db()
    return db.legislation.find_one({"bill_id": bill_id})


def get_politician_by_bioguide(bioguide_id: str):
    """Get politician details"""
    db = get_db()
    return db.politicians.find_one({"bioguide_id": bioguide_id})


def get_bills_by_sponsor(bioguide_id: str, limit: int = 20):
    """Get bills sponsored by a specific politician"""
    db = get_db()
    return list(db.legislation.find({"sponsor_bioguide_id": bioguide_id})
                .sort("introduced_date", -1)
                .limit(limit))


def get_bill_stats():
    """Get statistics about bills in database"""
    db = get_db()
    
    total = db.legislation.count_documents({})
    by_status = {}
    
    for status in ["introduced", "in_committee", "passed_house", "passed_senate", "became_law"]:
        count = db.legislation.count_documents({"status": status})
        if count > 0:
            by_status[status] = count
    
    return {
        "total": total,
        "by_status": by_status
    }


# ============================================================================
# UI Components
# ============================================================================

def display_bill_card(bill: dict, show_sponsor: bool = True):
    """Display a bill as a card"""
    
    # Bill type badge color
    bill_type_colors = {
        "hr": "🔵",
        "s": "🟢",
        "hres": "🔷",
        "sres": "🟩",
        "hjres": "🔶",
        "sjres": "🟧"
    }
    bill_type_emoji = bill_type_colors.get(bill.get("bill_type", ""), "⚪")
    
    # Status badge
    status_display = bill.get("status", "").replace("_", " ").title()
    
    with st.container():
        col1, col2 = st.columns([4, 1])
        
        with col1:
            # Bill number and title
            bill_type_upper = bill.get("bill_type", "").upper()
            number = bill.get("number", "?")
            congress = bill.get("congress", "?")
            
            st.markdown(f"### {bill_type_emoji} {bill_type_upper}. {number} ({congress}th Congress)")
            
            # Title
            title = bill.get("title", "No title")
            if len(title) > 150:
                title = title[:150] + "..."
            st.markdown(f"**{title}**")
            
            # Sponsor
            if show_sponsor:
                sponsor_id = bill.get("sponsor_bioguide_id")
                if sponsor_id:
                    sponsor = get_politician_by_bioguide(sponsor_id)
                    if sponsor:
                        st.caption(f"👤 Sponsor: {sponsor.get('full_name', 'Unknown')} ({sponsor.get('party', '?')}-{sponsor.get('state', '?')})")
        
        with col2:
            # Status
            st.metric("Status", status_display)
            
            # Date
            intro_date = bill.get("introduced_date")
            if intro_date:
                if isinstance(intro_date, datetime):
                    date_str = intro_date.strftime("%b %d, %Y")
                else:
                    date_str = str(intro_date)
                st.caption(f"📅 {date_str}")
        
        # Expandable details
        with st.expander("View Details"):
            detail_col1, detail_col2 = st.columns(2)
            
            with detail_col1:
                st.write("**Bill ID:**", bill.get("bill_id", "N/A"))
                st.write("**Policy Area:**", bill.get("policy_area", "Not specified"))
                
                # Subjects
                subjects = bill.get("subjects", [])
                if subjects:
                    st.write("**Topics:**", ", ".join(subjects[:5]))
            
            with detail_col2:
                st.write("**Latest Action:**")
                latest_action = bill.get("latest_action_text", "No recent action")
                if len(latest_action) > 100:
                    latest_action = latest_action[:100] + "..."
                st.caption(latest_action)
                
                # Links
                if bill.get("congress_gov_url"):
                    st.link_button("View on Congress.gov", bill["congress_gov_url"], use_container_width=True)
            
            # Summary if available
            summary = bill.get("summary")
            if summary:
                st.write("**Summary:**")
                if len(summary) > 500:
                    summary = summary[:500] + "..."
                st.caption(summary)
        
        st.divider()


# ============================================================================
# Main Page
# ============================================================================

def main():
    st.title("📜 Federal Legislation")
    st.markdown("Track bills and resolutions in Congress")
    
    # Get stats
    stats = get_bill_stats()
    
    if stats["total"] == 0:
        st.warning("⚠️ No bills in database yet.")
        st.info("Run the sync script: `uv run python scripts/sync_bills.py --max 100`")
        return
    
    # Show stats in sidebar
    with st.sidebar:
        st.markdown("## 📊 Statistics")
        st.metric("Total Bills", stats["total"])
        
        if stats["by_status"]:
            st.markdown("### By Status")
            for status, count in stats["by_status"].items():
                status_display = status.replace("_", " ").title()
                st.metric(status_display, count)
    
    # ========================================================================
    # Filters
    # ========================================================================
    
    st.subheader("Filters")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Status",
            ["All", "Introduced", "In Committee", "Passed House", "Passed Senate", "Became Law"],
            index=0
        )
    
    with col2:
        # Get list of sponsors for filter
        db = get_db()
        utah_sponsors = list(db.politicians.find(
            {"state": "UT", "in_office": True},
            {"bioguide_id": 1, "full_name": 1}
        ))
        
        sponsor_options = ["All Sponsors"] + [f"{s['full_name']} ({s['bioguide_id']})" for s in utah_sponsors]
        sponsor_filter = st.selectbox("Utah Sponsor", sponsor_options, index=0)
    
    with col3:
        limit = st.number_input("Number of bills", min_value=10, max_value=500, value=50, step=10)
    
    # Parse sponsor filter
    sponsor_id = None
    if sponsor_filter != "All Sponsors":
        # Extract bioguide_id from "Name (ID)" format
        sponsor_id = sponsor_filter.split("(")[-1].rstrip(")")
    
    # ========================================================================
    # Bill List
    # ========================================================================
    
    st.divider()
    
    # Fetch bills
    with st.spinner("Loading bills..."):
        bills = get_recent_bills(
            limit=limit,
            status=status_filter if status_filter != "All" else None,
            sponsor_id=sponsor_id
        )
    
    if not bills:
        st.info("No bills match your filters.")
        return
    
    st.subheader(f"Recent Bills ({len(bills)} shown)")
    
    # Display bills
    for bill in bills:
        display_bill_card(bill, show_sponsor=True)


# ============================================================================
# Run
# ============================================================================

if __name__ == "__main__":
    main()