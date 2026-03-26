# AAP 2.6 LDAP Gateway Field Mapping

## Overview

In AAP 2.6, LDAP authentication moved from Controller (`/api/controller/v2/settings/ldap/`) to Platform Gateway (`/api/gateway/v1/authenticators/`).

The field names have changed from `AUTH_LDAP_*` to simplified names without the prefix.

## Gateway LDAP Authenticator Schema

### Plugin Type
```
ansible_base.authentication.authenticator_plugins.ldap
```

### Field Mapping: AAP 2.4 → AAP 2.6 Gateway

| AAP 2.4 (Controller) | AAP 2.6 (Gateway) | Type | Required |
|---------------------|-------------------|------|----------|
| **Connection Settings** |
| `AUTH_LDAP_SERVER_URI` | `SERVER_URI` | URLListField | ✅ Yes |
| `AUTH_LDAP_BIND_DN` | `BIND_DN` | DNField | No |
| `AUTH_LDAP_BIND_PASSWORD` | `BIND_PASSWORD` | CharField | No |
| `AUTH_LDAP_CONNECTION_OPTIONS` | `CONNECTION_OPTIONS` | LDAPConnectionOptions | No |
| `AUTH_LDAP_START_TLS` | `START_TLS` | BooleanField | No |
| **User Settings** |
| `AUTH_LDAP_USER_SEARCH` | `USER_SEARCH` | LDAPSearchField | No |
| `AUTH_LDAP_USER_DN_TEMPLATE` | `USER_DN_TEMPLATE` | DNField | No |
| `AUTH_LDAP_USER_ATTR_MAP` | `USER_ATTR_MAP` | UserAttrMap | ✅ Yes |
| **Group Settings** |
| `AUTH_LDAP_GROUP_TYPE` | `GROUP_TYPE` | ChoiceField | ✅ Yes |
| `AUTH_LDAP_GROUP_TYPE_PARAMS` | `GROUP_TYPE_PARAMS` | DictField | ✅ Yes |
| `AUTH_LDAP_GROUP_SEARCH` | `GROUP_SEARCH` | LDAPSearchField | No |
| `AUTH_LDAP_REQUIRE_GROUP` | `REQUIRE_GROUP` | DNField | No |
| `AUTH_LDAP_DENY_GROUP` | `DENY_GROUP` | DNField | No |
| **Organization & Team Mappings** |
| `AUTH_LDAP_ORGANIZATION_MAP` | `ORGANIZATION_MAP` | DictField | No |
| `AUTH_LDAP_TEAM_MAP` | `TEAM_MAP` | DictField | No |
| `AUTH_LDAP_USER_FLAGS_BY_GROUP` | `USER_FLAGS_BY_GROUP` | DictField | No |

### Multiple LDAP Servers

AAP 2.4 supports multiple LDAP servers using numbered prefixes:
- Primary: `AUTH_LDAP_*`
- Secondary: `AUTH_LDAP_1_*`
- Tertiary: `AUTH_LDAP_2_*`

AAP 2.6 Gateway handles multiple LDAP servers by creating **separate authenticator objects**, each with its own configuration.

## Gateway Authenticator Payload Structure

### Creating LDAP Authenticator

```json
POST /api/gateway/v1/authenticators/

{
  "name": "Primary LDAP",
  "type": "ansible_base.authentication.authenticator_plugins.ldap",
  "enabled": true,
  "create_objects": true,
  "remove_users": false,
  "order": 2,
  "configuration": {
    "SERVER_URI": ["ldap://ldap.example.com:389"],
    "BIND_DN": "cn=ansible-svc,ou=ServiceAccounts,dc=example,dc=com",
    "BIND_PASSWORD": "password123",
    "CONNECTION_OPTIONS": {
      "OPT_REFERRALS": 0,
      "OPT_NETWORK_TIMEOUT": 30
    },
    "GROUP_TYPE": "MemberDNGroupType",
    "GROUP_TYPE_PARAMS": {
      "member_attr": "member",
      "name_attr": "cn"
    },
    "GROUP_SEARCH": ["ou=Groups,dc=example,dc=com", "SCOPE_SUBTREE", "(objectClass=group)"],
    "START_TLS": false,
    "USER_ATTR_MAP": {
      "first_name": "givenName",
      "last_name": "sn",
      "email": "mail"
    },
    "USER_SEARCH": ["ou=Users,dc=example,dc=com", "SCOPE_SUBTREE", "(sAMAccountName=%(user)s)"],
    "USER_FLAGS_BY_GROUP": {
      "is_superuser": "cn=AAP-Admins,ou=Groups,dc=example,dc=com",
      "is_system_auditor": "cn=AAP-Auditors,ou=Groups,dc=example,dc=com"
    },
    "ORGANIZATION_MAP": {
      "Global Engineering": {
        "admins": "cn=Engineering-Admins,ou=Groups,dc=example,dc=com",
        "users": "cn=Engineering-Users,ou=Groups,dc=example,dc=com",
        "remove_admins": false,
        "remove_users": false
      }
    },
    "TEAM_MAP": {
      "Backend Development": {
        "organization": "Global Engineering",
        "users": "cn=Backend-Developers,ou=Groups,dc=example,dc=com",
        "remove": false
      }
    }
  }
}
```

