"""
Bills by Politician - see what each legislator is sponsoring.
"""
import streamlit as st
from pymongo import MongoClient

from src.config.settings import settings


st.set_page_config(
    page_title="Bills by Politician",
    page_icon="🔗",
    layout="wide"
)


@st.cache_resource
def get_db():
    """Get MongoDB database connection"""
    client = MongoClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DATABASE]


def get_all_politicians():
    """Get all politicians"""
    db = get_db()
    return list(db.politicians.find(
        {"in_office": True}
    ).sort([("state", 1), ("last_name", 1)]))


def get_bills_by_sponsor(bioguide_id: str):
    """Get bills sponsored by politician"""
    db = get_db()
    return list(db.legislation.find(
        {"sponsor_bioguide_id": bioguide_id}
    ).sort("introduced_date", -1))


def main():
    st.title("🔗 Bills by Politician")
    st.markdown("See what each legislator is sponsoring")
    
    # Get all politicians
    politicians = get_all_politicians()
    
    if not politicians:
        st.warning("No politicians in database")
        return
    
    # Create selection dropdown
    politician_options = {
        f"{p['full_name']} ({p['party']}-{p['state']})": p
        for p in politicians
    }
    
    selected_name = st.selectbox(
        "Select a legislator",
        options=list(politician_options.keys()),
        index=None,
        placeholder="Choose a politician..."
    )
    
    if not selected_name:
        st.info("👆 Select a politician to see their sponsored bills")
        return
    
    # Get selected politician
    politician = politician_options[selected_name]
    
    # Display politician info
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Name", politician['full_name'])
    with col2:
        st.metric("Party", politician['party'])
    with col3:
        st.metric("State", politician['state'])
    with col4:
        chamber = politician['chamber'].title()
        st.metric("Chamber", chamber)
    
    st.divider()
    
    # Get bills
    bills = get_bills_by_sponsor(politician['bioguide_id'])
    
    if not bills:
        st.info(f"No bills found sponsored by {politician['full_name']}")
        return
    
    st.subheader(f"Bills Sponsored ({len(bills)} total)")
    
    # Display bills
    for bill in bills:
        bill_type_upper = bill.get("bill_type", "").upper()
        number = bill.get("number", "?")
        congress = bill.get("congress", "?")
        title = bill.get("title", "No title")
        status = bill.get("status", "").replace("_", " ").title()
        
        with st.container():
            col_a, col_b = st.columns([3, 1])
            
            with col_a:
                st.markdown(f"**{bill_type_upper}. {number}** ({congress}th Congress)")
                st.caption(title)
            
            with col_b:
                st.caption(f"Status: {status}")
            
            if bill.get("congress_gov_url"):
                st.link_button("View on Congress.gov", bill["congress_gov_url"], use_container_width=True)
            
            st.divider()


if __name__ == "__main__":
    main()