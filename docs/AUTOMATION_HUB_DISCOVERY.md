# Automation Hub Migration - Discovery & Analysis

**Product Owner:** AI Product Owner  
**Date:** 2026-05-04  
**Branch:** automationhub  
**Status:** Discovery Phase

---

## Executive Summary

This document analyzes the feasibility and approach for migrating **Automation Hub** content from AAP 2.4 to AAP 2.6, focusing on the Pulp 3 API endpoints available at `/api/galaxy/pulp/api/v3/`.

---

## 1. What is Automation Hub?

### Overview
Automation Hub is the content management system in Ansible Automation Platform that:
- Hosts Ansible Collections (packaged automation content)
- Manages collection namespaces and repositories
- Provides private/certified/community collection distribution
- Handles collection versioning and dependencies
- Manages execution environments (container images)

### Key Components
1. **Collections**: Packaged Ansible content (roles, plugins, modules)
2. **Namespaces**: Organizational units (e.g., `ansible`, `community`, `redhat`)
3. **Repositories**: Collection storage locations (certified, community, custom)
4. **Execution Environments**: Container images for running automation
5. **Collection Versions**: Specific versions of collections
6. **Collection Dependencies**: Inter-collection requirements

---

## 2. API Endpoint Discovery

### Base URL Structure

**AAP 2.4 Automation Hub:**
```
https://<aap-2.4-host>/api/galaxy/pulp/api/v3/
```

**AAP 2.6 Automation Hub:**
```
https://<aap-2.6-host>/api/galaxy/pulp/api/v3/
```

### Primary API Endpoints (Pulp 3)

#### Collection Management
| Endpoint | Purpose | Migratable |
|----------|---------|------------|
| `/api/galaxy/pulp/api/v3/collections/` | List all collections | ✅ Yes |
| `/api/galaxy/pulp/api/v3/collections/{namespace}/{name}/` | Collection details | ✅ Yes |
| `/api/galaxy/pulp/api/v3/collections/{namespace}/{name}/versions/` | Collection versions | ✅ Yes |
| `/api/galaxy/pulp/api/v3/collections/{namespace}/{name}/versions/{version}/` | Specific version | ✅ Yes |

#### Namespace Management
| Endpoint | Purpose | Migratable |
|----------|---------|------------|
| `/api/galaxy/_ui/v1/namespaces/` | List namespaces | ✅ Yes |
| `/api/galaxy/_ui/v1/namespaces/{name}/` | Namespace details | ✅ Yes |

#### Repository Management
| Endpoint | Purpose | Migratable |
|----------|---------|------------|
| `/api/galaxy/pulp/api/v3/repositories/ansible/ansible/` | Ansible repositories | ✅ Yes |
| `/api/galaxy/pulp/api/v3/distributions/ansible/ansible/` | Repository distributions | ✅ Yes |
| `/api/galaxy/pulp/api/v3/content/ansible/collection_versions/` | Collection content | ✅ Yes |

#### Execution Environments
| Endpoint | Purpose | Migratable |
|----------|---------|------------|
| `/api/galaxy/_ui/v1/execution-environments/repositories/` | EE repositories | ⚠️ Partial |
| `/api/galaxy/pulp/api/v3/repositories/container/container-push/` | Container repos | ⚠️ Partial |

#### Remote Registries
| Endpoint | Purpose | Migratable |
|----------|---------|------------|
| `/api/galaxy/pulp/api/v3/remotes/ansible/collection/` | Remote collection sources | ✅ Yes |
| `/api/galaxy/pulp/api/v3/remotes/container/container/` | Remote container registries | ⚠️ Partial |

#### User & RBAC
| Endpoint | Purpose | Migratable |
|----------|---------|------------|
| `/api/galaxy/_ui/v1/users/` | User management | ❌ No (managed in AAP core) |
| `/api/galaxy/_ui/v1/groups/` | Group management | ❌ No (managed in AAP core) |
| `/api/galaxy/pulp/api/v3/roles/` | RBAC roles | ⚠️ Partial |

---

