import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Apex Store Intelligence", 
    page_icon="🛍️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INTERNAL DOCKER NETWORKING ---
API_URL = "http://api:8000"

def fetch_data(endpoint):
    """Helper function to fetch data safely from FastAPI."""
    try:
        res = requests.get(f"{API_URL}{endpoint}", timeout=2)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None

# --- SIDEBAR (Static, doesn't reload) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3594/3594083.png", width=60) # Generic Retail Icon
    st.title("Control Center")
    
    store_id = st.selectbox("🏬 Select Store Feed", ["ST1008", "ST1076"])
    refresh_rate = st.slider("⏱️ Refresh Rate (seconds)", 1, 10, 2)
    
    st.markdown("---")
    st.markdown("### 🧪 Evaluator Guide")
    st.info("To see this dashboard update live, run the stream simulator in a separate terminal:\n\n`python simulate_stream.py`")

# --- MAIN DASHBOARD HEADER ---
st.title(f"🛍️ Store Operations: {store_id}")
st.markdown("Real-time CCTV Analytics, Conversion Tracking, and Anomaly Detection")

# --- DYNAMIC FRAGMENT (Auto-refreshes seamlessly) ---
@st.fragment(run_every=refresh_rate)
def render_live_dashboard(selected_store):
    
    # 1. Fetch all backend data
    health = fetch_data("/health")
    metrics = fetch_data(f"/stores/{selected_store}/metrics")
    anomalies = fetch_data(f"/stores/{selected_store}/anomalies")
    funnel = fetch_data(f"/stores/{selected_store}/funnel")
    heatmap = fetch_data(f"/stores/{selected_store}/heatmap")

    # 2. System Status Ribbon
    if health:
        status_color = "🟢" if health['status'] == "HEALTHY" else "🔴"
        st.caption(f"**Pipeline Status:** {status_color} {health['status']} | **Latency:** {health.get('lag_minutes', 0)} mins")
    else:
        st.error("🚨 CRITICAL: Cannot connect to Intelligence API. Ensure the backend container is running.")
        return

    # 3. Active Anomalies Banner (Only shows if anomalies exist)
    if anomalies and anomalies.get("active_anomalies"):
        for a in anomalies["active_anomalies"]:
            if a["severity"] == "CRITICAL":
                st.error(f"🚨 **{a['issue'].replace('_', ' ').upper()}**: {a.get('description', '')} ➔ **{a.get('suggested_action', '')}**")
            else:
                st.warning(f"⚠️ **{a['issue'].replace('_', ' ').upper()}**: {a.get('description', '')} ➔ **{a.get('suggested_action', '')}**")

    # 4. KPI Metrics Row
    if metrics:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Unique Visitors", metrics.get("unique_visitors", 0))
        with col2:
            st.metric("Conversion Rate", f"{metrics.get('conversion_rate', 0.0)}%")
        with col3:
            st.metric("Abandonment Rate", f"{metrics.get('abandonment_rate', 0.0)}%")
        with col4:
            q_depth = metrics.get("queue_depth", 0)
            st.metric("Live Queue Depth", q_depth, delta="Spike" if q_depth > 4 else None, delta_color="inverse")
            
    st.divider()

    # 5. Visualizations Row
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("🛒 Conversion Funnel")
        if funnel and funnel.get("funnel") and funnel["funnel"].get("1_entry", 0) > 0:
            f_data = funnel["funnel"]
            df_funnel = pd.DataFrame({
                "Stage": ["1. Entrance", "2. Zone Browsing", "3. Joined Queue", "4. Completed Purchase"],
                "Shoppers": [f_data.get("1_entry", 0), f_data.get("2_zone_visit", 0), f_data.get("3_billing_queue", 0), f_data.get("4_purchase", 0)]
            })
            # Draw beautiful Plotly funnel
            fig = px.funnel(df_funnel, x='Shoppers', y='Stage', color_discrete_sequence=['#8353E2'])
            fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Awaiting visitor entry events...")

    with col_right:
        st.subheader("📍 Spatial Engagement")
        if heatmap and heatmap.get("heatmap"):
            h_data = heatmap["heatmap"]
            if h_data:
                df_heatmap = pd.DataFrame(h_data).sort_values("frequency_normalized")
                # Draw beautiful horizontal bar chart for intensity
                fig2 = px.bar(
                    df_heatmap, 
                    x="frequency_normalized", 
                    y="zone_id", 
                    orientation='h',
                    color="avg_dwell_sec", 
                    color_continuous_scale="magma",
                    labels={"frequency_normalized": "Traffic Intensity (%)", "avg_dwell_sec": "Avg Dwell (sec)", "zone_id": "Store Zone"}
                )
                fig2.update_layout(margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)
                
                # Show data confidence
                st.caption(f"Data Confidence: **{heatmap.get('data_confidence', 'UNKNOWN')}**")
            else:
                st.info("Awaiting zone dwell events...")
        else:
            st.info("Awaiting spatial layout events...")

# --- EXECUTE FRAGMENT ---
render_live_dashboard(store_id)