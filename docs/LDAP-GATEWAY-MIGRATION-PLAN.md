# LDAP Gateway Migration Plan - AAP 2.6

## Issue
In AAP 2.6, LDAP authentication settings moved from Controller to Platform Gateway.

## Current Behavior
Settings migration currently imports ALL settings to Controller:
```
POST /api/controller/v2/settings/all/
```

## Problem
LDAP settings should be imported to Gateway in AAP 2.6:
```
POST /api/gateway/v1/authenticators/
```

## API Endpoints

### AAP 2.4 (Source)
- LDAP settings: `/api/v2/settings/ldap/`
- All settings: `/api/v2/settings/all/`

### AAP 2.6 (Target)
- **LDAP settings**: `/api/gateway/v1/authenticators/` ✅ CONFIRMED
- Controller settings: `/api/controller/v2/settings/all/`
- Gateway settings: `/api/gateway/v1/settings/`

## Solution Plan

### 1. Detect AAP Version
```python
# In SettingsImporter
target_version = await self.get_aap_version()
is_aap_26 = version.parse(target_version) >= version.parse("2.6.0")
```

### 2. Split Settings by Destination
```python
# Categorize settings
ldap_settings = {k: v for k, v in settings.items() if k.startswith('AUTH_LDAP_')}
controller_settings = {k: v for k, v in settings.items() if not k.startswith('AUTH_LDAP_')}
```

### 3. Import to Correct Endpoints
```python
if is_aap_26:
    # Import LDAP to Gateway
    await self.import_ldap_to_gateway(ldap_settings)
    # Import others to Controller
    await self.client.patch("settings/all/", json_data=controller_settings)
else:
    # AAP 2.4/2.5: Import all to Controller
    await self.client.patch("settings/all/", json_data=settings)
```

### 4. Keep AUTH_LDAP_BIND_PASSWORD Manual
Regardless of version, password remains manual entry for security.

## Implementation Files

### Files to Modify
1. `src/aap_migration/migration/importer.py` - SettingsImporter class
2. `src/aap_migration/client/aap_target_client.py` - Add Gateway support
3. `src/aap_migration/migration/transformer.py` - Split LDAP settings

### New Methods Needed
```python
class SettingsImporter:
    async def import_ldap_to_gateway(self, ldap_settings: dict) -> dict:
        """Import LDAP settings to Gateway /authenticators/ endpoint"""

    async def get_aap_version(self) -> str:
        """Detect target AAP version"""
```

## Testing Requirements

### Test Cases
1. ✅ AAP 2.4 → AAP 2.4: All settings to Controller
2. ✅ AAP 2.4 → AAP 2.5: All settings to Controller
3. 🔲 AAP 2.4 → AAP 2.6: LDAP to Gateway, others to Controller
4. 🔲 Verify LDAP authentication works after Gateway import
5. 🔲 Verify AUTH_LDAP_BIND_PASSWORD must be manually entered

### Test Data
- Source: AAP 2.4 with LDAP configured
- Target: AAP 2.6 (containerized)
- Verify both endpoints receive correct settings

## Gateway Authenticators Endpoint Details

**Endpoint:** `POST /api/gateway/v1/authenticators/`

**Expected Payload Structure:** (TBD - needs AAP 2.6 testing)
```json
{
  "type": "ldap",
  "name": "Primary LDAP",
  "configuration": {
    "AUTH_LDAP_SERVER_URI": "ldaps://ldap.example.com:636",
    "AUTH_LDAP_BIND_DN": "cn=service,dc=example,dc=com",
    ...
  }
}
```

**Unknown:**
- Exact JSON schema for authenticators endpoint
- Mapping from AUTH_LDAP_* settings to Gateway format
- How to handle multiple LDAP configs (AUTH_LDAP_1_*, AUTH_LDAP_2_*)

## Status

**Current Status:** Planning - AAP 2.6 not available for testing

**Next Steps:**
1. Wait for AAP 2.6 environment to be available
2. Test Gateway authenticators endpoint
3. Determine exact JSON payload format
4. Implement automatic LDAP split
5. Test end-to-end migration

## Branch

**Branch:** `fix-ldap-migration`
**Based on:** `main` (commit b8448f3)

## References

- Gateway endpoint confirmed by user: `/api/gateway/v1/authenticators/`
- Current workaround documented in README.md "Post-Migration: Verify LDAP Authentication"
- Related files: SETTINGS-REVIEW-REPORT.md generation

---

**Created:** 2026-03-26
**Last Updated:** 2026-03-26
**Status:** Deferred - Awaiting AAP 2.6 availability
