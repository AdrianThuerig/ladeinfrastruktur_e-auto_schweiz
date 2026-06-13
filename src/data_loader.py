"""
data_loader.py
==============
Modul zum Laden der Rohdaten aus verschiedenen Quellen (ASTRA, BFE, BFS).
"""

import os
import pandas as pd
import geopandas as gpd

def load_astra_data(filepath: str):
    """Lädt die ASTRA-Fahrzeugbestandsdaten aus Parquet."""
    if os.path.exists(filepath):
        try:
            return pd.read_parquet(filepath)
        except Exception as e:
            print(f"Fehler beim Laden von {filepath}: {e}")
    return pd.DataFrame()


def load_bfe_data(filepath: str):
    """Lädt die BFE-Ladestellen-Daten aus Parquet."""
    if os.path.exists(filepath):
        try:
            return gpd.read_parquet(filepath)
        except Exception as e:
            print(f"Fehler beim Laden von {filepath}: {e}")
    return gpd.GeoDataFrame()


def load_boundary_data():
    """Lädt die optimierten SwissBOUNDARIES3D Gemeindedaten."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parquet_path = os.path.join(base_dir, "data", "swissboundaries.parquet")
    
    if os.path.exists(parquet_path):
        return gpd.read_parquet(parquet_path)
    return gpd.GeoDataFrame()


def load_amtovz_data():
    """Lädt das AMTOVZ PLZ-Verzeichnis als Lookup-Table (aus Parquet)."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parquet_path = os.path.join(base_dir, "data", "AMTOVZ_CSV_LV95.parquet")
    
    if os.path.exists(parquet_path):
        df = pd.read_parquet(parquet_path)
        # Typen sicherstellen für Joins
        df['PLZ4'] = df['PLZ4'].astype(str)
        df['BFS-Nr'] = df['BFS-Nr'].astype(str)
        return df
    return pd.DataFrame()

