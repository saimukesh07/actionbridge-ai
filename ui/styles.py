"""
ActionBridge AI - Premium UI Styles & Theme Definition
Modern AI SaaS aesthetic with deep indigo primary, restrained violet accents,
clean card surfaces, accessible typography, and responsive spacing.
"""

CUSTOM_CSS = """
<style>
/* Modern typography and container constraints */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* Header & Sidebar brand aesthetics */
.css-1d391kg, [data-testid="stSidebar"] {
    background-color: #0F172A;
    color: #F8FAFC;
}
[data-testid="stSidebar"] hr {
    border-color: #1E293B;
}

/* Subtle Card Containers */
.ab-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    transition: border-color 0.15s ease-in-out;
}
.ab-card:hover {
    border-color: #CBD5E1;
}

/* Executive Callout Card */
.ab-hero-card {
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.05) 0%, rgba(124, 58, 237, 0.05) 100%);
    border: 1px solid #DBEAFE;
    border-left: 5px solid #2563EB;
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 24px;
}

/* Action Callout (Start Here) */
.ab-action-card {
    background: #FFFBEB;
    border: 1px solid #FDE68A;
    border-left: 5px solid #F59E0B;
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 20px;
}

/* Recommendation Banner */
.ab-rec-card {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-left: 5px solid #16A34A;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 20px;
}

/* Modern Status and Risk Badges */
.ab-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}
.ab-badge-low {
    background-color: #ECFDF5;
    color: #065F46;
    border: 1px solid #A7F3D0;
}
.ab-badge-medium {
    background-color: #FFFBEB;
    color: #92400E;
    border: 1px solid #FDE68A;
}
.ab-badge-high {
    background-color: #FEF2F2;
    color: #991B1B;
    border: 1px solid #FECACA;
}
.ab-badge-critical {
    background-color: #7F1D1D;
    color: #FFFFFF;
}

/* Milestone Journey bar */
.ab-milestone-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 14px 20px;
    margin-bottom: 24px;
}
.ab-milestone-item {
    font-size: 0.92rem;
    font-weight: 600;
    color: #1E293B;
}
.ab-milestone-arrow {
    color: #94A3B8;
    font-weight: bold;
}

/* Streamlit Button overrides for cohesive feel */
.stButton>button {
    border-radius: 8px;
    font-weight: 600;
    padding: 8px 18px;
    transition: all 0.15s ease-in-out;
}

/* Cleaner Expanders */
.streamlit-expanderHeader {
    font-weight: 600;
    border-radius: 8px;
}

/* Metric styling */
[data-testid="stMetricValue"] {
    font-weight: 700;
}
</style>
"""
