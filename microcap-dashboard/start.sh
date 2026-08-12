#!/bin/bash
set -e
cd /home/openclaw/.openclaw/workspace/microcap-dashboard

echo "=== Starting Microcap Hunt Dashboard ==="

# Start API
echo "[1/3] Installing API dependencies..."
pip install fastapi uvicorn --break-system-packages -q 2>/dev/null || pip install fastapi uvicorn -q
echo "[2/3] Starting API on port 8765..."
export PATH="$HOME/.local/bin:$PATH"
cd api && uvicorn main:app --host 0.0.0.0 --port 8765 --reload &
API_PID=$!
echo "      API PID: $API_PID"
sleep 2

# Build + serve frontend
echo "[3/3] Building frontend..."
cd ../frontend
npm install -q
npm run build
npx serve dist -l 3100 -s --no-clipboard &
FRONT_PID=$!
echo "      Frontend PID: $FRONT_PID"
sleep 2

PUBLIC_IP=$(curl -4 -s ifconfig.me 2>/dev/null || curl -s ifconfig.me 2>/dev/null || echo "localhost")
echo ""
echo "========================================"
echo "  Dashboard: http://${PUBLIC_IP}:3100"
echo "  API:       http://${PUBLIC_IP}:8765"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop all services."
wait
