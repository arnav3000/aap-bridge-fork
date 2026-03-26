# State Storage Alternatives Analysis

## Current Approach: PostgreSQL

The tool currently requires an external PostgreSQL database for state management. This provides:

### Capabilities Needed
1. **ID Mapping**: Store source_id → target_id mappings for all resource types
2. **State Tracking**: Track migration progress (pending, in_progress, completed)
3. **Checkpoint Resume**: Support resuming from any checkpoint
4. **Idempotency**: Prevent duplicate resource creation
5. **Scale**: Handle 80,000+ host mappings efficiently

### Current Implementation Stats
- Tables: id_mappings, migration_state, checkpoints
- Typical data volume for large migration:
  - 80,000 hosts × 2 IDs = 160,000 mapping records
  - Plus inventories, credentials, templates, etc.
  - Total: ~200,000-500,000 records

## Alternative 1: SQLite (Embedded Database)

### Overview
Replace PostgreSQL with SQLite file-based database.

### Pros
- ✅ No separate database server required
- ✅ Zero-configuration setup
- ✅ Same SQL interface (minimal code changes)
- ✅ ACID transactions
- ✅ Can handle millions of records
- ✅ Built into Python standard library
- ✅ Single file for entire state
- ✅ Easy to backup/restore (just copy file)

### Cons
- ❌ Limited concurrent writes (not an issue for single-process migration)
- ❌ Slightly slower than PostgreSQL for very large datasets
- ❌ No network access (must run on same machine)

### Implementation Effort
**Low** - SQLAlchemy already supports SQLite, just change connection string:

```python
# Current
MIGRATION_STATE_DB_PATH=postgresql://user:pass@localhost:5432/aap_migration

# SQLite
MIGRATION_STATE_DB_PATH=sqlite:///./migration_state.db
```

### Recommendation
⭐ **Highly Recommended** - Best trade-off for most users.

```bash
# Simple deployment
export MIGRATION_STATE_DB_PATH=sqlite:///./aap_migration_state.db
aap-bridge migrate full
```

---

## Alternative 2: JSON Files (Structured Storage)

### Overview
Store ID mappings and state in JSON files:
- `state/id_mappings_organizations.json`
- `state/id_mappings_hosts.json`
- `state/migration_state.json`
- `state/checkpoints.json`

### Pros
- ✅ No database required
- ✅ Human-readable (can inspect with text editor)
- ✅ Simple backup (just copy directory)
- ✅ Easy debugging
- ✅ Works anywhere (no dependencies)

### Cons
- ❌ Slow for large datasets (must load entire file into memory)
- ❌ No transaction safety (corruption risk on crash)
- ❌ No concurrent access support
- ❌ Inefficient lookups (O(n) vs O(1))
- ❌ Memory issues with 80,000+ hosts (could be 100MB+ JSON in memory)

### Implementation Effort
**Medium** - Need to rewrite state.py to use file-based operations.

### Recommendation
❌ **Not Recommended** - Only suitable for small migrations (<1,000 resources).

---

## Alternative 3: Hybrid: SQLite + JSON Snapshots

### Overview
Use SQLite for runtime, export snapshots to JSON for portability.

### Pros
- ✅ Fast runtime performance (SQLite)
- ✅ Portable state (JSON exports)
- ✅ Human-readable backups
- ✅ Can resume from JSON snapshot

### Implementation
```python
# Export state to JSON after each phase
aap-bridge export-state --output state_snapshot.json

# Import state from JSON to continue
aap-bridge import-state --input state_snapshot.json
```

### Recommendation
⭐ **Good Option** - Provides both performance and portability.

---

## Alternative 4: Redis (In-Memory Database)

### Overview
Use Redis for fast in-memory state storage.

### Pros
- ✅ Extremely fast lookups
- ✅ Built-in persistence (RDB/AOF)
- ✅ Supports concurrent access
- ✅ Can run in Docker easily

### Cons
- ❌ Requires Redis server (more infrastructure)
- ❌ Memory-intensive (must fit entire state in RAM)
- ❌ Not ideal for very large migrations (80k hosts = 50-100MB RAM)
- ❌ More complex than SQLite

### Recommendation
⚠️ **Overkill** - Redis is better suited for real-time, distributed use cases.

---

## Alternative 5: Embedded Key-Value Store (RocksDB/LMDB)

### Overview
Use embedded key-value database like RocksDB or LMDB.

