"""
Politician Search - find any legislator by name, state, party, or chamber.
"""
import streamlit as st
from pymongo import MongoClient
import re

from src.config.settings import settings


st.set_page_config(
    page_title="Search Politicians",
    page_icon="🔍",
    layout="wide"
)


@st.cache_resource
def get_db():
    """Get MongoDB database connection"""
    client = MongoClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DATABASE]


def search_politicians(
    query: str = None,
    state: str = None,
    party: str = None,
    chamber: str = None,
    in_office: bool = True
):
    """Search politicians with multiple filters"""
    db = get_db()

    filter_dict = {}

    # Name search (flexible - searches first name, last name, and full name)
    if query:
        # Split query into words for more flexible matching
        words = query.strip().split()
        if len(words) == 1:
            # Single word - search in any name field
            filter_dict["$or"] = [
                {"first_name": {"$regex": query, "$options": "i"}},
                {"last_name": {"$regex": query, "$options": "i"}},
                {"full_name": {"$regex": query, "$options": "i"}}
            ]
        else:
            # Multiple words - create pattern that matches all words in any order
            # This allows "John Curtis" to match "John R. Curtis"
            word_patterns = [{"full_name": {"$regex": re.escape(word), "$options": "i"}} for word in words]
            filter_dict["$and"] = word_patterns

    if state and state != "All States":
        filter_dict["state"] = state

    if party and party != "All Parties":
        filter_dict["party"] = party

    if chamber and chamber != "All Chambers":
        filter_dict["chamber"] = chamber.lower().replace(" ", "_")

    if in_office is not None:
        filter_dict["in_office"] = in_office

    results = list(db.politicians.find(filter_dict)
                   .sort([("state", 1), ("last_name", 1)])
                   .limit(200))

    return results


def main():
    st.title("🔍 Search Politicians")
    st.markdown("Find any federal legislator")
    
    # Search inputs
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_query = st.text_input(
            "Search by name",
            placeholder="e.g., Mike Lee, Smith, John",
            help="Case-insensitive partial match"
        )
    
    with col2:
        show_former = st.checkbox("Include former members", value=False)
    
    # Filters
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        state_filter = st.selectbox(
            "State",
            ["All States"] + [
                "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
                "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
                "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
                "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
                "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
            ]
        )
    
    with filter_col2:
        party_filter = st.selectbox(
            "Party",
            ["All Parties", "R", "D", "I"]
        )
    
    with filter_col3:
        chamber_filter = st.selectbox(
            "Chamber",
            ["All Chambers", "Senate", "House"]
        )
    
    # Search button
    if st.button("🔍 Search", type="primary") or search_query:
        
        with st.spinner("Searching..."):
            results = search_politicians(
                query=search_query if search_query else None,
                state=state_filter,
                party=party_filter,
                chamber=chamber_filter,
                in_office=not show_former
            )
        
        if not results:
            st.warning("No politicians found matching your criteria.")
            return
        
        st.success(f"Found {len(results)} politicians")
        
        # Display results
        for politician in results:
            col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 1])
            
            with col_a:
                # Make name clickable to detail page
                name = politician['full_name']
                bioguide = politician['bioguide_id']
                st.markdown(f"**{name}**")
                
                # Additional info
                title = politician.get('title', 'N/A')
                district = f", District {politician.get('district')}" if politician.get('district') else ""
                st.caption(f"{title}{district}")
            
            with col_b:
                party_emoji = {"R": "🔴", "D": "🔵", "I": "🟣"}.get(politician['party'], "⚪")
                st.write(f"{party_emoji} {politician['party']}")
            
            with col_c:
                st.write(politician['state'])
            
            with col_d:
                chamber = politician['chamber'].title()
                st.write(chamber)
            
            # View detail button
            if st.button(f"View Profile", key=f"view_{bioguide}"):
                st.session_state['selected_politician'] = bioguide
                st.switch_page("pages/5_👤_Politician_Detail.py")
            
            st.divider()
    
    else:
        st.info("👆 Enter search criteria and click Search")


if __name__ == "__main__":
    main()