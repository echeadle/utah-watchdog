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

@st.cache_data(ttl=3600)  # Cache for 1 hour
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


@st.cache_data(ttl=3600)  # Cache for 1 hour
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


@st.cache_data(ttl=3600)  # Cache for 1 hour
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


@st.cache_data(ttl=3600)  # Cache for 1 hour
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


@st.cache_data(ttl=3600)  # Cache for 1 hour
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


@st.cache_data(ttl=1800)  # Cache for 30 min (recent changes more often)
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
    start_date = None,
    end_date = None,
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

    if start_date is not None or end_date is not None:
        filter_dict["contribution_date"] = {}
        if start_date is not None:
            # Convert date to datetime for MongoDB comparison
            filter_dict["contribution_date"]["$gte"] = datetime.combine(start_date, datetime.min.time())
        if end_date is not None:
            # Convert date to datetime for MongoDB comparison
            filter_dict["contribution_date"]["$lte"] = datetime.combine(end_date, datetime.max.time())

    results = list(db.contributions.find(filter_dict)
                   .sort("amount", -1)
                   .limit(limit))

    return results


@st.cache_data(ttl=3600)  # Cache for 1 hour
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


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_contribution_source_breakdown(bioguide_id: str):
    """Get breakdown of contributions by source type (Individual vs PAC)"""
    db = get_db()

    pipeline = [
        {"$match": {"bioguide_id": bioguide_id}},
        {
            "$group": {
                "_id": "$contributor_type",
                "count": {"$sum": 1},
                "total_amount": {"$sum": "$amount"}
            }
        },
        {"$sort": {"total_amount": -1}}
    ]

    results = list(db.contributions.aggregate(pipeline))

    breakdown = []
    for result in results:
        source_type = result["_id"] or "Unknown"
        breakdown.append({
            "type": source_type,
            "count": result["count"],
            "total": float(result["total_amount"])
        })

    return breakdown


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_contribution_size_distribution(bioguide_id: str):
    """Get contribution distribution by size brackets"""
    db = get_db()

    # Define contribution size brackets
    brackets = [
        {"name": "$1 - $100", "min": 1, "max": 100},
        {"name": "$101 - $500", "min": 101, "max": 500},
        {"name": "$501 - $1,000", "min": 501, "max": 1000},
        {"name": "$1,001 - $2,000", "min": 1001, "max": 2000},
        {"name": "$2,001 - $2,900", "min": 2001, "max": 2900},
        {"name": "$2,901+", "min": 2901, "max": float('inf')}
    ]

    distribution = []

    for bracket in brackets:
        query = {
            "bioguide_id": bioguide_id,
            "amount": {
                "$gte": bracket["min"],
                "$lte": bracket["max"] if bracket["max"] != float('inf') else 999999
            }
        }

        count = db.contributions.count_documents(query)

        # Calculate total amount in this bracket
        pipeline = [
            {"$match": query},
            {"$group": {
                "_id": None,
                "total": {"$sum": "$amount"}
            }}
        ]

        result = list(db.contributions.aggregate(pipeline))
        total_amount = float(result[0]["total"]) if result else 0.0

        distribution.append({
            "bracket": bracket["name"],
            "count": count,
            "total": total_amount
        })

    return distribution


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_overall_stats():
    """Get overall contribution statistics"""
    db = get_db()

    total_contributions = db.contributions.count_documents({})

    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_raised": {"$sum": "$amount"},
                "avg_contribution": {"$avg": "$amount"},
                "latest_update": {"$max": "$last_updated"},
                "earliest_contrib": {"$min": "$contribution_date"},
                "latest_contrib": {"$max": "$contribution_date"}
            }
        }
    ]

    result = list(db.contributions.aggregate(pipeline))

    # Get most common cycle
    cycle_pipeline = [
        {"$group": {"_id": "$cycle", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 1}
    ]
    cycle_result = list(db.contributions.aggregate(cycle_pipeline))

    if result:
        return {
            "total_contributions": total_contributions,
            "total_raised": float(result[0]["total_raised"]),
            "avg_contribution": float(result[0]["avg_contribution"]),
            "last_updated": result[0].get("latest_update"),
            "earliest_contribution": result[0].get("earliest_contrib"),
            "latest_contribution": result[0].get("latest_contrib"),
            "primary_cycle": cycle_result[0]["_id"] if cycle_result else "Unknown"
        }

    return {
        "total_contributions": 0,
        "total_raised": 0.0,
        "avg_contribution": 0.0,
        "last_updated": None,
        "earliest_contribution": None,
        "latest_contribution": None,
        "primary_cycle": "Unknown"
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

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 💳 Top Individual Donors")
        st.caption("Individuals who have contributed the most")
    with col2:
        # CSV Export button
        if donors:
            df_export = pd.DataFrame(donors)
            csv = df_export.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name="top_donors.csv",
                mime="text/csv",
                use_container_width=True
            )

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

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 🏢 Top Contributing Employers")
        st.caption("Employers whose employees contribute the most")
    with col2:
        # CSV Export button
        if employers:
            df_export = pd.DataFrame(employers)
            csv = df_export.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name="top_employers.csv",
                mime="text/csv",
                use_container_width=True
            )
    
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

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 🗺️ Contributions by State")
        st.caption("Where contributions are coming from")
    with col2:
        # CSV Export button
        if states:
            df_export = pd.DataFrame(states)
            csv = df_export.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name="contributions_by_state.csv",
                mime="text/csv",
                use_container_width=True
            )

    # Interactive US Map
    if len(states) >= 1:
        df = pd.DataFrame(states)

        # Create choropleth map
        fig_map = px.choropleth(
            df,
            locations='state',
            locationmode='USA-states',
            color='total_amount',
            scope='usa',
            title='Geographic Distribution of Contributions',
            labels={'total_amount': 'Total Amount ($)', 'state': 'State'},
            color_continuous_scale='Blues',
            hover_data={
                'state': True,
                'total_amount': ':$,.2f',
                'num_contributions': True
            }
        )

        fig_map.update_layout(
            geo=dict(
                showlakes=True,
                lakecolor='rgb(255, 255, 255)',
            ),
            height=500
        )

        st.plotly_chart(fig_map, use_container_width=True)

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


