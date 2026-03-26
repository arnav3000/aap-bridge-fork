"""Unit tests for AAP client version detection."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aap_migration.client.aap_source_client import AAPSourceClient
from aap_migration.client.aap_target_client import AAPTargetClient
from aap_migration.config import AAPInstanceConfig


@pytest.fixture
def source_config():
    """Create test source configuration."""
    return AAPInstanceConfig(
        url="https://source-aap.example.com/api/v2",
        token="test-token",
        verify_ssl=False,
        timeout=30,
    )


@pytest.fixture
def target_config():
    """Create test target configuration."""
    return AAPInstanceConfig(
        url="https://target-aap.example.com/api/controller/v2",
        token="test-token",
        verify_ssl=False,
        timeout=30,
    )


class TestAAPSourceClientVersionDetection:
    """Test version detection for AAP source client."""

    @pytest.mark.asyncio
    async def test_get_version_2_4(self, source_config):
        """Test version detection for AAP 2.4."""
        client = AAPSourceClient(source_config)

        # Mock the get() method to return version info
        client.get = AsyncMock(return_value={"version": "2.4.0"})

        version = await client.get_version()
        assert version == "2.4.0"
        client.get.assert_called_once_with("config/")

    @pytest.mark.asyncio
    async def test_get_version_2_5(self, source_config):
        """Test version detection for AAP 2.5."""
        client = AAPSourceClient(source_config)
        client.get = AsyncMock(return_value={"version": "2.5.1"})

        version = await client.get_version()
        assert version == "2.5.1"

    @pytest.mark.asyncio
    async def test_get_version_fallback_to_ansible_version(self, source_config):
        """Test version detection fallback when version field missing."""
        client = AAPSourceClient(source_config)
        client.get = AsyncMock(return_value={"ansible_version": "2.4.2"})

        version = await client.get_version()
        assert version == "2.4.2"

    @pytest.mark.asyncio
    async def test_get_version_default_on_error(self, source_config):
        """Test version detection defaults to 2.4.0 on error."""
        client = AAPSourceClient(source_config)
        client.get = AsyncMock(side_effect=Exception("API error"))

        version = await client.get_version()
        assert version == "2.4.0"

    @pytest.mark.asyncio
    async def test_get_version_cached(self, source_config):
        """Test version is cached after first call."""
        client = AAPSourceClient(source_config)
        client.get = AsyncMock(return_value={"version": "2.4.0"})

        # First call
        version1 = await client.get_version()
        # Second call should use cache
        version2 = await client.get_version()

        assert version1 == version2 == "2.4.0"
        # Should only call API once
        client.get.assert_called_once_with("config/")


class TestAAPTargetClientVersionDetection:
    """Test version detection for AAP target client."""

    @pytest.mark.asyncio
    async def test_get_version_2_6(self, target_config):
        """Test version detection for AAP 2.6."""
        client = AAPTargetClient(target_config)
        client.get = AsyncMock(return_value={"version": "2.6.0"})

        version = await client.get_version()
        assert version == "2.6.0"
        client.get.assert_called_once_with("config/")

    @pytest.mark.asyncio
    async def test_get_version_2_5(self, target_config):
        """Test version detection for AAP 2.5."""
        client = AAPTargetClient(target_config)
        client.get = AsyncMock(return_value={"version": "2.5.0"})

        version = await client.get_version()
        assert version == "2.5.0"

    @pytest.mark.asyncio
    async def test_get_version_fallback_to_ansible_version(self, target_config):
        """Test version detection fallback when version field missing."""
        client = AAPTargetClient(target_config)
        client.get = AsyncMock(return_value={"ansible_version": "2.6.1"})

        version = await client.get_version()
        assert version == "2.6.1"

    @pytest.mark.asyncio
    async def test_get_version_default_on_error(self, target_config):
        """Test version detection defaults to 2.6.0 on error."""
        client = AAPTargetClient(target_config)
        client.get = AsyncMock(side_effect=Exception("API error"))

        version = await client.get_version()
        assert version == "2.6.0"

    @pytest.mark.asyncio
    async def test_get_version_cached(self, target_config):
        """Test version is cached after first call."""
        client = AAPTargetClient(target_config)
        client.get = AsyncMock(return_value={"version": "2.6.0"})

        # First call
        version1 = await client.get_version()
        # Second call should use cache
        version2 = await client.get_version()

        assert version1 == version2 == "2.6.0"
        # Should only call API once
        client.get.assert_called_once_with("config/")

    @pytest.mark.asyncio
    async def test_platform_gateway_url_enforcement(self):
        """Test that target client enforces Platform Gateway URL."""
        # Without /api/controller/v2
        config_no_gateway = AAPInstanceConfig(
            url="https://target-aap.example.com",
            token="test-token",
            verify_ssl=False,
            timeout=30,
        )
        client = AAPTargetClient(config_no_gateway)
        assert "/api/controller/v2" in client.base_url

        # With /api/controller/v2
        config_with_gateway = AAPInstanceConfig(
            url="https://target-aap.example.com/api/controller/v2",
            token="test-token",
            verify_ssl=False,
            timeout=30,
        )
        client = AAPTargetClient(config_with_gateway)
        assert client.base_url.endswith("/api/controller/v2")
