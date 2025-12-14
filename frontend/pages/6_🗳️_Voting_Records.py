"""
Voting Records - see how politicians voted on bills.
"""
import streamlit as st
from pymongo import MongoClient
from datetime import datetime

from src.config.settings import settings


st.set_page_config(
    page_title="Voting Records",
    page_icon="🗳️",
    layout="wide"
)


@st.cache_resource
def get_db():
    """Get MongoDB database connection"""
    client = MongoClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DATABASE]


def get_recent_votes(limit: int = 50):
    """Get recent votes"""
    db = get_db()
    return list(db.votes.find()
                .sort("vote_date", -1)
                .limit(limit))


def get_vote_by_id(vote_id: str):
    """Get a specific vote"""
    db = get_db()
    return db.votes.find_one({"vote_id": vote_id})


def get_politician_votes_for_vote(vote_id: str):
    """Get how each politician voted"""
    db = get_db()
    return list(db.politician_votes.find({"vote_id": vote_id}))


def get_politician_by_bioguide(bioguide_id: str):
    """Get politician details"""
    db = get_db()
    return db.politicians.find_one({"bioguide_id": bioguide_id})


def get_bill_by_id(bill_id: str):
    """Get bill details"""
    db = get_db()
    return db.legislation.find_one({"bill_id": bill_id})


def get_utah_votes_on_vote(vote_id: str):
    """Get how Utah delegation voted"""
    db = get_db()
    
    # Get all politician votes for this vote
    all_votes = list(db.politician_votes.find({"vote_id": vote_id}))
    
    # Filter for Utah politicians
    utah_votes = []
    for pv in all_votes:
        pol = db.politicians.find_one({"bioguide_id": pv["bioguide_id"]})
        if pol and pol.get("state") == "UT":
            utah_votes.append({
                "politician": pol,
                "position": pv["position"]
            })
    
    return utah_votes


def main():
    st.title("🗳️ Voting Records")
    st.markdown("See how representatives voted on legislation")
    
    # Check if we have votes
    db = get_db()
    vote_count = db.votes.count_documents({})
    
    if vote_count == 0:
        st.warning("⚠️ No votes in database yet.")
        st.info("Run: `uv run python scripts/sync_votes.py --chamber house --congress 118 --max 100`")
        return
    
    st.success(f"📊 {vote_count} votes in database")
    
    # ========================================================================
    # Recent Votes
    # ========================================================================
    
    st.subheader("Recent House Votes")
    
    limit = st.slider("Number of votes to show", 10, 100, 50, 10)
    
    votes = get_recent_votes(limit=limit)
    
    for vote in votes:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                # Vote question
                question = vote.get("question", "Unknown")
                roll_num = vote.get("roll_number")
                congress = vote.get("congress")
                
                st.markdown(f"**Roll Call {roll_num}** (Congress {congress})")
                st.caption(question)
                
                # Linked bill
                bill_id = vote.get("bill_id")
                if bill_id:
                    bill = get_bill_by_id(bill_id)
                    if bill:
                        bill_title = bill.get("title", "")
                        if len(bill_title) > 100:
                            bill_title = bill_title[:100] + "..."
                        st.caption(f"📜 {bill_title}")
            
            with col2:
                # Result
                result = vote.get("result", "Unknown")
                if result.lower() in ["passed", "agreed to"]:
                    st.success(result)
                else:
                    st.error(result)
                
                # Date
                vote_date = vote.get("vote_date")
                if vote_date:
                    if isinstance(vote_date, datetime):
                        date_str = vote_date.strftime("%b %d, %Y")
                    else:
                        date_str = str(vote_date)
                    st.caption(date_str)
            
            with col3:
                # Vote counts
                yea = vote.get("yea_count", 0)
                nay = vote.get("nay_count", 0)
                st.metric("Yea-Nay", f"{yea}-{nay}")
            
            # Expandable details
            with st.expander("View Voting Details"):
                detail_col1, detail_col2 = st.columns([2, 1])
                
                with detail_col1:
                    st.write("**Vote Breakdown:**")
                    st.write(f"✅ Yea: {vote.get('yea_count', 0)}")
                    st.write(f"❌ Nay: {vote.get('nay_count', 0)}")
                    st.write(f"⚪ Present: {vote.get('present_count', 0)}")
                    st.write(f"⏸️ Not Voting: {vote.get('not_voting_count', 0)}")
                
                with detail_col2:
                    # Show how Utah voted
                    st.write("**🏔️ Utah Delegation:**")
                    utah_votes = get_utah_votes_on_vote(vote["vote_id"])
                    
                    if utah_votes:
                        for uv in utah_votes:
                            name = uv["politician"]["full_name"]
                            position = uv["position"]
                            
                            # Emoji for vote
                            vote_emoji = {
                                "Aye": "✅",
                                "Nay": "❌",
                                "Present": "⚪",
                                "Not Voting": "⏸️"
                            }.get(position, "❓")
                            
                            st.caption(f"{vote_emoji} {name}: {position}")
                    else:
                        st.caption("No Utah votes found")
                
                # Link to Congress.gov
                if vote.get("congress_gov_url"):
                    st.link_button("View on Congress.gov", vote["congress_gov_url"])
            
            st.divider()


if __name__ == "__main__":
    main()