def display_contribution_source_breakdown(breakdown: list, bioguide_id: str = None):
    """Display contribution source breakdown with drill-down capability"""
    if not breakdown:
        st.info("No contribution source data available")
        return

    st.markdown("### 🏛️ Contribution Source Breakdown")
    st.caption("Individual donors vs PACs and organizations")

    # Create DataFrame
    df = pd.DataFrame(breakdown)

    if df.empty:
        st.info("No contribution source data")
        return

    # Calculate totals and percentages
    total_count = df['count'].sum()
    total_amount = df['total'].sum()

    df['pct_count'] = (df['count'] / total_count * 100).round(1)
    df['pct_amount'] = (df['total'] / total_amount * 100).round(1)

    # Create two columns for visualizations
    col1, col2 = st.columns(2)

    with col1:
        # Pie chart by count
        fig_count = px.pie(
            df,
            values='count',
            names='type',
            title='Contributions by Source Type',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_count.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_count, use_container_width=True)

    with col2:
        # Pie chart by amount
        fig_amount = px.pie(
            df,
            values='total',
            names='type',
            title='Total Amount by Source Type',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_amount.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_amount, use_container_width=True)

    # Summary table
    st.markdown("#### Detailed Breakdown")

    display_df = pd.DataFrame({
        'Source Type': df['type'],
        'Count': df['count'],
        '% of Contributions': df['pct_count'].apply(lambda x: f"{x}%"),
        'Total Amount': df['total'].apply(lambda x: f"${x:,.2f}"),
        '% of Total Raised': df['pct_amount'].apply(lambda x: f"{x}%")
    })

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Drill-down section for each contributor type
    st.markdown("#### 🔍 Drill Down by Source Type")
    st.caption("Explore sample contributions from each source type")

    for _, row in df.iterrows():
        contrib_type = row['type']
        count = int(row['count'])
        total = row['total']

        with st.expander(f"**{contrib_type}** - {count:,} contributions (${total:,.2f})"):
            # Fetch sample contributions of this type
            if bioguide_id:
                db = get_db()
                sample_contribs = list(db.contributions.find({
                    "bioguide_id": bioguide_id,
                    "contributor_type": contrib_type
                }).sort("amount", -1).limit(10))

                if sample_contribs:
                    st.caption(f"Top 10 contributions (out of {count:,} total)")

                    # Display samples in a table format
                    for i, contrib in enumerate(sample_contribs, 1):
                        col1, col2, col3 = st.columns([3, 2, 1])

                        with col1:
                            name = contrib.get("contributor_name", "Unknown")
                            st.markdown(f"**{i}. {name}**")
                            employer = contrib.get("contributor_employer", "Not provided")
                            if employer and employer != "Not provided":
                                st.caption(f"Employer: {employer}")

                        with col2:
                            city = contrib.get("contributor_city", "")
                            state = contrib.get("contributor_state", "")
                            location = f"{city}, {state}" if city and state else (state or city or "Unknown")
                            st.caption(f"📍 {location}")

                        with col3:
                            amount = float(contrib.get("amount", 0))
                            st.metric("", f"${amount:,.2f}")

                        st.divider()
                else:
                    st.info("No contributions found for this type")

    # Key insights
    if len(df) > 0:
        st.markdown("#### 💡 Key Insights")

        # Show breakdown for all types
        col1, col2 = st.columns(2)

        with col1:
            # Find individual contributions
            individual_row = df[df['type'].str.lower().str.contains('individual', na=False)]
            if not individual_row.empty:
                ind_pct = individual_row['pct_amount'].iloc[0]
                ind_count = int(individual_row['count'].iloc[0])
                st.success(f"**Individual Donors:** {ind_pct}% of total (${individual_row['total'].iloc[0]:,.2f} from {ind_count:,} contributions)")

        with col2:
            # Find other/PAC contributions
            pac_rows = df[~df['type'].str.lower().str.contains('individual', na=False)]
            if not pac_rows.empty:
                pac_total_pct = pac_rows['pct_amount'].sum()
                pac_total_amount = pac_rows['total'].sum()
                pac_total_count = int(pac_rows['count'].sum())
                st.info(f"**PACs & Organizations:** {pac_total_pct:.1f}% of total (${pac_total_amount:,.2f} from {pac_total_count:,} contributions)")


