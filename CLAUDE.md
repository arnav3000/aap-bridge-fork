# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AAP Bridge is a production-grade Python tool for migrating Ansible Automation Platform (AAP) installations between versions. It's designed to handle large-scale migrations (80,000+ hosts) using bulk APIs, database-backed state management (SQLite or PostgreSQL), and checkpoint/resume capabilities.

**Supported Migrations:**
- Source: AAP 2.3+, 2.4+, 2.5+
- Target: AAP 2.5+, 2.6+
- Common use case: AAP 2.4 (RPM-based) → AAP 2.6 (containerized)

## Development Commands

### Environment Setup

```bash
# Create virtual environment
uv venv --seed --python 3.12
source .venv/bin/activate

# Install dependencies and package in editable mode
uv sync

# Initialize environment file
cp .env.example .env
# Edit .env with AAP credentials (SQLite database used by default)
```

### Code Quality

```bash
make format      # Format with black and isort
make lint        # Run ruff linter
make typecheck   # Run mypy type checking
make check       # Run all checks (format, lint, typecheck, test)
```

### Testing

```bash
pytest                          # Run all tests
pytest tests/unit/              # Unit tests only
pytest tests/integration/ -m integration  # Integration tests only
pytest --cov=src/aap_migration --cov-report=html  # With coverage
```

### Running the Tool

```bash
aap-bridge                      # Interactive menu-based CLI
aap-bridge migrate full --config config/config.yaml
aap-bridge export all --output exports/
aap-bridge import inventories --input exports/inventories.json
aap-bridge validate all --sample-size 4000
aap-bridge report summary
```

### Documentation

```bash
mkdocs serve -a localhost:8001  # Serve docs locally with hot-reload
mkdocs build                    # Build static HTML docs
```

## Architecture

### Core Components

The codebase is organized into these key layers:

**1. Client Layer** (`src/aap_migration/client/`)
- `base_client.py`: HTTP client foundation with retry logic and rate limiting
- `aap_source_client.py`: Client for source AAP instance
- `aap_target_client.py`: Client for target AAP instance (handles Platform Gateway routing)
- `bulk_operations.py`: Bulk API operations (hosts, inventories)
- `vault_client.py`: HashiCorp Vault integration for credential migration

**2. Migration Layer** (`src/aap_migration/migration/`)
- `coordinator.py`: Orchestrates the full migration pipeline
- `exporter.py`: Exports resources from source AAP (supports parallel page fetching)
- `transformer.py`: Transforms exported data (ID mapping, field normalization)
- `importer.py`: Imports transformed data to target AAP (uses bulk operations)
- `state.py`: Database-backed state tracking for idempotency (SQLite default, PostgreSQL optional)
- `checkpoint.py`: Checkpoint creation and resume functionality
- `parallel_exporter.py`: Parallel resource type export (experimental)

**3. CLI Layer** (`src/aap_migration/cli/`)
- `main.py`: Entry point and Click-based CLI
- `menu.py`: Interactive menu interface
- `commands/`: Individual command implementations (migrate, export, import, validate, etc.)
- `context.py`: CLI context management
- `decorators.py`: Reusable CLI decorators

**4. Reporting Layer** (`src/aap_migration/reporting/`)
- `live_progress.py`: Rich-based live progress display
- `progress_orchestrator.py`: Coordinates progress reporting across operations
- `migration_report.py`: Migration summary reports
- `schema_report.py`: Schema comparison reports

**5. Supporting Modules**
- `config.py`: Pydantic-based configuration management (reads `config/config.yaml` and `.env`)
- `resources.py`: Resource type definitions and field mappings
- `validation/`: Post-migration validation logic
- `prep/`: Pre-migration schema discovery and comparison
- `schema/`: AAP schema definitions

### Migration Workflow

The tool follows a strict dependency order when migrating resources:

1. **Phase 1**: Organizations, Labels, Users, Teams
2. **Phase 2**: Credential Types, Credentials
3. **Phase 3**: Projects (with sync), Execution Environments
4. **Phase 4**: Inventories (bulk operations, 200/batch)
5. **Phase 5**: Hosts (bulk operations, 200/batch - AAP maximum)
6. **Phase 6**: Job Templates, Workflows
7. **Phase 7**: RBAC role assignments

Each phase:
- Exports data from source AAP (with pagination)
- Transforms data (ID mapping, field normalization)
- Imports to target AAP (with idempotency checks)
- Creates checkpoint for resumability

### State Management

The tool uses a database (SQLite by default, PostgreSQL optional) to track:
- ID mappings (source ID → target ID) for all resources
- Migration progress and checkpoints
- Failed operations for retry
- Metadata for split-file exports

This enables:
- **Idempotency**: Re-running migrations won't create duplicates
- **Resumability**: Resume from any checkpoint after interruption
- **Validation**: Compare source/target states

### Configuration

