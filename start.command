#!/bin/bash
# Move to the directory containing this script
cd "$(dirname "$0")"

# Start the dashboard using python3 or python
if command -v python3 >/dev/null 2>&1; then
    python3 start.py
elif command -v python >/dev/null 2>&1; then
    python start.py
else
    echo "Error: Python 3 could not be found. Please install Python 3."
    read -p "Press Enter to exit..."
fi
