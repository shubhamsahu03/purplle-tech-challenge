from sqlalchemy import create_engine, Column, String, Boolean, Integer, Float, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local_test.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class EventDB(Base):
    __tablename__ = "events"
    event_id = Column(String, primary_key=True, index=True)
    store_id = Column(String, index=True)
    visitor_id = Column(String, index=True)
    session_id = Column(String, index=True)
    event_type = Column(String, index=True)
    zone_id = Column(String, nullable=True)
    timestamp = Column(DateTime)
    dwell_ms = Column(Integer, default=0)
    confidence = Column(Float, default=1.0)
    camera_id = Column(String)
    is_staff = Column(Boolean, default=False)
    queue_depth = Column(Integer, nullable=True)
    model_meta = Column(JSON, nullable=True)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()