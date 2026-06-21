#!/bin/bash
cd "$(dirname "$0")/.."
python3 dashboard.py &
echo "[*] AI Server Manager started on http://localhost:8000"
