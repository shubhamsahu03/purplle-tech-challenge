EVENTS_SCHEMA = [
    'event_id', 'store_id', 'visitor_id', 'session_id', 'event_type',
    'camera_id', 'zone_id', 'timestamp', 'dwell_ms', 'confidence',
    'is_staff', 'queue_depth', 'sku_zone', 'session_seq', 'model_meta',
]
SESSIONS_SCHEMA = [
    'store_id', 'visitor_id', 'session_id', 'entry_time', 'exit_time',
    'zones_visited', 'dwell_by_zone', 'queue_events',
    'conversion_outcome', 'is_staff', 'group_id',
]
TRACK_SEMANTICS_SCHEMA = [
    'store_id', 'track_id', 'camera_id', 'frame_id', 'zone_id',
    'micro_intent', 'clip_top_prompt', 'clip_score',
    'staff_score', 'is_staff', 'embedding',
]
EVENT_TYPES = [
    'ENTRY', 'EXIT', 'REENTRY',
    'ZONE_ENTER', 'ZONE_EXIT', 'ZONE_DWELL',
    'BILLING_QUEUE_JOIN', 'BILLING_QUEUE_ABANDON',
]
