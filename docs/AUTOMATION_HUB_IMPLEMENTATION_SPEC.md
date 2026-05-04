# Automation Hub Migration - Implementation Specification

**Technical Spec for AAP Bridge Integration**  
**Date:** 2026-05-04  
**Status:** Draft  
**Related:** AUTOMATION_HUB_DISCOVERY.md

---

## 1. Architecture Overview

### Integration with AAP Bridge

```
aap-bridge/
├── src/aap_migration/
│   ├── automation_hub/              # NEW MODULE
│   │   ├── __init__.py
│   │   ├── exporter.py             # AutomationHubExporter
│   │   ├── transformer.py          # AutomationHubTransformer
│   │   ├── importer.py             # AutomationHubImporter
│   │   ├── client.py               # Galaxy API client
│   │   ├── models.py               # Data models
│   │   └── resources.py            # Resource definitions
│   ├── cli/commands/
│   │   ├── export_hub.py           # NEW: export-hub command
│   │   ├── import_hub.py           # NEW: import-hub command
│   │   └── migrate_hub.py          # NEW: migrate-hub command
│   └── migration/
│       └── models.py                # Add Hub tables
```

---

## 2. Configuration Schema

### Environment Variables

```bash
# Source Automation Hub (AAP 2.4)
SOURCE_HUB__URL=https://aap24.example.com
SOURCE_HUB__TOKEN=<galaxy-token>
SOURCE_HUB__VERIFY_SSL=false

# Target Automation Hub (AAP 2.6)
TARGET_HUB__URL=https://aap26.example.com
TARGET_HUB__TOKEN=<galaxy-token>
TARGET_HUB__VERIFY_SSL=false

# Migration Options
HUB_MIGRATION__INCLUDE_NAMESPACES=ansible,community,myorg  # or "all"
HUB_MIGRATION__SKIP_ARTIFACTS=false
HUB_MIGRATION__ARTIFACT_DIR=./artifacts
HUB_MIGRATION__CHUNK_SIZE=10485760  # 10MB chunks for uploads
```

### Config File (config.yaml)

```yaml
automation_hub:
  source:
    url: "https://aap24.example.com"
    token: "${SOURCE_HUB__TOKEN}"
    verify_ssl: false
    timeout: 120
  
  target:
    url: "https://aap26.example.com"
    token: "${TARGET_HUB__TOKEN}"
    verify_ssl: false
    timeout: 120
  
  migration:
    # Filter options
    include_namespaces:
      - ansible
      - community
      - myorg
    exclude_namespaces:
      - test
      - staging
    
    # Artifact handling
    download_artifacts: true
    artifact_directory: "./artifacts"
    verify_checksums: true
    chunk_size_mb: 10
    
    # Performance
    max_concurrent_downloads: 5
    max_concurrent_uploads: 3
    retry_attempts: 3
    retry_delay_seconds: 5
    
    # Options
    skip_existing_collections: true
    force_overwrite: false
    create_missing_namespaces: true
```

---

## 3. Data Models

