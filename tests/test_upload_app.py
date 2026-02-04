"""Tests for /upload-app endpoint."""

import io
import os
import zipfile
import pytest
import httpx
from pathlib import Path


# Test configuration
IOS_HOST = os.environ.get("IOS_HOST", "localhost")
IOS_PORT = os.environ.get("IOS_PORT", "9226")
ANDROID_HOST = os.environ.get("ANDROID_HOST", "phost.local")
ANDROID_PORT = os.environ.get("ANDROID_PORT", "9225")

TOKEN_FILE = Path.home() / ".android-mcp-token"
TOKEN = TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else None


def get_ios_url():
    return f"http://{IOS_HOST}:{IOS_PORT}"


def get_android_url():
    return f"http://{ANDROID_HOST}:{ANDROID_PORT}"


def get_headers():
    headers = {"Content-Type": "application/octet-stream"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    return headers


def create_mock_ios_app_zip() -> bytes:
    """Create a minimal mock iOS .app bundle as a zip."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Create a minimal .app structure
        zf.writestr("MockApp.app/Info.plist", """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key>
    <string>com.example.mockapp</string>
    <key>CFBundleExecutable</key>
    <string>MockApp</string>
    <key>CFBundleName</key>
    <string>MockApp</string>
</dict>
</plist>""")
        # Empty executable placeholder
        zf.writestr("MockApp.app/MockApp", b"")
    return buffer.getvalue()


def create_mock_apk() -> bytes:
    """Create minimal mock APK data (not a real APK, just for testing endpoint)."""
    # Real APK has ZIP structure with specific files
    # This is just for testing the endpoint accepts data
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("AndroidManifest.xml", b"mock manifest")
        zf.writestr("classes.dex", b"mock dex")
    return buffer.getvalue()


class TestUploadAppEndpoint:
    """Test the /upload-app endpoint."""

    @pytest.mark.asyncio
    async def test_upload_requires_auth(self):
        """Test that upload requires authentication."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{get_ios_url()}/upload-app",
                content=b"test data",
                headers={"Content-Type": "application/octet-stream"},
            )
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_rejects_empty_body(self):
        """Test that upload rejects empty or too-small body."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{get_ios_url()}/upload-app",
                content=b"tiny",
                headers=get_headers(),
            )
            assert response.status_code == 400
            assert "too small" in response.json().get("detail", "").lower()

    @pytest.mark.asyncio
    async def test_upload_accepts_zip(self):
        """Test that upload accepts a zip file (may fail on install but endpoint works)."""
        mock_zip = create_mock_ios_app_zip()

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{get_ios_url()}/upload-app",
                content=mock_zip,
                headers=get_headers(),
            )
            # Either succeeds or fails on actual install (mock app won't work)
            # But we should get past the upload/extract phase
            assert response.status_code in [200, 500]
            data = response.json()
            if response.status_code == 200:
                assert data.get("success") is True
                assert data.get("platform") == "ios"


@pytest.mark.ios_only
class TestIOSAppUpload:
    """iOS-specific upload tests (require simulator running)."""

    @pytest.fixture
    def test_app_path(self):
        """Get path to test app if it exists."""
        test_app = Path(__file__).parent.parent / "test_app" / "build" / "ios" / "iphonesimulator" / "Runner.app"
        if not test_app.exists():
            pytest.skip("Test app not built. Run: cd test_app && flutter build ios --debug --simulator")
        return test_app

    @pytest.mark.asyncio
    async def test_upload_real_ios_app(self, test_app_path):
        """Test uploading a real iOS app (requires test app built)."""
        # Create zip of the .app bundle
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in test_app_path.rglob("*"):
                if file_path.is_file():
                    arc_name = f"{test_app_path.name}/{file_path.relative_to(test_app_path)}"
                    zf.write(file_path, arc_name)

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{get_ios_url()}/upload-app",
                content=buffer.getvalue(),
                headers={
                    **get_headers(),
                    "X-Bundle-Id": "com.example.flutterControlTestApp",
                    "X-Launch": "true",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data.get("success") is True
            assert data.get("platform") == "ios"


@pytest.mark.android_only
class TestAndroidAppUpload:
    """Android-specific upload tests (require emulator running)."""

    @pytest.fixture
    def test_apk_path(self):
        """Get path to test APK if it exists."""
        test_apk = Path(__file__).parent.parent / "test_app" / "build" / "app" / "outputs" / "flutter-apk" / "app-debug.apk"
        if not test_apk.exists():
            pytest.skip("Test APK not built. Run: cd test_app && flutter build apk --debug")
        return test_apk

    @pytest.mark.asyncio
    async def test_upload_real_android_app(self, test_apk_path):
        """Test uploading a real Android APK (requires test app built)."""
        apk_data = test_apk_path.read_bytes()

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{get_android_url()}/upload-app",
                content=apk_data,
                headers={
                    **get_headers(),
                    "X-Bundle-Id": "com.example.flutter_control_test_app",
                    "X-Launch": "true",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data.get("success") is True
            assert data.get("platform") == "android"


class TestUploadAppHeaders:
    """Test header handling for upload-app."""

    @pytest.mark.asyncio
    async def test_device_header(self):
        """Test X-Device header is passed through."""
        mock_zip = create_mock_ios_app_zip()

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{get_ios_url()}/upload-app",
                content=mock_zip,
                headers={
                    **get_headers(),
                    "X-Device": "booted",
                },
            )
            # Check response includes device info
            if response.status_code == 200:
                data = response.json()
                assert data.get("device") == "booted"

    @pytest.mark.asyncio
    async def test_bundle_id_header(self):
        """Test X-Bundle-Id header for launch."""
        mock_zip = create_mock_ios_app_zip()

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{get_ios_url()}/upload-app",
                content=mock_zip,
                headers={
                    **get_headers(),
                    "X-Bundle-Id": "com.example.test",
                    "X-Launch": "true",
                },
            )
            # Response should include bundle_id if launch was attempted
            if response.status_code == 200:
                data = response.json()
                if data.get("launched") is not None:
                    assert "bundle_id" in data or data.get("launched") is False
