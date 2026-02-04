#!/bin/bash
# Cleanup obsolete Flutter Control LaunchAgents on Host Mac
# Run with: curl -sS http://claude-dev.local:9999/scripts/cleanup-host.sh | bash

set -e

echo "=== Flutter Control Host Cleanup ==="
echo ""

# Services to KEEP (these are the correct ones)
# - com.erace.flutter-control        (port 9225, Android)
# - com.erace.flutter-control.ios    (port 9227, iOS)
# - com.erace.flutter-control.observatory-bridge

# Services to REMOVE (obsolete/duplicate)
OBSOLETE_AGENTS=(
    "com.erace.flutter-control.android"
)

# Old installation paths to remove
OBSOLETE_PATHS=(
    "/usr/local/opt/flutter_control"
)

echo "1. Stopping obsolete LaunchAgents..."
for agent in "${OBSOLETE_AGENTS[@]}"; do
    if launchctl list | grep -q "$agent"; then
        echo "   Stopping: $agent"
        launchctl bootout gui/$(id -u)/$agent 2>/dev/null || true
    else
        echo "   Already stopped: $agent"
    fi
done
echo ""

echo "2. Removing obsolete plist files..."
for agent in "${OBSOLETE_AGENTS[@]}"; do
    plist="$HOME/Library/LaunchAgents/${agent}.plist"
    if [ -f "$plist" ]; then
        echo "   Removing: $plist"
        rm "$plist"
    else
        echo "   Not found: $plist"
    fi
done
echo ""

echo "3. Removing obsolete installation paths..."
for path in "${OBSOLETE_PATHS[@]}"; do
    if [ -d "$path" ]; then
        echo "   Removing: $path"
        rm -rf "$path"
    else
        echo "   Not found: $path"
    fi
done
echo ""

echo "4. Verifying active services..."
echo "   Active flutter-control LaunchAgents:"
launchctl list | grep -E "flutter-control|erace" | while read pid status name; do
    if [ "$pid" != "-" ]; then
        echo "   ✓ $name (PID: $pid)"
    else
        echo "   ✗ $name (not running, exit: $status)"
    fi
done
echo ""

echo "5. Checking ports..."
echo "   Port 9225 (Android):"
curl -s http://localhost:9225/version 2>/dev/null | python3 -c "import sys,json; v=json.load(sys.stdin); print(f'     Version: {v[\"version\"]}, Platform: {v[\"platform\"]}')" 2>/dev/null || echo "     Not responding"

echo "   Port 9227 (iOS):"
curl -s http://localhost:9227/version 2>/dev/null | python3 -c "import sys,json; v=json.load(sys.stdin); print(f'     Version: {v[\"version\"]}, Platform: {v[\"platform\"]}')" 2>/dev/null || echo "     Not responding"
echo ""

echo "=== Cleanup Complete ==="
echo ""
echo "Active services:"
echo "  • com.erace.flutter-control (Android, port 9225)"
echo "  • com.erace.flutter-control.ios (iOS, port 9227)"
echo "  • com.erace.flutter-control.observatory-bridge"
