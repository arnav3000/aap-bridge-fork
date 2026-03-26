# AAP 2.4 to 2.6 Migration Support

This document outlines the changes made to ensure AAP Bridge fully supports migrating from AAP 2.4 (RPM-based) to AAP 2.6 (containerized).

## Overview

AAP Bridge now fully supports migrations between various AAP versions:

- **Source**: AAP 2.3+, 2.4+, 2.5+
- **Target**: AAP 2.5+, 2.6+
- **Primary use case**: AAP 2.4 (RPM/VM) → AAP 2.6 (containerized)

## Changes Implemented

### 1. Dynamic Version Detection

**Files Modified:**
- `src/aap_migration/client/aap_source_client.py`
- `src/aap_migration/client/aap_target_client.py`

**Changes:**
- Added `get_version()` method to both clients
- Queries `/api/v2/config/` endpoint to detect actual AAP version
- Caches version after first detection to avoid repeated API calls
- Falls back to sensible defaults (2.4.0 for source, 2.6.0 for target) if detection fails
- Updated class docstrings to reflect support for multiple versions

**Benefits:**
- No more hardcoded version assumptions
- Automatic adaptation to source/target versions
- Better error messages when versions are incompatible

### 2. Version Compatibility Validation

**Files Created:**
- `src/aap_migration/utils/version_validation.py`

**Features:**
- `parse_version()`: Parses version strings into (major, minor, patch) tuples
- `validate_version_compatibility()`: Ensures source and target versions are compatible
- `get_version_info()`: Provides detailed version metadata (supports_platform_gateway, etc.)

**Validation Rules:**
- Source must be >= 2.3.0
- Target must be >= 2.5.0
- Warns (but allows) downgrade migrations (target < source)
- Configurable minimum version requirements

**Files Modified:**
- `src/aap_migration/cli/commands/prep.py`

**Integration:**
- Prep command now detects versions before schema discovery
- Validates compatibility before proceeding with migration
- Displays clear error messages for incompatible versions

### 3. Documentation Updates

**Files Modified:**
- `src/aap_migration/client/aap_source_client.py`
- `src/aap_migration/client/aap_target_client.py`
- `src/aap_migration/migration/transformer.py`
- `src/aap_migration/migration/importer.py`
- `CLAUDE.md`

**Changes:**
- Updated all "AAP 2.3" references to "AAP 2.4+"
- Updated transformer documentation to reflect 2.4+ → 2.5+ migrations
- Documented built-in credential type ID assumptions (IDs 1-27)
- Added version detection documentation to CLAUDE.md

### 4. Comprehensive Test Suite

**Files Created:**
- `tests/unit/test_version_validation.py`
- `tests/unit/test_client_version_detection.py`
- `tests/__init__.py`
- `tests/unit/__init__.py`

**Test Coverage:**
- Version parsing (standard, dev/rc suffixes, missing components)
- Version compatibility validation (valid migrations, invalid migrations)
- Version info extraction (feature detection by version)
- Client version detection (mocked API calls)
- Version caching behavior
- Platform Gateway URL enforcement

**Test Categories:**
- Valid migrations: 2.4→2.6, 2.4→2.5, 2.3→2.6
- Invalid migrations: Too old source/target, downgrade warnings
- Edge cases: Invalid version strings, missing version fields, API errors

## Usage

### Running Prep with Version Detection

```bash
# The prep command now automatically detects versions
aap-bridge prep --output schemas/

# Output shows detected versions:
# ✓ Connecting to source-aap and target-aap
# ✓ Detecting AAP versions (Source: 2.4.1, Target: 2.6.0)
# ✓ Discovering endpoints
# ✓ Generating schemas
# ✓ Comparing schemas
```

### Version Compatibility Checks

The tool now validates version compatibility automatically:

```python
# Successful validation
Source: 2.4.0, Target: 2.6.0 ✓

# Source too old
Source: 2.2.0, Target: 2.6.0 ✗
Error: Source AAP version 2.2.0 is below minimum supported version 2.3.0

# Target too old
Source: 2.4.0, Target: 2.4.0 ✗
Error: Target AAP version 2.4.0 is below minimum supported version 2.5.0

# Downgrade migration (warning)
Source: 2.6.0, Target: 2.5.0 ⚠
Warning: Target version is older than source version. Downgrade migrations may have compatibility issues.
```

## Key Architectural Notes

### Platform Gateway (AAP 2.6+)

AAP 2.6 introduced the Platform Gateway, which requires routing through `/api/controller/v2`:

- **Source (AAP 2.4)**: `https://source-aap.example.com/api/v2`
- **Target (AAP 2.6)**: `https://target-aap.example.com/api/controller/v2`

