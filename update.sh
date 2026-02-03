#!/bin/bash
~/.flutter-control-venv/bin/pip install -q --force-reinstall http://claude-dev.local:9999/dist/flutter_control_mcp-0.3.0-py3-none-any.whl
launchctl kickstart -k gui/$(id -u)/com.erace.flutter-control
echo "Updated and restarted"
