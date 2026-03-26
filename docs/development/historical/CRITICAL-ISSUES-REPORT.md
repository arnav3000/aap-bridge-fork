# AAP Migration - Critical Issues Report

**Date:** 2026-03-04
**Migration:** AAP 2.4 (v4.5.30) → AAP 2.6 (v4.7.8)
**Status:** 🚨 **CRITICAL FAILURES DETECTED**

---

## Executive Summary

The migration encountered **two critical failures** that must be addressed:

1. **🔴 RBAC COMPLETE FAILURE:** All role assignments lost (100% failure rate)
2. **🟠 API TIMEOUT ERRORS:** 67 timeout errors preventing full migration (60-second timeouts)

**Overall Migration Success:** 51% of resources migrated, but **0% of RBAC** preserved.

---

## 🚨 CRITICAL ISSUE #1: RBAC Migration Failure

### Problem Statement

**ALL user role assignments were lost during migration.** While user accounts migrated successfully, none of their permissions, roles, or access rights transferred.

### Impact Assessment

| Severity | **CRITICAL - Production Blocker** |
|----------|-----------------------------------|
| **Users Affected** | ALL 23 users (100%) |
| **Roles Lost** | ~30+ role assignments |
| **Security Impact** | Users have no access to resources |
| **Business Impact** | Cannot use migrated AAP environment |

### Detailed Findings

#### User-Level Role Loss:

| User | Source Roles | Target Roles | Loss | Impact |
|------|--------------|--------------|------|--------|
| **admin** | 16 | 1 | 15 (94%) | Lost most admin access |
| **arnav** | 2 | 0 | 2 (100%) | No access |
| **arnav_b** | 2 | 0 | 2 (100%) | Lost System Auditor |
| **kevin.audit** | 7 | 0 | 7 (100%) | Lost System Auditor + all org roles |
| **amanda.pentest** | 2 | 0 | 2 (100%) | No access |
| **All Others** | varies | 0 | 100% | No access |

#### Types of Roles Lost:

1. **System-Level Roles:**
   - System Auditor flags (`is_system_auditor`) reset to `false`
   - 2 users lost System Auditor access

2. **Organization Roles:**
   - Organization Member
   - Organization Admin
   - Organization Auditor
   - Organization Execute
   - Organization Read

3. **Team Roles:**
   - Team Member
   - Team Admin
   - Team Read

4. **Resource-Level Roles:**
   - Project Admin/Read/Use
   - Inventory Admin/Read/Use/Adhoc
   - Job Template Admin/Read/Execute
   - Credential Admin/Read/Use

### Root Cause

From migration logs:
```
skipped_manual=['settings', 'applications', 'tokens', 'inventory_sources', 'roles']
```

**The `roles` resource type is marked as `skipped_manual`**, meaning:
- Migration tool **intentionally does not migrate RBAC roles**
- Roles are considered "manual migration" items
- No automated RBAC transfer occurs

### Why This Happens

RBAC in AAP is complex:
- Many-to-many relationships (users ↔ roles ↔ resources)
- Implicit vs explicit permissions
- Role inheritance and delegation
- Different role types (organization, team, object)
- Platform Gateway changes in AAP 2.6 may have altered role APIs

The migration tool appears to skip this complexity, requiring manual RBAC recreation.

---

## 🟠 CRITICAL ISSUE #2: API Timeout Errors

### Problem Statement

Target AAP 2.6 consistently times out after exactly **60 seconds** on complex API operations, causing migration failures.

### Impact Assessment

| Severity | **HIGH - Migration Blocker** |
|----------|------------------------------|
| **Total Timeout Errors** | 67 |
| **Resources Affected** | Job Templates, Inventories, Hosts, Credentials |
| **Migration Success** | 51% (should be 80%+) |

### Timeout Breakdown

| Endpoint | Timeouts | Impact |
|----------|----------|--------|
| `/job_templates/` | 18 | Only 1/15 migrated |
| `/credentials/` | 10 | Only 20/23 migrated |
| `/users/` | 5 | Migration delays |
| `/teams/` | 5 | Migration delays |
| `/organizations/` | 5 | Migration delays |
| `/projects/` | 2 | PATCH failures |

### Timeout Pattern

