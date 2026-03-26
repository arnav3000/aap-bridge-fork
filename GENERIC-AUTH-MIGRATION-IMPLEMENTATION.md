# Generic Authentication Migration - Implementation Complete

## Summary

Extended the AAP 2.6 Gateway migration to support **multiple authentication methods** while maintaining 100% backward compatibility with the existing LDAP implementation.

## Supported Authentication Methods

The migration framework now automatically detects and migrates:

1. ✅ **LDAP** (existing implementation - unchanged)
   - Settings prefix: `AUTH_LDAP_*`
   - Plugin type: `ansible_base.authentication.authenticator_plugins.ldap`
   - Supports organization/team mapping via authenticator_maps

2. ✅ **SAML SSO** (new)
   - Settings prefix: `SOCIAL_AUTH_SAML_*`
   - Plugin type: `ansible_base.authentication.authenticator_plugins.saml`
   - Supports organization/team mapping via authenticator_maps (uses SAML attributes)

3. ✅ **Azure AD OAuth2** (new)
   - Settings prefix: `SOCIAL_AUTH_AZUREAD_OAUTH2_*`
   - Plugin type: `ansible_base.authentication.authenticator_plugins.azuread_oauth`

4. ✅ **GitHub Enterprise** (new)
   - Settings prefix: `SOCIAL_AUTH_GITHUB_ENTERPRISE_*`
   - Plugin type: `ansible_base.authentication.authenticator_plugins.github`

## Implementation Details

### New Methods Added to `SettingsImporter`

#### 1. Orchestration Method
```python
async def _migrate_all_authentication_to_gateway(
    safe: dict,
    review_required: dict,
    sensitive: dict
) -> dict[str, Any]
```
- Detects which authentication methods are configured
- Calls appropriate migration method for each
- Returns structured result with migration details
- Tracks migrated prefixes for cleanup

#### 2. SAML Migration
```python
async def _migrate_saml_to_gateway(saml_settings: dict) -> bool
def _transform_saml_to_gateway(saml_settings: dict) -> dict | None
async def _create_saml_authenticator_maps(authenticator_id: int, saml_settings: dict) -> int
```
- Transforms SAML settings from AAP 2.4 to Gateway format
- Creates authenticator with SAML plugin
- Creates organization/team maps using SAML attributes (not LDAP groups)
- Excludes `SP_PRIVATE_KEY` for security

#### 3. Azure AD Migration
```python
async def _migrate_azure_ad_to_gateway(azure_settings: dict) -> bool
def _transform_azure_ad_to_gateway(azure_settings: dict) -> dict | None
```
- Transforms Azure AD OAuth2 settings
- Creates authenticator with Azure AD plugin
- Excludes `SECRET` for security

#### 4. GitHub Migration
```python
async def _migrate_github_to_gateway(github_settings: dict) -> bool
def _transform_github_to_gateway(github_settings: dict) -> dict | None
```
- Transforms GitHub Enterprise settings
- Creates authenticator with GitHub plugin
- Excludes `SECRET` for security

### Updated Report Generation

Modified `_generate_settings_review_report()` to:
- Accept full authentication migration info (not just LDAP boolean)
- Display all migrated authentication methods
- List specific credentials needed for each auth type:
  - LDAP: `BIND_PASSWORD`
  - SAML: `SP_PRIVATE_KEY`
  - Azure AD: `SECRET`
  - GitHub: `SECRET`

## Field Mapping Examples

### SAML
| AAP 2.4 Field | Gateway Field | Security |
|---------------|---------------|----------|
| `SOCIAL_AUTH_SAML_SP_ENTITY_ID` | `SP_ENTITY_ID` | ✅ Safe |
| `SOCIAL_AUTH_SAML_SP_PUBLIC_CERT` | `SP_PUBLIC_CERT` | ✅ Safe |
| `SOCIAL_AUTH_SAML_SP_PRIVATE_KEY` | ⚠️ **MANUAL ENTRY** | 🔒 Excluded |
| `SOCIAL_AUTH_SAML_ENABLED_IDPS` | `ENABLED_IDPS` | ✅ Safe |
| `SOCIAL_AUTH_SAML_SECURITY_CONFIG` | `SECURITY_CONFIG` | ✅ Safe |

