# Campaign Finance Analytics Roadmap

This document outlines potential analytics and visualizations for the Campaign Finance page. These are organized by implementation priority and complexity.

## Status Legend
- ✅ Implemented
- 🚧 In Progress
- ⏳ Planned
- 💡 Idea/Future

---

## Current Features (✅ Implemented)

1. **Timeline Visualization** - Contributions over time with monthly aggregation
2. **Top Donors Table** - Individual contributors ranked by total amount
3. **Top Employers** - Organizations whose employees contribute most
4. **State Breakdown** - Geographic distribution with interactive US map
5. **Contribution Size Distribution** - Breakdown by amount brackets ($1-100, $101-500, etc.)
6. **Source Breakdown** - Individual vs PAC contributions with drill-down
7. **Recent Contributions** - Latest individual donations
8. **Multi-Politician Comparison** - Compare 2-4 politicians side-by-side
9. **CSV Exports** - Download data for donors, employers, states
10. **Advanced Search** - Filter by employer, state, amount range, date range

---

## Tier 1: High Value, Relatively Easy

### 1. 🚧 In-State vs Out-of-State Breakdown
**Value:** Shows whether support is local or national
**Complexity:** Low
**Implementation:**
- Compare contributor_state to politician's home state
- Create pie chart showing percentage breakdown
- Add metrics for in-state vs out-of-state totals
- Highlight home state on geographic map
- Include average donation amount by category

**Use Case:** Understand if a politician has strong local support or relies on national donors

---

### 2. 🚧 Small Dollar vs Large Dollar Analysis
**Value:** Reveals fundraising strategy and grassroots support
**Complexity:** Low
**Implementation:**
- Define brackets:
  - Small Dollar: <$200 (grassroots/unitemized limit)
  - Mid-Tier: $200-$999
  - Major Donors: $1,000-$2,900
  - Max Donors: $2,900+ (at or near individual limit)
- Show volume vs revenue for each category
- Calculate metrics:
  - % of total contributions (count)
  - % of total revenue (amount)
  - Average donation per bracket
- Visualizations:
  - Dual pie charts (count vs amount)
  - Stacked bar chart showing both dimensions

**Use Case:** Identify if campaign is grassroots-funded or relies on wealthy donors

---

### 3. ⏳ Contribution Velocity/Momentum
**Value:** Shows fundraising acceleration or deceleration
**Complexity:** Low-Medium
**Implementation:**
- Calculate rolling averages (30-day, 90-day)
- Show $/month or $/quarter trends
- Add slope indicators (📈 accelerating, 📉 slowing)
- Highlight fastest fundraising periods
- Compare velocity between politicians in comparison mode

**Use Case:** Identify momentum shifts, successful fundraising periods

---

### 4. ⏳ Recurring Donor Analysis
**Value:** Measures donor loyalty and engagement
**Complexity:** Medium
**Implementation:**
- Group by contributor_name + contributor_state
- Count contributions per unique donor
- Metrics to track:
  - % of donors who give 2+, 3+, 5+ times
  - Average # of contributions per donor
  - Total from repeat vs one-time donors
- Show top repeat donors table
- Cohort analysis: first-time vs returning donors by month

**Use Case:** Understand donor loyalty and grassroots engagement

---

### 5. ⏳ Contribution Calendar Heatmap
**Value:** Visualizes donation patterns and spikes
**Complexity:** Medium
**Implementation:**
- GitHub-style calendar heatmap
- Color intensity by daily contribution total
- Hover to show date, amount, count
- Highlight key dates (debates, announcements, deadlines)
- Annual or custom date range view

**Use Case:** Identify fundraising spikes around events, quarterly patterns

---

## Tier 2: Medium Complexity, High Insight

### 6. 💡 Industry/Sector Analysis
**Value:** Shows which industries support a politician
**Complexity:** High (requires employer classification)
**Implementation:**
- Build employer-to-industry mapping
  - Use keyword matching (e.g., "Google" → Tech)
  - Consider external datasets (OpenSecrets industry codes)
  - Allow manual classification for common employers
- Aggregate by industry sector:
  - Technology
  - Finance/Banking
  - Healthcare
  - Energy
  - Legal
  - Education
  - Manufacturing
  - Retail
  - etc.
- Visualizations:
  - Treemap showing industry composition
  - Bar chart of top sectors
  - Comparison mode: industry breakdown across politicians

**Data Needed:** Employer name standardization and industry mapping table

**Use Case:** Understand industry influence, compare sector support across politicians

---

### 7. 💡 Cumulative Fundraising Curve
**Value:** Shows total raised over time (S-curve)
**Complexity:** Low-Medium
**Implementation:**
- Calculate running total by date
- Line chart showing cumulative amount
- Add comparison lines:
  - Opponent (if available)
  - Party average
  - Previous election cycle
- Show key milestones (e.g., "reached $1M on [date]")
- Projection line for current trajectory

**Use Case:** Track fundraising progress toward goals, compare against benchmarks

---

### 8. 💡 Top Zip Codes
**Value:** Hyperlocal geographic analysis
**Complexity:** Medium (requires zip code data)
**Implementation:**
- Add zip code field to contribution data model
- Top 25 zip codes by total contributions
- Map visualization with zip code boundaries
- Demographic overlay (median income, political lean)
- Compare zip code patterns across politicians

