#!/bin/bash
# Start Flutter Control MCP server on VM for iOS
# This server handles iOS simulator automation (Maestro + Flutter Driver)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$HOME/Library/Logs/flutter-control"
VENV_DIR="$PROJECT_DIR/.venv"
PORT="${FLUTTER_CONTROL_PORT:-9226}"

echo "=== Starting Flutter Control MCP Server (iOS) ==="

# Create log directory
mkdir -p "$LOG_DIR"

# Ensure Maestro is in PATH
export PATH="$PATH:$HOME/.maestro/bin"

# Check Maestro
if ! command -v maestro &> /dev/null; then
    echo "Error: Maestro not found. Install with:"
    echo "  curl -Ls 'https://get.maestro.mobile.dev' | bash"
    exit 1
fi

# Check venv
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --quiet fastapi uvicorn pydantic httpx websockets
fi

# Check if already running
if lsof -i ":$PORT" > /dev/null 2>&1; then
    echo "Server already running on port $PORT"
    exit 0
fi

# Start server
cd "$PROJECT_DIR"
nohup "$VENV_DIR/bin/python" -c "
import sys
sys.path.insert(0, '.')
from flutter_control.mcp.server import app
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=$PORT)
" > "$LOG_DIR/vm-server.log" 2>&1 &

echo "Server starting on port $PORT..."
sleep 2

if curl -s "http://localhost:$PORT/health" | grep -q "ok"; then
    echo "=== Server Running ==="
    echo "Port: $PORT"
    echo "Logs: $LOG_DIR/vm-server.log"
    echo ""
    echo "Test: curl -H 'Authorization: Bearer \$(cat ~/.android-mcp-token)' http://localhost:$PORT/tools"
else
    echo "=== Warning: Server may not be running ==="
    echo "Check logs: tail -f $LOG_DIR/vm-server.log"
    exit 1
fi