## 3. Object Model Analysis

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Automation Hub                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │  Namespaces  │────────>│ Collections  │                 │
│  │              │         │   Versions   │                 │
│  └──────────────┘         └──────────────┘                 │
│         │                         │                          │
│         │                         │                          │
│         v                         v                          │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │ Repositories │<────────│   Content    │                 │
│  │              │         │  (artifacts) │                 │
│  └──────────────┘         └──────────────┘                 │
│         │                                                    │
│         v                                                    │
│  ┌──────────────┐                                          │
│  │Distribution  │ (Endpoints for content access)           │
│  └──────────────┘                                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Object Relationships

```
Namespace (e.g., "ansible")
  └── Collections (e.g., "posix", "windows")
      └── Versions (e.g., "1.2.0", "1.3.0")
          └── Artifacts (.tar.gz files)
              └── Metadata (MANIFEST.json, files.json)

Repository (e.g., "rh-certified")
  ├── Content (collection versions)
  └── Distribution (URL path)

Remote Registry
  └── Sync configuration
      └── Pulls from external sources
```

---

## 4. Migration Scope Analysis

### ✅ Migratable Objects

#### 4.1 Collections & Versions
**What:**
- Collection metadata (name, namespace, description)
- Collection versions (semantic versions)
- Collection artifacts (.tar.gz files)
- Collection dependencies
- Tags and keywords

**How:**
1. Export: Download collection artifacts from source
2. Transform: Validate metadata compatibility
3. Import: Upload to target repositories

**Complexity:** MEDIUM
**Risk:** LOW
**Priority:** HIGH (core functionality)

---

#### 4.2 Namespaces
**What:**
- Namespace names
- Namespace metadata
- Company/organization info

**How:**
1. Export: API call to get namespace list
2. Transform: Map namespace metadata
3. Import: Create namespaces in target

**Complexity:** LOW
**Risk:** LOW
**Priority:** HIGH (required before collections)

**Note:** Some namespaces may be pre-created in AAP 2.6 (e.g., `ansible`, `redhat`)

---

#### 4.3 Custom Repositories
**What:**
- Custom repository definitions
- Repository metadata
- Content assignments

**How:**
1. Export: Repository configuration
2. Transform: Validate against AAP 2.6 schema
3. Import: Create repositories and assign content

**Complexity:** MEDIUM
**Risk:** MEDIUM (may differ in AAP 2.6)
**Priority:** MEDIUM

---

#### 4.4 Remote Registries (Collection Remotes)
**What:**
- Remote source configurations
- Sync settings
- Authentication credentials (requires Vault)

**How:**
1. Export: Remote configurations
2. Transform: Update URLs if needed
3. Import: Create remote definitions

**Complexity:** MEDIUM
**Risk:** HIGH (credentials handling)
**Priority:** LOW (can be reconfigured)

---

### ⚠️ Partially Migratable Objects

#### 4.5 Execution Environments
**What:**
- Container image references
- EE metadata
- Image tags

**Why Partial:**
- Large binary data (container images)
- May require re-push to target registry
- Different registry structure in AAP 2.6

**Approach:**
1. Export: Image metadata and tags
2. Manual: Re-push images to target registry
3. Import: Create EE references in target

**Complexity:** HIGH
**Risk:** HIGH
**Priority:** MEDIUM

---

#### 4.6 RBAC & Permissions
**What:**
- Collection-level permissions
- Namespace ownership

**Why Partial:**
- Users/groups managed in AAP core
- May need manual permission recreation

**Approach:**
- Document permissions
- Manual recreation after user migration

**Complexity:** LOW
**Risk:** LOW
**Priority:** LOW

---

### ❌ Non-Migratable Objects

#### 4.7 Users & Groups
**Why Not:**
- Managed at AAP platform level (not Automation Hub)
- Covered by AAP Bridge core migration

**Action:** Use AAP Bridge main migration

---

#### 4.8 Audit Logs
**Why Not:**
- Time-series data
- Not critical for migration
- New audit trail starts in target

**Action:** Archive if needed for compliance

---

#### 4.9 Download Statistics
**Why Not:**
- Historical metrics
- Not essential for functionality

**Action:** Optional export for reporting

---

## 5. Key Differences: AAP 2.4 vs AAP 2.6

### 5.1 API Changes