### 3.1 Namespace Model

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class Namespace:
    """Automation Hub Namespace"""
    name: str
    company: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    resources: Optional[str] = None
    links: list[dict] = None
    metadata: dict = None
    
    # Source/Target IDs
    source_id: Optional[str] = None
    target_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to API format"""
        return {
            "name": self.name,
            "company": self.company,
            "email": self.email,
            "avatar_url": self.avatar_url,
            "description": self.description,
            "resources": self.resources,
            "links": self.links or [],
        }
```

### 3.2 Collection Model

```python
@dataclass
class Collection:
    """Ansible Collection"""
    namespace: str
    name: str
    description: Optional[str] = None
    deprecated: bool = False
    
    # Computed fields
    fqn: Optional[str] = None  # namespace.name
    
    # Versions
    latest_version: Optional[str] = None
    versions: list['CollectionVersion'] = None
    
    # Metadata
    download_count: int = 0
    tags: list[str] = None
    metadata: dict = None
    
    def __post_init__(self):
        if not self.fqn:
            self.fqn = f"{self.namespace}.{self.name}"
        if self.versions is None:
            self.versions = []
        if self.tags is None:
            self.tags = []


@dataclass
class CollectionVersion:
    """Specific version of a collection"""
    namespace: str
    name: str
    version: str
    
    # Artifact info
    artifact_url: Optional[str] = None
    artifact_sha256: Optional[str] = None
    artifact_size: Optional[int] = None
    
    # Metadata
    dependencies: dict = None
    metadata: dict = None
    manifest: dict = None
    files: dict = None
    
    # Local storage
    local_path: Optional[str] = None
    downloaded: bool = False
    uploaded: bool = False
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = {}
    
    @property
    def fqn(self) -> str:
        return f"{self.namespace}.{self.name}"
    
    @property
    def full_name(self) -> str:
        return f"{self.fqn}:{self.version}"
```

### 3.3 Repository Model

```python
@dataclass
class Repository:
    """Ansible Collection Repository"""
    name: str
    description: Optional[str] = None
    pulp_href: Optional[str] = None
    
    # Configuration
    retain_repo_versions: Optional[int] = None
    remote: Optional[str] = None  # Link to remote if synced
    
    # Content
    latest_version_href: Optional[str] = None
    content_count: int = 0
    
    # Source/Target tracking
    source_id: Optional[str] = None
    target_id: Optional[str] = None
    
    metadata: dict = None
```

### 3.4 Remote Registry Model

```python
@dataclass
class RemoteRegistry:
    """Remote collection source"""
    name: str
    url: str
    
    # Authentication
    auth_url: Optional[str] = None
    token: Optional[str] = None  # Encrypted via Vault
    username: Optional[str] = None
    password: Optional[str] = None  # Encrypted via Vault
    
    # Sync configuration
    requirements_file: Optional[str] = None
    sync_dependencies: bool = True
    download_concurrency: int = 10
    rate_limit: Optional[int] = None
    
    # TLS
    tls_validation: bool = True
    ca_cert: Optional[str] = None
    client_cert: Optional[str] = None
    client_key: Optional[str] = None  # Encrypted via Vault
    
    # Proxy
    proxy_url: Optional[str] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None  # Encrypted via Vault
    
    # Pulp
    pulp_href: Optional[str] = None
    
    # Tracking
    source_id: Optional[str] = None
    target_id: Optional[str] = None
```

---

## 4. API Client Implementation

### 4.1 GalaxyAPIClient

```python
from typing import Optional, AsyncIterator
import httpx
from pathlib import Path

class GalaxyAPIClient:
    """Client for Automation Hub Galaxy API"""
    
    def __init__(
        self,
        base_url: str,
        token: str,
        verify_ssl: bool = True,
        timeout: int = 120,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            verify=verify_ssl,
            timeout=timeout,
        )
    
    # Namespace Operations
    async def list_namespaces(self) -> list[dict]:
        """List all namespaces"""
        url = "/api/galaxy/_ui/v1/namespaces/"
        return await self._paginated_get(url)
    
    async def get_namespace(self, name: str) -> dict:
        """Get namespace details"""
        url = f"/api/galaxy/_ui/v1/namespaces/{name}/"
        return await self._get(url)
    
    async def create_namespace(self, namespace: dict) -> dict:
        """Create a namespace"""
        url = "/api/galaxy/_ui/v1/namespaces/"
        return await self._post(url, json=namespace)
    
    # Collection Operations
    async def list_collections(
        self, 
        namespace: Optional[str] = None
    ) -> list[dict]:
        """List all collections"""
        url = "/api/galaxy/pulp/api/v3/content/ansible/collection_versions/"
        params = {}
        if namespace:
            params["namespace"] = namespace
        return await self._paginated_get(url, params=params)
    
    async def get_collection_versions(
        self, 
        namespace: str, 
        name: str
    ) -> list[dict]:
        """Get all versions of a collection"""
        url = f"/api/galaxy/pulp/api/v3/content/ansible/collection_versions/"
        params = {"namespace": namespace, "name": name}
        return await self._paginated_get(url, params=params)
    
    async def download_collection_artifact(
        self,
        download_url: str,
        output_path: Path,
        chunk_size: int = 1024 * 1024,  # 1MB
    ) -> Path:
        """Download collection artifact (.tar.gz)"""
        async with self.client.stream("GET", download_url) as response:
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size):
                    f.write(chunk)
        
        return output_path
    
    async def upload_collection_artifact(
        self,
        artifact_path: Path,
        sha256: str,
    ) -> dict:
        """Upload collection artifact to target"""
        url = "/api/galaxy/v3/artifacts/collections/"
        
        with open(artifact_path, "rb") as f:
            files = {"file": f}
            data = {"sha256": sha256}
            
            # Note: httpx requires special handling for multipart
            response = await self.client.post(
                url,
                files=files,
                data=data,
            )
            response.raise_for_status()
            return response.json()
    
    # Repository Operations
    async def list_repositories(self) -> list[dict]:
        """List Ansible repositories"""
        url = "/api/galaxy/pulp/api/v3/repositories/ansible/ansible/"
        return await self._paginated_get(url)
    
    async def get_repository(self, pulp_href: str) -> dict:
        """Get repository details"""
        return await self._get(pulp_href)
    
    async def create_repository(self, repository: dict) -> dict:
        """Create a repository"""
        url = "/api/galaxy/pulp/api/v3/repositories/ansible/ansible/"
        return await self._post(url, json=repository)
    
    # Remote Registry Operations
    async def list_remotes(self) -> list[dict]:
        """List collection remotes"""
        url = "/api/galaxy/pulp/api/v3/remotes/ansible/collection/"
        return await self._paginated_get(url)
    
    async def create_remote(self, remote: dict) -> dict:
        """Create a remote registry"""
        url = "/api/galaxy/pulp/api/v3/remotes/ansible/collection/"
        return await self._post(url, json=remote)
    
    # Task Operations
    async def wait_for_task(
        self, 
        task_href: str, 
        poll_interval: int = 2,
        timeout: int = 600,
    ) -> dict:
        """Wait for Pulp async task to complete"""
        import asyncio
        
        elapsed = 0
        while elapsed < timeout:
            task = await self._get(task_href)
            state = task.get("state")
            
            if state == "completed":
                return task
            elif state == "failed":
                raise Exception(f"Task failed: {task.get('error')}")
            elif state in ("canceled", "canceling"):
                raise Exception(f"Task was canceled")
            
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        raise TimeoutError(f"Task did not complete within {timeout}s")
    
    # Helper methods
    async def _get(self, url: str, **kwargs) -> dict:
        """GET request"""
        response = await self.client.get(url, **kwargs)
        response.raise_for_status()
        return response.json()
    
    async def _post(self, url: str, **kwargs) -> dict:
        """POST request"""
        response = await self.client.post(url, **kwargs)
        response.raise_for_status()
        return response.json()
    
    async def _paginated_get(
        self, 
        url: str, 
        params: dict = None
    ) -> list[dict]:
        """Handle paginated API responses"""
        results = []
        next_url = url
        
        while next_url:
            response = await self._get(next_url, params=params)
            results.extend(response.get("results", []))
            next_url = response.get("next")
            params = None  # Params already in next URL
        
        return results
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
```

---

## 5. Exporter Implementation

### 5.1 AutomationHubExporter

```python
import json
from pathlib import Path
from typing import Optional
import hashlib

from aap_migration.automation_hub.client import GalaxyAPIClient
from aap_migration.automation_hub.models import (
    Namespace,
    Collection,
    CollectionVersion,
    Repository,
    RemoteRegistry,
)
from aap_migration.utils.logging import get_logger

logger = get_logger(__name__)


class AutomationHubExporter:
    """Export Automation Hub content from source"""
    
    def __init__(
        self,
        client: GalaxyAPIClient,
        output_dir: Path,
        include_namespaces: Optional[list[str]] = None,
        exclude_namespaces: Optional[list[str]] = None,
    ):
        self.client = client
        self.output_dir = Path(output_dir)
        self.include_namespaces = include_namespaces
        self.exclude_namespaces = exclude_namespaces or []
        
        # Create directory structure
        self.namespaces_dir = self.output_dir / "namespaces"
        self.collections_dir = self.output_dir / "collections"
        self.artifacts_dir = self.output_dir / "artifacts"
        self.repositories_dir = self.output_dir / "repositories"
        self.remotes_dir = self.output_dir / "remotes"
        
        for dir in [
            self.namespaces_dir,
            self.collections_dir,
            self.artifacts_dir,
            self.repositories_dir,
            self.remotes_dir,
        ]:
            dir.mkdir(parents=True, exist_ok=True)
    
    async def export_all(self) -> dict:
        """Export all Automation Hub content"""
        logger.info("Starting Automation Hub export")
        
        stats = {
            "namespaces": 0,
            "collections": 0,
            "versions": 0,
            "artifacts_downloaded": 0,
            "repositories": 0,
            "remotes": 0,
        }
        
        # Export namespaces
        namespaces = await self.export_namespaces()
        stats["namespaces"] = len(namespaces)
        
        # Export collections for each namespace
        for namespace in namespaces:
            collections = await self.export_collections(namespace.name)
            stats["collections"] += len(collections)
            
            for collection in collections:
                versions = await self.export_collection_versions(
                    namespace.name, collection.name
                )
                stats["versions"] += len(versions)
                
                # Download artifacts
                for version in versions:
                    if await self.download_artifact(version):
                        stats["artifacts_downloaded"] += 1
        
        # Export repositories
        repositories = await self.export_repositories()
        stats["repositories"] = len(repositories)
        
        # Export remotes
        remotes = await self.export_remotes()
        stats["remotes"] = len(remotes)
        
        # Save metadata
        metadata = {
            "export_date": datetime.now().isoformat(),
            "source_url": self.client.base_url,
            "statistics": stats,
        }
        
        metadata_file = self.output_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info("Automation Hub export completed", **stats)
        return stats
    
    async def export_namespaces(self) -> list[Namespace]:
        """Export all namespaces"""
        logger.info("Exporting namespaces")
        
        raw_namespaces = await self.client.list_namespaces()
        namespaces = []
        
        for raw in raw_namespaces:
            name = raw["name"]
            
            # Apply filters
            if self.include_namespaces and name not in self.include_namespaces:
                continue
            if name in self.exclude_namespaces:
                continue
            
            namespace = Namespace(
                name=name,
                company=raw.get("company"),
                email=raw.get("email"),
                avatar_url=raw.get("avatar_url"),
                description=raw.get("description"),
                resources=raw.get("resources"),
                links=raw.get("links", []),
                metadata=raw,
                source_id=raw.get("id"),
            )
            
            # Save to file
            namespace_file = self.namespaces_dir / f"{name}.json"
            with open(namespace_file, "w") as f:
                json.dump(namespace.to_dict(), f, indent=2)
            
            namespaces.append(namespace)
            logger.debug(f"Exported namespace: {name}")
        
        logger.info(f"Exported {len(namespaces)} namespaces")
        return namespaces
    
    async def export_collections(self, namespace: str) -> list[Collection]:
        """Export collections for a namespace"""
        logger.info(f"Exporting collections for namespace: {namespace}")
        
        raw_collections = await self.client.list_collections(namespace=namespace)
        
        # Group by collection name (multiple versions)
        collections_dict = {}
        for raw in raw_collections:
            name = raw["name"]
            if name not in collections_dict:
                collections_dict[name] = Collection(
                    namespace=namespace,
                    name=name,
                    description=raw.get("description"),
                    deprecated=raw.get("deprecated", False),
                    metadata=raw,
                )
        
        collections = list(collections_dict.values())
        
        # Save metadata
        for collection in collections:
            collection_dir = self.collections_dir / f"{collection.fqn}"
            collection_dir.mkdir(parents=True, exist_ok=True)
            
            metadata_file = collection_dir / "metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(collection.metadata, f, indent=2)
        
        logger.info(f"Exported {len(collections)} collections for {namespace}")
        return collections
    
    async def export_collection_versions(
        self, namespace: str, name: str
    ) -> list[CollectionVersion]:
        """Export all versions of a collection"""
        logger.debug(f"Exporting versions for {namespace}.{name}")
        
        raw_versions = await self.client.get_collection_versions(namespace, name)
        versions = []
        
        collection_dir = self.collections_dir / f"{namespace}.{name}"
        versions_dir = collection_dir / "versions"
        versions_dir.mkdir(parents=True, exist_ok=True)
        
        for raw in raw_versions:
            version = CollectionVersion(
                namespace=namespace,
                name=name,
                version=raw["version"],
                artifact_url=raw.get("download_url"),
                artifact_sha256=raw.get("sha256"),
                artifact_size=raw.get("size"),
                dependencies=raw.get("dependencies", {}),
                metadata=raw,
                manifest=raw.get("manifest"),
                files=raw.get("files"),
            )
            
            # Save version metadata
            version_file = versions_dir / f"{version.version}.json"
            with open(version_file, "w") as f:
                json.dump(raw, f, indent=2)
            
            versions.append(version)
        
        logger.debug(f"Exported {len(versions)} versions for {namespace}.{name}")
        return versions
    
    async def download_artifact(
        self, version: CollectionVersion
    ) -> bool:
        """Download collection artifact"""
        if not version.artifact_url:
            logger.warning(
                f"No artifact URL for {version.full_name}, skipping"
            )
            return False
        
        artifact_name = f"{version.namespace}-{version.name}-{version.version}.tar.gz"
        artifact_path = self.artifacts_dir / artifact_name
        
        if artifact_path.exists():
            logger.debug(f"Artifact already exists: {artifact_name}")
            version.local_path = str(artifact_path)
            version.downloaded = True
            return True
        
        try:
            logger.info(f"Downloading artifact: {artifact_name}")
            await self.client.download_collection_artifact(
                version.artifact_url,
                artifact_path,
            )
            
            # Verify checksum
            if version.artifact_sha256:
                computed_sha = self._compute_sha256(artifact_path)
                if computed_sha != version.artifact_sha256:
                    logger.error(
                        f"Checksum mismatch for {artifact_name}: "
                        f"expected {version.artifact_sha256}, got {computed_sha}"
                    )
                    artifact_path.unlink()
                    return False
            
            version.local_path = str(artifact_path)
            version.downloaded = True
            logger.info(f"Downloaded: {artifact_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download {artifact_name}: {e}")
            return False
    
    def _compute_sha256(self, file_path: Path) -> str:
        """Compute SHA256 checksum"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    async def export_repositories(self) -> list[Repository]:
        """Export custom repositories"""
        logger.info("Exporting repositories")
        
        raw_repos = await self.client.list_repositories()
        repositories = []
        
        for raw in raw_repos:
            repository = Repository(
                name=raw["name"],
                description=raw.get("description"),
                pulp_href=raw.get("pulp_href"),
                retain_repo_versions=raw.get("retain_repo_versions"),
                remote=raw.get("remote"),
                latest_version_href=raw.get("latest_version_href"),
                metadata=raw,
                source_id=raw.get("pulp_href"),
            )
            
            # Save to file
            repo_file = self.repositories_dir / f"{repository.name}.json"
            with open(repo_file, "w") as f:
                json.dump(raw, f, indent=2)
            
            repositories.append(repository)
        
        logger.info(f"Exported {len(repositories)} repositories")
        return repositories
    
    async def export_remotes(self) -> list[RemoteRegistry]:
        """Export remote registries"""
        logger.info("Exporting remote registries")
        
        raw_remotes = await self.client.list_remotes()
        remotes = []
        
        for raw in raw_remotes:
            # Note: Credentials are encrypted/masked in API response
            remote = RemoteRegistry(
                name=raw["name"],
                url=raw["url"],
                auth_url=raw.get("auth_url"),
                requirements_file=raw.get("requirements_file"),
                sync_dependencies=raw.get("sync_dependencies", True),
                download_concurrency=raw.get("download_concurrency", 10),
                rate_limit=raw.get("rate_limit"),
                tls_validation=raw.get("tls_validation", True),
                pulp_href=raw.get("pulp_href"),
                source_id=raw.get("pulp_href"),
            )
            
            # Save to file (without credentials)
            remote_file = self.remotes_dir / f"{remote.name}.json"
            with open(remote_file, "w") as f:
                json.dump(raw, f, indent=2)
            
            remotes.append(remote)
        
        logger.info(f"Exported {len(remotes)} remote registries")
        return remotes
