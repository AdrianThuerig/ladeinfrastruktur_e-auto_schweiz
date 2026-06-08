# ⚡ Dashboard: Charging Infrastructure of the Future

Interactive Streamlit dashboard for analyzing and forecasting the Swiss charging infrastructure for electric vehicles at the municipality level.

## Prerequisites

- Python 3.10+ (must be installed on the target system and available in PATH)

## Quick Start (Cross-Platform)

You can launch the dashboard with a single click using the launcher scripts. The script will automatically create a virtual environment (`.venv`), verify/install all dependencies, and start the Streamlit application.

- **macOS / Linux**: Double-click `start.command` (or run `./start.command` in the terminal).
- **Windows**: Double-click `start.bat`.

Alternatively, run the Python launcher script directly:
```bash
python start.py
```

## Manual Installation & Startup (Optional)

If you prefer to set up and run the application manually:

### 1. Installation
Install the required packages in your active environment:
```bash
pip install -r requirements.txt
```

### 2. Startup
Run the Streamlit application:
```bash
streamlit run app.py
```

## Project Structure

```
dashboard/
├── app.py                  # Main Streamlit application
├── start.py                # Cross-platform startup script
├── start.command           # macOS/Linux double-clickable launcher
├── start.bat               # Windows double-clickable launcher
├── requirements.txt        # Python dependencies
├── data/                   # Raw data
│   ├── BEST.txt            # ASTRA vehicle fleet data
│   └── *.json              # BFE charging stations data
└── src/                    # Source code
    ├── data_loader.py      # Data loading functions
    ├── pipeline.py         # ETL pipeline
    ├── forecaster.py       # Forecasting models
    └── visualizations/     # Plot classes
        ├── base_plot.py    # Abstract base class
        └── plots.py        # Concrete visualizations
```

## Data Sources

- **ASTRA**: Vehicle fleet (opendata.astra.admin.ch)
- **BFE**: Charging stations electromobility
- **BFS**: Municipality boundaries (geodata)

## Author

Adrian Thürig – MAS Data Science, ZHAW
