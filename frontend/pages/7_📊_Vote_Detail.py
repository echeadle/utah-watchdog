"""
Vote Detail Page - detailed view of a single roll call vote.

Shows vote results, member positions, and associated bill.
"""
import streamlit as st
from pymongo import MongoClient
from datetime import datetime

from src.config.settings import settings


st.set_page_config(
    page_title="Vote Detail",
    page_icon="📊",
    layout="wide"
)


@st.cache_resource
def get_db():
    """Get MongoDB database connection"""
    client = MongoClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DATABASE]


def get_vote(vote_id: str):
    """Get vote by ID"""
    db = get_db()
    return db.votes.find_one({"vote_id": vote_id})


def get_member_votes(vote_id: str):
    """Get how each member voted"""
    db = get_db()
    
    # Get member votes
    member_votes = list(db.politician_votes.find({"vote_id": vote_id}))
    
    # Enrich with politician details
    enriched = []
    for mv in member_votes:
        politician = db.politicians.find_one(
            {"bioguide_id": mv["bioguide_id"]},
            {"full_name": 1, "party": 1, "state": 1, "district": 1}
        )
        
        if politician:
            enriched.append({
                **mv,
                "full_name": politician.get("full_name", "Unknown"),
                "party": politician.get("party", "?"),
                "state": politician.get("state", "?"),
                "district": politician.get("district")
            })
    
    return enriched


def get_utah_votes(vote_id: str):
    """Get how Utah delegation voted"""
    db = get_db()
    
    utah_members = list(db.politician_votes.aggregate([
        {"$match": {"vote_id": vote_id}},
        {
            "$lookup": {
                "from": "politicians",
                "localField": "bioguide_id",
                "foreignField": "bioguide_id",
                "as": "politician"
            }
        },
        {"$unwind": "$politician"},
        {"$match": {"politician.state": "UT"}},
        {
            "$project": {
                "bioguide_id": 1,
                "position": 1,
                "full_name": "$politician.full_name",
                "party": "$politician.party",
                "district": "$politician.district"
            }
        }
    ]))
    
    return utah_members


def get_bill(bill_id: str):
    """Get associated bill"""
    if not bill_id:
        return None
    
    db = get_db()
    return db.legislation.find_one({"bill_id": bill_id})


