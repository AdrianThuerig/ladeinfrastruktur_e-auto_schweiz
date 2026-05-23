"""
app.py
======
Hauptanwendung: Streamlit Dashboard – Ladeinfrastruktur der Zukunft.

Starten mit:
    streamlit run app.py
"""
import os
import streamlit as st
import pandas as pd
import geopandas as gpd

# Eigene Module importieren
# Eigene Module importieren
from src.data_loader import load_astra_data, load_bfe_data, load_bfs_data, load_boundary_data, load_amtovz_data
from src.pipeline import DataPipeline
from src.forecaster import GapForecaster
from src.visualizations.plots import InvestmentHeatmapPlot, GrowthOverTimePlot, EngineDistributionPlot


# Personalisiertes Laden der neuen Datenstruktur
@st.cache_data(show_spinner="Lade optimierte Parquet-Daten...")
def load_all_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Lade ASTRA Bestand
    astra_path = os.path.join(base_dir, "data", "BEST.parquet")
    astra_df = load_astra_data(astra_path)
    
    # 3. Lade BFE Ladestellen
    bfe_path = os.path.join(base_dir, "data", "ch.bfe.ladestellen-elektromobilitaet.parquet")
    bfe_gdf = load_bfe_data(bfe_path)
    
    # 4. Lade neue Gemeindedaten (SwissBOUNDARIES3D) und PLZ-Lookup (AMTOVZ)
    boundary_gdf = load_boundary_data()
    amtovz_df = load_amtovz_data()
    
    return astra_df, bfe_gdf, boundary_gdf, amtovz_df


@st.cache_data(show_spinner="Verarbeite Daten und durchlaufe ETL-Pipeline...")
def run_pipeline(_astra_df, _bfe_gdf, _boundary_gdf, _amtovz_df):
    pipeline = DataPipeline()
    
    # 1. Fahrzeuge aggregieren und mit Geodaten joinen (via PLZ -> BFS mapping)
    merged_gdf = pipeline.run(_astra_df, _boundary_gdf, _amtovz_df)
    
    # 2. Aggregation der BFE-Ladestationen auf Gemeinde-Ebene
    # Wir nutzen einen Spatial Join zwischen Ladestation-Punkten und Gemeinde-Polygonen
    if not _bfe_gdf.empty and not _boundary_gdf.empty:
        if _bfe_gdf.crs != _boundary_gdf.crs:
            _bfe_gdf = _bfe_gdf.to_crs(_boundary_gdf.crs)
            
        # Wir nutzten BFS_NUMMER als Schlüssel
        bfe_joined = gpd.sjoin(_bfe_gdf, _boundary_gdf[['BFS_NUMMER', 'geometry']], how="inner", predicate="intersects")
        infra_df = bfe_joined.groupby('BFS_NUMMER').size().reset_index(name='Anzahl_Ladestationen')
        # Wichtig: Typ-Gleichheit für Späteren Join (Pipeline nutzt Strings)
        infra_df['BFS_NUMMER'] = infra_df['BFS_NUMMER'].astype(str)
    else:
        infra_df = pd.DataFrame(columns=['BFS_NUMMER', 'Anzahl_Ladestationen'])
        
    return merged_gdf, infra_df