| Aspect | AAP 2.4 | AAP 2.6 | Impact |
|--------|---------|---------|--------|
| Pulp Version | Pulp 3.x | Pulp 3.y (newer) | May have new fields |
| Collection Upload | `/api/galaxy/v3/collections/` | Same | No change |
| Namespace API | `/_ui/v1/namespaces/` | Same | No change |
| EE Registries | Separate registry | Integrated | Architecture change |

### 5.2 Schema Differences

**To be discovered during implementation:**
- New required fields in AAP 2.6
- Deprecated fields from AAP 2.4
- Field type changes
- Validation rule changes

**Action:** Create schema comparison during development

---

## 6. Migration Strategy

### Phase 1: Read-Only Discovery
**Goal:** Understand source Automation Hub content
**Actions:**
1. Enumerate all namespaces
2. List all collections and versions
3. Identify custom repositories
4. Document remote registries

**Output:** Inventory of all content to migrate

---

### Phase 2: Metadata Migration
**Goal:** Migrate structure without artifacts
**Actions:**
1. Create namespaces in target
2. Create repositories in target
3. Configure remote registries
4. Establish permissions

**Output:** Empty structure ready for content

---

### Phase 3: Content Migration
**Goal:** Migrate collection artifacts
**Actions:**
1. Download collection .tar.gz from source
2. Validate artifact integrity
3. Upload to target repositories
4. Verify versions and dependencies

**Output:** Fully populated Automation Hub

---

### Phase 4: Execution Environments (Optional)
**Goal:** Migrate container images
**Actions:**
1. Export image metadata
2. Re-push images to target registry
3. Create EE definitions in target

**Output:** Available execution environments

---

### Phase 5: Validation
**Goal:** Verify migration success
**Actions:**
1. Compare collection counts
2. Verify version completeness
3. Test collection downloads
4. Validate dependencies resolve

**Output:** Migration verification report

---

## 7. Technical Challenges

### 7.1 Large Binary Artifacts
**Challenge:** Collection .tar.gz files can be large (100MB+)
**Solution:**
- Stream downloads/uploads
- Checksum validation (SHA256)
- Resume capability for failed transfers

---

### 7.2 Dependency Resolution
**Challenge:** Collections depend on other collections
**Solution:**
- Topological sort for upload order
- Retry failed uploads after dependencies
- Validate dependency closure

---

### 7.3 Credentials Management
**Challenge:** Remote registries require credentials
**Solution:**
- Use Vault for credential storage (like AAP Bridge)
- Support credential migration
- Mask secrets in logs

---

### 7.4 Version Conflicts
**Challenge:** Target may already have some collections
**Solution:**
- Skip existing versions (idempotent)
- Version comparison
- Conflict resolution strategy

---

### 7.5 Rate Limiting
**Challenge:** Pulp API may rate limit requests
**Solution:**
- Implement backoff/retry
- Batch operations
- Progress tracking

---

## 8. Migration Workflow Design

### 8.1 Exporter Design

```python
class AutomationHubExporter:
    """Export Automation Hub content from AAP 2.4"""
    
    async def export_namespaces(self) -> list[dict]:
        """Export all namespaces"""
        
    async def export_collections(self, namespace: str) -> list[dict]:
        """Export collections for a namespace"""
        
    async def export_collection_versions(
        self, namespace: str, name: str
    ) -> list[dict]:
        """Export all versions of a collection"""
        
    async def download_collection_artifact(
        self, namespace: str, name: str, version: str, output_dir: Path
    ) -> Path:
        """Download collection .tar.gz artifact"""
        
    async def export_repositories(self) -> list[dict]:
        """Export custom repositories"""
        
    async def export_remotes(self) -> list[dict]:
        """Export remote registry configurations"""
```

### 8.2 Transformer Design

```python
class AutomationHubTransformer:
    """Transform Automation Hub data for AAP 2.6"""
    
    def transform_namespace(self, namespace: dict) -> dict:
        """Transform namespace for target"""
        
    def transform_collection_metadata(self, collection: dict) -> dict:
        """Transform collection metadata"""
        
    def validate_artifact(self, artifact_path: Path) -> bool:
        """Validate collection artifact integrity"""
        
    def resolve_dependencies(
        self, collections: list[dict]
    ) -> list[dict]:
        """Topologically sort collections by dependencies"""
```

