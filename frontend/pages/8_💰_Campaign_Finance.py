"""
Campaign Finance page - track political contributions.

Shows campaign contributions, top donors, and allows searching by employer/state.
Enhanced with charts and visualizations.
"""
import streamlit as st
from pymongo import MongoClient
from datetime import datetime
from decimal import Decimal
from collections import defaultdict
import pandas as pd
import plotly.express as px

from src.config.settings import settings


# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="Campaign Finance",
    page_icon="💰",
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
# Data Fetching Functions
# ============================================================================

def get_politicians_with_contributions():
    """Get list of politicians who have contribution data"""
    db = get_db()
    
    # Find politicians with contributions (using bioguide_id field)
    politicians_with_data = db.contributions.distinct("bioguide_id")
    
    # Filter out None values
    politicians_with_data = [p for p in politicians_with_data if p is not None]
    
    if not politicians_with_data:
        return []
    
    # Get their full info
    politicians = list(db.politicians.find(
        {"bioguide_id": {"$in": politicians_with_data}},
        {"full_name": 1, "bioguide_id": 1, "party": 1, "state": 1}
    ).sort("last_name", 1))
    
    return politicians


def get_contribution_summary(bioguide_id: str):
    """Get total contributions summary for a politician"""
    db = get_db()
    
    pipeline = [
        {"$match": {"bioguide_id": bioguide_id}},
        {
            "$group": {
                "_id": None,
                "total_raised": {"$sum": "$amount"},
                "num_contributions": {"$sum": 1},
                "avg_contribution": {"$avg": "$amount"}
            }
        }
    ]
    
    result = list(db.contributions.aggregate(pipeline))
    
    if result:
        return {
            "total_raised": float(result[0]["total_raised"]),
            "num_contributions": result[0]["num_contributions"],
            "avg_contribution": float(result[0]["avg_contribution"])
        }
    
    return {
        "total_raised": 0.0,
        "num_contributions": 0,
        "avg_contribution": 0.0
    }


def get_top_donors(bioguide_id: str, limit: int = 10):
    """Get top individual contributors"""
    db = get_db()
    
    pipeline = [
        {"$match": {"bioguide_id": bioguide_id}},
        {
            "$group": {
                "_id": {
                    "name": "$contributor_name",
                    "employer": "$contributor_employer",
                    "city": "$contributor_city",
                    "state": "$contributor_state"
                },
                "total_amount": {"$sum": "$amount"},
                "num_contributions": {"$sum": 1}
            }
        },
        {"$sort": {"total_amount": -1}},
        {"$limit": limit}
    ]
    
    results = list(db.contributions.aggregate(pipeline))
    
    return [
        {
            "name": r["_id"]["name"],
            "employer": r["_id"]["employer"] or "Not provided",
            "city": r["_id"]["city"] or "",
            "state": r["_id"]["state"] or "",
            "total_amount": float(r["total_amount"]),
            "num_contributions": r["num_contributions"]
        }
        for r in results
    ]


def get_top_employers(bioguide_id: str, limit: int = 10):
    """Get top employers/organizations by total contributions"""
    db = get_db()
    
    pipeline = [
        {"$match": {
            "bioguide_id": bioguide_id,
            "contributor_employer": {"$ne": None, "$ne": ""}
        }},
        {
            "$group": {
                "_id": "$contributor_employer",
                "total_amount": {"$sum": "$amount"},
                "num_contributors": {"$sum": 1}
            }
        },
        {"$sort": {"total_amount": -1}},
        {"$limit": limit}
    ]
    
    results = list(db.contributions.aggregate(pipeline))
    
    return [
        {
            "employer": r["_id"],
            "total_amount": float(r["total_amount"]),
            "num_contributors": r["num_contributors"]
        }
        for r in results
    ]


def get_contributions_by_state(bioguide_id: str):
    """Get contributions grouped by state"""
    db = get_db()
    
    pipeline = [
        {"$match": {
            "bioguide_id": bioguide_id,
            "contributor_state": {"$ne": None, "$ne": ""}
        }},
        {
            "$group": {
                "_id": "$contributor_state",
                "total_amount": {"$sum": "$amount"},
                "num_contributions": {"$sum": 1}
            }
        },
        {"$sort": {"total_amount": -1}},
        {"$limit": 15}
    ]
    
    results = list(db.contributions.aggregate(pipeline))
    
    return [
        {
            "state": r["_id"],
            "total_amount": float(r["total_amount"]),
            "num_contributions": r["num_contributions"]
        }
        for r in results
    ]


def get_recent_contributions(bioguide_id: str, limit: int = 20):
    """Get recent individual contributions"""
    db = get_db()
    
    contributions = list(db.contributions.find(
        {"bioguide_id": bioguide_id}
    ).sort("contribution_date", -1).limit(limit))
    
    return contributions


