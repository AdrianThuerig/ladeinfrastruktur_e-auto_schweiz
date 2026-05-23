"""
pipeline.py
===========
ETL-Pipeline-Klasse für den reproduzierbaren Datenverarbeitungsprozess.
"""


import pandas as pd
import geopandas as gpd

class DataPipeline:
    """
    Reproduzierbare ETL-Pipeline:
    - Filterung von Personenwagen und Mappen von TREIBSTOFF auf Antriebsarten
    - Geografische Verknüpfung (Spatial Join) und Aggregationen auf Gemeindeebene
    """

    def __init__(self):
        pass

    def filter_personenwagen(self, df):
        """Filtert Personenwagen und mappt TREIBSTOFF auf Antriebsarten."""
        # Nur Personenwagen filtern, falls Spalte vorhanden
        if 'Fahrzeugart' in df.columns:
            df = df[df['Fahrzeugart'].str.contains('Personenwagen', na=False, case=False)].copy()
        
        # Mappen von Treibstoff
        if 'Treibstoff' in df.columns:
            def map_treibstoff(val):
                val_str = str(val).lower()
                # 1. Reine Elektroautos (inkl. Range Extender)
                if val_str == 'elektrisch' or 'range extender' in val_str:
                    return 'Elektro'
                # 2. Hybride (Kombinationen von Elektro mit Verbrenner)
                elif 'elektrisch' in val_str and ('benzin' in val_str or 'diesel' in val_str):
                    return 'Hybrid'
                elif 'hybrid' in val_str:
                    return 'Hybrid'
                # 3. Klassische Verbrenner und andere
                else:
                    return 'Verbrenner'
            
            df['Antriebsart'] = df['Treibstoff'].apply(map_treibstoff)
            
        return df

    def spatial_join_gemeinden(self, df, geodf, lookup_df=None):
        """
        Geografische Verknüpfung und Aggregation.
        Unterstützt PLZ-Join oder Gemeinde-Join via Lookup (AMTOVZ).
        """
        if 'Antriebsart' not in df.columns:
            return df

        # Fall A: Wir haben ein Lookup-Table (AMTOVZ) um von PLZ auf BFS-Nr zu kommen
        if lookup_df is not None and 'PLZ' in df.columns:
            # 1. ASTRA PLZ bereinigen (viele sind anonymisiert wie '64..')
            df['PLZ_Prefix'] = df['PLZ'].astype(str).str[:2]
            
            # 2. AMTOVZ ebenfalls auf 2-Steller aggregieren
            lookup_df['PLZ2'] = lookup_df['PLZ4'].astype(str).str[:2]
            
            # 3. Aggregation des Bestands auf 2-Steller (Regionen)
            agg_df_prefix = df.groupby(['PLZ_Prefix', 'Antriebsart']).size().unstack(fill_value=0).reset_index()
            
            # 4. Proportionale Verteilung auf Gemeinden
            # Zuerst zählen, wie viele Gemeinden pro PLZ-Region existieren
            gemeinde_mapping = lookup_df[['BFS-Nr', 'PLZ2']].drop_duplicates()
            counts_per_prefix = gemeinde_mapping.groupby('PLZ2').size().reset_index(name='Municipality_Count')
            
            # Join mit dem Bestand und Division durch die Anzahl der Gemeinden
            agg_df = gemeinde_mapping.merge(agg_df_prefix, left_on='PLZ2', right_on='PLZ_Prefix', how='left')
            agg_df = agg_df.merge(counts_per_prefix, on='PLZ2', how='left')
            
            antriebs_cols = [col for col in ['Elektro', 'Hybrid', 'Verbrenner'] if col in agg_df.columns]
            for col in antriebs_cols:
                agg_df[col] = agg_df[col] / agg_df['Municipality_Count']
                
            # NA-Werte mit 0 füllen
            agg_df[antriebs_cols] = agg_df[antriebs_cols].fillna(0)
            
            # Join mit der Karte (SwissBOUNDARIES3D nutzt BFS_NUMMER)
            geodf['BFS_NUMMER'] = geodf['BFS_NUMMER'].astype(str)
            merged_gdf = geodf.merge(agg_df, left_on='BFS_NUMMER', right_on='BFS-Nr', how='left')
            
        # Fall B: Direkter PLZ-Join (wie bisher)
        elif 'PLZ' in df.columns and 'PLZ' in geodf.columns:
            agg_df = df.groupby(['PLZ', 'Antriebsart']).size().unstack(fill_value=0).reset_index()
            agg_df['PLZ'] = agg_df['PLZ'].astype(str)
            geodf['PLZ'] = geodf['PLZ'].astype(str)
            merged_gdf = geodf.merge(agg_df, on='PLZ', how='left')
        else:
            return df
            
        # NA-Werte mit 0 füllen
        antriebs_cols = [col for col in ['Elektro', 'Hybrid', 'Verbrenner'] if col in merged_gdf.columns]
        merged_gdf[antriebs_cols] = merged_gdf[antriebs_cols].fillna(0)
        
        return merged_gdf

    def run(self, astra_df, geodf, lookup_df=None):
        """Führt die komplette Pipeline aus."""
        print("-> Filtere Personenwagen und mappe Treibstoffe...")
        df_filtered = self.filter_personenwagen(astra_df)
        
        print("-> Aggergiere Daten und verknüpfe mit Regionen...")
        df_final = self.spatial_join_gemeinden(df_filtered, geodf, lookup_df)
        
        print("Pipeline erfolgreich durchlaufen!")
        return df_final
