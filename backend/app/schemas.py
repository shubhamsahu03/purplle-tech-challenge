from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class EventSchema(BaseModel):
    event_id: str
    store_id: str
    visitor_id: str
    session_id: str
    event_type: str
    zone_id: Optional[str] = None
    timestamp: datetime
    dwell_ms: int = 0
    confidence: float = 1.0
    camera_id: str
    is_staff: bool = False
    queue_depth: Optional[int] = None
    model_meta: Optional[Dict[str, Any]] = {}