import typer
import requests
import websocket
import json
import os
from typing import Optional
import time

app = typer.Typer()
API_URL = os.getenv("API_URL", "http://localhost:8000")
WS_URL = os.getenv("WS_URL", "ws://localhost:8000")


@app.command()
def ingest(file_path: str):
    if not os.path.exists(file_path):
        typer.echo(f"File {file_path} not found")
        return

    typer.echo(f"Uploading {file_path}...")
    with open(file_path, "rb") as f:
        response = requests.post(f"{API_URL}/ingest", files={"file": f})

    if response.status_code != 200:
        typer.echo(f"Error starting ingestion: {response.text}")
        return

    data = response.json()
    ingestion_id = data["ingestion_id"]
    typer.echo(f"Ingestion started with ID: {ingestion_id}")

    # Connect to WebSocket for progress
    ws = websocket.create_connection(f"{WS_URL}/ws/status/{ingestion_id}")

    try:
        with typer.progressbar(length=100, label="Ingesting data") as progress:
            current_progress = 0
            while True:
                result = ws.recv()
                status_data = json.loads(result)

                new_progress = status_data.get("progress", 0)
                if new_progress > current_progress:
                    progress.update(new_progress - current_progress)
                    current_progress = new_progress

                if status_data.get("status") == "completed":
                    progress.update(100 - current_progress)
                    typer.echo("\nIngestion completed successfully!")
                    break
                elif status_data.get("status") == "failed":
                    typer.echo(f"\nIngestion failed: {status_data.get('error')}")
                    break
    except Exception as e:
        typer.echo(f"\nConnection lost: {e}")
    finally:
        ws.close()


@app.command()
def report(
    region: Optional[str] = typer.Option(
        None, "--region", help="Filter by region name"
    ),
    min_lat: Optional[float] = typer.Option(None, "--min-lat", help="Minimum latitude"),
    min_lon: Optional[float] = typer.Option(
        None, "--min-lon", help="Minimum longitude"
    ),
    max_lat: Optional[float] = typer.Option(None, "--max-lat", help="Maximum latitude"),
    max_lon: Optional[float] = typer.Option(
        None, "--max-lon", help="Maximum longitude"
    ),
):
    """Generate weekly average trips report with optional filters."""
    params = {}

    if region:
        params["region"] = region
    if min_lat is not None:
        params["min_lat"] = min_lat
    if min_lon is not None:
        params["min_lon"] = min_lon
    if max_lat is not None:
        params["max_lat"] = max_lat
    if max_lon is not None:
        params["max_lon"] = max_lon

    typer.echo(f"Fetching report with params: {params}")

    try:
        response = requests.get(f"{API_URL}/report/weekly_average", params=params)
        response.raise_for_status()
    except requests.RequestException as e:
        typer.echo(f"Error fetching report: {e}")
        raise typer.Exit(code=1)

    data = response.json()

    typer.echo("-" * 50)
    typer.echo(f"Weekly Average Trips: {data['weekly_average']:.2f}")
    typer.echo(f"Total Trips: {data['total_trips']:,}")
    typer.echo(f"Total Weeks: {data['total_weeks']}")
    typer.echo("-" * 50)

    if data.get("details"):
        typer.echo("📋 Details by week:")
        for detail in data["details"]:
            typer.echo(f"  Week {detail['week']}: {detail['trips']:,} trips")


if __name__ == "__main__":
    app()