def main():
    st.set_page_config(
        page_title="Analytics Dashboard: Ladeinfrastruktur Schweiz",
        page_icon="⚡", # Icon im Tab lassen, aber Titel clean
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Lade und verarbeite Daten
    astra_df, bfe_gdf, boundary_gdf, amtovz_df = load_all_data()
    
    if astra_df.empty or boundary_gdf.empty:
        st.error("Daten konnten nicht vollständig geladen werden.")
        st.stop()
        
    merged_gdf, infra_df = run_pipeline(astra_df, bfe_gdf, boundary_gdf, amtovz_df)
    
    # ==========================
    # KANTONS-MAPPING
    # ==========================
    CANTON_MAP = {
        1: "Zürich", 2: "Bern", 3: "Luzern", 4: "Uri", 5: "Schwyz", 
        6: "Obwalden", 7: "Nidwalden", 8: "Glarus", 9: "Zug", 10: "Freiburg",
        11: "Solothurn", 12: "Basel-Stadt", 13: "Basel-Landschaft", 14: "Schaffhausen",
        15: "Appenzell Ausserrhoden", 16: "Appenzell Innerrhoden", 17: "Sankt Gallen",
        18: "Graubünden", 19: "Aargau", 20: "Thurgau", 21: "Tessin", 22: "Waadt",
        23: "Wallis", 24: "Neuenburg", 25: "Genf", 26: "Jura"
    }
    
    # Kanton-Name hinzufügen für Suche und Tooltips
    if 'KANTONSNUMMER' in merged_gdf.columns:
        merged_gdf['Kanton'] = merged_gdf['KANTONSNUMMER'].map(CANTON_MAP)

    # ==========================
    # DATEN-BEREINIGUNG
    # ==========================
    # 1. Entferne Einträge ohne Kantonsnummer oder Name (z.B. Seen oder technische Artefakte)
    if 'KANTONSNUMMER' in merged_gdf.columns:
        # Nur Kantone behalten, die in unserem Mapping (1-26) existieren
        valid_cantons = list(CANTON_MAP.keys())
        merged_gdf = merged_gdf[merged_gdf['KANTONSNUMMER'].isin(valid_cantons)].copy()
        
        # Sicherstellen, dass Name vorhanden ist
        merged_gdf = merged_gdf.dropna(subset=['NAME'])
        merged_gdf['KANTONSNUMMER'] = merged_gdf['KANTONSNUMMER'].astype(int)
    
    # 2. Entferne Regionen/Gemeinden, die keinerlei Fahrzeuge enthalten (Leere Datensätze)
    # Dies bereinigt die Liste in der Suche und in der Tabelle
    vehicle_cols = ['Elektro', 'Hybrid', 'Verbrenner']
    if all(col in merged_gdf.columns for col in vehicle_cols):
        total_vehicles = merged_gdf[vehicle_cols].sum(axis=1)
        merged_gdf = merged_gdf[total_vehicles > 0].copy()

    # Index zurücksetzen nach Bereinigung
    merged_gdf = merged_gdf.reset_index(drop=True)

    # ==========================
    # FORECASTING & FILTER (Sidebar)
    # ==========================
    st.sidebar.header("Karten-Optionen")
    map_level = st.sidebar.radio("Detaillierungsgrad", ["Gemeinde", "Kanton"], index=1)
    
    st.sidebar.header("Suche")
    if map_level == "Gemeinde":
        search_options = ["Alle"] + sorted(list(merged_gdf['NAME'].unique()))
        search_label = "Suche nach Gemeinde"
    else:
        # Kantonsnamen aus dem Mapping nehmen
        search_options = ["Alle"] + sorted(list(CANTON_MAP.values()))
        search_label = "Suche nach Kanton"

    search_query = st.sidebar.selectbox(search_label, options=search_options, index=0)

    st.sidebar.header("Prognose-Parameter")
    target_year = st.sidebar.slider("Zieljahr der Prognose", min_value=2024, max_value=2035, value=2030, step=1)
    growth_rate = st.sidebar.slider("Angenommenes jährliches Wachstum der Elektro-Fahrzeuge (%)", min_value=0, max_value=50, value=15, step=1) / 100.0
    
    st.sidebar.header("Anzeige-Optionen")
    show_surplus = st.sidebar.toggle("Überfluss an Ladestationen anzeigen", value=True)
    
    st.sidebar.header("Barrierefreiheit")
    color_safe_mode = st.sidebar.toggle("Barrierefreie Farben (Farbenblind-Modus)", value=False)

    # Aggregation auf Kantonsebene falls gewählt
    if map_level == "Kanton":
        # Typ-Sicherheit für KANTONSNUMMER
        if 'KANTONSNUMMER' in merged_gdf.columns:
            merged_gdf['KANTONSNUMMER'] = merged_gdf['KANTONSNUMMER'].fillna(0).astype(int)

        # Summierbare Spalten auswählen (Fahrzeuge)
        sum_cols = ['Elektro', 'Hybrid', 'Verbrenner']
        
        # Wir filtern den GDF auf die benötigten Spalten + Geometrie vor dem Dissolve
        # (Dies verhindert Fehler mit Datentypen wie datetime64 bei sum)
        available_cols = [c for c in (['KANTONSNUMMER', 'geometry'] + sum_cols) if c in merged_gdf.columns]
        merged_gdf = merged_gdf[available_cols]
        merged_gdf = merged_gdf.dissolve(by='KANTONSNUMMER', aggfunc='sum').reset_index()
        
        # Namen korrigieren (Kanton-Name aus Mapping)
        merged_gdf['NAME'] = merged_gdf['KANTONSNUMMER'].map(CANTON_MAP)
        
        # Infrastruktur auf Kantonsebene
        if not infra_df.empty:
            # BFS_NUMMER als String für den Join sicherstellen (da infra_df nun Strings hat)
            boundary_gdf_copy = boundary_gdf.copy()
            boundary_gdf_copy['BFS_NUMMER_STR'] = boundary_gdf_copy['BFS_NUMMER'].astype(str)
            
            infra_kanton = infra_df.merge(boundary_gdf_copy[['BFS_NUMMER_STR', 'KANTONSNUMMER']], left_on='BFS_NUMMER', right_on='BFS_NUMMER_STR', how='inner')
            infra_df = infra_kanton.groupby('KANTONSNUMMER')['Anzahl_Ladestationen'].sum().reset_index()
            # Typ-Gleichheit für join_key in forecaster
            infra_df['KANTONSNUMMER'] = infra_df['KANTONSNUMMER'].fillna(0).astype(int)

    # ==========================
    # PROGNOSE-BERECHNUNG
    # ==========================
    forecaster = GapForecaster()
    
    # Sicherstellen, dass Gemeinden eindeutig sind (Aggregation nach Name/BFS falls nötig)
    # Dies verhindert Duplikate bei Gemeinden mit mehreren PLZ
    if map_level == "Gemeinde":
        # Summierbare Spalten auswählen (Fahrzeuge)
        sum_cols = ['Elektro', 'Hybrid', 'Verbrenner']
        
        # Identifikations-Spalten
        id_cols = ['BFS_NUMMER', 'NAME', 'Kanton']
        
        # Wir filtern den GDF auf die benötigten Spalten + Geometrie vor dem Dissolve
        # (Dies verhindert Fehler mit Datentypen wie datetime64 bei sum und schützt IDs)
        available_cols = [c for c in (id_cols + ['geometry'] + sum_cols) if c in merged_gdf.columns]
        merged_gdf = merged_gdf[available_cols]
        
        # Bestimme Gruppierungsvariablen, die tatsächlich existieren
        group_by_cols = [c for c in id_cols if c in merged_gdf.columns]
        
        merged_gdf = merged_gdf.dissolve(by=group_by_cols, aggfunc='sum').reset_index()

    # 1. Berechnung für den gesamten Datensatz (Ungefiltert für Ranglisten)
    df_pred_full = forecaster.predict_future_density(merged_gdf, target_year, growth_rate)
    df_gap_full = forecaster.calculate_predicted_gap_index(df_pred_full, infra_df)
    
    # Begrenze den Index immer auf [-100, 100] für konsistente Farbskalen
    if 'Predicted_Gap_Index' in df_gap_full.columns:
        df_gap_full['Predicted_Gap_Index'] = df_gap_full['Predicted_Gap_Index'].clip(lower=-100, upper=100)
    
    # 2. Suche/Filter anwenden für die restlichen UI-Elemente
    if search_query != "Alle":
        df_gap = df_gap_full[df_gap_full['NAME'] == search_query].reset_index(drop=True)
    else:
        df_gap = df_gap_full.copy()
    
    # Überfluss-Anzeige Logik (auf gefilterte Daten)
    if not show_surplus:
        df_gap['Predicted_Gap_Index'] = df_gap['Predicted_Gap_Index'].clip(lower=0)
        df_gap['Predicted_Gap'] = df_gap['Predicted_Gap'].clip(lower=0)
    
    # Numerische Konsistenz erzwingen (Ganze Zahlen)
    for col in ['Elektro', 'Hybrid', 'Verbrenner', 'Elektro_Prognose', 'Hybrid_Prognose', 'Verbrenner_Prognose', 'Anzahl_Ladestationen', 'Predicted_Gap']:
        for df in [df_gap, df_gap_full]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).round(0).astype(int)
    
    for df in [df_gap, df_gap_full]:
        if 'NAME' in df.columns:
            df['NAME'] = df['NAME'].astype(str)

    # ==========================
    # UI LAYOUT & VISUALISIERUNG
    # ==========================
    st.title("Analytics Dashboard: Ladeinfrastruktur Schweiz")
    st.markdown(f"""
    Dieses interaktive Dashboard zeigt die Verteilung von Fahrzeugantrieben in der Schweiz und prognostiziert den zukünftigen Bedarf an Ladeinfrastruktur pro {map_level}.
    
    *Wichtiger Datenhinweis: Die letzten realen Bestandsdaten des ASTRA stammen aus dem Jahr 2024. Alle Daten, Berechnungen und Visualisierungen für die darauffolgenden Jahre stellen eine Prognose und Simulation für das gewählte Zieljahr {target_year} dar.*
    
    *Hinweis: Die Verteilung der Antriebsarten auf Gemeindeebene basiert auf einer proportionalen Schätzung via PLZ-Regionen.*
    """)

    # Bedarf Index Erklärung
    with st.expander("Details zur Berechnung des Bedarf Index"):
        st.write(f"""
        Der **Bedarf Index (-100 bis 100)** bewertet die regionale Lade-Infrastruktur auf Basis der {map_level}sebene:
        1. **Nachfrage-Prognose**: Der BEV-Bestand wird mit der gewählten Wachstumsrate zum Zieljahr hochgerechnet. (Auf Gemeindeebene erfolgt eine proportionale Verteilung der ASTRA-Regionaldaten).
        2. **Kapazitäts-Bedarf**: Es wird ein Verhältnis von 1 öffentlicher Ladestation pro 20 Elektroautos angesetzt.
        3. **Gap-Analyse**: Die Differenz zwischen berechnetem Bedarf und existierenden Stationen ergibt den absoluten 'Gap' (Fehlende Plätze).
        4. **Index-Skalierung**: Der höchste absolute Gap-Wert in der Schweiz auf der gewählten Ebene ({map_level}) entspricht dem Index 100. Werte um 0 bedeuten eine bedarfsgerechte Abdeckung.
        """)

    # ==========================
    # KACHELN (METRIKEN) STYLE
    # ==========================
    st.markdown("""
    <style>
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
        height: 165px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        background-color: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(0, 204, 150, 0.4);
    }
    [data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricDelta"] {
        font-weight: 500 !important;
    }
    /* Fix for vertical alignment when delta is missing */
    [data-testid="stMetric"] > div {
        width: 100%;
    }
    
    /* Tabs besser sichtbar machen (Clean & Neutral) */
    button[data-baseweb="tab"] {
        font-size: 1.15rem !important;
        font-weight: 600 !important;
        color: rgba(255, 255, 255, 0.6) !important;
        border-bottom: 3px solid rgba(255, 255, 255, 0.05) !important;
        padding: 12px 24px !important;
        background-color: rgba(255, 255, 255, 0.01) !important;
        border-radius: 8px 8px 0 0 !important;
        margin-right: 4px !important;
        transition: all 0.2s ease-in-out !important;
    }
    button[data-baseweb="tab"]:hover {
        color: rgba(255, 255, 255, 0.9) !important;
        background-color: rgba(255, 255, 255, 0.04) !important;
        border-bottom-color: rgba(255, 255, 255, 0.2) !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #ffffff !important;
        background-color: rgba(255, 255, 255, 0.08) !important;
        border-bottom: 3px solid #ffffff !important;
        box-shadow: 0 4px 12px rgba(255, 255, 255, 0.05) !important;
    }
    /* Tab-Leiste Hintergrund und Abstände */
    div[data-baseweb="tab-list"] {
        background-color: rgba(0, 0, 0, 0.2) !important;
        padding: 6px 6px 0 6px !important;
        border-radius: 12px 12px 0 0 !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Top-Level Metriken (Immer schweizweite Gesamtzahlen)
    total_bevs = df_gap_full.get('Elektro', pd.Series([0])).sum()
    pred_bevs = df_gap_full.get('Elektro_Prognose', pd.Series([0])).sum()
    total_infra = df_gap_full.get('Anzahl_Ladestationen', pd.Series([0])).sum()
    # Wir nehmen für die Metrik nur die Gaps (>0), um den Gesamtausbaubedarf zu zeigen
    gap_infra = df_gap_full.get('Predicted_Gap', pd.Series([0])).clip(lower=0).sum()
    
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Elektrofahrzeuge (2024)", f"{int(total_bevs):,}".replace(",", "'"))
    
    # Delta für Prognose (Mehr E-Autos = Verbesserung -> Grün)
    bev_diff = pred_bevs - total_bevs
    bev_pct = (bev_diff / total_bevs * 100) if total_bevs > 0 else 0
    col2.metric(
        f"Prognose Elektro ({target_year})", 
        f"{int(pred_bevs):,}".replace(",", "'"),
        delta=f"+{int(bev_diff):,}".replace(",", "'") + f" ({bev_pct:.1f}%)",
        delta_color="normal"
    )
    
    # Ladestationen (Ist) - Ohne Delta
    col3.metric(
        "Ladestationen (Ist)", 
        f"{int(total_infra):,}".replace(",", "'")
    )
    
    # Delta für Bedarf (Zusätzlicher Bedarf/Gap = Verschlechterung/Handlungsbedarf -> Rot)
    col4.metric(
        "Zusätzlicher Bedarf", 
        f"{int(max(0, gap_infra)):,}".replace(",", "'"),
        delta=f"+{int(gap_infra):,}".replace(",", "'"),
        delta_color="inverse"
    )

    st.divider()

    # Tabs für verschiedene Ansichten
    tab1, tab2, tab3 = st.tabs(["Bedarfs-Heatmap", "Antriebs-Verteilung", "Simulations-Trend"])

    with tab1:
        st.subheader(f"Bedarfs-Analyse der Infrastruktur ({map_level})")
        st.info(f"Die Karte visualisiert den Bedarf an Ladeplätzen im Jahr {target_year}. Die Legende passt sich dynamisch an.")
        
        # Bestimme den Farbbereich immer auf Basis der ungefilterten nationalen Daten
        if not df_gap_full.empty:
            full_min = df_gap_full['Predicted_Gap_Index'].min()
            full_max = df_gap_full['Predicted_Gap_Index'].max()
            
            # Berücksichtige die show_surplus-Option für den globalen Bereich
            if not show_surplus:
                global_range = [0, full_max] if full_max > 0 else [0, 1]
            elif color_safe_mode:
                global_range = [full_min, full_max] if full_min < full_max else [0, 1]
            elif full_min < 0:
                limit = max(abs(full_min), abs(full_max))
                global_range = [-limit, limit]
            else:
                global_range = [0, full_max] if full_max > 0 else [0, 1]
        else:
            global_range = None

        # Umwandlung zurück in GeoDataFrame für Plotly
        final_gdf = gpd.GeoDataFrame(df_gap, geometry='geometry')
        
        # Wir nutzen 'NAME' für den Hover und 'Predicted_Gap_Index' (Bedarf Index) für die Farbe
        heatmap_plot = InvestmentHeatmapPlot(
            final_gdf, 
            color_col="Predicted_Gap_Index", 
            hover_name="NAME", 
            color_safe_mode=color_safe_mode,
            range_color=global_range
        )
        st.plotly_chart(heatmap_plot.render(), use_container_width=True)

        st.divider()
        st.subheader("Datentabelle (Details)")
        
        # Auswahl und Umbenennung der Spalten für die Tabelle
        display_df = df_gap.copy()
        if "Predicted_Gap" in display_df.columns:
            display_df = display_df.sort_values(by="Predicted_Gap", ascending=False)
        cols_to_show = {
            "NAME": "Gebiet",
            "Elektro": "Ist-Bestand Elektro",
            "Elektro_Prognose": f"Prognose {target_year}",
            "Anzahl_Ladestationen": "Ladestationen (Ist)",
            "Predicted_Gap": "Bedarf (Plätze)",
            "Predicted_Gap_Index": "Bedarf Index"
        }
        # Nur vorhandene Spalten nehmen
        available_display_cols = [c for c in cols_to_show.keys() if c in display_df.columns]
        table_df = display_df[available_display_cols].rename(columns=cols_to_show)
        

        # Pagination Logik
        items_per_page = 50
        num_items = len(table_df)
        num_pages = (num_items // items_per_page) + (1 if num_items % items_per_page > 0 else 0)
        
        if num_pages > 1:
            col_page, col_info = st.columns([1, 5])
            current_page = col_page.number_input("Seite", min_value=1, max_value=num_pages, value=1, step=1)
            start_row = (current_page - 1) * items_per_page
            end_row = min(start_row + items_per_page, num_items)
            table_page_df = table_df.iloc[start_row:end_row].copy()
            # Index auf 1-basiert umstellen
            table_page_df.index = range(start_row + 1, end_row + 1)
            col_info.write(f"Anzeige von {start_row + 1} bis {end_row} von {num_items} Einträgen")
        else:
            table_page_df = table_df.copy()
            table_page_df.index = range(1, len(table_page_df) + 1)

        # Statische Tabelle (st.table) des aktuellen Ausschnitts
        st.table(
            table_page_df.style.format({
                f"Prognose {target_year}": "{:,.0f}",
                "Ist-Bestand Elektro": "{:,.0f}",
                "Ladestationen (Ist)": "{:,.0f}",
                "Bedarf (Plätze)": "{:,.0f}",
                "Bedarf Index": "{:,.1f}"
            })
        )

    with tab2:
        st.subheader("Analyse der Antriebsarten")
        
        with st.expander("Wie wird die Prognose berechnet?"):
            st.write(f"""
            Die Simulation zeigt den Trend bis 2035 basierend auf folgenden Annahmen:
            - **Elektro (BEV)**: Wächst jährlich um den in der Sidebar gewählten Wert (**{growth_rate*100:.1f}%**).
            - **Hybrid**: Es wird ein moderates, bevölkerungs- und technologiewachstumsbedingtes Plus von **2%** pro Jahr angenommen.
            - **Verbrenner**: Hier wird eine schrittweise Abnahme von **5%** pro Jahr simuliert (Substitution durch alternative Antriebe).
            - **Total**: Der Gesamtbestand ergibt sich aus der Summe der Kategorien. In einer wachsenden Bevölkerung (Szenario Schweiz) steigt die Gesamtzahl der Motorfahrzeuge tendenziell an, sofern die Zunahme der E-Fahrzeuge die Abnahme der Verbrenner übersteigt.
            """)
        
        # Die Daten richten sich nach der Auswahl in der Sidebar (search_query)
        pie_cols = ["Elektro_Prognose", "Hybrid_Prognose", "Verbrenner_Prognose"]
        pie_data = df_gap # Bereits durch Sidebar gefiltert
        total_val = int(pie_data[pie_cols].sum().sum())
        
        if search_query == "Alle":
            st.subheader(f"Gesamtverteilung im Jahr {target_year} (Total: {total_val:,})".replace(",", "'"))
        else:
            st.subheader(f"Verteilung für {search_query} im Jahr {target_year} (Total: {total_val:,})".replace(",", "'"))

        pie_plot = EngineDistributionPlot(pie_data, value_cols=pie_cols, color_safe_mode=color_safe_mode)
        st.plotly_chart(pie_plot.render(), use_container_width=True)
        
        st.divider()
        st.subheader("Vergleich der Kantone")
        st.markdown(f"Top Kantone nach prognostiziertem Elektroauto-Bestand ({target_year}).")
        
        # Daten für den Kantons-Vergleich vorbereiten (IMMER auf den vollen Daten, ungefiltert)
        if map_level == "Gemeinde" and "Kanton" in df_gap_full.columns:
            # Aggregation der Gemeinden auf Kantonsebene für diesen spezifischen Plot
            kantone_bar_data = df_gap_full.groupby("Kanton")[pie_cols].sum().reset_index()
            bar_x_col = "Kanton"
        else:
            # Wenn Map bereits auf Kanton ist, nutzen wir NAME
            kantone_bar_data = df_gap_full
            bar_x_col = "NAME"

        # Sortierte Bar-Anzeige basierend auf der Prognose
        bar_data = kantone_bar_data.sort_values(by="Elektro_Prognose", ascending=False).head(26) # Alle Kantone möglich
        
        import plotly.express as px
        
        # Barrierefreies Farbschema für den Bar Chart
        if color_safe_mode:
            bar_colors = ["#0072B2", "#E69F00", "#56B4E9"]
        else:
            bar_colors = ["#00CC96", "#AB63FA", "#EF553B"]

        fig_bar = px.bar(
            bar_data, 
            x=bar_x_col, 
            y=pie_cols,
            title=f"Antriebsarten nach Kanton ({target_year})",
            color_discrete_sequence=bar_colors,
            labels={"value": "Anzahl", "variable": "Antrieb", bar_x_col: "Kanton"}
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with tab3:
        st.subheader("Simulations-Trend der Antriebsarten")
        
        with st.expander("Wie wird die Prognose berechnet?"):
            st.write(f"""
            Die Simulation zeigt den Trend bis 2035 basierend auf folgenden Annahmen:
            - **Elektro (BEV)**: Wächst jährlich um den in der Sidebar gewählten Wert (**{growth_rate*100:.1f}%**).
            - **Hybrid**: Es wird ein moderates, bevölkerungs- und technologiewachstumsbedingtes Plus von **2%** pro Jahr angenommen.
            - **Verbrenner**: Hier wird eine schrittweise Abnahme von **5%** pro Jahr simuliert (Substitution durch alternative Antriebe).
            - **Total**: Der Gesamtbestand ergibt sich aus der Summe der Kategorien. In einer wachsenden Bevölkerung (Szenario Schweiz) steigt die Gesamtzahl der Motorfahrzeuge tendenziell an, sofern die Zunahme der E-Fahrzeuge die Abnahme der Verbrenner übersteigt.
            """)
        
        # Wir fixieren den Simulationszeitraum bis 2035 für eine saubere Darstellung
        sim_years = list(range(2024, 2036))
        sim_data = []
        
        # Lokale Berechnung für den Chart
        total_e = merged_gdf['Elektro'].sum()
        total_h = merged_gdf['Hybrid'].sum()
        total_v = merged_gdf['Verbrenner'].sum()
        
        for y in sim_years:
            e_val = total_e * ((1 + growth_rate) ** (y - 2024))
            h_val = total_h * ((1 + 0.02) ** (y - 2024))
            v_val = max(0, total_v * (0.95 ** (y - 2024)))
            sim_data.append({
                "Jahr": y,
                "Elektro": e_val,
                "Hybrid": h_val,
                "Verbrenner": v_val,
                "Gesamt": e_val + h_val + v_val
            })
            
        df_time = pd.DataFrame(sim_data)
        
        area_plot = GrowthOverTimePlot(df_time, x_col="Jahr", y_cols=["Elektro", "Hybrid", "Verbrenner"], color_safe_mode=color_safe_mode)
        fig_area = area_plot.render()
        
        # Vertikale Linie für das aktuell gewählte Zieljahr
        fig_area.add_vline(x=target_year, line_dash="dash", line_color="white", annotation_text=f"Zieljahr {target_year}")
        
        st.plotly_chart(fig_area, use_container_width=True)


if __name__ == "__main__":
    main()