**Data Needed:** contributor_zip field in database

**Use Case:** Understand hyperlocal support, target fundraising efforts

---

### 9. 💡 Maxed-Out Donors
**Value:** Shows sophisticated donor engagement
**Complexity:** Low
**Implementation:**
- FEC individual limit: $3,300 per election (2024)
- Identify donors at $2,900+ (at or near max)
- Metrics:
  - Count of maxed-out donors
  - Total from maxed donors
  - % of fundraising from max donors
- Table of maxed donors with contribution dates
- Compare % of max donors across politicians

**Use Case:** Measure donor commitment, identify VIP supporters

---

### 10. 💡 Shared Donor Network
**Value:** Shows donor overlap between politicians
**Complexity:** Medium-High
**Implementation:**
- In comparison mode, identify donors contributing to multiple selected politicians
- Metrics:
  - # of shared donors
  - Total $ from shared donors per politician
  - Exclusive vs shared donor breakdown
- Visualizations:
  - Venn diagram (2-3 politicians)
  - Network graph (3+ politicians)
  - List of top shared donors

**Use Case:** Understand donor coalitions, identify cross-party support

---

## Tier 3: Advanced Analytics

### 11. 💡 Contribution Limits Compliance
**Value:** Data quality and transparency
**Complexity:** Medium
**Implementation:**
- Track total contributions per donor per cycle
- Flag any exceeding FEC limits
- Show distribution near limit
- Compliance dashboard

**Use Case:** Data verification, transparency reporting

---

### 12. 💡 Quarterly Reporting Patterns
**Value:** Aligns with FEC filing deadlines
**Complexity:** Low
**Implementation:**
- Group by FEC quarters (Q1: Jan-Mar, Q2: Apr-Jun, etc.)
- Show quarterly totals
- Compare quarters across years
- End-of-quarter surge analysis

**Use Case:** Align with official FEC reporting, identify deadline-driven donations

---

### 13. 💡 Donor Demographics Analysis
**Value:** Understand donor base composition
**Complexity:** High (requires external data)
**Implementation:**
- Link zip codes to demographic data:
  - Median income
  - Age distribution
  - Education level
  - Political lean (Cook PVI)
- Show donor base profile
- Compare demographics across politicians

**Data Needed:** Census data, political indexes

**Use Case:** Profile donor base, target similar demographics

---

### 14. 💡 Contribution Attribution
**Value:** Links donations to events/messaging
**Complexity:** High (requires manual annotation)
**Implementation:**
- Tag date ranges with events:
  - TV ads
  - Debates
  - Endorsements
  - Controversies
  - Email campaigns
- Show contribution spikes with event overlays
- Calculate ROI for fundraising campaigns

**Data Needed:** Event timeline data

**Use Case:** Optimize fundraising strategy, understand what drives donations

---

### 15. 💡 Burn Rate Analysis
**Value:** Financial sustainability
**Complexity:** High (requires expenditure data)
**Implementation:**
- Track spending vs fundraising
- Cash on hand over time
- Runway calculation
- Spending categories

**Data Needed:** FEC expenditure data

**Use Case:** Assess campaign financial health

---

## Implementation Priority

### Phase 1 (Current - Q1)
- ✅ Basic analytics (completed)
- 🚧 In-State vs Out-of-State
- 🚧 Small Dollar vs Large Dollar

### Phase 2 (After User Testing)
- Contribution Velocity
- Recurring Donor Analysis
- Calendar Heatmap

### Phase 3 (Future)
- Industry/Sector Analysis
- Cumulative Curves
- Maxed-Out Donors

### Phase 4 (Advanced)
- Shared Donor Networks
- Quarterly Patterns
- Demographic overlays

---

## Data Model Enhancements Needed

To support advanced analytics, consider adding these fields:

```python
# Current fields:
{
    "bioguide_id": str,
    "contributor_name": str,
    "contributor_employer": str,
    "contributor_city": str,
    "contributor_state": str,
    "contributor_type": str,  # Individual, PAC, etc.
    "amount": float,
    "contribution_date": datetime,
    "cycle": str,
    "last_updated": datetime
}

# Future additions:
{
    "contributor_zip": str,  # For zip code analysis
    "contributor_occupation": str,  # For occupation analysis
    "employer_industry": str,  # Derived field for sector analysis
    "is_max_donor": bool,  # Cached flag for at/near limit
    "donor_id": str,  # Normalized donor identifier for recurring analysis
    "fec_quarter": str,  # Q1-2024, Q2-2024, etc.
    "contribution_source": str,  # Online, Event, Mail, etc. (if available)
}
```

---

## Performance Considerations

- Use MongoDB aggregation pipelines for complex analytics
- Maintain caching for expensive calculations (`@st.cache_data`)
- Consider pre-computing metrics during data ingestion
- Add database indexes for common queries:
  - `contributor_state`
  - `contribution_date`
  - `contributor_name + contributor_state` (for recurring donors)
  - `amount` (for bucketing)

---

## Notes

- Start simple, validate with real usage
- Gather user feedback on most valuable insights
- Balance complexity vs usability
- Ensure all visualizations are mobile-friendly
- Maintain consistent color schemes and design patterns
- Add export capabilities for all new analytics

---

**Last Updated:** 2024-12-24
**Status:** Phase 1 Complete, Phase 2 Starting
