"""Async HTTP client for MCP tool calls."""

import os
from pathlib import Path
from typing import Any, Optional

import httpx

from .platform import PlatformConfig


class MCPClientError(Exception):
    """Error from MCP client."""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class MCPClient:
    """Async HTTP client for calling MCP tools."""

    def __init__(self, config: PlatformConfig, timeout: float = 60.0):
        """Initialize the MCP client.

        Args:
            config: Platform configuration with MCP server details
            timeout: Request timeout in seconds
        """
        self.config = config
        self.timeout = timeout
        self._token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def token(self) -> Optional[str]:
        """Get the authentication token."""
        if self._token is None:
            # Try environment variable first
            self._token = os.getenv("FLUTTER_CONTROL_TOKEN")
            if not self._token:
                # Fall back to token file
                token_file = Path.home() / ".android-mcp-token"
                if token_file.exists():
                    self._token = token_file.read_text().strip()
        return self._token

    async def __aenter__(self) -> "MCPClient":
        """Enter async context."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        self._client = httpx.AsyncClient(
            base_url=self.config.mcp_url,
            headers=headers,
            timeout=httpx.Timeout(self.timeout),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health(self) -> dict:
        """Check server health."""
        if not self._client:
            raise MCPClientError("Client not initialized. Use 'async with' context.")

        response = await self._client.get("/health")
        response.raise_for_status()
        return response.json()

    async def list_tools(self) -> list[dict]:
        """List available MCP tools."""
        if not self._client:
            raise MCPClientError("Client not initialized. Use 'async with' context.")

        response = await self._client.get("/tools")
        response.raise_for_status()
        return response.json()

    async def call(
        self,
        tool_name: str,
        arguments: Optional[dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> dict:
        """Call an MCP tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            timeout: Override timeout for this call

        Returns:
            Tool result as a dictionary

        Raises:
            MCPClientError: If the call fails
        """
        if not self._client:
            raise MCPClientError("Client not initialized. Use 'async with' context.")

        payload = {
            "name": tool_name,
            "arguments": arguments or {},
        }

        # Use custom timeout if provided
        client_timeout = httpx.Timeout(timeout) if timeout else None

        try:
            response = await self._client.post(
                "/call",
                json=payload,
                timeout=client_timeout,
            )
        except httpx.TimeoutException as e:
            raise MCPClientError(f"Request timed out: {e}") from e
        except httpx.RequestError as e:
            raise MCPClientError(f"Request failed: {e}") from e

        if response.status_code != 200:
            raise MCPClientError(
                f"Tool call failed: {response.text}",
                status_code=response.status_code,
                response=response.json() if response.text else None,
            )

        return response.json()

    async def call_with_finder(
        self,
        tool_name: str,
        finder: dict[str, Any],
        backend: Optional[str] = None,
        extra_args: Optional[dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> dict:
        """Call an MCP tool with a finder, optionally forcing a backend.

        Args:
            tool_name: Name of the tool to call
            finder: Finder dictionary (e.g., {"text": "Button"})
            backend: Backend to force ("maestro" or "driver"), or None for unified
            extra_args: Additional arguments to pass
            timeout: Override timeout for this call

        Returns:
            Tool result as a dictionary
        """
        # Build the finder with optional backend
        finder_with_backend = dict(finder)
        if backend and backend != "unified":
            finder_with_backend["backend"] = backend

        arguments = {"finder": finder_with_backend}
        if extra_args:
            arguments.update(extra_args)

        return await self.call(tool_name, arguments, timeout=timeout)