```
[13:03:10] Request to /api/controller/v2/credentials/
[13:04:10] ❌ Timeout after 60 seconds
[13:04:10] Retry attempt 1/5
[13:05:11] ❌ Timeout after 60 seconds
[13:05:11] Retry attempt 2/5
... (repeats 5 times = 5 minutes total)
[13:08:17] ❌ All retries exhausted - FAILED
```

### Root Cause

1. **Timeout Value NOT Increased:**
   - Despite user indication, timeout remains **60 seconds**
   - Environment shows: `SOURCE__TIMEOUT=60`, `TARGET__TIMEOUT=60`
   - No evidence of increase in actual operations

2. **Target AAP Performance:**
   - Simple `/ping` responds in 0.2 seconds ✅
   - Complex list/create operations timeout at 60s ❌
   - Suggests database or backend processing issues

3. **Contributing Factors:**
   - Target AAP may be under-resourced
   - Database slow queries
   - Platform Gateway overhead in AAP 2.6
   - Large batch sizes overwhelming the API

---

## 📊 Migration Results Summary

### Successfully Migrated (51%):

| Resource | Count | Success | Notes |
|----------|-------|---------|-------|
| Organizations | 9/9 | 100% | ✅ Complete |
| Users | 23/23 | 100% | ✅ Accounts only (no roles) |
| Teams | 11/11 | 100% | ✅ Definitions only (no members) |
| Projects | 9/7 | 128% | ✅ Complete |
| Credentials | 20/23 | 86% | ⚠️ 3 failed |

### Failed/Incomplete (49%):

| Resource | Count | Success | Blocker |
|----------|-------|---------|---------|
| Inventories | 2/10 | 20% | ❌ Timeouts |
| Hosts | 1/21 | 4% | ❌ Timeouts + missing inventories |
| Job Templates | 1/15 | 6% | ❌ Timeouts + missing dependencies |
| Schedules | 4/15 | 26% | ❌ Missing parent resources |
| **RBAC Roles** | **0/~30** | **0%** | ❌ **Skipped by design** |

---

## 🔧 Recommended Solutions

### Priority 1: Fix RBAC Migration (CRITICAL)

#### Option A: Manual RBAC Recreation

```bash
# 1. Export roles from source
curl -sk -H "Authorization: Bearer ENOBFlD2GAB2LmCD5P2RqsTEOjbrlA" \
  "https://localhost:8443/api/v2/roles/?page_size=200" > source_roles.json

# 2. Export user roles
for user_id in {1..25}; do
  curl -sk -H "Authorization: Bearer ENOBFlD2GAB2LmCD5P2RqsTEOjbrlA" \
    "https://localhost:8443/api/v2/users/${user_id}/roles/" \
    > "user_${user_id}_roles.json"
done

# 3. Manually recreate critical roles in target AAP
# This requires creating POST requests to assign roles
```

#### Option B: Extend Migration Tool

Investigate if the migration tool can be enhanced to include RBAC:

```bash
# Check if there's a way to enable role migration
cd /Users/arbhati/project/git/aap-bridge-fork
grep -r "skipped_manual" src/

# Possibly modify the code to include 'roles' in migrated types
# Or create a separate RBAC migration script
```

#### Option C: Custom RBAC Migration Script

Create a dedicated script to:
1. Export all role assignments from source
2. Map source IDs to target IDs (using migration state DB)
3. Recreate role assignments in target

### Priority 2: Fix Timeout Issues (HIGH)

#### Immediate Actions:

**1. Increase Timeout Settings:**

Edit `.env`:
```bash
SOURCE__TIMEOUT=300
TARGET__TIMEOUT=300
```

**2. Reduce Batch Sizes:**

Edit `config/config.yaml`:
```yaml
performance:
  batch_sizes:
    organizations: 50        # Reduced from 100
    users: 50                # Reduced from 100
    teams: 25                # Reduced from 50
    credentials: 25          # Reduced from 50
    job_templates: 50        # Reduced from 100
    inventories: 100         # Reduced from 200
    hosts: 100               # Reduced from 200
```

**3. Reduce Concurrency:**

```yaml
performance:
  max_concurrent: 5          # Reduced from 20
  rate_limit: 10             # Reduced from 25
  max_concurrent_pages: 3    # Reduced from 10
```