## Available GROUP_TYPE Values

```
- PosixGroupType
- MemberDNGroupType
- GroupOfNamesType
- GroupOfUniqueNamesType
- ActiveDirectoryGroupType
- OrganizationalRoleGroupType
- NestedMemberDNGroupType
- NestedGroupOfNamesType
- NestedGroupOfUniqueNamesType
- NestedActiveDirectoryGroupType
- NestedOrganizationalRoleGroupType
- PosixUIDGroupType
```

## Migration Strategy

### 1. Detect AAP 2.6
```python
target_version = await self.get_target_version()
if version.parse(target_version) >= version.parse("2.6.0"):
    # Use Gateway LDAP migration
```

### 2. Extract LDAP Settings
```python
# From AAP 2.4 settings
ldap_primary = {k: v for k, v in settings.items() if k.startswith('AUTH_LDAP_') and not k.startswith('AUTH_LDAP_1_')}
ldap_secondary = {k: v for k, v in settings.items() if k.startswith('AUTH_LDAP_1_')}
```

### 3. Transform to Gateway Format
```python
def transform_ldap_to_gateway(aap24_settings: dict, server_name: str) -> dict:
    """Transform AAP 2.4 LDAP settings to Gateway authenticator format"""
    return {
        "name": server_name,
        "type": "ansible_base.authentication.authenticator_plugins.ldap",
        "enabled": True,
        "create_objects": True,
        "remove_users": False,
        "configuration": {
            "SERVER_URI": [aap24_settings.get('AUTH_LDAP_SERVER_URI')],
            "BIND_DN": aap24_settings.get('AUTH_LDAP_BIND_DN'),
            "BIND_PASSWORD": aap24_settings.get('AUTH_LDAP_BIND_PASSWORD'),
            "CONNECTION_OPTIONS": aap24_settings.get('AUTH_LDAP_CONNECTION_OPTIONS', {}),
            "GROUP_TYPE": aap24_settings.get('AUTH_LDAP_GROUP_TYPE'),
            "GROUP_TYPE_PARAMS": aap24_settings.get('AUTH_LDAP_GROUP_TYPE_PARAMS'),
            "GROUP_SEARCH": aap24_settings.get('AUTH_LDAP_GROUP_SEARCH'),
            "START_TLS": aap24_settings.get('AUTH_LDAP_START_TLS', False),
            "USER_DN_TEMPLATE": aap24_settings.get('AUTH_LDAP_USER_DN_TEMPLATE'),
            "USER_ATTR_MAP": aap24_settings.get('AUTH_LDAP_USER_ATTR_MAP'),
            "USER_SEARCH": aap24_settings.get('AUTH_LDAP_USER_SEARCH'),
        }
    }
```

### 4. Create Authenticators
```python
# Create primary LDAP authenticator
await gateway_client.post("authenticators/", json_data=primary_ldap_config)

# Create secondary LDAP authenticator (if exists)
if ldap_secondary:
    await gateway_client.post("authenticators/", json_data=secondary_ldap_config)
```

## Testing

### Verify Authenticator Created
```bash
curl -sk -H "Authorization: Bearer $TOKEN" \
  https://localhost:10443/api/gateway/v1/authenticators/ | jq .
```

### Test LDAP Login
```bash
# After creating authenticator, test LDAP user login via AAP UI
```

## Notes

- **BIND_PASSWORD**: Will still be manual entry (security best practice)
- **Order**: Authenticators are processed in order (primary = 2, secondary = 3, etc.)
- **Fallback**: Local database authenticator (order = 1) remains as fallback
- **Documentation**: https://django-auth-ldap.readthedocs.io/en/latest/

## Status

- ✅ Gateway endpoint confirmed: `/api/gateway/v1/authenticators/`
- ✅ LDAP plugin schema documented
- ✅ Field mapping completed
- ✅ **Implementation complete** (automatic LDAP migration to Gateway)
- 🔲 Testing pending

## Implementation

**Automatic LDAP migration is now implemented in:**
- `src/aap_migration/migration/importer.py` - SettingsImporter class
- `src/aap_migration/client/aap_target_client.py` - Gateway authenticator methods

**How it works:**
1. Detects target AAP version (>= 2.6.0)
2. Extracts LDAP settings from all categories (safe, review_required, sensitive)
3. Groups LDAP servers (PRIMARY, SECONDARY, TERTIARY)
4. Transforms AUTH_LDAP_* fields to Gateway format (removes prefix)
5. Creates Gateway authenticator objects via `/api/gateway/v1/authenticators/`
6. Imports non-LDAP settings to Controller API as before
7. BIND_PASSWORD excluded for security (manual entry required in Gateway UI)

---

**Created:** 2026-03-26
**Last Updated:** 2026-03-26
