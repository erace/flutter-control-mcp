# Architecture

## Overview

Flutter Control MCP provides UI automation for Flutter apps via two backends:

| Backend | Protocol | Best For | Finder Types |
|---------|----------|----------|--------------|
| **Maestro** | Accessibility layer | Any app | `{text: "..."}`, `{id: "..."}` |
| **Flutter Driver** | VM Service WebSocket | Apps with driver extension | `{key: "..."}`, `{type: "..."}` |

The server auto-selects the backend based on finder type, with automatic fallback.

## Network Topology

```
┌─────────────────────────────────────────────────────────────────────┐
│ VM (claude-dev.local)                                               │
│                                                                     │
│  ┌─────────────────────┐    ┌─────────────────────┐                │
│  │ Claude Code         │    │ iOS Flutter Control │                │
│  │ (MCP Client)        │    │ Server (:9226)      │                │
│  └─────────┬───────────┘    └─────────┬───────────┘                │
│            │ stdio                    │                            │
│            ▼                          ▼                            │
│  ┌─────────────────────┐    ┌─────────────────────┐                │
│  │ flutter-control-mcp │    │ iOS Simulator       │                │
│  │ (stdio→HTTP proxy)  │    │                     │                │
│  └─────────┬───────────┘    └─────────────────────┘                │
│            │ HTTP                                                   │
└────────────┼────────────────────────────────────────────────────────┘
             │
             │ phost.local:9225
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Host Mac (phost.local)                                              │
│                                                                     │
│  ┌─────────────────────┐    ┌─────────────────────┐                │
│  │ Android Flutter     │    │ Android MCP Bridge  │                │
│  │ Control (:9225)     │    │ (:9222)             │                │
│  └─────────┬───────────┘    └─────────┬───────────┘                │
│            │                          │                            │
│            ▼                          ▼                            │
│  ┌─────────────────────┐    ┌─────────────────────┐                │
│  │ Maestro CLI         │    │ ADB Server          │                │
│  │ Flutter Driver WS   │    │ Emulator lifecycle  │                │
│  └─────────┬───────────┘    └─────────────────────┘                │
│            │                                                        │
│            ▼                                                        │
│  ┌─────────────────────┐                                           │
│  │ Android Emulator    │                                           │
│  │                     │                                           │
│  └─────────────────────┘                                           │
└─────────────────────────────────────────────────────────────────────┘
```

## Services

### Flutter Control MCP Server (HTTP)

The main automation server. Runs on each platform:

| Platform | Host | Port | Service Name |
|----------|------|------|--------------|
| Android | Host Mac | 9225 | `com.erace.flutter-control` |
| iOS | VM | 9226 | `com.erace.flutter-control` |

**Endpoints:**
- `GET /health` - Health check
- `GET /version` - Version and deployment info
- `GET /tools` - List available MCP tools
- `POST /call` - Execute a tool
- `POST /mcp` - MCP JSON-RPC endpoint

### MCP Stdio Server

Translates stdio MCP protocol to HTTP calls. Used by MCP clients like Claude Code.

```
stdin (JSON-RPC) → flutter-control-mcp → HTTP POST /mcp → stdout (JSON-RPC)
```

### Android MCP Bridge (port 9222)

Separate service for Android emulator lifecycle management:
- `android_list_devices` - List devices and AVDs
- `android_start_emulator` - Boot AVD
- `android_stop_emulator` - Shutdown emulator
- ADB proxy for remote ADB access

### Observatory Bridge (port 9233)

Exposes Flutter VM Service from emulator to network for hot reload support.

## mDNS Hostnames

Always use mDNS hostnames instead of IP addresses:

| Hostname | Resolves To | Purpose |
|----------|-------------|---------|
| `phost.local` | Host Mac | Android services |
| `claude-dev.local` | VM | iOS services, file serving |
| `localhost` | Same machine | Local services only |

Benefits:
- Works across network changes (DHCP, VPN)
- Self-documenting configuration
- Bonjour auto-discovery

## Data Flow

### Tap Operation (Maestro)

```
1. MCP Client sends: flutter_tap {text: "Submit"}
2. Server selects Maestro backend (text finder)
3. Maestro generates YAML flow
4. Maestro executes via accessibility layer
5. Result returned to client
```

### Tap Operation (Flutter Driver)

```
1. MCP Client sends: flutter_tap {key: "submit_btn"}
2. Server selects Driver backend (key finder)
3. Driver sends JSON-RPC over WebSocket to VM Service
4. Flutter app executes tap via widget tree
5. Result returned to client
```

### Screenshot (Smart)

```
1. MCP Client sends: flutter_screenshot {}
2. Server detects platform (port 9225=Android, 9226=iOS)
3. Android: adb exec-out screencap -p
   iOS: xcrun simctl io screenshot
4. On error: fallback to Maestro screenshot
5. Base64 image returned to client
```

## Security

### Authentication

Bearer token authentication for all `/call` and `/mcp` endpoints:
- Token stored in `~/.android-mcp-token`
- Generated on first install: `openssl rand -hex 16`
- Shared between Flutter Control and Android MCP Bridge

### Network Binding

- HTTP server binds to `0.0.0.0` (all interfaces) for cross-machine access
- Firewall rules recommended for production use

## File Locations

| Path | Purpose |
|------|---------|
| `~/.android-mcp-token` | Authentication token |
| `~/Library/Logs/flutter-control/` | Server logs |
| `~/Library/LaunchAgents/com.erace.flutter-control.plist` | macOS service |
| `~/.flutter-control-venv/` | Python virtual environment |
| `~/.claude/mcp_servers.json` | MCP client configuration |