### Azure AD OAuth2
| AAP 2.4 Field | Gateway Field | Security |
|---------------|---------------|----------|
| `SOCIAL_AUTH_AZUREAD_OAUTH2_KEY` | `KEY` | ✅ Safe |
| `SOCIAL_AUTH_AZUREAD_OAUTH2_SECRET` | ⚠️ **MANUAL ENTRY** | 🔒 Excluded |
| `SOCIAL_AUTH_AZUREAD_OAUTH2_URL` | `URL` | ✅ Safe |

### GitHub Enterprise
| AAP 2.4 Field | Gateway Field | Security |
|---------------|---------------|----------|
| `SOCIAL_AUTH_GITHUB_ENTERPRISE_URL` | `URL` | ✅ Safe |
| `SOCIAL_AUTH_GITHUB_ENTERPRISE_API_URL` | `API_URL` | ✅ Safe |
| `SOCIAL_AUTH_GITHUB_ENTERPRISE_KEY` | `KEY` | ✅ Safe |
| `SOCIAL_AUTH_GITHUB_ENTERPRISE_SECRET` | ⚠️ **MANUAL ENTRY** | 🔒 Excluded |

## Migration Flow

### AAP 2.6+ (Automatic Gateway Migration)
```
1. Detect AAP version >= 2.6.0
2. Extract authentication settings by prefix:
   - AUTH_LDAP_* → LDAP
   - SOCIAL_AUTH_SAML_* → SAML
   - SOCIAL_AUTH_AZUREAD_OAUTH2_* → Azure AD
   - SOCIAL_AUTH_GITHUB_ENTERPRISE_* → GitHub
3. For each detected auth method:
   - Transform settings to Gateway format
   - Create Gateway authenticator
   - Create authenticator maps (for LDAP, SAML)
4. Remove migrated settings from other categories
5. Import non-auth settings to Controller API
6. Generate report with migration status
```

### AAP 2.4/2.5 (Legacy Migration)
```
1. Import all settings to Controller API as before
2. No Gateway interaction
3. Generate standard report
```

## Testing Instructions

### Test Scenario: Multiple Authentication Methods

```bash
# 1. Configure multiple auth methods in source AAP 2.4
# - LDAP: AUTH_LDAP_SERVER_URI, AUTH_LDAP_BIND_DN, etc.
# - SAML: SOCIAL_AUTH_SAML_ENABLED_IDPS, etc.
# - Azure AD: SOCIAL_AUTH_AZUREAD_OAUTH2_KEY, etc.

# 2. Run migration
aap-bridge migrate -r settings --skip-prep

# 3. Verify authenticators created
curl -sk -H "Authorization: Bearer $TARGET__TOKEN" \
  https://localhost:10443/api/gateway/v1/authenticators/ | jq '.results[] | {id, name, type, enabled}'

# Expected output:
# - "Primary LDAP" (type: ldap)
# - "SAML SSO" (type: saml)
# - "Azure AD OAuth2" (type: azuread_oauth)
# - "GitHub Enterprise" (type: github) [if configured]

# 4. Verify authenticator maps (LDAP, SAML only)
curl -sk -H "Authorization: Bearer $TARGET__TOKEN" \
  https://localhost:10443/api/gateway/v1/authenticator_maps/ | jq '.results[] | {id, name, map_type, organization, team}'

# 5. Check migration report
cat SETTINGS-REVIEW-REPORT.md

# Expected report sections:
# - ✅ Authentication Settings Migrated to Gateway: LDAP, SAML, Azure AD OAuth2
# - List of credentials to manually enter
# - Verification links
```