Configuration is hierarchical:
1. `config/config.yaml`: Performance tuning, batch sizes, concurrency
2. `.env`: Credentials and connection strings (never commit!)
3. `config/mappings.yaml`: Resource name mappings (e.g., renamed credential types)

**Critical AAP 2.6 Note**: Target URL must point to Platform Gateway (`/api/controller/v2`), not direct controller API (`/api/v2`).

### Version Detection

The tool automatically detects AAP versions from both source and target instances:
- Queries `/api/v2/config/` endpoint to get actual version
- Validates version compatibility before migration
- Logs warnings for unsupported version combinations
- Falls back to defaults (2.4.0 for source, 2.6.0 for target) if detection fails

Version validation ensures:
- Source version >= 2.3.0
- Target version >= 2.5.0
- Warns on downgrade migrations (target < source)

## Key Design Principles

### Bulk Operations
Uses AAP's bulk APIs for performance:
- Hosts: 200 per request (API maximum)
- Inventories: 200 per batch
- Other resources: 50-100 per batch (configurable in `config/config.yaml`)

### Idempotency
All operations check state database before creating resources. Safe to re-run migrations.

### Progress Display
Rich-based live progress with multiple output modes:
- Normal: Live progress with real-time metrics
- Quiet (`--quiet`): Errors only
- CI/CD (`--disable-progress`): Structured logs for pipelines
- Detailed (`--show-stats`): Additional statistics

### Split-File Export
Large datasets automatically split into multiple files (default: 1000 records/file). Import handles multi-file structure transparently.

## Important Constraints

### Encrypted Credentials
AAP API returns `$encrypted$` for secret fields. Credentials must be:
1. Recreated in HashiCorp Vault before migration (if using Vault)
2. OR manually recreated after migration

### Platform Gateway (AAP 2.6+)
All API calls route through Platform Gateway. The target client automatically handles this.

### Database Backend

**Default: SQLite (Zero Configuration)**
- File-based database (`migration_state.db`)
- No server setup required
- Handles migrations with 80,000+ hosts
- Suitable for 95% of use cases

**Optional: PostgreSQL (Enterprise Scale)**
- Recommended for 100,000+ resources
- Supports distributed/remote access
- Requires separate database setup
- NOT AAP's internal database - separate instance

To use PostgreSQL, update `.env`:
```bash
MIGRATION_STATE_DB_PATH=postgresql://user:pass@localhost:5432/aap_migration
```

## Code Style

- Python 3.12+ required
- Type hints mandatory (enforced by mypy)
- Line length: 100 characters (black + ruff)
- Import order: stdlib, third-party, local (isort with black profile)
- Logging: Use structlog with appropriate levels (DEBUG for file, WARNING for console)

## Adding New Resource Types

To add support for a new AAP resource type:

1. Add resource definition to `resources.py` (fields, relationships)
2. Implement export logic in `exporter.py`
3. Implement transform logic in `transformer.py` (ID mapping, field normalization)
4. Implement import logic in `importer.py` (bulk operations if supported)
5. Add to migration order in `coordinator.py`
6. Update CLI commands in `cli/commands/export_import.py`
7. Update state models in `migration/models.py` if needed

## Common Patterns

### Progress Reporting
All long-running operations should use `ProgressOrchestrator` for consistent progress display:
```python
from aap_migration.reporting.progress_orchestrator import ProgressOrchestrator

progress = ProgressOrchestrator(console_level=logging.WARNING)
progress.start_phase("resource_type", total_items)
# ... do work ...
progress.advance_phase(items_processed)
progress.complete_phase()
```

### State Tracking
Use `MigrationState` for all database operations:
```python
from aap_migration.migration.state import MigrationState

state = MigrationState(db_path)
state.store_id_mapping("organizations", source_id, target_id)
target_id = state.get_target_id("organizations", source_id)
```

### Retry Logic
All HTTP clients inherit from `BaseClient` which provides automatic retry with exponential backoff for:
- Network errors
- Gateway errors (502, 503, 504)
- Rate limiting (429)

## Environment Variables

Required:
- `SOURCE__URL`: Source AAP URL with `/api/v2` path
- `SOURCE__TOKEN`: Source AAP access token
- `TARGET__URL`: Target AAP URL with `/api/controller/v2` path (Platform Gateway)
- `TARGET__TOKEN`: Target AAP access token

Database (auto-configured in `.env.example`):
- `MIGRATION_STATE_DB_PATH`: Database connection string
  - Default: `sqlite:///./migration_state.db` (file-based, zero setup)
  - Enterprise: `postgresql://user:pass@host:5432/dbname` (optional, for 100k+ resources)

Optional:
- `VAULT__URL`, `VAULT__ROLE_ID`, `VAULT__SECRET_ID`: HashiCorp Vault credentials
- Performance tuning via `AAP_BRIDGE__*` variables (see `.env.example`)