def display_contribution_size_distribution(distribution: list):
    """Display contribution size distribution with charts"""
    if not distribution:
        st.info("No contribution distribution data available")
        return

    st.markdown("### 📊 Contribution Size Distribution")
    st.caption("Breakdown by contribution amount brackets")

    # Create DataFrame for easier manipulation
    df = pd.DataFrame(distribution)

    # Filter out empty brackets
    df_filtered = df[df['count'] > 0]

    if df_filtered.empty:
        st.info("No contributions in any size bracket")
        return

    # Create two columns for the charts
    col1, col2 = st.columns(2)

    with col1:
        # Bar chart by count
        fig_count = px.bar(
            df_filtered,
            x='bracket',
            y='count',
            title='Number of Contributions by Size',
            labels={'bracket': 'Contribution Size', 'count': 'Number of Contributions'},
            color='count',
            color_continuous_scale='Blues'
        )
        fig_count.update_layout(
            xaxis_tickangle=-45,
            showlegend=False,
            height=400
        )
        st.plotly_chart(fig_count, use_container_width=True)

    with col2:
        # Bar chart by total amount
        fig_amount = px.bar(
            df_filtered,
            x='bracket',
            y='total',
            title='Total Amount Raised by Size',
            labels={'bracket': 'Contribution Size', 'total': 'Total Amount ($)'},
            color='total',
            color_continuous_scale='Greens'
        )
        fig_amount.update_layout(
            xaxis_tickangle=-45,
            showlegend=False,
            height=400
        )
        st.plotly_chart(fig_amount, use_container_width=True)

    # Summary table
    st.markdown("#### Detailed Breakdown")

    # Calculate percentages
    total_count = df_filtered['count'].sum()
    total_amount = df_filtered['total'].sum()

    df_filtered['pct_count'] = (df_filtered['count'] / total_count * 100).round(1)
    df_filtered['pct_amount'] = (df_filtered['total'] / total_amount * 100).round(1)

    # Format for display
    display_df = pd.DataFrame({
        'Size Bracket': df_filtered['bracket'],
        'Count': df_filtered['count'],
        '% of Contributions': df_filtered['pct_count'].apply(lambda x: f"{x}%"),
        'Total Amount': df_filtered['total'].apply(lambda x: f"${x:,.2f}"),
        '% of Total Raised': df_filtered['pct_amount'].apply(lambda x: f"{x}%")
    })

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Key insights
    if not df_filtered.empty:
        max_count_bracket = df_filtered.loc[df_filtered['count'].idxmax()]
        max_amount_bracket = df_filtered.loc[df_filtered['total'].idxmax()]

        st.markdown("#### 💡 Key Insights")
        col1, col2 = st.columns(2)

        with col1:
            st.info(f"**Most Common:** {max_count_bracket['bracket']} ({max_count_bracket['count']} contributions)")

        with col2:
            st.info(f"**Highest Revenue:** {max_amount_bracket['bracket']} (${max_amount_bracket['total']:,.2f})")


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

        st.markdown("## 🔍 Data Quality")

        # Election cycle
        st.caption(f"**Election Cycle:** {stats['primary_cycle']}")

        # Date range
        if stats['earliest_contribution'] and stats['latest_contribution']:
            earliest = stats['earliest_contribution']
            latest = stats['latest_contribution']

            if isinstance(earliest, datetime):
                earliest_str = earliest.strftime("%b %Y")
            else:
                earliest_str = str(earliest)[:7]

            if isinstance(latest, datetime):
                latest_str = latest.strftime("%b %Y")
            else:
                latest_str = str(latest)[:7]

            st.caption(f"**Contribution Period:** {earliest_str} - {latest_str}")

        # Last data sync
        if stats['last_updated']:
            last_update = stats['last_updated']

            if isinstance(last_update, datetime):
                days_old = (datetime.utcnow() - last_update).days

                if days_old == 0:
                    freshness = "🟢 Today"
                elif days_old <= 7:
                    freshness = f"🟢 {days_old} days ago"
                elif days_old <= 30:
                    freshness = f"🟡 {days_old} days ago"
                else:
                    freshness = f"🔴 {days_old} days ago"

                st.caption(f"**Last Synced:** {freshness}")
            else:
                st.caption(f"**Last Synced:** {str(last_update)[:10]}")

        st.caption("💡 Update data: `scripts/csv-files/update_csv_from_api.py --contributions`")

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

    # Add comparison mode toggle
    compare_mode = st.checkbox("📊 Compare Multiple Politicians", value=False)

    st.divider()

    if compare_mode:
        # ====================================================================
        # COMPARISON MODE
        # ====================================================================
        st.subheader("Compare Politicians")

        # Multi-select for politicians
        selected_names = st.multiselect(
            "Select 2-4 politicians to compare",
            options=list(politician_options.keys()),
            max_selections=4,
            help="Choose multiple politicians to compare their campaign finance data"
        )

        if len(selected_names) < 2:
            st.info("👆 Select at least 2 politicians to see a comparison")
            return

        # Get bioguide IDs for selected politicians
        selected_politicians = [politician_options[name] for name in selected_names]
        bioguide_ids = [p["bioguide_id"] for p in selected_politicians]

        # Fetch summaries for all selected politicians
        db = get_db()
        summaries = {}
        for pol, bioguide_id in zip(selected_politicians, bioguide_ids):
            full_pol = db.politicians.find_one({"bioguide_id": bioguide_id})
            if full_pol:
                pol = full_pol
            summary = get_contribution_summary(bioguide_id)
            summaries[bioguide_id] = {
                "politician": pol,
                "summary": summary
            }

        # Display comparison
        st.markdown("### 💰 Fundraising Comparison")

        # Create comparison metrics
        cols = st.columns(len(selected_politicians))

        for i, (name, pol) in enumerate(zip(selected_names, selected_politicians)):
            bioguide_id = pol["bioguide_id"]
            summary = summaries[bioguide_id]["summary"]
            politician = summaries[bioguide_id]["politician"]

            with cols[i]:
                st.markdown(f"**{politician.get('full_name', 'Unknown')}**")
                party = politician.get('party', '?')
                state = politician.get('state', '??')
                st.caption(f"{party}-{state}")

                st.metric("Total Raised", f"${summary['total_raised']:,.2f}")
                st.metric("Contributions", f"{summary['total_contributions']:,}")
                st.metric("Avg Amount", f"${summary['avg_contribution']:,.2f}")

        st.divider()

        # Comparison bar chart - Total raised
        st.markdown("### 📊 Total Contributions Raised")

        chart_data = []
        for name, pol in zip(selected_names, selected_politicians):
            bioguide_id = pol["bioguide_id"]
            summary = summaries[bioguide_id]["summary"]
            politician = summaries[bioguide_id]["politician"]
            chart_data.append({
                "Politician": politician.get('full_name', 'Unknown'),
                "Total Raised": summary['total_raised']
            })

        df_chart = pd.DataFrame(chart_data)
        fig = px.bar(
            df_chart,
            x="Politician",
            y="Total Raised",
            title="Total Contributions Raised",
            color="Total Raised",
            color_continuous_scale="Blues"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Source breakdown comparison
        st.markdown("### 🏛️ Source Breakdown Comparison")

        source_cols = st.columns(len(selected_politicians))
        for i, pol in enumerate(selected_politicians):
            bioguide_id = pol["bioguide_id"]
            politician = summaries[bioguide_id]["politician"]

            with source_cols[i]:
                st.markdown(f"**{politician.get('full_name', 'Unknown')}**")
                breakdown = get_contribution_source_breakdown(bioguide_id)

                if breakdown:
                    df_breakdown = pd.DataFrame(breakdown)
                    fig = px.pie(
                        df_breakdown,
                        values='total',
                        names='type',
                        title=f"{politician.get('full_name', 'Unknown')[:20]}..."
                    )
                    fig.update_traces(textposition='inside', textinfo='percent')
                    st.plotly_chart(fig, use_container_width=True)

        return  # Exit here for comparison mode

    # ====================================================================
    # SINGLE POLITICIAN MODE (original flow)
    # ====================================================================

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

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📈 Timeline",
        "💳 Top Donors",
        "🏢 Top Employers",
        "🗺️ By State",
        "📊 Size Distribution",
        "🏛️ Source Breakdown",
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
        size_distribution = get_contribution_size_distribution(bioguide_id)
        display_contribution_size_distribution(size_distribution)

    with tab6:
        source_breakdown = get_contribution_source_breakdown(bioguide_id)
        display_contribution_source_breakdown(source_breakdown, bioguide_id)

    with tab7:
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

    date_col1, date_col2 = st.columns(2)

    with date_col1:
        start_date = st.date_input(
            "Start Date",
            value=None,
            help="Filter contributions from this date onwards"
        )

    with date_col2:
        end_date = st.date_input(
            "End Date",
            value=None,
            help="Filter contributions up to this date"
        )

    if st.button("🔍 Search", type="primary"):
        with st.spinner("Searching contributions..."):
            search_results = search_contributions(
                employer=employer_search if employer_search else None,
                state=state_search if state_search != "All States" else None,
                min_amount=min_amount if min_amount > 0 else None,
                max_amount=max_amount if max_amount < 10000 else None,
                start_date=start_date if start_date else None,
                end_date=end_date if end_date else None,
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