"""CLI commands for Flutter Control MCP."""

import argparse
import os
import secrets
import subprocess
import sys
from pathlib import Path

from . import __version__


def get_paths():
    """Get installation paths."""
    return {
        "log_dir": Path.home() / "Library" / "Logs" / "flutter-control",
        "token_file": Path.home() / ".android-mcp-token",
        "launch_agent": Path.home() / "Library" / "LaunchAgents" / "com.erace.flutter-control.plist",
        "venv_python": Path(sys.executable),
    }


def install_service():
    """Install Flutter Control as a macOS LaunchAgent service."""
    parser = argparse.ArgumentParser(description="Install Flutter Control as macOS service")
    parser.add_argument("--port", type=int, default=9225, help="Port to run on (default: 9225)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall the service")
    args = parser.parse_args()

    paths = get_paths()

    if args.uninstall:
        return uninstall_service_impl(paths)

    print(f"=== Flutter Control v{__version__} - Service Installation ===\n")

    # Create log directory
    paths["log_dir"].mkdir(parents=True, exist_ok=True)
    print(f"✓ Log directory: {paths['log_dir']}")

    # Ensure token exists
    if not paths["token_file"].exists():
        token = secrets.token_hex(16)
        paths["token_file"].write_text(token)
        paths["token_file"].chmod(0o600)
        print(f"✓ Generated auth token: {paths['token_file']}")
    else:
        print(f"✓ Using existing token: {paths['token_file']}")

    # Find maestro
    maestro_path = Path.home() / ".maestro" / "bin"
    if not (maestro_path / "maestro").exists():
        print("\n⚠ Maestro not found. Install it with:")
        print("  curl -Ls 'https://get.maestro.mobile.dev' | bash")
        print()

    # Find flutter
    import shutil
    flutter_bin = shutil.which("flutter")
    flutter_path = Path(flutter_bin).parent if flutter_bin else Path.home() / "flutter" / "bin"
    if not (flutter_path / "flutter").exists():
        print("\n⚠ Flutter not found. The flutter_run tool won't work.")
        print()

    # Build PATH with all required tools
    path_components = [
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
        str(maestro_path),
        str(flutter_path),
        # Android SDK platform-tools (for adb)
        str(Path.home() / "Library" / "Android" / "sdk" / "platform-tools"),
    ]
    service_path = ":".join(path_components)

    # Create LaunchAgent plist
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.erace.flutter-control</string>
    <key>ProgramArguments</key>
    <array>
        <string>{paths['venv_python']}</string>
        <string>-m</string>
        <string>flutter_control.mcp.server</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>FLUTTER_CONTROL_PORT</key>
        <string>{args.port}</string>
        <key>FLUTTER_CONTROL_HOST</key>
        <string>{args.host}</string>
        <key>PATH</key>
        <string>{service_path}</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{paths['log_dir']}/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>{paths['log_dir']}/stderr.log</string>
</dict>
</plist>
"""

    paths["launch_agent"].parent.mkdir(parents=True, exist_ok=True)
    paths["launch_agent"].write_text(plist_content)
    print(f"✓ Created LaunchAgent: {paths['launch_agent']}")

    # Load the service
    subprocess.run(["launchctl", "unload", str(paths["launch_agent"])],
                   capture_output=True)
    result = subprocess.run(["launchctl", "load", str(paths["launch_agent"])],
                           capture_output=True, text=True)

    if result.returncode != 0:
        print(f"\n✗ Failed to load service: {result.stderr}")
        return 1

    print(f"✓ Service started on port {args.port}")

    # Verify
    import time
    time.sleep(2)

    try:
        import urllib.request
        with urllib.request.urlopen(f"http://localhost:{args.port}/health", timeout=5) as resp:
            if resp.status == 200:
                print(f"\n=== Installation Complete ===")
                print(f"Server: http://localhost:{args.port}")
                print(f"Token: {paths['token_file'].read_text().strip()}")
                print(f"Logs: tail -f {paths['log_dir']}/stderr.log")
                return 0
    except Exception:
        pass

    print(f"\n⚠ Service may not be running. Check logs:")
    print(f"  tail -f {paths['log_dir']}/stderr.log")
    return 1


def uninstall_service_impl(paths):
    """Uninstall the service."""
    print("=== Uninstalling Flutter Control Service ===\n")

    if paths["launch_agent"].exists():
        subprocess.run(["launchctl", "unload", str(paths["launch_agent"])],
                       capture_output=True)
        paths["launch_agent"].unlink()
        print(f"✓ Removed LaunchAgent")
    else:
        print(f"  LaunchAgent not found")

    print("\nService uninstalled. To fully remove:")
    print(f"  pip uninstall flutter-control-mcp")
    print(f"  rm -rf {paths['log_dir']}")
    print(f"  rm {paths['token_file']}  # if not shared with other tools")
    return 0


def uninstall_service():
    """Uninstall Flutter Control macOS service."""
    paths = get_paths()
    return uninstall_service_impl(paths)


def run_server():
    """Run the MCP server directly (for development)."""
    from .mcp.server import main
    main()


def show_version():
    """Show version information."""
    print(f"flutter-control-mcp {__version__}")


def mcp_stdio():
    """MCP stdio server - for use with uvx/npx.

    This is the main entry point for MCP clients like Claude Code.
    Reads JSON-RPC requests from stdin, proxies to HTTP server, returns responses.

    Environment variables:
        FLUTTER_CONTROL_HOST: Server host (default: phost.local for Android, localhost for iOS)
        FLUTTER_CONTROL_PORT: Server port (default: 9225)
        FLUTTER_CONTROL_TOKEN: Auth token (or reads from ~/.android-mcp-token)
    """
    import json
    import urllib.request
    import urllib.error

    host = os.environ.get("FLUTTER_CONTROL_HOST", "phost.local")
    port = os.environ.get("FLUTTER_CONTROL_PORT", "9225")
    base_url = f"http://{host}:{port}"

    # Get token
    token = os.environ.get("FLUTTER_CONTROL_TOKEN")
    if not token:
        token_file = Path.home() / ".android-mcp-token"
        if token_file.exists():
            token = token_file.read_text().strip()

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    def send_response(response):
        print(json.dumps(response), flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            send_response({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {e}"}})
            continue

        request_id = request.get("id")

        try:
            data = json.dumps(request).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url}/mcp",
                data=data,
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                send_response(result)
        except urllib.error.HTTPError as e:
            send_response({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": f"HTTP {e.code}: {e.reason}"}
            })
        except urllib.error.URLError as e:
            send_response({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": f"Connection error: {e.reason}"}
            })
        except Exception as e:
            send_response({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": str(e)}
            })


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Flutter Control MCP - UI automation for Flutter apps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  flutter-control-mcp        Run MCP stdio server (for uvx/Claude Code)
  flutter-control-install    Install as macOS LaunchAgent service
  flutter-control-uninstall  Uninstall the service
  flutter-control-server     Run HTTP server directly (development)

Examples:
  # Use with uvx (standard MCP pattern)
  uvx flutter-control-mcp

  # Install HTTP server as macOS service
  flutter-control-install --port 9225

  # Configure MCP client (Claude Code)
  # Add to ~/.claude/mcp_servers.json:
  # {
  #   "flutter-control": {
  #     "command": "uvx",
  #     "args": ["flutter-control-mcp"],
  #     "env": {"FLUTTER_CONTROL_HOST": "phost.local"}
  #   }
  # }
"""
    )
    parser.add_argument("--version", action="store_true", help="Show version")
    args = parser.parse_args()

    if args.version:
        show_version()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