def search_contributions(
    bioguide_id: str = None,
    employer: str = None,
    state: str = None,
    min_amount: float = None,
    max_amount: float = None,
    limit: int = 50
):
    """Search contributions by various criteria"""
    db = get_db()
    
    filter_dict = {}
    
    if bioguide_id:
        filter_dict["bioguide_id"] = bioguide_id
    
    if employer:
        filter_dict["contributor_employer"] = {"$regex": employer, "$options": "i"}
    
    if state:
        filter_dict["contributor_state"] = state
    
    if min_amount is not None or max_amount is not None:
        filter_dict["amount"] = {}
        if min_amount is not None:
            filter_dict["amount"]["$gte"] = float(min_amount)
        if max_amount is not None:
            filter_dict["amount"]["$lte"] = float(max_amount)
    
    results = list(db.contributions.find(filter_dict)
                   .sort("amount", -1)
                   .limit(limit))
    
    return results


def get_contributions_timeline(bioguide_id: str):
    """Get contributions over time for trend visualization"""
    db = get_db()

    pipeline = [
        {"$match": {
            "bioguide_id": bioguide_id,
            "contribution_date": {"$ne": None}
        }},
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m",
                        "date": "$contribution_date"
                    }
                },
                "total_amount": {"$sum": "$amount"},
                "num_contributions": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]

    results = list(db.contributions.aggregate(pipeline))

    return [
        {
            "month": r["_id"],
            "total_amount": float(r["total_amount"]),
            "num_contributions": r["num_contributions"]
        }
        for r in results
    ]


def get_overall_stats():
    """Get overall contribution statistics"""
    db = get_db()

    total_contributions = db.contributions.count_documents({})

    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_raised": {"$sum": "$amount"},
                "avg_contribution": {"$avg": "$amount"}
            }
        }
    ]

    result = list(db.contributions.aggregate(pipeline))

    if result:
        return {
            "total_contributions": total_contributions,
            "total_raised": float(result[0]["total_raised"]),
            "avg_contribution": float(result[0]["avg_contribution"])
        }

    return {
        "total_contributions": 0,
        "total_raised": 0.0,
        "avg_contribution": 0.0
    }


# ============================================================================
# Display Functions
# ============================================================================

