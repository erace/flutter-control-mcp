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
    # Only validate Android env vars when running Android tests
    if os.getenv("TEST_PLATFORM") != "android":
        return

    warnings = []

    # Get the canonical ANDROID_HOST
    android_host = os.getenv("ANDROID_HOST", "phost.local")

    # Auto-configure ADB_SERVER_SOCKET for Android tests via proxy
    if not os.getenv("ADB_SERVER_SOCKET"):
        os.environ["ADB_SERVER_SOCKET"] = f"tcp:{android_host}:15037"

    # Check for deprecated/legacy env vars that should be migrated
    legacy_vars = {
        "ANDROID_MCP_HOST": "ANDROID_HOST",
        "ANDROID_MCP_PORT": "FLUTTER_CONTROL_PORT",
        "ANDROID_MCP_BRIDGE_HOST": "ANDROID_HOST (single host for all services)",
        "ANDROID_MCP_BRIDGE_PORT": "BRIDGE_PORT",
    }

    for old_var, new_var in legacy_vars.items():
        if os.getenv(old_var):
            warnings.append(
                f"{old_var} is deprecated.\n"
                f"         Use: {new_var}"
            )

    # Check ANDROID_HOST for hardcoded IP
    if android_host and "192.168" in android_host:
        warnings.append(
            f"ANDROID_HOST={android_host} looks like a hardcoded IP.\n"
            f"         Consider using: ANDROID_HOST=phost.local (mDNS)"
        )

    if warnings:
        print("\n" + "=" * 60)
        print("⚠️  ENVIRONMENT VARIABLE WARNINGS")
        print("=" * 60)
        for w in warnings:
            print(f"  • {w}")
        print("=" * 60)
        print("Fix: Remove old vars from ~/.zshrc, use new config:")
        print("  export ANDROID_HOST=phost.local  # (or omit for default)")
        print("=" * 60 + "\n")


# Session-scoped fixtures


@pytest.fixture(scope="session")
def platform_config() -> PlatformConfig:
    """Get the platform configuration for this test session."""
    return get_platform_config()


@pytest.fixture(scope="session")
def bootstrap_result(platform_config: PlatformConfig) -> BootstrapResult:
    """Bootstrap test environment before any tests run.

    Uses MCP tools to:
    - Start emulator/simulator if not running
    - Launch app with flutter_run (enables Driver/Observatory)
    - Connect to Flutter Driver
    """
    token_file = Path.home() / ".android-mcp-token"
    token = token_file.read_text().strip() if token_file.exists() else ""

    loop = asyncio.new_event_loop()
    try:
        if platform_config.is_android:
            # Use config from PlatformConfig (derived from ANDROID_HOST)
            bootstrap = AndroidBootstrap(
                mcp_bridge_host=platform_config.bridge_host,
                mcp_bridge_port=platform_config.bridge_port,
                token=token,
                flutter_control_host=platform_config.mcp_host,
                flutter_control_port=platform_config.mcp_port,
            )
        else:
            bootstrap = IOSBootstrap(
                mcp_host=platform_config.mcp_host,
                mcp_port=platform_config.mcp_port,
                token=token,
                device_name=os.getenv("IOS_DEVICE_NAME", "iPhone 16e"),
            )
        result = loop.run_until_complete(bootstrap.bootstrap())
    finally:
        loop.close()

    if result.error:
        pytest.exit(f"Bootstrap failed: {result.error}", returncode=1)

    print(f"\n✓ Bootstrap complete: {result.platform}")
    print(f"  Device: {result.device_id}")
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
