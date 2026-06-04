import pandas as pd
from sqlalchemy.orm import Session
from .database import EventDB

def load_store_df(store_id: str, db: Session, exclude_staff: bool = True) -> pd.DataFrame:
    query = db.query(EventDB).filter(EventDB.store_id == store_id)
    if exclude_staff:
        query = query.filter(EventDB.is_staff == False)
    
    # In pandas 2.x, it's safer to pass the connection
    df = pd.read_sql(query.statement, db.connection())
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    return df

def get_metrics(store_id: str, db: Session):
    df = load_store_df(store_id, db)
    if df.empty:
        return {"unique_visitors": 0, "conversion_rate": 0.0, "abandonment_rate": 0.0, "queue_depth": 0}

    unique_visitors = df[df['event_type'].isin(['ENTRY', 'REENTRY'])]['session_id'].nunique()
    queue_joins = df[df['event_type'] == 'BILLING_QUEUE_JOIN']['session_id'].nunique()
    abandons = df[df['event_type'] == 'BILLING_QUEUE_ABANDON']['session_id'].nunique()
    purchases = max(0, queue_joins - abandons)

    conv_rate = round((purchases / unique_visitors) * 100, 2) if unique_visitors else 0.0
    aban_rate = round((abandons / queue_joins) * 100, 2) if queue_joins else 0.0

    queue_events = df[df['event_type'] == 'BILLING_QUEUE_JOIN'].sort_values('timestamp')
    q_depth = int(queue_events.iloc[-1]['queue_depth']) if not queue_events.empty and pd.notna(queue_events.iloc[-1]['queue_depth']) else 0

    return {"unique_visitors": unique_visitors, "conversion_rate": conv_rate, "abandonment_rate": aban_rate, "queue_depth": q_depth}

def get_funnel(store_id: str, db: Session):
    df = load_store_df(store_id, db)
    if df.empty: return {"funnel": {}, "drop_offs_pct": {}}

    entries = df[df['event_type'].isin(['ENTRY', 'REENTRY'])]['session_id'].nunique()
    zones = df[(df['event_type'] == 'ZONE_ENTER') & (df['zone_id'] != 'BILLING')]['session_id'].nunique()
    billing = df[df['event_type'] == 'BILLING_QUEUE_JOIN']['session_id'].nunique()
    abandons = df[df['event_type'] == 'BILLING_QUEUE_ABANDON']['session_id'].nunique()
    purchases = max(0, billing - abandons)

    return {
        "funnel": {"1_entry": entries, "2_zone_visit": zones, "3_billing_queue": billing, "4_purchase": purchases},
        "drop_offs_pct": {
            "entry_to_zone": round(((entries - zones) / entries * 100), 1) if entries else 0.0,
            "zone_to_billing": round(((zones - billing) / zones * 100), 1) if zones else 0.0,
            "billing_to_purchase": round(((billing - purchases) / billing * 100), 1) if billing else 0.0
        }
    }

def get_heatmap(store_id: str, db: Session):
    df = load_store_df(store_id, db)
    total_sessions = df['session_id'].nunique() if not df.empty else 0
    confidence = "HIGH" if total_sessions >= 20 else "LOW"
    
    if df.empty: return {"data_confidence": confidence, "heatmap": []}

    zone_df = df[(df['event_type'] == 'ZONE_DWELL') & df['zone_id'].notna() & (df['zone_id'] != 'BILLING')]
    if zone_df.empty: return {"data_confidence": confidence, "heatmap": []}

    visits = zone_df.groupby('zone_id')['session_id'].nunique()
    max_visits = visits.max() if not visits.empty else 1

    duration = zone_df.groupby(['zone_id', 'session_id'])['timestamp'].agg(['min', 'max'])
    duration['true_dwell_sec'] = (duration['max'] - duration['min']).dt.total_seconds()
    avg_dwell = duration.groupby('zone_id')['true_dwell_sec'].mean()

    heatmap = []
    for zone in visits.index:
        heatmap.append({
            "zone_id": zone,
            "frequency_normalized": round((visits[zone] / max_visits) * 100, 1),
            "avg_dwell_sec": round(avg_dwell.get(zone, 0.0), 1)
        })
    return {"data_confidence": confidence, "heatmap": heatmap}

def get_anomalies(store_id: str, db: Session):
    df = load_store_df(store_id, db, exclude_staff=False)
    anomalies = []
    if df.empty: return {"active_anomalies": []}

    last_time = df['timestamp'].max()
    
    # Queue Spike
    queue_recent = df[(df['event_type'] == 'BILLING_QUEUE_JOIN') & (df['timestamp'] >= last_time - pd.Timedelta(minutes=15))]
    if len(queue_recent) >= 5:
        anomalies.append({"severity": "CRITICAL", "issue": "queue_spike", "description": "5+ shoppers joined recently.", "suggested_action": "Deploy line-busting mobile POS."})

    # Dead Zone
    all_zones = df[df['zone_id'].notna()]['zone_id'].unique()
    recent_zones = df[(df['event_type'] == 'ZONE_ENTER') & (df['timestamp'] >= last_time - pd.Timedelta(minutes=30))]['zone_id'].unique()
    for dz in set(all_zones) - set(recent_zones):
        if dz != 'BILLING':
            anomalies.append({"severity": "WARN", "issue": f"dead_zone_{dz}", "description": "0 visits in 30 mins.", "suggested_action": f"Check for occlusions in {dz}."})
            
    return {"active_anomalies": anomalies}

def get_health(db: Session):
    df = pd.read_sql(db.query(EventDB).statement, db.connection())
    if df.empty: return {"status": "INITIALIZING", "lag_minutes": 0}
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    last_event = df['timestamp'].max()
    lag = (pd.Timestamp.utcnow() - last_event).total_seconds() / 60
    
    return {"status": "STALE_FEED" if lag > 10 else "HEALTHY", "last_event": last_event.isoformat(), "lag_minutes": round(lag, 1)}