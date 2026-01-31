#!/usr/bin/env python3
"""Observatory bridge for Host Mac.

Exposes the ADB-forwarded VM Service (localhost:9223) to the network (0.0.0.0:9223)
so that the VM's Observatory relay can connect to it.

Flow: VM:9223 -> Host:9223 (this bridge) -> localhost:9223 (ADB forward) -> emulator

This runs on the HOST Mac, not the VM.
"""
import asyncio
import sys

# Listen on all interfaces so VM can reach it
# Use port 9233 (not 9223) to avoid conflict with ADB forward
LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = 9233

# Forward to localhost where ADB forward is (port 9223)
FORWARD_HOST = '127.0.0.1'
FORWARD_PORT = 9223


async def forward(reader, writer, name):
    """Forward data between two streams."""
    try:
        while True:
            data = await reader.read(8192)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[{name}] Error: {e}", file=sys.stderr)
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except:
            pass


async def handle_client(local_reader, local_writer):
    """Handle incoming connection by forwarding to ADB forward port."""
    peer = local_writer.get_extra_info('peername')
    print(f"[observatory-bridge] Connection from {peer}")

    try:
        remote_reader, remote_writer = await asyncio.open_connection(FORWARD_HOST, FORWARD_PORT)
        print(f"[observatory-bridge] Connected to ADB forward at {FORWARD_HOST}:{FORWARD_PORT}")

        await asyncio.gather(
            forward(local_reader, remote_writer, "client->adb"),
            forward(remote_reader, local_writer, "adb->client"),
        )
    except ConnectionRefusedError:
        print(f"[observatory-bridge] Connection refused to {FORWARD_HOST}:{FORWARD_PORT}", file=sys.stderr)
        print(f"[observatory-bridge] Run: adb forward tcp:9223 tcp:<vm_service_port>", file=sys.stderr)
    except Exception as e:
        print(f"[observatory-bridge] Error: {e}", file=sys.stderr)
    finally:
        try:
            local_writer.close()
            await local_writer.wait_closed()
        except:
            pass
        print(f"[observatory-bridge] Connection closed from {peer}")


async def main():
    server = await asyncio.start_server(handle_client, LISTEN_HOST, LISTEN_PORT)
    addr = server.sockets[0].getsockname()
    print(f"[observatory-bridge] Listening on {addr[0]}:{addr[1]}")
    print(f"[observatory-bridge] Forwarding to {FORWARD_HOST}:{FORWARD_PORT} (ADB forward)")
    print(f"[observatory-bridge] VM can now connect to Host:{LISTEN_PORT}")

    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[observatory-bridge] Stopped")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"[observatory-bridge] Port {LISTEN_PORT} already in use", file=sys.stderr)
            print(f"[observatory-bridge] Check: lsof -i :{LISTEN_PORT}", file=sys.stderr)
        else:
            raise