### Test Scenario: LDAP Only (Backward Compatibility)

```bash
# 1. Configure only LDAP in source (no SAML, Azure AD, etc.)

# 2. Run migration
aap-bridge migrate -r settings --skip-prep

# 3. Verify only LDAP authenticator created
curl -sk -H "Authorization: Bearer $TARGET__TOKEN" \
  https://localhost:10443/api/gateway/v1/authenticators/ | jq '.results[] | select(.type | contains("ldap"))'

# Expected: Single LDAP authenticator (exactly as before)
```

## Backward Compatibility

✅ **100% Compatible** - The implementation:
- Does NOT modify any existing LDAP migration code
- LDAP migration runs first (same order as before)
- LDAP methods (`_migrate_ldap_to_gateway`, `_transform_ldap_to_gateway`, etc.) unchanged
- If only LDAP is configured, behavior is identical to previous implementation
- New auth types are purely additive

## Security Considerations

**Sensitive credentials NOT migrated automatically:**
- LDAP: `AUTH_LDAP_BIND_PASSWORD`
- SAML: `SOCIAL_AUTH_SAML_SP_PRIVATE_KEY`
- Azure AD: `SOCIAL_AUTH_AZUREAD_OAUTH2_SECRET`
- GitHub: `SOCIAL_AUTH_GITHUB_ENTERPRISE_SECRET`

**Must be manually entered in Gateway UI:**
1. Navigate to: Settings → Authentication → Authenticators
2. Edit each authenticator
3. Enter the sensitive credential in configuration
4. Save

## Files Modified

```
src/aap_migration/migration/importer.py    (+390 lines)
```

### Changes:
1. Added `_migrate_all_authentication_to_gateway()` - Generic orchestration
2. Added `_migrate_saml_to_gateway()` - SAML migration
3. Added `_migrate_azure_ad_to_gateway()` - Azure AD migration
4. Added `_migrate_github_to_gateway()` - GitHub migration
5. Added `_transform_saml_to_gateway()` - SAML field mapping
6. Added `_transform_azure_ad_to_gateway()` - Azure AD field mapping
7. Added `_transform_github_to_gateway()` - GitHub field mapping
8. Added `_create_saml_authenticator_maps()` - SAML org/team maps
9. Updated `_generate_settings_review_report()` - Multi-auth reporting
10. Updated `import_resource()` - Calls generic orchestration method

## Future Extensions

To add support for additional authentication methods:

1. **Add detection in `_migrate_all_authentication_to_gateway()`:**
```python
# 5. Google OAuth2 Migration
google_settings = self._extract_auth_settings(
    safe, review_required, sensitive, 'SOCIAL_AUTH_GOOGLE_OAUTH2_'
)
if google_settings:
    google_migrated = await self._migrate_google_to_gateway(google_settings)
```

2. **Implement migration method:**
```python
async def _migrate_google_to_gateway(self, google_settings: dict) -> bool:
    config = self._transform_google_to_gateway(google_settings)
    authenticator = await self.client.create_gateway_authenticator(
        name="Google OAuth2",
        plugin_type="ansible_base.authentication.authenticator_plugins.google_oauth",
        configuration=config
    )
    return True
```

3. **Implement transformation method:**
```python
def _transform_google_to_gateway(self, google_settings: dict) -> dict | None:
    field_mapping = {
        'SOCIAL_AUTH_GOOGLE_OAUTH2_KEY': 'KEY',
        # SECRET excluded for security
    }
    # ... mapping logic
```

## Status

- ✅ **Implementation Complete**
- ✅ **Syntax Validated**
- ✅ **Backward Compatible**
- 🔲 Testing Pending (requires AAP 2.6 with SAML/Azure AD configured)

---

**Created:** 2026-03-26
**Branch:** 24-26-final
**Implementation Time:** ~1 hour
