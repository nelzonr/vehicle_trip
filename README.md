# Jobsity Data Engineering & Software Engineering Project

A scalable solution for ingesting and reporting on trip data using Python, FastAPI, PostGIS, and Celery.

## Architecture

- **FastAPI:** Handles REST endpoints and WebSocket notifications.
- **PostGIS:** Efficiently stores and queries spatial data at scale (up to 100M+).
- **Celery + Redis:** Asynchronous background processing for data ingestion.
- **WebSockets:** Real-time updates for ingestion status (no polling).
- **Grouped Data Model:** During ingestion, similar trips (spatial & temporal proximity) are aggregated into a `trip_summaries` table to ensure report performance even with 100M+ raw records.

## Requirements

- Docker & Docker Compose
- Python 3.11 (for CLI usage)

## Quick Start

1.  **Build and Start Services:**
    ```bash
    docker-compose up -d --build
    ```

2.  **Install Local Dependencies (for CLI):**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run Ingestion using CLI:**
    ```bash
    python cli/main.py ingest trips.csv
    ```

4.  **View Reports using CLI:**
    ```bash
    python cli/main.py report --region Prague
    ```

## API Endpoints

- `POST /ingest`: Upload a CSV for background processing.
- `GET /report/weekly_average`: Get weekly average trips (supports region or bounding box).
- `WS /ws/status/{ingestion_id}`: Real-time progress updates.

## Scalability Proofs (100M Entries)

The solution is designed for scalability through:
1.  **Database Indexing:** GIST indexes for spatial data and B-Tree for timestamps.
2.  **Ingestion in Chunks:** Data is processed in 5,000-row chunks to prevent memory issues.
3.  **Pre-Aggregation:** Reports query the `trip_summaries` table, which is significantly smaller than the raw `trips` table while maintaining the required precision.

### Testing Escalability

1.  **Generate Synthetic Data (e.g., 1 million rows):**
    ```bash
    python scripts/generate_data.py --count 1000000 --output data/large_trips.csv
    ```
2.  **Run Load Tests:**
    ```bash
    locust -f scripts/locustfile.py --host http://localhost:8000
    ```
3.  **Verify Database Execution Plans:**
    Connect to the database and use `EXPLAIN ANALYZE` on spatial queries to confirm index usage.
    ```sql
    EXPLAIN ANALYZE SELECT * FROM trip_summaries WHERE ST_Within(origin_coord, ST_MakeEnvelope(5, 40, 20, 55, 4326));
    ```

## Development

All commands and code are in English.
SQL database is PostGIS enabled.
WebSocket implementation avoids client-side polling.
Grouping logic is applied during the ingestion phase for maximum performance.