def display_contribution_summary(politician: dict, summary: dict):
    """Display contribution summary metrics"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Raised",
            f"${summary['total_raised']:,.2f}",
            help="Total amount raised from all contributions"
        )
    
    with col2:
        st.metric(
            "Contributions",
            f"{summary['num_contributions']:,}",
            help="Number of individual contributions"
        )
    
    with col3:
        st.metric(
            "Average Amount",
            f"${summary['avg_contribution']:,.2f}",
            help="Average contribution amount"
        )


def display_contribution_timeline(timeline: list):
    """Display contribution timeline chart"""
    if not timeline or len(timeline) < 2:
        st.info("Not enough data for timeline visualization")
        return

    st.markdown("### 📈 Contribution Timeline")
    st.caption("Contributions over time")

    df = pd.DataFrame(timeline)

    # Create dual-axis chart
    fig = px.line(
        df,
        x='month',
        y='total_amount',
        title='Contributions Over Time',
        labels={'month': 'Month', 'total_amount': 'Total Amount ($)'},
        markers=True
    )
    fig.update_layout(height=400)
    fig.update_traces(line_color='#1f77b4', line_width=3)
    st.plotly_chart(fig, use_container_width=True)

    # Add count chart
    fig2 = px.bar(
        df,
        x='month',
        y='num_contributions',
        title='Number of Contributions Over Time',
        labels={'month': 'Month', 'num_contributions': 'Number of Contributions'},
        color='num_contributions',
        color_continuous_scale='Purples'
    )
    fig2.update_layout(height=300, showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)


def display_top_donors_table(donors: list):
    """Display top donors with visualization and table"""
    if not donors:
        st.info("No donor data available")
        return

    st.markdown("### 💳 Top Individual Donors")
    st.caption("Individuals who have contributed the most")

    # Add bar chart for top 10 donors
    if len(donors) >= 3:
        df = pd.DataFrame(donors[:10])
        fig = px.bar(
            df,
            x='total_amount',
            y='name',
            orientation='h',
            title='Top 10 Individual Donors',
            labels={'total_amount': 'Total Amount ($)', 'name': 'Donor'},
            color='total_amount',
            color_continuous_scale='Reds',
            hover_data=['employer', 'num_contributions']
        )
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Detailed Breakdown")

    for i, donor in enumerate(donors, 1):
        col1, col2, col3 = st.columns([4, 2, 1])

        with col1:
            st.markdown(f"**{i}. {donor['name']}**")
            st.caption(f"Employer: {donor['employer']}")
            if donor['city'] and donor['state']:
                st.caption(f"📍 {donor['city']}, {donor['state']}")

        with col2:
            st.metric("Total Given", f"${donor['total_amount']:,.2f}")

        with col3:
            st.metric("Times", donor['num_contributions'])

        st.divider()


def display_top_employers_table(employers: list):
    """Display top employers in a table with chart"""
    if not employers:
        st.info("No employer data available")
        return
    
    st.markdown("### 🏢 Top Contributing Employers")
    st.caption("Employers whose employees contribute the most")
    
    # Create bar chart
    if len(employers) >= 3:
        df = pd.DataFrame(employers)
        fig = px.bar(
            df,
            x='total_amount',
            y='employer',
            orientation='h',
            title='Top 10 Employers by Total Contributions',
            labels={'total_amount': 'Total Amount ($)', 'employer': 'Employer'},
            color='total_amount',
            color_continuous_scale='Blues'
        )
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    # Display table
    for i, employer in enumerate(employers, 1):
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            st.markdown(f"**{i}. {employer['employer']}**")
        
        with col2:
            st.metric("Total", f"${employer['total_amount']:,.2f}")
        
        with col3:
            st.metric("Contributors", employer['num_contributors'])
        
        st.divider()


def display_state_breakdown(states: list):
    """Display contributions by state with map visualization"""
    if not states:
        st.info("No state data available")
        return
    
    st.markdown("### 🗺️ Contributions by State")
    st.caption("Where contributions are coming from")
    
    # Create horizontal bar chart
    if len(states) >= 3:
        df = pd.DataFrame(states)
        fig = px.bar(
            df,
            x='total_amount',
            y='state',
            orientation='h',
            title='Top States by Total Contributions',
            labels={'total_amount': 'Total Amount ($)', 'state': 'State'},
            color='total_amount',
            color_continuous_scale='Greens'
        )
        fig.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    # Display table
    st.markdown("#### State Breakdown")
    for i, state_data in enumerate(states, 1):
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            st.markdown(f"**{i}. {state_data['state']}**")
        
        with col2:
            st.metric("Amount", f"${state_data['total_amount']:,.2f}")
        
        with col3:
            st.metric("Contributions", state_data['num_contributions'])
        
        st.divider()


def display_recent_contributions(contributions: list):
    """Display recent contributions"""
    if not contributions:
        st.info("No recent contributions")
        return
    
    st.markdown("### ⏱️ Recent Contributions")
    st.caption("Most recent individual contributions")
    
    for contrib in contributions:
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            name = contrib.get("contributor_name", "Unknown")
            st.markdown(f"**{name}**")
            
            employer = contrib.get("contributor_employer", "Not provided")
            st.caption(f"Employer: {employer}")
        
        with col2:
            amount = float(contrib.get("amount", 0))
            st.metric("Amount", f"${amount:,.2f}")
        
        with col3:
            contrib_date = contrib.get("contribution_date")
            if contrib_date:
                if isinstance(contrib_date, datetime):
                    st.caption(contrib_date.strftime("%b %d, %Y"))
                else:
                    st.caption(str(contrib_date))
        
        st.divider()


# ============================================================================
# Main Page
# ============================================================================

def main():
    st.title("💰 Campaign Finance")
    st.markdown("Track political contributions and follow the money")
    
    # Get overall stats
    stats = get_overall_stats()
    
    if stats["total_contributions"] == 0:
        st.warning("⚠️ No contribution data in database yet.")
        st.info("""
        **To populate contribution data:**
        
        1. Make sure politicians have FEC IDs:
           ```bash
           uv run python scripts/maintenance/populate_fec_ids.py
           ```
        
        2. Sync contributions:
           ```bash
           uv run python scripts/pipelines/sync_fec_contributions.py --cycle 2024
           ```
        """)
        return
    
    # Display overall stats in sidebar
    with st.sidebar:
        st.markdown("## 📊 Overall Statistics")
        st.metric("Total Contributions", f"{stats['total_contributions']:,}")
        st.metric("Total Raised", f"${stats['total_raised']:,.2f}")
        st.metric("Average Amount", f"${stats['avg_contribution']:,.2f}")
        
        st.divider()
        
        st.markdown("## ℹ️ Data Source")
        st.caption("Campaign finance data from FEC filings")
        st.caption("Data may be incomplete or delayed")
        
        st.divider()
        
        st.markdown("## 💡 Tip")
        st.caption("Use the search feature at the bottom to find contributions by employer, state, or amount range")
    
    # ========================================================================
    # Politician Selector
    # ========================================================================
    
    st.subheader("Select a Politician")
    
    politicians = get_politicians_with_contributions()
    
    if not politicians:
        st.error("No politicians with contribution data found")
        st.info("Run `populate_fec_ids.py` and `sync_fec_contributions.py` to add data")
        return
    
    # Create dropdown options
    politician_options = {
        f"{p['full_name']} ({p['party']}-{p['state']})": p
        for p in politicians
    }
    
    selected_name = st.selectbox(
        "Choose a legislator to view their campaign contributions",
        options=list(politician_options.keys()),
        index=0
    )
    
    if not selected_name:
        st.info("👆 Select a politician to view their contributions")
        return
    
    politician = politician_options[selected_name]
    bioguide_id = politician["bioguide_id"]
    
    # Fetch full politician details from database
    db = get_db()
    full_politician = db.politicians.find_one({"bioguide_id": bioguide_id})
    
    if full_politician:
        politician = full_politician
    
    st.divider()
    
    # ========================================================================
    # Politician Summary
    # ========================================================================
    
    st.header(f"💰 {politician.get('full_name', 'Unknown')}")
    
    # Get party and state
    party = politician.get('party', '?')
    state = politician.get('state', '??')
    chamber = politician.get('chamber', '').title()
    
    st.caption(f"{chamber} • {party}-{state}")
    
    # Get contribution summary
    summary = get_contribution_summary(bioguide_id)
    
    display_contribution_summary(politician, summary)
    
    st.divider()
    
    # ========================================================================
    # Tabs for Different Views
    # ========================================================================

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Timeline",
        "💳 Top Donors",
        "🏢 Top Employers",
        "🗺️ By State",
        "⏱️ Recent Contributions"
    ])

    with tab1:
        timeline = get_contributions_timeline(bioguide_id)
        display_contribution_timeline(timeline)

    with tab2:
        top_donors = get_top_donors(bioguide_id, limit=15)
        display_top_donors_table(top_donors)

    with tab3:
        top_employers = get_top_employers(bioguide_id, limit=10)
        display_top_employers_table(top_employers)

    with tab4:
        by_state = get_contributions_by_state(bioguide_id)
        display_state_breakdown(by_state)

    with tab5:
        recent = get_recent_contributions(bioguide_id, limit=25)
        display_recent_contributions(recent)
    
    # ========================================================================
    # Search Section
    # ========================================================================
    
    st.divider()
    st.header("🔍 Search All Contributions")
    st.markdown("Search across all contributions in the database")
    
    search_col1, search_col2 = st.columns(2)
    
    with search_col1:
        employer_search = st.text_input(
            "Employer/Organization",
            placeholder="e.g., Google, Applied Materials",
            help="Case-insensitive partial match"
        )
    
    with search_col2:
        state_search = st.selectbox(
            "State",
            ["All States"] + [
                "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
                "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
                "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
                "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
                "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
            ]
        )
    
    amount_col1, amount_col2 = st.columns(2)
    
    with amount_col1:
        min_amount = st.number_input(
            "Minimum Amount ($)",
            min_value=0.0,
            value=0.0,
            step=100.0
        )
    
    with amount_col2:
        max_amount = st.number_input(
            "Maximum Amount ($)",
            min_value=0.0,
            value=10000.0,
            step=100.0
        )
    
    if st.button("🔍 Search", type="primary"):
        with st.spinner("Searching contributions..."):
            search_results = search_contributions(
                employer=employer_search if employer_search else None,
                state=state_search if state_search != "All States" else None,
                min_amount=min_amount if min_amount > 0 else None,
                max_amount=max_amount if max_amount < 10000 else None,
                limit=100
            )
        
        if not search_results:
            st.warning("No contributions found matching your criteria")
        else:
            st.success(f"Found {len(search_results)} contributions")
            
            # Display results
            for contrib in search_results:
                # Get politician name
                pol_bioguide = contrib.get("bioguide_id")
                pol = None
                if pol_bioguide:
                    pol = db.politicians.find_one(
                        {"bioguide_id": pol_bioguide},
                        {"full_name": 1, "party": 1, "state": 1}
                    )
                
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    name = contrib.get("contributor_name", "Unknown")
                    employer = contrib.get("contributor_employer", "Not provided")
                    
                    st.markdown(f"**{name}**")
                    st.caption(f"Employer: {employer}")
                    
                    if pol:
                        st.caption(f"→ To: {pol.get('full_name', 'Unknown')} ({pol.get('party', '?')}-{pol.get('state', '?')})")
                
                with col2:
                    amount = float(contrib.get("amount", 0))
                    st.metric("Amount", f"${amount:,.2f}")
                
                with col3:
                    state_code = contrib.get("contributor_state", "")
                    if state_code:
                        st.write(f"📍 {state_code}")
                    
                    date = contrib.get("contribution_date")
                    if date and isinstance(date, datetime):
                        st.caption(date.strftime("%b %d, %Y"))
                
                st.divider()


# ============================================================================
# Run
# ============================================================================

if __name__ == "__main__":
    main()