```

---

## 6. CLI Commands

### 6.1 export-hub Command

```bash
# Export entire Automation Hub
aap-bridge export-hub --output exports/hub/

# Export specific namespaces
aap-bridge export-hub --namespace ansible --namespace community

# Skip artifact downloads (metadata only)
aap-bridge export-hub --skip-artifacts

# Dry run (show what would be exported)
aap-bridge export-hub --dry-run
```

### 6.2 import-hub Command

```bash
# Import from export directory
aap-bridge import-hub --input exports/hub/

# Import specific namespaces only
aap-bridge import-hub --input exports/hub/ --namespace myorg

# Skip existing collections (idempotent)
aap-bridge import-hub --input exports/hub/ --skip-existing

# Force overwrite
aap-bridge import-hub --input exports/hub/ --force
```

### 6.3 migrate-hub Command

```bash
# Full migration (export + import)
aap-bridge migrate-hub

# Migration with filters
aap-bridge migrate-hub --namespace ansible --namespace community

# Metadata only (no artifacts)
aap-bridge migrate-hub --metadata-only
```

---

## 7. Database Schema Extensions

### New Tables

```sql
-- Automation Hub namespace tracking
CREATE TABLE hub_namespaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    source_id TEXT,
    target_id TEXT,
    status TEXT,  -- pending, completed, failed, skipped
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Collection tracking
CREATE TABLE hub_collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    namespace TEXT NOT NULL,
    name TEXT NOT NULL,
    fqn TEXT NOT NULL,  -- namespace.name
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(namespace, name)
);