def main():
    st.title("📊 Vote Detail")
    
    # Get vote ID from session state or query params
    vote_id = st.query_params.get("id") or st.session_state.get("selected_vote")
    
    if not vote_id:
        st.warning("No vote selected")
        st.info("Go to the Votes page to select a vote")
        
        if st.button("🗳️ Go to Votes"):
            st.switch_page("pages/6_🗳️_Votes.py")
        return
    
    # Fetch vote
    vote = get_vote(vote_id)
    
    if not vote:
        st.error(f"Vote not found: {vote_id}")
        return
    
    # ========================================================================
    # Header
    # ========================================================================
    
    roll_num = vote.get("roll_number")
    congress = vote.get("congress")
    chamber = vote.get("chamber", "").title()
    result = vote.get("result", "Unknown")
    
    result_emoji = "✅" if result == "Passed" else "❌" if result == "Failed" else "⚪"
    
    st.header(f"{chamber} Roll Call #{roll_num}")
    st.subheader(f"{congress}th Congress")
    
    # Result badge
    if result == "Passed":
        st.success(f"{result_emoji} {result}")
    elif result == "Failed":
        st.error(f"{result_emoji} {result}")
    else:
        st.info(f"{result_emoji} {result}")
    
    st.divider()
    
    # ========================================================================
    # Vote Details
    # ========================================================================
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Vote Question")
        question = vote.get("question", "Unknown")
        st.markdown(f"**{question}**")
        
        # Associated bill
        bill_id = vote.get("bill_id")
        if bill_id:
            bill = get_bill(bill_id)
            if bill:
                st.markdown("### Associated Bill")
                st.markdown(f"**{bill_id.upper()}**: {bill.get('title', 'No title')}")
                
                if bill.get("congress_gov_url"):
                    st.link_button("View Bill on Congress.gov", bill["congress_gov_url"])
    
    with col2:
        st.markdown("### Vote Date")
        vote_date = vote.get("vote_date")
        if vote_date:
            if isinstance(vote_date, datetime):
                st.write(vote_date.strftime("%B %d, %Y"))
                st.caption(vote_date.strftime("%I:%M %p"))
            else:
                st.write(str(vote_date))
        
        st.markdown("### Totals")
        st.metric("Yea", vote.get("yea_count", 0))
        st.metric("Nay", vote.get("nay_count", 0))
        st.metric("Present", vote.get("present_count", 0))
        st.metric("Not Voting", vote.get("not_voting_count", 0))
    
    st.divider()
    
    # ========================================================================
    # Tabs for different views
    # ========================================================================
    
    tab1, tab2, tab3 = st.tabs([
        "🗳️ All Member Votes",
        "🏔️ Utah Delegation",
        "📊 By Party"
    ])
    
    with tab1:
        st.subheader("How Members Voted")
        
        # Get all member votes
        member_votes = get_member_votes(vote_id)
        
        if not member_votes:
            st.info("No member vote data available")
        else:
            # Filters
            filter_col1, filter_col2, filter_col3 = st.columns(3)
            
            with filter_col1:
                position_filter = st.selectbox(
                    "Position",
                    ["All", "Aye", "Nay", "Present", "Not Voting"],
                    key="position_filter"
                )
            
            with filter_col2:
                party_filter = st.selectbox(
                    "Party",
                    ["All", "R", "D", "I"],
                    key="party_filter"
                )
            
            with filter_col3:
                search = st.text_input("Search name", key="name_search")
            
            # Apply filters
            filtered_votes = member_votes
            
            if position_filter != "All":
                filtered_votes = [v for v in filtered_votes if v["position"] == position_filter]
            
            if party_filter != "All":
                filtered_votes = [v for v in filtered_votes if v["party"] == party_filter]
            
            if search:
                filtered_votes = [v for v in filtered_votes 
                                if search.lower() in v["full_name"].lower()]
            
            st.write(f"Showing {len(filtered_votes)} of {len(member_votes)} members")
            
            # Display as table
            for vote_item in sorted(filtered_votes, key=lambda x: x["full_name"]):
                col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 1])
                
                with col_a:
                    name = vote_item["full_name"]
                    district = f" (District {vote_item['district']})" if vote_item.get("district") else ""
                    st.write(f"**{name}**{district}")
                
                with col_b:
                    party_emoji = {"R": "🔴", "D": "🔵", "I": "🟣"}.get(vote_item["party"], "⚪")
                    st.write(f"{party_emoji} {vote_item['party']}")
                
                with col_c:
                    st.write(vote_item["state"])
                
                with col_d:
                    position = vote_item["position"]
                    if position == "Aye":
                        st.success(position)
                    elif position == "Nay":
                        st.error(position)
                    else:
                        st.info(position)
    
    with tab2:
        st.subheader("Utah Delegation Votes")
        
        utah_votes = get_utah_votes(vote_id)
        
        if not utah_votes:
            st.info("No Utah votes recorded for this roll call")
        else:
            for utah_vote in sorted(utah_votes, key=lambda x: x["full_name"]):
                col_a, col_b, col_c = st.columns([3, 1, 1])
                
                with col_a:
                    name = utah_vote["full_name"]
                    district = f" (District {utah_vote.get('district')})" if utah_vote.get("district") else ""
                    st.write(f"**{name}**{district}")
                
                with col_b:
                    party_emoji = {"R": "🔴", "D": "🔵"}.get(utah_vote["party"], "⚪")
                    st.write(f"{party_emoji} {utah_vote['party']}")
                
                with col_c:
                    position = utah_vote["position"]
                    if position == "Aye":
                        st.success(position)
                    elif position == "Nay":
                        st.error(position)
                    else:
                        st.info(position)
                
                st.divider()
    
    with tab3:
        st.subheader("Vote Breakdown by Party")
        
        member_votes = get_member_votes(vote_id)
        
        if member_votes:
            # Count by party and position
            party_breakdown = {}
            
            for mv in member_votes:
                party = mv.get("party", "Other")
                position = mv.get("position", "Unknown")
                
                if party not in party_breakdown:
                    party_breakdown[party] = {"Aye": 0, "Nay": 0, "Present": 0, "Not Voting": 0}
                
                if position in party_breakdown[party]:
                    party_breakdown[party][position] += 1
            
            # Display party breakdown
            for party in ["R", "D", "I"]:
                if party in party_breakdown:
                    party_name = {"R": "Republican", "D": "Democrat", "I": "Independent"}.get(party, party)
                    
                    st.markdown(f"### {party_name}")
                    
                    breakdown = party_breakdown[party]
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Aye", breakdown["Aye"])
                    col2.metric("Nay", breakdown["Nay"])
                    col3.metric("Present", breakdown["Present"])
                    col4.metric("Not Voting", breakdown["Not Voting"])
                    
                    st.divider()


if __name__ == "__main__":
    main()