### Pros
- ✅ Very fast (optimized for SSD)
- ✅ Embedded (no server)
- ✅ Scales to billions of records

### Cons
- ❌ Requires Python bindings (external dependency)
- ❌ More complex API than SQL
- ❌ Need to implement indexing/queries manually

### Recommendation
❌ **Not Worth It** - SQLite provides similar benefits with simpler interface.

---

## Alternative 6: No State Management (Re-query AAP)

### Overview
Instead of storing mappings, re-query target AAP for each resource.

Example:
```python
# Instead of: target_id = state.get_target_id("organizations", source_id)
# Do: target_org = target_client.search("organizations", name=source_org["name"])
```

### Pros
- ✅ No database required
- ✅ Always up-to-date with target state

### Cons
- ❌ Extremely slow (thousands of API calls per migration)
- ❌ No idempotency guarantee (name collisions)
- ❌ Cannot resume from checkpoint
- ❌ Cannot validate all IDs were migrated
- ❌ Fragile (what if names are duplicated?)

### Recommendation
❌ **Not Viable** - Defeats the purpose of state management.

---

## Recommendation Matrix

| Use Case | Recommended Solution | Reason |
|----------|---------------------|--------|
| **Default** | SQLite | Best trade-off: simple + performant |
| **Large scale (100k+ resources)** | PostgreSQL or SQLite | Both work; PostgreSQL slightly faster |
| **Embedded tools** | SQLite | No external dependencies |
| **Distributed migration** | PostgreSQL | Network-accessible state |
| **Small migrations (<1k)** | JSON Files | Simple and readable |
| **CI/CD pipelines** | SQLite | No infrastructure setup |
| **Cloud deployments** | PostgreSQL (RDS) | Managed service available |

---

## Proposed Implementation Plan

### Step 1: Make Database Backend Configurable

Update config to support multiple backends:

```yaml
# config/config.yaml
state:
  backend: "sqlite"  # or "postgresql", "json"
  db_path: "./migration_state.db"  # for sqlite
  # db_path: "postgresql://..." # for postgresql
  # db_path: "./state/" # for json
```

### Step 2: Create Database Abstraction Layer

```python
# src/aap_migration/migration/state_backends.py

class StateBackend(ABC):
    """Abstract base class for state storage backends."""

    @abstractmethod
    def store_id_mapping(self, resource_type, source_id, target_id): ...

    @abstractmethod
    def get_target_id(self, resource_type, source_id): ...

    @abstractmethod
    def create_checkpoint(self, name, metadata): ...

class SQLiteBackend(StateBackend):
    """SQLite-based state storage (default)."""
    # Uses SQLAlchemy with sqlite:/// connection

class PostgreSQLBackend(StateBackend):
    """PostgreSQL-based state storage (for large scale)."""
    # Uses SQLAlchemy with postgresql:// connection

class JSONBackend(StateBackend):
    """JSON file-based state storage (for small migrations)."""
    # Stores state in JSON files
```

### Step 3: Update Documentation

```bash
# Default: SQLite (zero-config)
aap-bridge migrate full

# Large scale: PostgreSQL
export STATE_BACKEND=postgresql
export MIGRATION_STATE_DB_PATH=postgresql://...
aap-bridge migrate full

# Small/portable: JSON
export STATE_BACKEND=json
export MIGRATION_STATE_DB_PATH=./state/
aap-bridge migrate full
```

---

## Conclusion

**Recommendation: Switch default to SQLite, keep PostgreSQL as option**

This provides the best user experience:
- **95% of users**: SQLite (zero-config, good performance)
- **5% of users** (enterprise, 100k+ resources): PostgreSQL

**Implementation Priority:**
1. High: Add SQLite support (change default connection string)
2. Medium: Make backend configurable
3. Low: Add JSON backend for small migrations
4. Low: Add state export/import commands

**Benefits:**
- Removes deployment complexity for most users
- Maintains enterprise-grade capabilities for large migrations
- Backward compatible (existing PostgreSQL users unaffected)

**Migration Path:**
```python
# Phase 1: Support both, default to SQLite
# .env.example
MIGRATION_STATE_DB_PATH=sqlite:///./migration_state.db  # NEW DEFAULT
# MIGRATION_STATE_DB_PATH=postgresql://...  # Still supported

# Phase 2: Add backend selector
STATE_BACKEND=sqlite  # or postgresql, json

# Phase 3: Deprecate PostgreSQL requirement from documentation
```

Would you like me to implement the SQLite backend as the new default?