### 8.3 Importer Design

```python
class AutomationHubImporter:
    """Import Automation Hub content to AAP 2.6"""
    
    async def create_namespace(self, namespace: dict) -> dict:
        """Create namespace in target"""
        
    async def upload_collection(
        self, artifact_path: Path, repository: str = "published"
    ) -> dict:
        """Upload collection artifact to target"""
        
    async def create_repository(self, repository: dict) -> dict:
        """Create custom repository"""
        
    async def configure_remote(self, remote: dict) -> dict:
        """Configure remote registry"""
        
    async def wait_for_task(self, task_href: str) -> dict:
        """Wait for Pulp async task completion"""
```

---

## 9. Data Storage Structure

### 9.1 Export Directory Layout

```
exports/automation_hub/
├── metadata.json                   # Export summary
├── namespaces/
│   ├── ansible.json
│   ├── community.json
│   └── custom_org.json
├── collections/
│   ├── ansible.posix/
│   │   ├── metadata.json          # Collection info
│   │   └── versions/
│   │       ├── 1.2.0.json         # Version metadata
│   │       └── 1.3.0.json
│   └── community.general/
│       └── ...
├── artifacts/                      # .tar.gz files
│   ├── ansible-posix-1.2.0.tar.gz
│   ├── ansible-posix-1.3.0.tar.gz
│   └── community-general-6.0.0.tar.gz
├── repositories/
│   ├── rh-certified.json
│   ├── community.json
│   └── custom-repo.json
└── remotes/
    ├── galaxy.json
    └── custom-remote.json
```

### 9.2 Database Tracking

**New Tables:**
```sql
-- Track Automation Hub migration
CREATE TABLE automation_hub_progress (
    id INTEGER PRIMARY KEY,
    resource_type TEXT,  -- namespace, collection, repository
    source_id TEXT,      -- namespace name or collection FQN
    target_id TEXT,      -- created resource ID
    status TEXT,         -- pending, completed, failed, skipped
    metadata JSON,       -- additional info
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Track collection artifacts
CREATE TABLE collection_artifacts (
    id INTEGER PRIMARY KEY,
    namespace TEXT,
    name TEXT,
    version TEXT,
    sha256 TEXT,         -- artifact checksum
    file_path TEXT,      -- local path
    file_size INTEGER,
    uploaded BOOLEAN,
    created_at TIMESTAMP
);
```

---

## 10. Risk Assessment

### High Risk Areas

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Large artifact transfer failures | HIGH | MEDIUM | Resumable downloads, checksums |
| Dependency resolution failures | HIGH | LOW | Topological sort, retry logic |
| API incompatibility 2.4→2.6 | HIGH | MEDIUM | Schema validation, version detection |
| Credential exposure | CRITICAL | LOW | Vault integration, no plaintext |

### Medium Risk Areas

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Version conflicts | MEDIUM | MEDIUM | Skip existing, idempotent |
| Repository config differences | MEDIUM | MEDIUM | Manual review, documentation |
| Performance/timeouts | MEDIUM | HIGH | Batch operations, progress tracking |

### Low Risk Areas

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Namespace already exists | LOW | HIGH | Skip if exists, no error |
| Missing non-critical metadata | LOW | MEDIUM | Log warnings, continue |

---

## 11. Success Criteria

### Must Have
- ✅ All namespaces migrated
- ✅ All collections and versions migrated
- ✅ Artifacts downloadable from target
- ✅ Dependencies resolve correctly
- ✅ No data loss

### Should Have
- ✅ Custom repositories recreated
- ✅ Remote registries configured
- ✅ Migration report generated
- ✅ Idempotent (can re-run)

### Nice to Have
- ✅ Execution environments migrated
- ✅ RBAC permissions documented
- ✅ Performance metrics collected

---

## 12. Next Steps

### Immediate Actions
1. ✅ **API Discovery:** Query live AAP 2.4/2.6 instances to confirm endpoints
2. ✅ **Schema Comparison:** Document field differences between versions
3. ✅ **Proof of Concept:** Migrate one collection manually to validate approach

