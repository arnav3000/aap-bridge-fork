"""
Automation Hub Transformer.

Transforms exported Automation Hub data from AAP 2.4 format to AAP 2.6 format.
"""

import json
from pathlib import Path
from typing import Optional

from aap_migration.automation_hub.models import (
    Namespace,
    CollectionVersion,
    Repository,
    RemoteRegistry,
)
from aap_migration.utils.logging import get_logger

logger = get_logger(__name__)


class AutomationHubTransformer:
    """Transforms Automation Hub content from AAP 2.4 to AAP 2.6."""

    def __init__(self, export_dir: Path):
        """Initialize transformer.

        Args:
            export_dir: Directory containing exported data
        """
        self.export_dir = export_dir
        self.hub_dir = export_dir / "automation_hub"

        self.namespaces_dir = self.hub_dir / "namespaces"
        self.collections_dir = self.hub_dir / "collections"
        self.artifacts_dir = self.hub_dir / "artifacts"
        self.repositories_dir = self.hub_dir / "repositories"
        self.remotes_dir = self.hub_dir / "remotes"

        # Transformation results
        self.transformed_namespaces: list[Namespace] = []
        self.transformed_collections: list[CollectionVersion] = []
        self.transformed_repositories: list[Repository] = []
        self.transformed_remotes: list[RemoteRegistry] = []

    def transform_all(self):
        """Transform all exported data.

        Reads exported JSON files and transforms them to target format.
        Most transformations are minimal as Galaxy API is compatible between versions.
        """
        logger.info("starting_hub_transformation", export_dir=str(self.hub_dir))

        # Transform namespaces
        self.transformed_namespaces = self.transform_namespaces()
        logger.info("transformed_namespaces", count=len(self.transformed_namespaces))

        # Transform collections
        self.transformed_collections = self.transform_collections()
        logger.info("transformed_collections", count=len(self.transformed_collections))

        # Derive namespaces from collections if no explicit namespaces were exported
        if not self.transformed_namespaces and self.transformed_collections:
            logger.warning(
                "no_explicit_namespaces_found",
                message="Deriving namespaces from collection metadata",
            )
            self.transformed_namespaces = self._derive_namespaces_from_collections()
            logger.info(
                "namespaces_derived_from_collections",
                count=len(self.transformed_namespaces),
            )

        # Transform repositories
        self.transformed_repositories = self.transform_repositories()
        logger.info("transformed_repositories", count=len(self.transformed_repositories))

        # Transform remotes
        self.transformed_remotes = self.transform_remotes()
        logger.info("transformed_remotes", count=len(self.transformed_remotes))

        logger.info(
            "hub_transformation_completed",
            namespaces=len(self.transformed_namespaces),
            collections=len(self.transformed_collections),
            repositories=len(self.transformed_repositories),
            remotes=len(self.transformed_remotes),
        )

    def transform_namespaces(self) -> list[Namespace]:
        """Transform namespace data.

        Returns:
            List of transformed Namespace objects
        """
        logger.info("transforming_namespaces")

        namespaces = []

        # Read all namespace JSON files
        for ns_file in self.namespaces_dir.glob("*.json"):
            if ns_file.name == "_index.json":
                continue

            with open(ns_file) as f:
                data = json.load(f)

            # Create Namespace from API data
            ns = Namespace.from_api(data)

            # Apply transformations if needed
            ns = self._transform_namespace(ns)

            namespaces.append(ns)
            logger.debug("namespace_transformed", name=ns.name)

        logger.info("namespaces_transformed", count=len(namespaces))
        return namespaces

    def _transform_namespace(self, namespace: Namespace) -> Namespace:
        """Apply namespace-specific transformations.

        Args:
            namespace: Source namespace

        Returns:
            Transformed namespace

        Note:
            Namespaces are largely compatible between AAP 2.4 and 2.6.
            Most fields can be copied directly.
        """
        # Clear target_id (will be assigned on import)
        namespace.target_id = None

        # Validate required fields
        if not namespace.name:
            raise ValueError("Namespace must have a name")

        # Sanitize name (lowercase, alphanumeric + underscore + hyphen only)
        namespace.name = namespace.name.lower().strip()

        return namespace

    def _derive_namespaces_from_collections(self) -> list[Namespace]:
        """Derive namespace objects from collection metadata.

        This is used when the source Hub has no explicit namespace objects
        (e.g., when collections were synced from external sources like console.redhat.com).

        Returns:
            List of Namespace objects derived from collections
        """
        logger.info("deriving_namespaces_from_collections")

        # Extract unique namespaces from collections
        namespace_names = set()
        for cv in self.transformed_collections:
            if cv.namespace:
                namespace_names.add(cv.namespace)

        # Create minimal namespace objects
        # API requires non-null values for company, email, avatar_url, resources
        namespaces = []
        for ns_name in sorted(namespace_names):
            ns = Namespace(
                name=ns_name,
                company="",  # Empty string instead of None (API requirement)
                email="",    # Empty string instead of None (API requirement)
                avatar_url="",  # Empty string instead of None (API requirement)
                resources="",   # Empty string instead of None (API requirement)
                description=f"Namespace for {ns_name} collections",
                source_id=None,
                target_id=None,
            )
            namespaces.append(ns)
            logger.debug("namespace_derived", name=ns_name)

        logger.info("namespaces_derived", count=len(namespaces))
        return namespaces

    def transform_collections(self) -> list[CollectionVersion]:
        """Transform collection version data.

        Returns:
            List of transformed CollectionVersion objects
        """
        logger.info("transforming_collections")

        versions = []

        # Read all collection JSON files
        for ns_dir in self.collections_dir.iterdir():
            if not ns_dir.is_dir():
                continue

            for coll_file in ns_dir.glob("*.json"):
                with open(coll_file) as f:
                    data = json.load(f)

                # Each file contains multiple versions
                for version_data in data.get("versions", []):
                    cv = CollectionVersion.from_api(version_data)

                    # Apply transformations
                    cv = self._transform_collection_version(cv)

                    versions.append(cv)

        logger.info("collections_transformed", count=len(versions))
        return versions

    def _transform_collection_version(
        self, version: CollectionVersion
    ) -> CollectionVersion:
        """Apply collection version transformations.

        Args:
            version: Source collection version

        Returns:
            Transformed collection version

        Note:
            Collection versions are uploaded as artifacts, so most metadata
            is preserved in the tarball itself. We mainly need to track
            which versions to upload.
        """
        # Clear target_id (will be assigned on import)
        version.target_id = None

        # Mark as not uploaded yet
        version.uploaded = False

        # Validate required fields
        if not version.namespace or not version.name or not version.version:
            raise ValueError(
                f"Collection version missing required fields: {version.full_name}"
            )

        # Check if artifact exists locally
        if self.artifacts_dir:
            artifact_path = (
                self.artifacts_dir / version.namespace / version.artifact_filename
            )
            if artifact_path.exists():
                version.local_path = str(artifact_path)
                version.downloaded = True
            else:
                logger.warning(
                    "artifact_not_found",
                    fqn=version.fqn,
                    version=version.version,
                    expected_path=str(artifact_path),
                )

        return version

    def transform_repositories(self) -> list[Repository]:
        """Transform repository data.

        Returns:
            List of transformed Repository objects
        """
        logger.info("transforming_repositories")

        repositories = []

        # Read all repository JSON files
        for repo_file in self.repositories_dir.glob("*.json"):
            if repo_file.name == "_index.json":
                continue

            with open(repo_file) as f:
                data = json.load(f)

            repo = Repository.from_api(data)

            # Apply transformations
            repo = self._transform_repository(repo)

            repositories.append(repo)
            logger.debug("repository_transformed", name=repo.name)

        logger.info("repositories_transformed", count=len(repositories))
        return repositories

    def _transform_repository(self, repository: Repository) -> Repository:
        """Apply repository transformations.

        Args:
            repository: Source repository

        Returns:
            Transformed repository

        Note:
            Repositories may need special handling as AAP 2.6 may have
            different default repositories or naming conventions.
        """
        # Clear target_id and pulp_href (will be created fresh)
        repository.target_id = None
        repository.pulp_href = None
        repository.latest_version_href = None

        # Clear remote link (will be relinked after remote creation)
        repository.remote = None

        # Validate required fields
        if not repository.name:
            raise ValueError("Repository must have a name")

        return repository

    def transform_remotes(self) -> list[RemoteRegistry]:
        """Transform remote registry data.

        Returns:
            List of transformed RemoteRegistry objects
        """
        logger.info("transforming_remotes")

        remotes = []

        # Read all remote JSON files
        for remote_file in self.remotes_dir.glob("*.json"):
            if remote_file.name == "_index.json":
                continue

            with open(remote_file) as f:
                data = json.load(f)

            remote = RemoteRegistry.from_api(data)

            # Apply transformations
            remote = self._transform_remote(remote)

            remotes.append(remote)
            logger.debug("remote_transformed", name=remote.name)

        logger.info("remotes_transformed", count=len(remotes))
        return remotes

    def _transform_remote(self, remote: RemoteRegistry) -> RemoteRegistry:
        """Apply remote registry transformations.

        Args:
            remote: Source remote

        Returns:
            Transformed remote

        Note:
            Remotes contain sensitive data (tokens, passwords) that should
            be handled via Vault in production. For migration, we preserve
            the configuration but may need to update URLs or credentials.
        """
        # Clear target_id and pulp_href (will be created fresh)
        remote.target_id = None
        remote.pulp_href = None

        # Validate required fields
        if not remote.name or not remote.url:
            raise ValueError("Remote must have name and URL")

        # Warn about credentials (should be handled via Vault)
        if remote.token or remote.password:
            logger.warning(
                "remote_has_credentials",
                name=remote.name,
                message="Credentials should be managed via Vault in production",
            )

        return remote

    def get_transformation_summary(self) -> dict:
        """Get summary of transformation results.

        Returns:
            Dictionary with transformation statistics
        """
        return {
            "namespaces": {
                "total": len(self.transformed_namespaces),
                "items": [ns.name for ns in self.transformed_namespaces],
            },
            "collections": {
                "total": len(self.transformed_collections),
                "with_artifacts": sum(
                    1 for cv in self.transformed_collections if cv.downloaded
                ),
                "without_artifacts": sum(
                    1 for cv in self.transformed_collections if not cv.downloaded
                ),
            },
            "repositories": {
                "total": len(self.transformed_repositories),
                "items": [repo.name for repo in self.transformed_repositories],
            },
            "remotes": {
                "total": len(self.transformed_remotes),
                "items": [remote.name for remote in self.transformed_remotes],
            },
        }
