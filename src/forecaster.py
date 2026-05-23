"""
forecaster.py
=============
Modelle für die Darstellung der historischen Entwicklung und Berechnung 
eines einfachen Predicted Gap Index.
"""

import pandas as pd


class GapForecaster:
    """
    Klasse für die Berechnung der zukünftigen E-Fahrzeugdichte pro Gemeinde 
    und des Predicted Gap Index basierend auf einem einfachen Wachstumstrend.
    Der Fokus liegt auf historischen Daten und einer simplen Fortschreibung.
    """

    def predict_future_density(self, current_data: pd.DataFrame, target_year: int = 2030, growth_rate: float = 0.10):
        """
        Erstellt eine einfache Prognose der zukünftigen E-Fahrzeugdichte.
        Wir nutzen eine simple konstante Wachstumsrate ausgehend vom aktuellen Jahr.
        
        current_data: DataFrame mit aktuellen Beständen (z.B. Spalte 'BEV')
        target_year: Das Ziel-Jahr der Prognose
        growth_rate: Angenommenes jährliches Wachstum (z.B. 10% = 0.10)
        """
        df_pred = current_data.copy()
        
        # Annahme: Wir befinden uns im Jahr der letzten ASTRA-Daten (z.B. 2024)
        current_year = 2024
        years_ahead = target_year - current_year
        
        if years_ahead < 0:
            years_ahead = 0
            
        if 'Elektro' in df_pred.columns:
            # Einfache exponentielle/lineare Fortschreibung
            growth_factor = (1 + growth_rate) ** years_ahead
            df_pred['Elektro_Prognose'] = df_pred['Elektro'] * growth_factor
        
        if 'Hybrid' in df_pred.columns:
             # Leichte Annahme: Hybrid nimmt moderat zu
             df_pred['Hybrid_Prognose'] = df_pred['Hybrid'] * (1.02 ** years_ahead)
             
        if 'Verbrenner' in df_pred.columns:
             # Leichte Annahme: Verbrenner nehmen ab
             df_pred['Verbrenner_Prognose'] = df_pred['Verbrenner'] * (0.95 ** years_ahead)
        
        return df_pred

    def calculate_predicted_gap_index(self, df_pred: pd.DataFrame, df_infra: pd.DataFrame):
        """
        Berechnet den "Predicted Gap Index": 
        Diskrepanz zwischen prognostiziertem BEV-Bestand und aktueller Infrastruktur.
        
        df_pred: DataFrame mit Prognose-Werten (Spalte 'BEV_Prognose')
        df_infra: DataFrame mit aktueller Infrastruktur (Spalte 'Anzahl_Ladestationen')
        """
        # Dynamische Ermittlung des Schlüssels (BFS_NUMMER, PLZ oder KANTONSNUMMER)
        join_key = None
        for key in ['BFS_NUMMER', 'PLZ', 'KANTONSNUMMER']:
            if key in df_pred.columns and key in df_infra.columns:
                join_key = key
                break
        
        if join_key:
            df_gap = pd.merge(df_pred, df_infra, on=join_key, how='left')
        else:
            # Fallback falls kein gemeinsamer Schlüssel gefunden wurde
            df_gap = df_pred.copy()
        
        if 'Anzahl_Ladestationen' in df_gap.columns:
            # Gemeinden ohne Ladestationen auf 0 setzen
            df_gap['Anzahl_Ladestationen'] = df_gap['Anzahl_Ladestationen'].fillna(0)
            
            # Gap = Prognostizierter Bedarf - Aktuelle Kapazität
            # Vereinfachte Annahme: 1 Ladestation reicht für ca. 20 E-Fahrzeuge
            capacity_per_station = 20
            bedarf_ladestationen = df_gap.get('Elektro_Prognose', 0) / capacity_per_station
            
            # Wie viele zusätzliche Ladestationen werden benötigt?
            df_gap['Predicted_Gap'] = bedarf_ladestationen - df_gap['Anzahl_Ladestationen']
            
            # Den Gap auf eine Skala von 0 bis 100 normalisieren für die Heatmap
            # Wir nutzen den absoluten Maximalwert für eine konsistente Skalierung, 
            # erlauben aber negative Werte (Überfluss)
            max_gap = df_gap['Predicted_Gap'].max()
            if max_gap > 0:
                df_gap['Predicted_Gap_Index'] = (df_gap['Predicted_Gap'] / max_gap) * 100
            else:
                # Falls alles Überfluss ist, skalieren wir relativ zum Minimum
                min_gap = df_gap['Predicted_Gap'].min()
                if abs(min_gap) > 0:
                    df_gap['Predicted_Gap_Index'] = (df_gap['Predicted_Gap'] / abs(min_gap)) * 100
                else:
                    df_gap['Predicted_Gap_Index'] = 0
                
        return df_gap
