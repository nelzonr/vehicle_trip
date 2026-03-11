from sqlalchemy import Column, Integer, String, DateTime, Index, Float
from geoalchemy2 import Geography
from .database import Base

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    region = Column(String, index=True)
    origin_coord = Column(Geography(geometry_type='POINT', srid=4326))
    destination_coord = Column(Geography(geometry_type='POINT', srid=4326))
    datetime = Column(DateTime, index=True)
    datasource = Column(String)
    
    __table_args__ = (
        Index('ix_trips_origin_coord', 'origin_coord', postgresql_using='gist'),
        Index('ix_trips_destination_coord', 'destination_coord', postgresql_using='gist'),
    )

class TripSummary(Base):
    __tablename__ = "trip_summaries"
    
    id = Column(Integer, primary_key=True)
    region = Column(String, index=True)
    # Representative coordinates (rounded)
    origin_coord = Column(Geography(geometry_type='POINT', srid=4326))
    destination_coord = Column(Geography(geometry_type='POINT', srid=4326))
    # Time slot (e.g., start of hour or 30min)
    time_slot = Column(DateTime, index=True)
    trip_count = Column(Integer, default=1)
    
    __table_args__ = (
        Index('ix_trip_summaries_origin_coord', 'origin_coord', postgresql_using='gist'),
        Index('ix_trip_summaries_destination_coord', 'destination_coord', postgresql_using='gist'),
        # Compound index for grouping logic
        Index('ix_trip_summaries_grouping', 'region', 'time_slot')
    )

class IngestionStatus(Base):
    __tablename__ = "ingestion_status"
    
    id = Column(Integer, primary_key=True)
    filename = Column(String)
    status = Column(String) # 'pending', 'processing', 'completed', 'failed'
    progress = Column(Integer, default=0) # 0 to 100
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
