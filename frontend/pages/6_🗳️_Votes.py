"""
Votes page - browse recent roll call votes.

Shows House votes with filters and links to details.
"""
import streamlit as st
from pymongo import MongoClient
from datetime import datetime

from src.config.settings import settings


st.set_page_config(
    page_title="Roll Call Votes",
    page_icon="🗳️",
    layout="wide"
)


@st.cache_resource
def get_db():
    """Get MongoDB database connection"""
    client = MongoClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DATABASE]


def get_recent_votes(limit: int = 50, result_filter: str = None):
    """Get recent votes with optional filters"""
    db = get_db()
    
    filter_dict = {}
    
    if result_filter and result_filter != "All":
        filter_dict["result"] = result_filter
    
    votes = list(db.votes.find(filter_dict)
                 .sort("vote_date", -1)
                 .limit(limit))
    
    return votes


def get_vote_stats():
    """Get vote statistics"""
    db = get_db()
    
    total = db.votes.count_documents({})
    passed = db.votes.count_documents({"result": "Passed"})
    failed = db.votes.count_documents({"result": "Failed"})
    
    return {
        "total": total,
        "passed": passed,
        "failed": failed
    }


def get_bill_title(bill_id: str):
    """Get bill title for display"""
    if not bill_id:
        return None
    
    db = get_db()
    bill = db.legislation.find_one({"bill_id": bill_id}, {"title": 1})
    
    if bill:
        title = bill.get("title", "")
        return title[:100] + "..." if len(title) > 100 else title
    
    return None


def display_vote_card(vote: dict):
    """Display a vote as a card"""
    
    # Vote result styling
    result = vote.get("result", "Unknown")
    result_color = "🟢" if result == "Passed" else "🔴" if result == "Failed" else "⚪"
    
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Vote identifier
            roll_num = vote.get("roll_number", "?")
            congress = vote.get("congress", "?")
            chamber = vote.get("chamber", "").title()
            
            st.markdown(f"### {result_color} {chamber} Roll Call #{roll_num} ({congress}th Congress)")
            
            # Vote question
            question = vote.get("question", "Unknown question")
            st.markdown(f"**{question}**")
            
            # Associated bill
            bill_id = vote.get("bill_id")
            if bill_id:
                bill_title = get_bill_title(bill_id)
                if bill_title:
                    st.caption(f"📜 Bill: {bill_title}")
                else:
                    st.caption(f"📜 Bill: {bill_id.upper()}")
        
        with col2:
            # Vote result
            st.metric("Result", result)
            
            # Date
            vote_date = vote.get("vote_date")
            if vote_date:
                if isinstance(vote_date, datetime):
                    date_str = vote_date.strftime("%b %d, %Y")
                else:
                    date_str = str(vote_date)
                st.caption(f"📅 {date_str}")
        
        # Vote counts
        col_a, col_b, col_c, col_d = st.columns(4)
        
        with col_a:
            st.metric("Yea", vote.get("yea_count", 0))
        with col_b:
            st.metric("Nay", vote.get("nay_count", 0))
        with col_c:
            st.metric("Present", vote.get("present_count", 0))
        with col_d:
            st.metric("Not Voting", vote.get("not_voting_count", 0))
        
        # View details button
        if st.button("👁️ View Vote Details", key=f"view_{vote['vote_id']}"):
            st.session_state['selected_vote'] = vote['vote_id']
            st.switch_page("pages/7_📊_Vote_Detail.py")
        
        st.divider()


def main():
    st.title("🗳️ Roll Call Votes")
    st.markdown("Browse recent votes in the House of Representatives")
    
    # Get stats
    stats = get_vote_stats()
    
    if stats["total"] == 0:
        st.warning("⚠️ No votes in database yet.")
        st.info("Run the sync script: `uv run python scripts/sync_votes.py --chamber house --max 100`")
        return
    
    # Sidebar stats
    with st.sidebar:
        st.markdown("## 📊 Statistics")
        st.metric("Total Votes", stats["total"])
        st.metric("Passed", stats["passed"])
        st.metric("Failed", stats["failed"])
        
        st.markdown("### ℹ️ Note")
        st.caption("Currently showing House votes only. Senate votes will be added when the API becomes available.")
    
    # Filters
    st.subheader("Filters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        result_filter = st.selectbox(
            "Result",
            ["All", "Passed", "Failed", "Agreed to"],
            index=0
        )
    
    with col2:
        limit = st.number_input(
            "Number of votes",
            min_value=10,
            max_value=500,
            value=50,
            step=10
        )
    
    st.divider()
    
    # Fetch votes
    with st.spinner("Loading votes..."):
        votes = get_recent_votes(
            limit=limit,
            result_filter=result_filter if result_filter != "All" else None
        )
    
    if not votes:
        st.info("No votes match your filters.")
        return
    
    st.subheader(f"Recent Votes ({len(votes)} shown)")
    
    # Display votes
    for vote in votes:
        display_vote_card(vote)


if __name__ == "__main__":
    main()