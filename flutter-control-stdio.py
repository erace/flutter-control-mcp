#!/usr/bin/env python3
"""Stdio-to-HTTP proxy for Flutter Control MCP server."""

import json
import sys
import os
import urllib.request
import urllib.error

HOST_IP = os.getenv("FLUTTER_CONTROL_HOST", "192.168.64.1")
PORT = int(os.getenv("FLUTTER_CONTROL_PORT", "9225"))
TOKEN_FILE = os.path.expanduser("~/.android-mcp-token")
BASE_URL = f"http://{HOST_IP}:{PORT}"


def get_token():
    token = os.getenv("FLUTTER_CONTROL_TOKEN")
    if token:
        return token
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            return f.read().strip()
    return None


def send_response(response):
    print(json.dumps(response), flush=True)


def main():
    token = get_token()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

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
                f"{BASE_URL}/mcp",
                data=data,
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
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


if __name__ == "__main__":
    main()
