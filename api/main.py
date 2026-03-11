from fastapi import FastAPI, UploadFile, File, BackgroundTasks, WebSocket, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from .websockets import ConnectionManager
from core.database import get_db, Base, engine
from core.models import IngestionStatus
import os
import uuid
from core.tasks import process_trips_task
from datetime import datetime
import asyncio
import redis.asyncio as redis
import json

# Initialize database tables
Base.metadata.create_all(bind=engine)
with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    conn.commit()

app = FastAPI(title="Jobsity Trips API")
manager = ConnectionManager()
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

async def redis_listener():
    r = redis.from_url(REDIS_URL)
    pubsub = r.pubsub()
    await pubsub.psubscribe("ingestion_status_*")
    
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                data = json.loads(message["data"])
                ingestion_id = data.get("ingestion_id")
                if ingestion_id:
                    await manager.broadcast(int(ingestion_id), data)
            await asyncio.sleep(0.1)
    except Exception as e:
        print(f"Redis listener error: {e}")
    finally:
        await pubsub.unsubscribe()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(redis_listener())

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Jobsity Trips API is running"}

@app.post("/ingest")
async def ingest_trips(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    file_id = str(uuid.uuid4())
    file_path = f"/tmp/{file_id}_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    status = IngestionStatus(
        filename=file.filename,
        status="pending",
        progress=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(status)
    db.commit()
    db.refresh(status)

    process_trips_task.delay(status.id, file_path)

    return {"message": "Ingestion started", "ingestion_id": status.id}

@app.get("/report/weekly_average")
def get_weekly_average(region: str = None, min_lat: float = None, min_lon: float = None, max_lat: float = None, max_lon: float = None, db: Session = Depends(get_db)):
    # Calculate weekly average number of trips for an area or region
    from sqlalchemy import func
    from core.models import TripSummary, Trip
    from geoalchemy2.functions import ST_MakeEnvelope, ST_Within
    
    query = db.query(
        func.date_trunc('week', TripSummary.time_slot).label('week'),
        func.sum(TripSummary.trip_count).label('total_trips')
    )
    
    if region:
        query = query.filter(TripSummary.region == region)
    
    if all(v is not None for v in [min_lat, min_lon, max_lat, max_lon]):
        envelope = ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
        query = query.filter(ST_Within(TripSummary.origin_coord, envelope))
    
    query = query.group_by('week').all()
    
    if not query:
        return {"weekly_average": 0, "details": []}
    
    total_weeks = len(query)
    total_trips = sum(q.total_trips for q in query)
    
    return {
        "weekly_average": total_trips / total_weeks if total_weeks > 0 else 0,
        "total_trips": total_trips,
        "total_weeks": total_weeks,
        "details": [{"week": q.week, "trips": q.total_trips} for q in query]
    }

@app.websocket("/ws/status/{ingestion_id}")
async def websocket_endpoint(websocket: WebSocket, ingestion_id: int):
    await manager.connect(websocket, ingestion_id)
    try:
        while True:
            await websocket.receive_text()
    except Exception as e:
        pass
    finally:
        manager.disconnect(websocket, ingestion_id)
