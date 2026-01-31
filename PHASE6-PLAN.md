# Phase 6: Polish & Service Cleanup

## Current State (Messy)

### VM LaunchAgents
| Label | Purpose | Status |
|-------|---------|--------|
| `com.android.adb-relay` | ADB relay | Keep, rename |
| `com.android.observatory-relay` | Observatory relay | Keep, rename |
| `com.flutter.control.ios` | iOS MCP server | Keep, rename |
| `com.android-mcp.fileserver` | HTTP file server | **STALE - Remove** |

### Host LaunchAgents
| Label | Purpose | Status |
|-------|---------|--------|
| `com.flutter.control` | Android MCP server | Keep, rename |
| `com.flutter.observatory-bridge` | Observatory bridge | Keep, rename |
| `com.android.mcp-bridge` | Android MCP Bridge | Keep (separate project) |

## New Naming Scheme

All flutter-control services use: `com.erace.flutter-control.<component>`

### VM Services
| New Label | Old Label | Purpose |
|-----------|-----------|---------|
| `com.erace.flutter-control.ios` | `com.flutter.control.ios` | iOS MCP Server |
| `com.erace.flutter-control.adb-relay` | `com.android.adb-relay` | ADB Relay |
| `com.erace.flutter-control.observatory-relay` | `com.android.observatory-relay` | Observatory Relay |

### Host Services
| New Label | Old Label | Purpose |
|-----------|-----------|---------|
| `com.erace.flutter-control.android` | `com.flutter.control` | Android MCP Server |
| `com.erace.flutter-control.observatory-bridge` | `com.flutter.observatory-bridge` | Observatory Bridge |

## Wrapper Scripts (Nice Process Names)

Instead of showing "Python" in Activity Monitor, create wrapper scripts:

```
/usr/local/opt/flutter_control/bin/
├── flutter-control-ios          # Runs iOS MCP server
├── flutter-control-android      # Runs Android MCP server
├── adb-relay                    # Runs ADB relay
├── observatory-relay            # Runs Observatory relay
├── observatory-bridge           # Runs Observatory bridge
```

Each wrapper is a shell script that execs Python with the right args,
and the script name becomes the process name.

## Version/Health Endpoint

Add to MCP server:

```python
@app.get("/version")
def version():
    return {
        "service": "flutter-control",
        "platform": "ios",  # or "android"
        "version": "1.0.0",
        "deployed_at": "2024-01-31T15:00:00Z",  # file mtime
        "git_commit": "abc123",  # if available
        "uptime_seconds": 3600
    }
```

MCP Tool:
```
flutter_version  # Returns version info for debugging
```

## Cleanup Steps

1. Stop all old services
2. Remove old LaunchAgent plists
3. Deploy new wrapper scripts
4. Deploy new LaunchAgent plists with new names
5. Start new services
6. Verify all running

## Files to Create

### VM
- `/usr/local/opt/flutter_control/bin/flutter-control-ios`
- `/usr/local/opt/flutter_control/bin/adb-relay`
- `/usr/local/opt/flutter_control/bin/observatory-relay`
- `~/Library/LaunchAgents/com.erace.flutter-control.ios.plist`
- `~/Library/LaunchAgents/com.erace.flutter-control.adb-relay.plist`
- `~/Library/LaunchAgents/com.erace.flutter-control.observatory-relay.plist`

### Host
- `/usr/local/opt/flutter_control/bin/flutter-control-android`
- `/usr/local/opt/flutter_control/bin/observatory-bridge`
- `~/Library/LaunchAgents/com.erace.flutter-control.android.plist`
- `~/Library/LaunchAgents/com.erace.flutter-control.observatory-bridge.plist`

## Files to Remove

### VM
- `~/Library/LaunchAgents/com.android-mcp.fileserver.plist`
- `~/Library/LaunchAgents/com.android.adb-relay.plist`
- `~/Library/LaunchAgents/com.android.observatory-relay.plist`
- `~/Library/LaunchAgents/com.flutter.control.ios.plist`

### Host
- `~/Library/LaunchAgents/com.flutter.control.plist`
- `~/Library/LaunchAgents/com.flutter.observatory-bridge.plist`
