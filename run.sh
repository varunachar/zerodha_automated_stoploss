#!/bin/bash
echo "Starting Zerodha GTT Automation..."

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 could not be found. Please install Python 3."
    exit 1
fi

# Install dependencies if needed
echo "Checking dependencies..."
pip3 install -r requirements.txt

# Run the main script
python3 main.py
