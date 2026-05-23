# ⚡ Dashboard: Ladeinfrastruktur der Zukunft

Interaktives Streamlit-Dashboard zur Analyse und Prognose der Schweizer
Ladeinfrastruktur für Elektrofahrzeuge auf Gemeindeebene.

## Voraussetzungen

- Python 3.10+

## Installation

```bash
pip install -r requirements.txt
```

## Starten

```bash
streamlit run app.py
```

## Projektstruktur

```
dashboard/
├── app.py                  # Streamlit Hauptanwendung
├── requirements.txt        # Python-Abhängigkeiten
├── data/                   # Rohdaten
│   ├── BEST.txt            # ASTRA-Fahrzeugbestand
│   └── *.json              # BFE-Ladestellen
└── src/                    # Source-Code
    ├── data_loader.py      # Daten-Ladefunktionen
    ├── pipeline.py         # ETL-Pipeline
    ├── forecaster.py       # Prognose-Modelle
    └── visualizations/     # Plot-Klassen
        ├── base_plot.py    # Abstrakte Basisklasse
        └── plots.py        # Konkrete Visualisierungen
```

## Datenquellen

- **ASTRA**: Fahrzeugbestand (opendata.astra.admin.ch)
- **BFE**: Ladestellen Elektromobilität
- **BFS**: Gemeindegrenzen (Geodaten)

## Autor

Adrian Thürig – MAS Data Science, ZHAW
