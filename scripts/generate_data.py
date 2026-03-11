import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import argparse

def generate_trips(count, output_file):
    regions = ['Prague', 'Turin', 'Hamburg', 'Berlin', 'Madrid', 'Paris']
    datasources = ['funny_car', 'baba_car', 'cheap_mobile', 'bad_diesel_vehicles', 'pt_search_app']
    
    # Coordinates range (roughly Europe)
    lat_min, lat_max = 40.0, 55.0
    lon_min, lon_max = 5.0, 20.0
    
    start_date = datetime(2023, 1, 1)
    
    def get_random_point():
        lat = random.uniform(lat_min, lat_max)
        lon = random.uniform(lon_min, lon_max)
        return f"POINT ({lon} {lat})"

    chunk_size = 100000
    first_chunk = True
    
    for i in range(0, count, chunk_size):
        current_chunk_size = min(chunk_size, count - i)
        data = {
            'region': [random.choice(regions) for _ in range(current_chunk_size)],
            'origin_coord': [get_random_point() for _ in range(current_chunk_size)],
            'destination_coord': [get_random_point() for _ in range(current_chunk_size)],
            'datetime': [start_date + timedelta(minutes=random.randint(0, 525600)) for _ in range(current_chunk_size)],
            'datasource': [random.choice(datasources) for _ in range(current_chunk_size)]
        }
        df = pd.DataFrame(data)
        df.to_csv(output_file, mode='a', index=False, header=first_chunk)
        first_chunk = False
        print(f"Generated {i + current_chunk_size} / {count} rows")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1000, help="Number of trips to generate")
    parser.add_argument("--output", type=str, default="synthetic_trips.csv", help="Output file name")
    args = parser.parse_args()
    
    generate_trips(args.count, args.output)
