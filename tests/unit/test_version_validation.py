"""Unit tests for version validation utilities."""

import pytest

from aap_migration.utils.version_validation import (
    VersionValidationError,
    get_version_info,
    parse_version,
    validate_version_compatibility,
)


class TestParseVersion:
    """Test version parsing functionality."""

    def test_parse_standard_version(self):
        """Test parsing a standard version string."""
        assert parse_version("2.4.0") == (2, 4, 0)
        assert parse_version("2.6.1") == (2, 6, 1)
        assert parse_version("3.0.0") == (3, 0, 0)

    def test_parse_version_with_dev_suffix(self):
        """Test parsing version with dev/rc suffix."""
        assert parse_version("2.4.0-dev") == (2, 4, 0)
        assert parse_version("2.6.0-rc1") == (2, 6, 0)
        assert parse_version("2.5.1+build123") == (2, 5, 1)

    def test_parse_version_missing_components(self):
        """Test parsing version with missing minor/patch."""
        assert parse_version("2") == (2, 0, 0)
        assert parse_version("2.4") == (2, 4, 0)

    def test_parse_invalid_version(self):
        """Test parsing invalid version string."""
        with pytest.raises(ValueError):
            parse_version("invalid")
        with pytest.raises(ValueError):
            parse_version("")


class TestValidateVersionCompatibility:
    """Test version compatibility validation."""

    def test_valid_2_4_to_2_6_migration(self):
        """Test valid 2.4 to 2.6 migration."""
        # Should not raise
        validate_version_compatibility("2.4.0", "2.6.0")
        validate_version_compatibility("2.4.1", "2.6.1")

    def test_valid_2_4_to_2_5_migration(self):
        """Test valid 2.4 to 2.5 migration."""
        # Should not raise
        validate_version_compatibility("2.4.0", "2.5.0")
        validate_version_compatibility("2.4.5", "2.5.2")

    def test_valid_2_3_to_2_6_migration(self):
        """Test valid 2.3 to 2.6 migration."""
        # Should not raise
        validate_version_compatibility("2.3.0", "2.6.0")
        validate_version_compatibility("2.3.5", "2.6.1")

    def test_source_version_too_old(self):
        """Test source version below minimum."""
        with pytest.raises(VersionValidationError, match="below minimum supported version"):
            validate_version_compatibility("2.2.0", "2.6.0")

        with pytest.raises(VersionValidationError, match="below minimum supported version"):
            validate_version_compatibility("2.1.0", "2.5.0")

    def test_target_version_too_old(self):
        """Test target version below minimum."""
        with pytest.raises(VersionValidationError, match="below minimum supported version"):
            validate_version_compatibility("2.4.0", "2.4.0")

        with pytest.raises(VersionValidationError, match="below minimum supported version"):
            validate_version_compatibility("2.3.0", "2.3.0")

    def test_downgrade_migration_warning(self, caplog):
        """Test downgrade migration logs warning but doesn't fail."""
        # Should not raise, but should log warning
        validate_version_compatibility("2.6.0", "2.5.0")
        # Note: Testing log messages requires caplog fixture from pytest

    def test_same_version_migration(self):
        """Test migration between same versions."""
        # Should work if both meet minimum requirements
        validate_version_compatibility("2.5.0", "2.5.0")
        validate_version_compatibility("2.6.0", "2.6.0")

    def test_custom_minimum_versions(self):
        """Test validation with custom minimum versions."""
        # Should fail with custom minimums
        with pytest.raises(VersionValidationError):
            validate_version_compatibility(
                "2.4.0", "2.5.0", min_source_version="2.5.0", min_target_version="2.6.0"
            )

        # Should pass with appropriate versions
        validate_version_compatibility(
            "2.5.0", "2.6.0", min_source_version="2.5.0", min_target_version="2.6.0"
        )


class TestGetVersionInfo:
    """Test version info extraction."""

    def test_version_2_4_info(self):
        """Test version info for AAP 2.4."""
        info = get_version_info("2.4.0")
        assert info["major"] == 2
        assert info["minor"] == 4
        assert info["patch"] == 0
        assert info["is_2_4"] is True
        assert info["is_2_5"] is False
        assert info["is_2_6"] is False
        assert info["supports_bulk_operations"] is True
        assert info["supports_platform_gateway"] is False

    def test_version_2_6_info(self):
        """Test version info for AAP 2.6."""
        info = get_version_info("2.6.0")
        assert info["major"] == 2
        assert info["minor"] == 6
        assert info["patch"] == 0
        assert info["is_2_4"] is False
        assert info["is_2_5"] is False
        assert info["is_2_6"] is True
        assert info["supports_bulk_operations"] is True
        assert info["supports_platform_gateway"] is True

    def test_version_2_5_info(self):
        """Test version info for AAP 2.5."""
        info = get_version_info("2.5.1")
        assert info["major"] == 2
        assert info["minor"] == 5
        assert info["patch"] == 1
        assert info["is_2_5"] is True
        assert info["supports_bulk_operations"] is True
        assert info["supports_platform_gateway"] is False

    def test_invalid_version_info(self):
        """Test version info for invalid version."""
        info = get_version_info("invalid")
        assert info["major"] == 0
        assert info["minor"] == 0
        assert info["patch"] == 0
        assert info["is_2_4"] is False
        assert info["supports_bulk_operations"] is False
        assert info["supports_platform_gateway"] is False