**4. Investigate Target AAP Performance:**

```bash
# Check target AAP logs for slow queries
ssh target-aap-server
journalctl -u automation-controller -f

# Check database performance
podman exec -it postgresql psql -U awx -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# Check system resources
htop
iostat -x 5
```

### Priority 3: Re-run Migration

After fixing timeouts:

```bash
# Resume migration (will skip already-migrated resources)
cd /Users/arbhati/project/git/aap-bridge-fork
source .venv/bin/activate
aap-bridge migrate --skip-prep --resume

# Or target specific failed resources
aap-bridge migrate --skip-prep -r inventories
aap-bridge migrate --skip-prep -r hosts
aap-bridge migrate --skip-prep -r job_templates
aap-bridge migrate --skip-prep -r schedules
```

---

## 🎯 Detailed Action Plan

### Phase 1: Emergency RBAC Fix (Day 1)

**Goal:** Restore critical user access

1. **Identify Critical Users:**
   - admin (needs full access)
   - kevin.audit (needs System Auditor)
   - arnav_b (needs System Auditor)
   - Team leads (need Organization Admin)

2. **Manual Role Assignment:**
   ```bash
   # Set System Auditor
   curl -sk -X POST \
     -H "Authorization: Bearer ea023U8zsSXEBuXXZRpiLidAYMT1aT" \
     -H "Content-Type: application/json" \
     -d '{"is_system_auditor": true}' \
     "https://localhost:10443/api/controller/v2/users/4/"  # arnav_b

   curl -sk -X PATCH \
     -H "Authorization: Bearer ea023U8zsSXEBuXXZRpiLidAYMT1aT" \
     -H "Content-Type: application/json" \
     -d '{"is_system_auditor": true}' \
     "https://localhost:10443/api/controller/v2/users/8/"  # kevin.audit

   # Assign Organization Admin role
   # Find organization ID
   ORG_ID=$(curl -sk -H "Authorization: Bearer ea023U8zsSXEBuXXZRpiLidAYMT1aT" \
     "https://localhost:10443/api/controller/v2/organizations/?name=Global%20Engineering" | jq -r '.results[0].id')

   # Find Admin role for that organization
   ROLE_ID=$(curl -sk -H "Authorization: Bearer ea023U8zsSXEBuXXZRpiLidAYMT1aT" \
     "https://localhost:10443/api/controller/v2/organizations/${ORG_ID}/object_roles/" | \
     jq -r '.results[] | select(.name=="Admin") | .id')

   # Assign user to role
   curl -sk -X POST \
     -H "Authorization: Bearer ea023U8zsSXEBuXXZRpiLidAYMT1aT" \
     -H "Content-Type: application/json" \
     -d '{"id": 5}' \
     "https://localhost:10443/api/controller/v2/roles/${ROLE_ID}/users/"  # user_id=5
   ```

3. **Verify Access:**
   ```bash
   # Test user can access organization
   curl -sk -u "username:password" \
     "https://localhost:10443/api/controller/v2/organizations/"
   ```

### Phase 2: Full RBAC Migration (Day 2-3)

**Goal:** Restore all user permissions

1. **Create RBAC Migration Script:**
   - Export all role assignments from source
   - Map to target using migration state DB
   - Batch create role assignments in target

2. **Validation:**
   - Compare role counts: source vs target
   - Test user access for each organization/team
   - Verify resource-level permissions

### Phase 3: Complete Resource Migration (Day 3-5)

**Goal:** Migrate remaining resources

1. **Apply Performance Fixes:**
   - Increase timeouts to 300 seconds
   - Reduce batch sizes
   - Lower concurrency

2. **Resume Migration:**
   ```bash
   aap-bridge migrate --skip-prep --resume
   ```

3. **Monitor:**
   ```bash
   tail -f logs/migration.log | grep -E "(timeout|error|completed)"
   ```

4. **Validate:**
   ```bash
   # Compare counts
   for resource in inventories hosts job_templates schedules; do
     echo "=== $resource ==="
     echo "Source: $(curl -sk ... /api/v2/$resource/ | jq '.count')"
     echo "Target: $(curl -sk ... /api/controller/v2/$resource/ | jq '.count')"
   done
   ```

