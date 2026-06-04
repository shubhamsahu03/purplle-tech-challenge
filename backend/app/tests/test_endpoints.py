from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def test_health_empty():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "INITIALIZING"

def test_ingest_idempotency_and_metrics():
    payload = [{
        "event_id": "uuid-1234", "store_id": "TEST1", "visitor_id": "V1",
        "session_id": "S1", "event_type": "ENTRY", "timestamp": "2026-06-04T12:00:00Z",
        "camera_id": "CAM1", "is_staff": False
    }]
    
    res1 = client.post("/events/ingest", json=payload)
    assert res1.json()["ingested_count"] == 1
    
    res2 = client.post("/events/ingest", json=payload)
    assert res2.json()["ingested_count"] == 0
    assert res2.json()["skipped_duplicates"] == 1

    metrics = client.get("/stores/TEST1/metrics")
    assert metrics.json()["unique_visitors"] == 1
    assert metrics.json()["conversion_rate"] == 0.0

def test_all_staff_ignored():
    payload = [{
        "event_id": "uuid-staff", "store_id": "TEST2", "visitor_id": "V2",
        "session_id": "S2", "event_type": "ENTRY", "timestamp": "2026-06-04T12:01:00Z",
        "camera_id": "CAM1", "is_staff": True 
    }]
    client.post("/events/ingest", json=payload)
    
    metrics = client.get("/stores/TEST2/metrics")
    assert metrics.json()["unique_visitors"] == 0