#!/bin/bash
# Radiant Node GUI Launcher (Linux/macOS)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for Python 3
if command -v python3 &> /dev/null; then
    python3 radiant_node_web.py
elif command -v python &> /dev/null; then
    python radiant_node_web.py
else
    echo "Error: Python 3 is required to run this application."
    echo "Please install Python 3 from https://www.python.org/downloads/"
    exit 1
fi
