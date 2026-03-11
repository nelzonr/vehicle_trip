from celery import Celery
import pandas as pd
import os
from .database import SessionLocal
from .models import Trip, TripSummary, IngestionStatus
from datetime import datetime, timedelta
import redis
import json
from sqlalchemy import text
from shapely import wkt
from shapely.geometry import Point
import numpy as np

CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("tasks", broker=CELERY_BROKER_URL)

r = redis.from_url(CELERY_BROKER_URL)

def round_coords(point_str, precision=3):
    # Extracts point coordinates from "POINT (lon lat)" and rounds them
    try:
        p = wkt.loads(point_str)
        return Point(round(p.x, precision), round(p.y, precision))
    except:
        return None

def round_time(dt, minutes=30):
    # Rounds datetime to the nearest minutes slot
    return dt.replace(minute=(dt.minute // minutes) * minutes, second=0, microsecond=0)

@celery_app.task
def process_trips_task(ingestion_id: int, file_path: str):
    db = SessionLocal()
    try:
        status = db.query(IngestionStatus).get(ingestion_id)
        status.status = "processing"
        db.commit()

        chunk_size = 5000
        total_rows = sum(1 for _ in open(file_path)) - 1
        processed_rows = 0

        for chunk in pd.read_csv(file_path, chunksize=chunk_size):
            chunk['datetime'] = pd.to_datetime(chunk['datetime'])
            
            # 1. Store Raw Trips
            trips = []
            for _, row in chunk.iterrows():
                trip = Trip(
                    region=row['region'],
                    origin_coord=f"SRID=4326;{row['origin_coord']}",
                    destination_coord=f"SRID=4326;{row['destination_coord']}",
                    datetime=row['datetime'],
                    datasource=row['datasource']
                )
                trips.append(trip)
            db.bulk_save_objects(trips)
            
            # 2. Group and Store Summaries
            # We group by region, rounded coords, and time slot
            chunk['time_slot'] = chunk['datetime'].apply(lambda x: round_time(x))
            chunk['origin_rounded'] = chunk['origin_coord'].apply(lambda x: round_coords(x))
            chunk['dest_rounded'] = chunk['destination_coord'].apply(lambda x: round_coords(x))
            
            # Convert Shapely objects to WKT for grouping
            chunk['origin_wkt'] = chunk['origin_rounded'].apply(lambda x: x.wkt if x else None)
            chunk['dest_wkt'] = chunk['dest_rounded'].apply(lambda x: x.wkt if x else None)
            
            summary_group = chunk.groupby(['region', 'origin_wkt', 'dest_wkt', 'time_slot']).size().reset_index(name='trip_count')
            
            summaries = []
            for _, row in summary_group.iterrows():
                summary = TripSummary(
                    region=row['region'],
                    origin_coord=f"SRID=4326;{row['origin_wkt']}",
                    destination_coord=f"SRID=4326;{row['dest_wkt']}",
                    time_slot=row['time_slot'],
                    trip_count=row['trip_count']
                )
                summaries.append(summary)
            db.bulk_save_objects(summaries)
            
            db.commit()
            
            processed_rows += len(chunk)
            progress = int((processed_rows / total_rows) * 100)
            status.progress = min(progress, 100)
            status.updated_at = datetime.utcnow()
            db.commit()

            r.publish(f"ingestion_status_{ingestion_id}", json.dumps({
                "ingestion_id": ingestion_id,
                "progress": status.progress,
                "status": "processing"
            }))

        status.status = "completed"
        status.progress = 100
        db.commit()
        
        r.publish(f"ingestion_status_{ingestion_id}", json.dumps({
            "ingestion_id": ingestion_id,
            "progress": 100,
            "status": "completed"
        }))

    except Exception as e:
        status = db.query(IngestionStatus).get(ingestion_id)
        if status:
            status.status = "failed"
            db.commit()
        r.publish(f"ingestion_status_{ingestion_id}", json.dumps({
            "ingestion_id": ingestion_id,
            "status": "failed",
            "error": str(e)
        }))
        print(f"Error processing ingestion {ingestion_id}: {e}")
    finally:
        db.close()
        if os.path.exists(file_path):
            os.remove(file_path)