-- Collection version tracking
CREATE TABLE hub_collection_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    namespace TEXT NOT NULL,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    fqn TEXT NOT NULL,  -- namespace.name:version
    
    -- Artifact info
    artifact_sha256 TEXT,
    artifact_size INTEGER,
    local_path TEXT,
    
    -- Status
    downloaded BOOLEAN DEFAULT 0,
    uploaded BOOLEAN DEFAULT 0,
    status TEXT,  -- pending, completed, failed, skipped
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(namespace, name, version)
);

-- Repository tracking
CREATE TABLE hub_repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    source_href TEXT,
    target_href TEXT,
    status TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Remote registry tracking
CREATE TABLE hub_remotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    source_href TEXT,
    target_href TEXT,
    status TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 8. Error Handling & Resilience

### Retry Strategy

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

class AutomationHubImporter:
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((httpx.HTTPError, TimeoutError)),
    )
    async def upload_collection(self, artifact_path: Path) -> dict:
        """Upload with retry logic"""
        # Upload implementation
        pass
```

### Checkpointing

```python
class MigrationCheckpoint:
    """Save/restore migration progress"""
    
    def save_checkpoint(self, phase: str, data: dict):
        """Save current migration state"""
        checkpoint = {
            "phase": phase,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }
        
        checkpoint_file = self.output_dir / ".checkpoint.json"
        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint, f, indent=2)
    
    def load_checkpoint(self) -> Optional[dict]:
        """Load saved checkpoint"""
        checkpoint_file = self.output_dir / ".checkpoint.json"
        if not checkpoint_file.exists():
            return None
        
        with open(checkpoint_file) as f:
            return json.load(f)
    
    def clear_checkpoint(self):
        """Remove checkpoint after successful completion"""
        checkpoint_file = self.output_dir / ".checkpoint.json"
        if checkpoint_file.exists():
            checkpoint_file.unlink()
