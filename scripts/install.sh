#!/bin/bash
# Install Flutter Control MCP server on host Mac
# Run: curl -sS http://claude-dev.local:9999/install.sh | bash

set -e

INSTALL_DIR="/usr/local/opt/flutter_control"
VENV_DIR="$INSTALL_DIR/.venv"
LOG_DIR="$HOME/Library/Logs/flutter-control"
LAUNCH_AGENT="$HOME/Library/LaunchAgents/com.flutter.control.plist"
VM_IP="${VM_IP:-claude-dev.local}"
VM_PORT="${VM_PORT:-9999}"
TOKEN_FILE="$HOME/.android-mcp-token"

echo "=== Flutter Control MCP Server Installation ==="

# Create directories
echo "Creating directories..."
sudo mkdir -p "$INSTALL_DIR"
sudo chown -R $(whoami) "$INSTALL_DIR"
mkdir -p "$LOG_DIR"

# Download files from VM
echo "Downloading from VM ($VM_IP:$VM_PORT)..."
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/__init__.py" -o "$INSTALL_DIR/__init__.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/config.py" -o "$INSTALL_DIR/config.py"

mkdir -p "$INSTALL_DIR/logging"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/logging/__init__.py" -o "$INSTALL_DIR/logging/__init__.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/logging/trace.py" -o "$INSTALL_DIR/logging/trace.py"

mkdir -p "$INSTALL_DIR/maestro"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/maestro/__init__.py" -o "$INSTALL_DIR/maestro/__init__.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/maestro/flow_builder.py" -o "$INSTALL_DIR/maestro/flow_builder.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/maestro/parser.py" -o "$INSTALL_DIR/maestro/parser.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/maestro/wrapper.py" -o "$INSTALL_DIR/maestro/wrapper.py"

mkdir -p "$INSTALL_DIR/mcp"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/mcp/__init__.py" -o "$INSTALL_DIR/mcp/__init__.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/mcp/tools.py" -o "$INSTALL_DIR/mcp/tools.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/mcp/server.py" -o "$INSTALL_DIR/mcp/server.py"

mkdir -p "$INSTALL_DIR/driver"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/driver/__init__.py" -o "$INSTALL_DIR/driver/__init__.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/driver/client.py" -o "$INSTALL_DIR/driver/client.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/driver/commands.py" -o "$INSTALL_DIR/driver/commands.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/driver/finders.py" -o "$INSTALL_DIR/driver/finders.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/driver/protocol.py" -o "$INSTALL_DIR/driver/protocol.py"

mkdir -p "$INSTALL_DIR/unified"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/unified/__init__.py" -o "$INSTALL_DIR/unified/__init__.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/unified/backend_selector.py" -o "$INSTALL_DIR/unified/backend_selector.py"
curl -sS "http://$VM_IP:$VM_PORT/flutter_control/unified/executor.py" -o "$INSTALL_DIR/unified/executor.py"

# Install Maestro if not present
if ! command -v maestro &> /dev/null && [ ! -f "$HOME/.maestro/bin/maestro" ]; then
    echo "Installing Maestro..."
    curl -Ls "https://get.maestro.mobile.dev" | bash
fi

# Ensure token exists (use same token as android-mcp-bridge)
if [ ! -f "$TOKEN_FILE" ]; then
    echo "Generating auth token..."
    openssl rand -hex 16 > "$TOKEN_FILE"
    chmod 600 "$TOKEN_FILE"
fi

# Create virtual environment and install dependencies
echo "Setting up Python virtual environment..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet fastapi uvicorn pydantic httpx websockets

# Create LaunchAgent
echo "Creating LaunchAgent..."
cat > "$LAUNCH_AGENT" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.flutter.control</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_DIR/bin/python3</string>
        <string>-c</string>
        <string>import sys; sys.path.insert(0, '/usr/local/opt'); from flutter_control.mcp.server import main; main()</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>FLUTTER_CONTROL_PORT</key>
        <string>9225</string>
        <key>FLUTTER_CONTROL_HOST</key>
        <string>0.0.0.0</string>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:$HOME/.maestro/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/stderr.log</string>
</dict>
</plist>
EOF

# Load LaunchAgent
echo "Starting service..."
launchctl unload "$LAUNCH_AGENT" 2>/dev/null || true
launchctl load "$LAUNCH_AGENT"

# Wait and verify
sleep 2
if curl -s http://localhost:9225/health | grep -q "ok"; then
    echo ""
    echo "=== Installation Complete ==="
    echo "Server running on port 9225"
    echo "Token: $(cat $TOKEN_FILE)"
    echo "Logs: $LOG_DIR/stderr.log"
else
    echo ""
    echo "=== Warning: Server may not be running ==="
    echo "Check logs: tail -f $LOG_DIR/stderr.log"
fi
