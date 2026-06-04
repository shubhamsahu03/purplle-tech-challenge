import time
import uuid
import json
import logging
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, IntegrityError
from typing import List

from .database import get_db, EventDB
from .schemas import EventSchema
from . import analytics

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("api_logger")

app = FastAPI(title="Purplle Intelligence API", version="2.0")

@app.middleware("http")
async def production_middleware(request: Request, call_next):
    trace_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        response = await call_next(request)
        status_code = response.status_code
    except OperationalError:
        status_code = 503
        response = JSONResponse(status_code=503, content={"error": "Database unavailable", "trace_id": trace_id})
    except Exception as e:
        status_code = 500
        response = JSONResponse(status_code=500, content={"error": str(e), "trace_id": trace_id})

    log_data = {
        "trace_id": trace_id,
        "store_id": request.path_params.get("id", "N/A"),
        "endpoint": request.url.path,
        "method": request.method,
        "latency_ms": round((time.time() - start_time) * 1000, 2),
        "status_code": status_code
    }
    logger.info(json.dumps(log_data))
    return response

@app.post("/events/ingest")
def ingest_events(events: List[EventSchema], db: Session = Depends(get_db)):
    if len(events) > 500:
        raise HTTPException(status_code=400, detail="Batch size exceeds 500.")
    
    success_count = 0
    for ev in events:
        try:
            db_event = EventDB(**ev.dict())
            db.add(db_event)
            db.commit()
            success_count += 1
        except IntegrityError:
            db.rollback() # Idempotency: Skip duplicates

    return {"status": "success", "ingested_count": success_count, "skipped_duplicates": len(events) - success_count}

@app.get("/stores/{id}/metrics")
def get_metrics(id: str, db: Session = Depends(get_db)): 
    return analytics.get_metrics(id, db)

@app.get("/stores/{id}/funnel")
def get_funnel(id: str, db: Session = Depends(get_db)): 
    return analytics.get_funnel(id, db)

@app.get("/stores/{id}/heatmap")
def get_heatmap(id: str, db: Session = Depends(get_db)): 
    return analytics.get_heatmap(id, db)

@app.get("/stores/{id}/anomalies")
def get_anomalies(id: str, db: Session = Depends(get_db)): 
    return analytics.get_anomalies(id, db)

@app.get("/health")
def health_check(db: Session = Depends(get_db)): 
    return analytics.get_health(db)