```

---

## 9. Performance Optimizations

### Concurrent Operations

```python
import asyncio
from typing import Callable, TypeVar, Awaitable

T = TypeVar('T')

async def run_concurrent(
    items: list[T],
    func: Callable[[T], Awaitable],
    max_concurrent: int = 5,
) -> list:
    """Run operations concurrently with limit"""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def bounded_func(item):
        async with semaphore:
            return await func(item)
    
    tasks = [bounded_func(item) for item in items]
    return await asyncio.gather(*tasks, return_exceptions=True)


# Usage
async def migrate_collections():
    versions = load_collection_versions()
    
    # Upload 5 collections at a time
    results = await run_concurrent(
        versions,
        upload_collection,
        max_concurrent=5,
    )
```

### Streaming Downloads

```python
async def download_large_artifact(url: str, output: Path):
    """Stream download for large files"""
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            
            with open(output, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=1024*1024):
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Progress tracking
                    if total_size:
                        percent = (downloaded / total_size) * 100
                        logger.debug(f"Downloaded {percent:.1f}%")
```

---

## 10. Testing Strategy

### Unit Tests

```python
# tests/unit/test_automation_hub_exporter.py

import pytest
from unittest.mock import AsyncMock, patch
from aap_migration.automation_hub.exporter import AutomationHubExporter

