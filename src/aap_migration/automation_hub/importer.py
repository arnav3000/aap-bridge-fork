"""
Automation Hub Importer.

Imports namespaces, collections, repositories, and remotes into target AAP 2.6.
"""

import asyncio
from pathlib import Path
from typing import Optional

from aap_migration.automation_hub.client import GalaxyAPIClient
from aap_migration.automation_hub.exceptions import (
    GalaxyAPIError,
    NamespaceError,
    CollectionError,
)
from aap_migration.automation_hub.models import (
    Namespace,
    CollectionVersion,
    Repository,
    RemoteRegistry,
)
from aap_migration.automation_hub.transformer import AutomationHubTransformer
from aap_migration.utils.logging import get_logger

logger = get_logger(__name__)


class AutomationHubImporter:
    """Imports Automation Hub content into target AAP 2.6."""

    def __init__(
        self,
        target_url: str,
        export_dir: Path,
        target_token: Optional[str] = None,
        target_username: Optional[str] = None,
        target_password: Optional[str] = None,
        verify_ssl: bool = True,
        skip_existing: bool = True,
        upload_artifacts: bool = True,
    ):
        """Initialize Automation Hub importer.

        Args:
            target_url: Target Automation Hub URL
            export_dir: Directory containing exported data
            target_token: Authentication token (AAP 2.6)
            target_username: Username for basic auth (AAP 2.4)
            target_password: Password for basic auth (AAP 2.4)
            verify_ssl: Whether to verify SSL certificates
            skip_existing: Skip resources that already exist on target
            upload_artifacts: Whether to upload collection artifacts
        """
        self.target_url = target_url
        self.target_token = target_token
        self.target_username = target_username
        self.target_password = target_password
        self.export_dir = export_dir
        self.verify_ssl = verify_ssl
        self.skip_existing = skip_existing
        self.upload_artifacts = upload_artifacts

        self.client: Optional[GalaxyAPIClient] = None
        self.transformer = AutomationHubTransformer(export_dir)

        # Import tracking
        self.stats = {
            "namespaces": {"created": 0, "skipped": 0, "failed": 0},
            "collections": {"uploaded": 0, "skipped": 0, "failed": 0},
            "repositories": {"created": 0, "skipped": 0, "failed": 0},
            "remotes": {"created": 0, "skipped": 0, "failed": 0},
        }

    async def connect(self):
        """Connect to target Automation Hub."""
        self.client = GalaxyAPIClient(
            base_url=self.target_url,
            token=self.target_token,
            username=self.target_username,
            password=self.target_password,
            verify_ssl=self.verify_ssl,
        )
        await self.client.connect()
        logger.info("connected_to_target_hub", url=self.target_url)

    async def close(self):
        """Close connection to target."""
        if self.client:
            await self.client.close()
            self.client = None

    async def import_all(self):
        """Import all Automation Hub content.

        Imports in order:
        1. Transform exported data
        2. Namespaces
        3. Repositories
        4. Remotes
        5. Collections (requires namespaces to exist)
        """
        logger.info("starting_hub_import", target_url=self.target_url)

        try:
            await self.connect()

            # Transform exported data
            logger.info("transforming_exported_data")
            self.transformer.transform_all()

            # Import namespaces first (collections depend on them)
            await self.import_namespaces()
            logger.info(
                "imported_namespaces",
                created=self.stats["namespaces"]["created"],
                skipped=self.stats["namespaces"]["skipped"],
                failed=self.stats["namespaces"]["failed"],
            )

            # Import repositories
            await self.import_repositories()
            logger.info(
                "imported_repositories",
                created=self.stats["repositories"]["created"],
                skipped=self.stats["repositories"]["skipped"],
                failed=self.stats["repositories"]["failed"],
            )

            # Import remotes
            await self.import_remotes()
            logger.info(
                "imported_remotes",
                created=self.stats["remotes"]["created"],
                skipped=self.stats["remotes"]["skipped"],
                failed=self.stats["remotes"]["failed"],
            )

            # Import collections last (requires namespaces)
            if self.upload_artifacts:
                await self.import_collections()
                logger.info(
                    "imported_collections",
                    uploaded=self.stats["collections"]["uploaded"],
                    skipped=self.stats["collections"]["skipped"],
                    failed=self.stats["collections"]["failed"],
                )

            logger.info("hub_import_completed", stats=self.stats)

        finally:
            await self.close()

    async def import_namespaces(self):
        """Import namespaces into target."""
        logger.info(
            "importing_namespaces", count=len(self.transformer.transformed_namespaces)
        )

        for ns in self.transformer.transformed_namespaces:
            try:
                # Check if namespace already exists
                if self.skip_existing:
                    exists = await self.client.namespace_exists(ns.name)
                    if exists:
                        logger.info("namespace_already_exists", name=ns.name)
                        self.stats["namespaces"]["skipped"] += 1
                        continue

                # Create namespace
                created = await self.client.create_namespace(ns)
                self.stats["namespaces"]["created"] += 1

                logger.info(
                    "namespace_created",
                    name=ns.name,
                    target_id=created.target_id,
                )

            except GalaxyAPIError as e:
                self.stats["namespaces"]["failed"] += 1
                logger.error(
                    "namespace_creation_failed",
                    name=ns.name,
                    error=str(e),
                    status_code=e.status_code,
                )

            except Exception as e:
                self.stats["namespaces"]["failed"] += 1
                logger.error(
                    "namespace_import_error",
                    name=ns.name,
                    error=str(e),
                )

    async def import_collections(self):
        """Import collection versions into target."""
        logger.info(
            "importing_collections",
            count=len(self.transformer.transformed_collections),
        )

        for cv in self.transformer.transformed_collections:
            try:
                # Verify namespace exists
                ns_exists = await self.client.namespace_exists(cv.namespace)
                if not ns_exists:
                    logger.error(
                        "namespace_missing_for_collection",
                        namespace=cv.namespace,
                        collection=cv.fqn,
                    )
                    self.stats["collections"]["failed"] += 1
                    continue

                # Check if version already exists
                if self.skip_existing:
                    existing_versions = await self.client.get_collection_versions(
                        namespace=cv.namespace,
                        name=cv.name,
                    )
                    if any(v.version == cv.version for v in existing_versions):
                        logger.info(
                            "collection_version_already_exists",
                            fqn=cv.fqn,
                            version=cv.version,
                        )
                        self.stats["collections"]["skipped"] += 1
                        continue

                # Verify artifact file exists
                if not cv.local_path or not Path(cv.local_path).exists():
                    logger.error(
                        "artifact_file_missing",
                        fqn=cv.fqn,
                        version=cv.version,
                        local_path=cv.local_path,
                    )
                    self.stats["collections"]["failed"] += 1
                    continue

                # Upload artifact
                artifact_path = Path(cv.local_path)
                result = await self.client.upload_collection_artifact(
                    artifact_path=artifact_path,
                    sha256=cv.artifact_sha256,
                )

                self.stats["collections"]["uploaded"] += 1

                logger.info(
                    "collection_uploaded",
                    fqn=cv.fqn,
                    version=cv.version,
                )

            except GalaxyAPIError as e:
                self.stats["collections"]["failed"] += 1
                logger.error(
                    "collection_upload_failed",
                    fqn=cv.fqn,
                    version=cv.version,
                    error=str(e),
                    status_code=e.status_code,
                )

            except Exception as e:
                self.stats["collections"]["failed"] += 1
                logger.error(
                    "collection_import_error",
                    fqn=cv.fqn,
                    version=cv.version,
                    error=str(e),
                )

    async def import_repositories(self):
        """Import repositories into target."""
        logger.info(
            "importing_repositories",
            count=len(self.transformer.transformed_repositories),
        )

        for repo in self.transformer.transformed_repositories:
            try:
                # Check if repository already exists by name
                if self.skip_existing:
                    existing_repos = await self.client.list_repositories()
                    if any(r.name == repo.name for r in existing_repos):
                        logger.info("repository_already_exists", name=repo.name)
                        self.stats["repositories"]["skipped"] += 1
                        continue

                # Create repository
                created = await self.client.create_repository(repo)
                self.stats["repositories"]["created"] += 1

                logger.info(
                    "repository_created",
                    name=repo.name,
                    href=created.pulp_href,
                )

            except GalaxyAPIError as e:
                self.stats["repositories"]["failed"] += 1
                logger.error(
                    "repository_creation_failed",
                    name=repo.name,
                    error=str(e),
                    status_code=e.status_code,
                )

            except Exception as e:
                self.stats["repositories"]["failed"] += 1
                logger.error(
                    "repository_import_error",
                    name=repo.name,
                    error=str(e),
                )

    async def import_remotes(self):
        """Import remote registries into target."""
        logger.info(
            "importing_remotes", count=len(self.transformer.transformed_remotes)
        )

        for remote in self.transformer.transformed_remotes:
            try:
                # Check if remote already exists by name
                if self.skip_existing:
                    existing_remotes = await self.client.list_remotes()
                    if any(r.name == remote.name for r in existing_remotes):
                        logger.info("remote_already_exists", name=remote.name)
                        self.stats["remotes"]["skipped"] += 1
                        continue

                # Create remote
                created = await self.client.create_remote(remote)
                self.stats["remotes"]["created"] += 1

                logger.info(
                    "remote_created",
                    name=remote.name,
                    href=created.pulp_href,
                )

            except GalaxyAPIError as e:
                self.stats["remotes"]["failed"] += 1
                logger.error(
                    "remote_creation_failed",
                    name=remote.name,
                    error=str(e),
                    status_code=e.status_code,
                )

            except Exception as e:
                self.stats["remotes"]["failed"] += 1
                logger.error(
                    "remote_import_error",
                    name=remote.name,
                    error=str(e),
                )

    def get_import_stats(self) -> dict:
        """Get import statistics.

        Returns:
            Dictionary with import statistics
        """
        return {
            "namespaces": {
                "created": self.stats["namespaces"]["created"],
                "skipped": self.stats["namespaces"]["skipped"],
                "failed": self.stats["namespaces"]["failed"],
                "total": sum(self.stats["namespaces"].values()),
            },
            "collections": {
                "uploaded": self.stats["collections"]["uploaded"],
                "skipped": self.stats["collections"]["skipped"],
                "failed": self.stats["collections"]["failed"],
                "total": sum(self.stats["collections"].values()),
            },
            "repositories": {
                "created": self.stats["repositories"]["created"],
                "skipped": self.stats["repositories"]["skipped"],
                "failed": self.stats["repositories"]["failed"],
                "total": sum(self.stats["repositories"].values()),
            },
            "remotes": {
                "created": self.stats["remotes"]["created"],
                "skipped": self.stats["remotes"]["skipped"],
                "failed": self.stats["remotes"]["failed"],
                "total": sum(self.stats["remotes"].values()),
            },
        }