### Development Tasks
1. Create `AutomationHubExporter` class
2. Create `AutomationHubTransformer` class
3. Create `AutomationHubImporter` class
4. Add CLI commands: `export-hub`, `import-hub`
5. Implement progress tracking
6. Add comprehensive error handling

### Testing Requirements
1. Unit tests for each component
2. Integration test with sample collections
3. E2E test with full repository
4. Performance test with large artifacts
5. Idempotency test (re-run migration)

---

## 13. Open Questions

### Questions for Stakeholders
1. **Scope:** Do we migrate ALL collections or allow filtering by namespace/repository?
2. **Credentials:** How are remote registry credentials stored in source AAP 2.4?
3. **EE Priority:** How important is execution environment migration vs manual re-push?
4. **Downtime:** Can we accept read-only mode during migration or must it be offline?
5. **Rollback:** What's the rollback strategy if migration fails mid-way?

### Technical Questions
1. **Pulp Tasks:** How long do Pulp async tasks typically take? Need timeout strategy?
2. **Concurrency:** Can we upload multiple collections in parallel or must it be serial?
3. **Versioning:** If AAP 2.6 has newer collection versions, do we keep them or overwrite?
4. **Signing:** Do collections require GPG signing in target?

---

## 14. Estimated Effort

### Development
- **Exporter:** 3-5 days
- **Transformer:** 2-3 days
- **Importer:** 4-6 days
- **CLI Integration:** 2-3 days
- **Testing:** 3-4 days
- **Documentation:** 2-3 days

**Total Development:** 16-24 days (3-5 weeks)

### Execution (Per Environment)
- **Small (< 50 collections):** 1-2 hours
- **Medium (50-200 collections):** 3-6 hours
- **Large (200+ collections):** 8-16 hours

---

## 15. Recommendations

### Approach
**Recommended:** Phased migration with validation gates
- Phase 1: Namespaces (low risk, fast)
- Phase 2: Collections metadata (validate before artifacts)
- Phase 3: Artifacts (bulk of time, resumable)
- Phase 4: Repositories/Remotes (optional, low priority)

### Tooling
**Recommended:** Extend AAP Bridge with Automation Hub module
- Reuse existing patterns (exporter/transformer/importer)
- Leverage existing CLI framework
- Use same database tracking
- Follow same error handling patterns

### Testing Strategy
**Recommended:** Test with sandbox environment first
- Create test AAP 2.4 with sample collections
- Validate migration to test AAP 2.6
- Measure performance and identify bottlenecks
- Refine before production migration

---

## Appendix A: API Endpoint Reference

### Collection Upload API
```http
POST /api/galaxy/v3/artifacts/collections/
Content-Type: multipart/form-data

file: <collection.tar.gz>
sha256: <checksum>
```

### Collection Query API
```http
GET /api/galaxy/pulp/api/v3/content/ansible/collection_versions/
    ?namespace=<namespace>
    &name=<name>
    &version=<version>
```

### Namespace Creation API
```http
POST /api/galaxy/_ui/v1/namespaces/
Content-Type: application/json

{
  "name": "my_namespace",
  "company": "My Company",
  "description": "Namespace description"
}
```

---

## Appendix B: Sample Migration Scenario

### Source Environment (AAP 2.4)
- 3 namespaces: `ansible`, `community`, `myorg`
- 50 collections
- 200 collection versions
- 2 custom repositories
- 1 remote registry

### Target Environment (AAP 2.6)
- Empty Automation Hub
- Default repositories present

### Migration Flow
1. Export namespaces → 3 items (1 minute)
2. Export collections → 50 items (5 minutes)
3. Export versions → 200 items (10 minutes)
4. Download artifacts → 200 files, 5GB total (30 minutes)
5. Create namespaces → 2 new (ansible/community pre-exist) (1 minute)
6. Upload artifacts → 200 uploads (60 minutes)
7. Verify migration → count checks (5 minutes)

**Total Time:** ~2 hours

---

## Document Status
- **Version:** 1.0 (Discovery Phase)
- **Next Review:** After API confirmation with live systems
- **Owner:** Product Owner (AI)
- **Approvers:** TBD

---

**End of Discovery Document**