@pytest.mark.asyncio
async def test_export_namespaces():
    """Test namespace export"""
    client = AsyncMock()
    client.list_namespaces.return_value = [
        {"name": "ansible", "company": "Red Hat"},
        {"name": "community", "company": "Community"},
    ]
    
    exporter = AutomationHubExporter(client, output_dir="/tmp/test")
    namespaces = await exporter.export_namespaces()
    
    assert len(namespaces) == 2
    assert namespaces[0].name == "ansible"
```

### Integration Tests

```python
# tests/integration/test_hub_migration.py

@pytest.mark.integration
async def test_migrate_single_collection():
    """Test migrating one collection end-to-end"""
    # Export from source
    exporter = AutomationHubExporter(source_client, output_dir)
    await exporter.export_collection_versions("ansible", "posix")
    
    # Import to target
    importer = AutomationHubImporter(target_client, input_dir)
    result = await importer.import_collection("ansible", "posix", "1.0.0")
    
    assert result["status"] == "completed"
```

---

## 11. Next Steps

### Development Phases

**Phase 1: Core Infrastructure (Week 1-2)**
- Implement GalaxyAPIClient
- Create data models
- Build exporter skeleton
- Add CLI commands

**Phase 2: Export Functionality (Week 2-3)**
- Implement namespace export
- Implement collection export
- Add artifact download
- Progress tracking

**Phase 3: Import Functionality (Week 3-4)**
- Implement namespace creation
- Implement collection upload
- Handle Pulp async tasks
- Error handling

**Phase 4: Testing & Polish (Week 4-5)**
- Unit tests
- Integration tests
- Documentation
- Performance tuning

---

## 12. Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| Large artifact timeouts | Streaming, resume capability |
| API rate limiting | Backoff, concurrent limits |
| Dependency cycles | Topological sort, multi-pass |
| Pulp task failures | Task monitoring, retry logic |
| Credential security | Vault integration, no plaintext |

---

**End of Implementation Specification**
