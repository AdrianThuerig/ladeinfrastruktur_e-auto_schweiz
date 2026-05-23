import os
import time
import pandas as pd
import geopandas as gpd
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from data_preprocessing import preprocess_all_data
from data_loader import load_astra_data, load_bfe_data, load_bfs_data

def verify():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "dashboard", "data")
    
    print("--- Performance Verification ---")
    
    start_total = time.time()
    
    # 1. Preprocessing check (should be instant if files exist)
    start = time.time()
    preprocess_all_data()
    print(f"Preprocessing check: {time.time() - start:.4f}s")
    
    # 2. Load ASTRA data
    astra_path = os.path.join(data_dir, "BEST.txt")
    start = time.time()
    df_astra = load_astra_data(astra_path)
    print(f"ASTRA Data (Parquet): {time.time() - start:.4f}s - Rows: {len(df_astra)}")
    
    # 3. Load BFE data
    bfe_path = os.path.join(data_dir, "ch.bfe.ladestellen-elektromobilitaet.json")
    start = time.time()
    gdf_bfe = load_bfe_data(bfe_path)
    print(f"BFE Data (Parquet): {time.time() - start:.4f}s - Rows: {len(gdf_bfe)}")
    
    # 4. Load BFS data (remote url)
    bfs_url = "https://raw.githubusercontent.com/zazuko/swiss-maps/master/2023/ch-plz.geojson"
    start = time.time()
    gdf_bfs = load_bfs_data(bfs_url)
    print(f"BFS Data (Parquet/Cache): {time.time() - start:.4f}s - Rows: {len(gdf_bfs)}")
    
    total_time = time.time() - start_total
    print(f"--- Total Loading Time: {total_time:.4f}s ---")
    
    if total_time < 5:
        print("Success: Loading time is very fast!")
    else:
        print("Warning: Loading time is higher than expected.")

if __name__ == "__main__":
    verify()
