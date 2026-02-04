"""ADB TCP Proxy - Allows remote Flutter/ADB connections from VM."""

import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger('adb-proxy')

# Default port - use 15037 to avoid conflict with local ADB server on 5037
ADB_PROXY_PORT = int(os.environ.get('ADB_PROXY_PORT', 15037))


class ADBProxy:
    """
    TCP proxy that forwards connections to the local ADB server.

    This allows Flutter in the VM to connect to the host's ADB server
    and deploy directly to emulators with hot reload support.
    """

    def __init__(self, listen_host: str = '0.0.0.0', listen_port: int = ADB_PROXY_PORT,
                 adb_host: str = '127.0.0.1', adb_port: int = 5037):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.adb_host = adb_host
        self.adb_port = adb_port
        self.server: Optional[asyncio.Server] = None
        self.connections: list = []

    async def start(self) -> bool:
        """Start the ADB proxy server."""
        if self.server is not None:
            logger.info("ADB proxy already running")
            return True

        try:
            # Find ADB path
            import shutil
            adb_path = shutil.which('adb')
            if adb_path:
                # Ensure ADB server is running locally first
                proc = await asyncio.create_subprocess_exec(
                    adb_path, 'start-server',
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await proc.wait()

            self.server = await asyncio.start_server(
                self._handle_connection,
                self.listen_host,
                self.listen_port
            )
            logger.info(f"ADB proxy listening on {self.listen_host}:{self.listen_port}")
            return True
        except OSError as e:
            if e.errno == 48:  # Address already in use
                logger.warning(f"Port {self.listen_port} already in use")
                return False
            raise

    async def stop(self):
        """Stop the ADB proxy server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
            # Close all active connections
            for conn in self.connections:
                try:
                    conn.close()
                except:
                    pass
            self.connections.clear()
            logger.info("ADB proxy stopped")

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle an incoming proxy connection."""
        client_addr = writer.get_extra_info('peername')
        logger.debug(f"New connection from {client_addr}")

        try:
            # Connect to local ADB server
            adb_reader, adb_writer = await asyncio.open_connection(
                self.adb_host, self.adb_port
            )
            self.connections.append(adb_writer)

            # Bidirectional forwarding
            await asyncio.gather(
                self._forward(reader, adb_writer),
                self._forward(adb_reader, writer),
                return_exceptions=True
            )
        except ConnectionRefusedError:
            logger.error("Cannot connect to local ADB server - is it running?")
        except Exception as e:
            logger.debug(f"Connection error: {e}")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except:
                pass

    async def _forward(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Forward data between streams."""
        try:
            while True:
                data = await reader.read(8192)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
            pass
        finally:
            try:
                writer.close()
            except:
                pass

    @property
    def is_running(self) -> bool:
        return self.server is not None and self.server.is_serving()

    def status(self) -> dict:
        return {
            'running': self.is_running,
            'listen_address': f"{self.listen_host}:{self.listen_port}",
            'adb_server': f"{self.adb_host}:{self.adb_port}",
            'active_connections': len(self.connections)
        }


# Global instance
_adb_proxy: Optional[ADBProxy] = None


def get_adb_proxy() -> ADBProxy:
    """Get or create the global ADB proxy instance."""
    global _adb_proxy
    if _adb_proxy is None:
        _adb_proxy = ADBProxy()
    return _adb_proxy
