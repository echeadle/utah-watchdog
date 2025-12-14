"""
Politician Detail Page - full profile for a single legislator.
"""
import streamlit as st
from pymongo import MongoClient

from src.config.settings import settings


st.set_page_config(
    page_title="Politician Detail",
    page_icon="👤",
    layout="wide"
)


@st.cache_resource
def get_db():
    """Get MongoDB database connection"""
    client = MongoClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DATABASE]


def get_politician(bioguide_id: str):
    """Get politician by bioguide ID"""
    db = get_db()
    return db.politicians.find_one({"bioguide_id": bioguide_id})


def get_sponsored_bills(bioguide_id: str, limit: int = 20):
    """Get bills sponsored by this politician"""
    db = get_db()
    return list(db.legislation.find({"sponsor_bioguide_id": bioguide_id})
                .sort("introduced_date", -1)
                .limit(limit))


def main():
    st.title("👤 Politician Profile")
    
    # Check if politician is selected
    bioguide_id = st.query_params.get("id") or st.session_state.get("selected_politician")
    
    if not bioguide_id:
        st.warning("No politician selected")
        st.info("Go to the Search page to find a politician")
        
        # Show search link
        if st.button("🔍 Go to Search"):
            st.switch_page("pages/4_🔍_Search_Politicians.py")
        return
    
    # Fetch politician
    politician = get_politician(bioguide_id)
    
    if not politician:
        st.error(f"Politician not found: {bioguide_id}")
        return
    
    # ========================================================================
    # Header Section
    # ========================================================================
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header(politician['full_name'])
        
        # Basic info
        title = politician.get('title', 'N/A')
        party_full = {"R": "Republican", "D": "Democrat", "I": "Independent", "O": "Other"}.get(politician['party'], "Unknown")
        state = politician['state']
        
        district_str = f", District {politician.get('district')}" if politician.get('district') else ""
        
        st.subheader(f"{title} ({party_full} - {state}{district_str})")
        
        # Status
        if politician.get('in_office'):
            st.success("✅ Currently in office")
        else:
            st.warning("⚠️ No longer in office")
    
    with col2:
        # Contact info box
        st.markdown("### 📞 Contact")
        
        if politician.get('phone'):
            st.write(f"**Phone:** {politician['phone']}")
        
        if politician.get('office'):
            st.write(f"**Office:** {politician['office']}")
        
        if politician.get('website'):
            st.link_button("Official Website", politician['website'], use_container_width=True)
    
    st.divider()
    
    # ========================================================================
    # Tabs for different sections
    # ========================================================================
    
    #tab1, tab2, tab3 = st.tabs(["📊 Overview", "📜 Sponsored Bills", "🏛️ Committees"])
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📜 Sponsored Bills", "🏛️ Committees", "🗳️ Voting History"]) 
    with tab1:
        st.subheader("Overview")
        
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.markdown("#### Basic Information")
            st.write(f"**Bioguide ID:** {politician['bioguide_id']}")
            st.write(f"**Chamber:** {politician['chamber'].title()}")
            st.write(f"**Party:** {party_full}")
            st.write(f"**State:** {state}")
            if politician.get('district'):
                st.write(f"**District:** {politician['district']}")
        
        with info_col2:
            st.markdown("#### Status")
            st.write(f"**In Office:** {'Yes' if politician.get('in_office') else 'No'}")
            
            if politician.get('last_updated'):
                last_update = politician['last_updated']
                if hasattr(last_update, 'strftime'):
                    st.write(f"**Last Updated:** {last_update.strftime('%Y-%m-%d')}")
    
    with tab2:
        st.subheader("Sponsored Bills")
        
        bills = get_sponsored_bills(bioguide_id)
        
        if not bills:
            st.info("No sponsored bills found in database")
        else:
            st.write(f"**{len(bills)} most recent bills**")
            
            for bill in bills:
                bill_type = bill.get('bill_type', '').upper()
                number = bill.get('number')
                title = bill.get('title', 'No title')
                status = bill.get('status', '').replace('_', ' ').title()
                
                with st.container():
                    st.markdown(f"**{bill_type}. {number}** - {status}")
                    st.caption(title)
                    
                    if bill.get('congress_gov_url'):
                        st.link_button(
                            "View on Congress.gov",
                            bill['congress_gov_url'],
                            key=f"bill_{bill['bill_id']}"
                        )
                    
                    st.divider()
    
    with tab3:
        st.subheader("Committee Assignments")
        
        committees = politician.get('committees', [])
        
        if not committees:
            st.info("No committee assignments found")
            st.caption("Run: `uv run python scripts/sync_committees.py`")
        else:
            st.write(f"**{len(committees)} committee assignments**")
            
            for committee in committees:
                role = committee.get('role', 'Member')
                name = committee.get('name', 'Unknown Committee')
                chamber = committee.get('chamber', '').title()
                
                # Role badge
                role_emoji = "⭐" if role in ["Chair", "Ranking Member"] else "👤"
                
                st.markdown(f"{role_emoji} **{role}** - {name} ({chamber})")
                st.divider()

    with tab4:
        st.subheader("Voting History")
        
        # Get politician's votes
        db = get_db()
        politician_votes = list(db.politician_votes.find({"bioguide_id": bioguide_id})
                            .sort("vote_id", -1)
                            .limit(50))
        
        if not politician_votes:
            st.info("No voting records found in database")
            st.caption("Run: `uv run python scripts/sync_votes.py --chamber house --congress 118 --max 100`")
        else:
            st.write(f"**{len(politician_votes)} most recent votes**")
            
            # Group by position
            vote_summary = {}
            for pv in politician_votes:
                position = pv.get("position", "Unknown")
                vote_summary[position] = vote_summary.get(position, 0) + 1
            
            # Show summary
            summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
            
            with summary_col1:
                st.metric("✅ Aye", vote_summary.get("Aye", 0))
            with summary_col2:
                st.metric("❌ Nay", vote_summary.get("Nay", 0))
            with summary_col3:
                st.metric("⚪ Present", vote_summary.get("Present", 0))
            with summary_col4:
                st.metric("⏸️ Not Voting", vote_summary.get("Not Voting", 0))
            
            st.divider()
            
            # Show individual votes
            for pv in politician_votes:
                vote_id = pv["vote_id"]
                position = pv["position"]
                
                # Get vote details
                vote = db.votes.find_one({"vote_id": vote_id})
                
                if vote:
                    vote_emoji = {
                        "Aye": "✅",
                        "Nay": "❌",
                        "Present": "⚪",
                        "Not Voting": "⏸️"
                    }.get(position, "❓")
                    
                    col_a, col_b = st.columns([3, 1])
                    
                    with col_a:
                        question = vote.get("question", "Unknown")
                        roll_num = vote.get("roll_number")
                        
                        st.markdown(f"**Roll Call {roll_num}** - {question}")
                        
                        # Linked bill
                        bill_id = vote.get("bill_id")
                        if bill_id:
                            bill = db.legislation.find_one({"bill_id": bill_id})
                            if bill:
                                st.caption(bill.get("title", ""))
                    
                    with col_b:
                        st.markdown(f"### {vote_emoji} {position}")
                        
                        vote_date = vote.get("vote_date")
                        if vote_date and isinstance(vote_date, datetime):
                            st.caption(vote_date.strftime("%b %d, %Y"))
                    
                    st.divider()
if __name__ == "__main__":
    main()