The `AAPTargetClient` automatically enforces the Platform Gateway path. If the URL doesn't end with `/api/controller/v2`, it appends it.

### Bulk Operations

Bulk operations (hosts, inventories) are available in AAP 2.4+:

- **Hosts**: 200 per batch (API maximum)
- **Inventories**: 200 per batch
- **Other resources**: 50-100 per batch (configurable)

The tool detects whether bulk operations are supported via `get_version_info()`.

### Credential Type IDs

**Important Assumption**: Built-in credential types have IDs 1-27 in AAP 2.3, 2.4, 2.5, and 2.6.

This assumption is documented in `src/aap_migration/migration/importer.py` with instructions to verify:

```bash
# Verify built-in credential type IDs on source
curl -k https://source-aap/api/v2/credential_types/?managed=true

# Verify built-in credential type IDs on target
curl -k https://target-aap/api/controller/v2/credential_types/?managed=true
```

If your AAP instances have different built-in credential type IDs, adjust `BUILTIN_CREDENTIAL_TYPE_MAX_ID` in `importer.py`.

## Testing the Changes

### Unit Tests

```bash
# Run version validation tests
pytest tests/unit/test_version_validation.py -v

# Run client version detection tests
pytest tests/unit/test_client_version_detection.py -v

# Run all unit tests
pytest tests/unit/ -v
```

### Integration Testing

For full integration testing with actual AAP instances:

1. Set up AAP 2.4 source instance
2. Set up AAP 2.6 target instance
3. Configure `.env` with credentials
4. Run prep command to verify version detection
5. Run test migration with small dataset
6. Validate results

## Migration Checklist for 2.4→2.6

- [ ] Verify source AAP is version 2.4+ (`/api/v2/config/`)
- [ ] Verify target AAP is version 2.6+ (`/api/controller/v2/config/`)
- [ ] Confirm target URL includes `/api/controller/v2` (Platform Gateway)
- [ ] Set up PostgreSQL state database
- [ ] Configure `.env` with source/target credentials
- [ ] Run `aap-bridge prep` to validate compatibility
- [ ] Review schema comparison report for field differences
- [ ] Verify built-in credential type IDs (1-27) if needed
- [ ] Set up HashiCorp Vault for credential migration (optional)
- [ ] Test with small dataset before full migration
- [ ] Monitor Platform Gateway for "no healthy upstream" errors

## Known Limitations

1. **Encrypted Credentials**: Cannot extract encrypted fields from source AAP (shows as `$encrypted$`). Must be recreated in Vault or manually.

2. **Downgrade Migrations**: Migrating from newer to older AAP versions (e.g., 2.6→2.4) is not recommended and may fail. The tool warns but allows it.

3. **Platform Gateway Load**: AAP 2.6 Platform Gateway can become overloaded with too many concurrent requests. The tool limits concurrency to prevent "no healthy upstream" errors.

4. **Credential Type IDs**: The tool assumes built-in credential types have IDs 1-27 in all versions. This must be verified for your specific AAP instances.

## Troubleshooting

### Version Detection Fails

If version detection fails, the tool defaults to:
- Source: 2.4.0
- Target: 2.6.0

Check:
- Network connectivity to `/api/v2/config/` endpoint
- Authentication token validity
- SSL certificate verification settings

### Version Compatibility Error

If you see "Source AAP version X.Y.Z is below minimum supported version":
- Upgrade your source AAP to 2.3.0 or later
- Or adjust `min_source_version` parameter if you understand the risks

### Platform Gateway Errors

If you see "no healthy upstream" errors:
- Reduce `max_concurrent` in `config/config.yaml`
- Reduce `cleanup_job_cancel_concurrency` (must be <= 25)
- Add delays between large batch operations

## Future Enhancements

1. **Dynamic Credential Type ID Detection**: Automatically detect built-in credential type ID range instead of hardcoding.

2. **Version-Specific Transformations**: Apply different field transformations based on source/target versions.

3. **Performance Tuning by Version**: Automatically adjust batch sizes and concurrency based on detected AAP version.

4. **Enhanced Compatibility Matrix**: Detailed documentation of known issues for each version combination.

## References

- [AAP 2.4 Release Notes](https://access.redhat.com/documentation/en-us/red_hat_ansible_automation_platform/2.4)
- [AAP 2.6 Release Notes](https://access.redhat.com/documentation/en-us/red_hat_ansible_automation_platform/2.6)
- [AAP Platform Gateway Documentation](https://docs.ansible.com/automation-controller/latest/html/administration/platform_gateway.html)
- [AAP Bulk Operations API](https://docs.ansible.com/automation-controller/latest/html/controllerapi/api_ref.html#/Bulk)