---

## 📈 Success Criteria

Migration is considered successful when:

- [ ] **100% of users** have correct role assignments
- [ ] **System Auditor flags** correctly set for kevin.audit and arnav_b
- [ ] **Organization admins** can access their organizations
- [ ] **Team members** can see their team resources
- [ ] **All resources** migrated (inventories, hosts, job templates)
- [ ] **No timeout errors** during migration
- [ ] **Validation passes** with 95%+ accuracy

---

## 🔐 Security Considerations

### Current State: **INSECURE**

- Users exist but have no permissions
- admin user may have limited access
- No one can execute job templates
- Potential for unauthorized access if defaults are permissive

### Required Actions:

1. **Immediate:** Restrict target AAP access until RBAC is fixed
2. **Short-term:** Manually assign critical roles
3. **Long-term:** Complete full RBAC migration

---

## 📝 Lessons Learned

### What Worked:

✅ User account migration (names, emails)
✅ Organization structure migration
✅ Team definition migration
✅ Project migration
✅ Migration tool's retry logic
✅ Idempotency (can re-run safely)

### What Failed:

❌ RBAC role migration (completely skipped)
❌ System auditor flag preservation
❌ API timeout handling
❌ Dependency resolution for complex resources
❌ Documentation on RBAC limitations

### For Next Migration:

1. **Pre-migration:** Test RBAC migration on small dataset
2. **During migration:** Monitor role assignment progress
3. **Post-migration:** Validate RBAC before declaring success
4. **Always:** Check if timeout settings are applied
5. **Document:** Known limitations (like RBAC being manual)

---

## 📞 Next Steps

### Immediate (Today):

1. ✅ **Review this report** with stakeholders
2. 🔴 **Fix critical RBAC** for admin and auditors
3. 🟠 **Increase timeout settings** to 300 seconds
4. 🟠 **Reduce batch sizes** in config

### Short-term (This Week):

5. 🔴 **Create RBAC migration script**
6. 🔴 **Restore all user permissions**
7. 🟠 **Re-run migration** for failed resources
8. 🟡 **Validate all resources** migrated correctly

### Medium-term (Next Week):

9. 🟡 **Performance tune** target AAP
10. 🟡 **Complete full validation** with users
11. 🟡 **Document workarounds** and limitations
12. 🟡 **Plan production migration** with lessons learned

---

## 📊 Files and Logs

**Migration Reports:**
- `MIGRATION-REPORT-2.md` - Full migration status
- `CRITICAL-ISSUES-REPORT.md` - This file
- `logs/migration.log` - Detailed migration logs
- `migration_state.db` - State database with ID mappings

**Useful Commands:**

```bash
# Check migration state
sqlite3 migration_state.db \
  "SELECT resource_type, COUNT(*) FROM resource_mappings GROUP BY resource_type;"

# Export RBAC from source
mkdir rbac_export
curl -sk -H "Authorization: Bearer ENOBFlD2GAB2LmCD5P2RqsTEOjbrlA" \
  "https://localhost:8443/api/v2/roles/?page_size=500" > rbac_export/all_roles.json

# Check user role counts
for uid in {1..23}; do
  src=$(curl -sk "https://localhost:8443/api/v2/users/${uid}/roles/" | jq '.count')
  tgt=$(curl -sk "https://localhost:10443/api/controller/v2/users/${uid}/roles/" | jq '.count')
  echo "User $uid: Source=$src, Target=$tgt"
done
```

---

**Report Generated:** 2026-03-04 14:45:00
**Status:** 🚨 **CRITICAL - REQUIRES IMMEDIATE ATTENTION**
**Contact:** Migration Team

---

## Conclusion

The migration successfully created the basic structure (orgs, teams, users) but **completely failed on RBAC permissions** - the most critical aspect for a usable AAP environment. Additionally, **timeout issues** prevented full resource migration.

**Priority Actions:**
1. 🚨 **Fix RBAC immediately** - Users currently have no access
2. 🟠 **Fix timeouts** - Increase to 300s, reduce batch sizes
3. 🟡 **Re-run migration** - Complete remaining resources

Without addressing these issues, the migrated AAP 2.6 environment is **not usable** for production.
