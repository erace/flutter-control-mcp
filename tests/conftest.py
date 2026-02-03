"""Pytest configuration and shared fixtures."""

import asyncio
import os
from pathlib import Path

import pytest
import pytest_asyncio

from .fixtures import (
    AndroidBootstrap,
    BootstrapResult,
    IOSBootstrap,
    MCPClient,
    PlatformConfig,
    ReportGenerator,
    TimingCollector,
    get_platform_config,
)


# Mark all tests as async by default
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "driver_only: requires Flutter Driver connection")
    config.addinivalue_line("markers", "maestro_only: only uses Maestro backend")
    config.addinivalue_line("markers", "android_only: only runs on Android")
    config.addinivalue_line("markers", "ios_only: only runs on iOS")

    # Validate environment variables - warn about stale IPs
    _validate_environment()


def _validate_environment():
    """Check for potentially stale environment variables and set defaults."""
    warnings = []

    # Auto-configure ADB_SERVER_SOCKET for Android tests via proxy
    if os.getenv("TEST_PLATFORM") == "android" and not os.getenv("ADB_SERVER_SOCKET"):
        bridge_host = os.getenv("ANDROID_MCP_BRIDGE_HOST", "phost.local")
        os.environ["ADB_SERVER_SOCKET"] = f"tcp:{bridge_host}:15037"

    # Check ANDROID_MCP_HOST
    host = os.getenv("ANDROID_MCP_HOST", "")
    if host and "192.168" in host:
        warnings.append(
            f"ANDROID_MCP_HOST={host} looks like a hardcoded IP.\n"
            f"         Consider using: ANDROID_MCP_HOST=phost.local"
        )

    # Check ANDROID_MCP_PORT (common mistake: using bridge port 9222 instead of 9225)
    port = os.getenv("ANDROID_MCP_PORT", "")
    if port == "9222":
        warnings.append(
            f"ANDROID_MCP_PORT=9222 is the android-mcp-bridge port.\n"
            f"         Flutter Control uses port 9225: ANDROID_MCP_PORT=9225"
        )

    # Check ANDROID_MCP_BRIDGE_HOST
    bridge_host = os.getenv("ANDROID_MCP_BRIDGE_HOST", "")
    if bridge_host and "192.168" in bridge_host:
        warnings.append(
            f"ANDROID_MCP_BRIDGE_HOST={bridge_host} looks like a hardcoded IP.\n"
            f"         Consider using: ANDROID_MCP_BRIDGE_HOST=phost.local"
        )

    if warnings:
        print("\n" + "=" * 60)
        print("⚠️  ENVIRONMENT VARIABLE WARNINGS")
        print("=" * 60)
        for w in warnings:
            print(f"  • {w}")
        print("=" * 60)
        print("Fix: Update ~/.zshrc or pass correct values explicitly")
        print("=" * 60 + "\n")


# Session-scoped fixtures


@pytest.fixture(scope="session")
def platform_config() -> PlatformConfig:
    """Get the platform configuration for this test session."""
    return get_platform_config()


@pytest.fixture(scope="session")
def bootstrap_result(platform_config: PlatformConfig) -> BootstrapResult:
    """Bootstrap test environment before any tests run.

    - Starts emulator/simulator if not running
    - Reinstalls test app (fresh install)
    - Launches test app
    - Connects to Flutter Driver Observatory
    """
    token_file = Path.home() / ".android-mcp-token"
    token = token_file.read_text().strip() if token_file.exists() else ""

    loop = asyncio.new_event_loop()
    try:
        if platform_config.is_android:
            bootstrap = AndroidBootstrap(
                mcp_bridge_host=os.getenv("ANDROID_MCP_BRIDGE_HOST", "phost.local"),
                mcp_bridge_port=int(os.getenv("ANDROID_MCP_BRIDGE_PORT", "9222")),
                token=token,
                flutter_control_host=os.getenv("ANDROID_MCP_HOST", "phost.local"),
                flutter_control_port=int(os.getenv("ANDROID_MCP_PORT", "9225")),
            )
        else:
            bootstrap = IOSBootstrap(
                mcp_host=os.getenv("IOS_MCP_HOST", "localhost"),
                mcp_port=int(os.getenv("IOS_MCP_PORT", "9226")),
                token=token,
                device_name=os.getenv("IOS_SIMULATOR_NAME", "iPhone 16e"),
            )
        result = loop.run_until_complete(bootstrap.bootstrap())
    finally:
        loop.close()

    if result.error:
        pytest.exit(f"Bootstrap failed: {result.error}", returncode=1)

    print(f"\n✓ Bootstrap complete: {result.platform}")
    print(f"  Device: {result.device_id}")
    print(f"  App installed: {result.app_installed}")
    print(f"  App launched: {result.app_launched}")
    print(f"  Driver connected: {result.driver_connected}")
    if result.driver_uri:
        print(f"  Driver URI: {result.driver_uri}")

    return result


@pytest.fixture(scope="session")
def timing_collector() -> TimingCollector:
    """Session-wide timing collector."""
    return TimingCollector()


@pytest.fixture(scope="session")
def report_generator(timing_collector: TimingCollector) -> ReportGenerator:
    """Session-wide report generator."""
    return ReportGenerator(timing_collector)


@pytest.fixture(scope="session")
def reports_dir() -> Path:
    """Directory for generated reports."""
    path = Path(__file__).parent / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


# Function-scoped fixtures


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def mcp_client(platform_config: PlatformConfig, bootstrap_result: BootstrapResult):
    """Create an MCP client for the current platform.

    Session-scoped to reuse connection and avoid event loop issues.
    Depends on bootstrap_result to ensure environment is ready.
    """
    async with MCPClient(platform_config) as client:
        yield client


@pytest.fixture
def platform(platform_config: PlatformConfig) -> str:
    """Get the current platform name."""
    return platform_config.name


@pytest.fixture
def is_android(platform_config: PlatformConfig) -> bool:
    """Check if running on Android."""
    return platform_config.is_android


@pytest.fixture
def is_ios(platform_config: PlatformConfig) -> bool:
    """Check if running on iOS."""
    return platform_config.is_ios


# Skip conditions


@pytest.fixture(autouse=True)
def skip_by_platform(request, platform_config: PlatformConfig):
    """Skip tests based on platform markers."""
    if request.node.get_closest_marker("android_only"):
        if not platform_config.is_android:
            pytest.skip("Test only runs on Android")

    if request.node.get_closest_marker("ios_only"):
        if not platform_config.is_ios:
            pytest.skip("Test only runs on iOS")


# Hooks for report generation


def pytest_sessionfinish(session, exitstatus):
    """Generate report after all tests complete."""
    # Get the timing collector from the session
    if hasattr(session, "_timing_collector"):
        collector = session._timing_collector
        if len(collector) > 0:
            reports_dir = Path(__file__).parent / "reports"
            report_gen = ReportGenerator(collector)
            report_path = reports_dir / "timing_report.md"
            report_gen.generate(report_path)
            print(f"\n\nTiming report written to: {report_path}")


@pytest.fixture(scope="session", autouse=True)
def store_timing_collector(request, timing_collector: TimingCollector):
    """Store timing collector on session for report generation."""
    request.session._timing_collector = timing_collector


# Backend parametrization helpers - use in test files with @pytest.mark.parametrize

BACKENDS_THREE = ["unified", "maestro", "driver"]
BACKENDS_TWO = ["unified", "maestro"]  # For operations without driver support
