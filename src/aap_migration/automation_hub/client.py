"""
Galaxy API Client for Automation Hub.

Provides async HTTP client for interacting with Automation Hub's
Galaxy API (Pulp 3 based).
"""

import asyncio
from pathlib import Path
from typing import Optional

import httpx

from aap_migration.automation_hub.exceptions import (
    GalaxyAPIError,
    TaskFailedError,
    TaskTimeoutError,
)
from aap_migration.automation_hub.models import (
    Namespace,
    Collection,
    CollectionVersion,
    Repository,
    RemoteRegistry,
)
from aap_migration.utils.logging import get_logger

logger = get_logger(__name__)


class GalaxyAPIClient:
    """Client for Automation Hub Galaxy API.

    Provides async methods for interacting with Automation Hub's Pulp 3 based
    Galaxy API, including namespaces, collections, repositories, and more.

    Supports two authentication methods:
    - Token-based (AAP 2.6): Galaxy token
    - Basic auth (AAP 2.4): username/password

    Usage:
        # Token-based (AAP 2.6)
        async with GalaxyAPIClient(url, token=token) as client:
            namespaces = await client.list_namespaces()

        # Basic auth (AAP 2.4)
        async with GalaxyAPIClient(url, username=user, password=pwd) as client:
            namespaces = await client.list_namespaces()
    """

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: bool = True,
        timeout: int = 120,
    ):
        """Initialize Galaxy API client.

        Args:
            base_url: Base URL of Automation Hub (e.g., https://localhost:10443)
            token: Authentication token (Galaxy token) - for AAP 2.6
            username: Username for basic auth - for AAP 2.4
            password: Password for basic auth - for AAP 2.4
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds

        Raises:
            ValueError: If neither token nor username/password provided
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.timeout = timeout

        # Validate authentication credentials
        if not token and not (username and password):
            raise ValueError(
                "Either token (AAP 2.6) or username/password (AAP 2.4) required"
            )

        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def connect(self):
        """Create HTTP client connection."""
        # Build headers and auth based on authentication method
        headers = {"Content-Type": "application/json"}
        auth = None

        if self.token:
            # Token-based auth (AAP 2.6)
            headers["Authorization"] = f"Bearer {self.token}"
            auth_method = "token"
        else:
            # Basic auth (AAP 2.4) - httpx.BasicAuth handles encoding
            auth = httpx.BasicAuth(username=self.username, password=self.password)
            auth_method = "basic"

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            auth=auth,
            verify=self.verify_ssl,
            timeout=self.timeout,
        )
        logger.info(
            "galaxy_client_connected",
            base_url=self.base_url,
            auth_method=auth_method,
            verify_ssl=self.verify_ssl,
        )

    async def close(self):
        """Close HTTP client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("galaxy_client_closed")

    # =========================================================================
    # Namespace Operations
    # =========================================================================

    async def list_namespaces(self, limit: Optional[int] = None) -> list[Namespace]:
        """List all namespaces.

        Args:
            limit: Maximum number of namespaces to return (None = all)

        Returns:
            List of Namespace objects

        Raises:
            GalaxyAPIError: If API request fails
        """
        logger.info("listing_namespaces", limit=limit)

        url = "/api/galaxy/_ui/v1/namespaces/"
        params = {}
        if limit:
            params["limit"] = limit

        raw_data = await self._paginated_get(url, params=params)

        namespaces = [Namespace.from_api(ns) for ns in raw_data]

        logger.info("namespaces_listed", count=len(namespaces))
        return namespaces

    async def get_namespace(self, name: str) -> Namespace:
        """Get namespace details.

        Args:
            name: Namespace name (e.g., "ansible", "community")

        Returns:
            Namespace object

        Raises:
            GalaxyAPIError: If namespace not found or API request fails
        """
        logger.debug("getting_namespace", name=name)

        url = f"/api/galaxy/_ui/v1/namespaces/{name}/"
        data = await self._get(url)

        namespace = Namespace.from_api(data)
        logger.debug("namespace_retrieved", name=name)
        return namespace

    async def create_namespace(self, namespace: Namespace) -> Namespace:
        """Create a namespace.

        Args:
            namespace: Namespace object to create

        Returns:
            Created Namespace object with target_id set

        Raises:
            GalaxyAPIError: If creation fails
        """
        logger.info("creating_namespace", name=namespace.name)

        url = "/api/galaxy/_ui/v1/namespaces/"
        data = await self._post(url, json=namespace.to_dict())

        created = Namespace.from_api(data)
        created.target_id = data.get("id")

        logger.info("namespace_created", name=namespace.name, id=created.target_id)
        return created

    async def namespace_exists(self, name: str) -> bool:
        """Check if namespace exists.

        Args:
            name: Namespace name

        Returns:
            True if namespace exists, False otherwise
        """
        try:
            await self.get_namespace(name)
            return True
        except GalaxyAPIError as e:
            if e.status_code == 404:
                return False
            raise

    # =========================================================================
    # Collection Operations
    # =========================================================================

    async def list_collections(
        self,
        namespace: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[CollectionVersion]:
        """List collection versions.

        Note: This returns CollectionVersion objects, not Collection objects,
        because the API returns individual versions.

        Args:
            namespace: Filter by namespace (None = all)
            limit: Maximum number of versions to return (None = all)

        Returns:
            List of CollectionVersion objects

        Raises:
            GalaxyAPIError: If API request fails
        """
        logger.info("listing_collections", namespace=namespace, limit=limit)

        url = "/api/galaxy/pulp/api/v3/content/ansible/collection_versions/"
        params = {}
        if namespace:
            params["namespace"] = namespace
        if limit:
            params["limit"] = limit

        raw_data = await self._paginated_get(url, params=params)

        versions = [CollectionVersion.from_api(v) for v in raw_data]

        logger.info("collections_listed", count=len(versions), namespace=namespace)
        return versions

    async def get_collection_versions(
        self,
        namespace: str,
        name: str,
    ) -> list[CollectionVersion]:
        """Get all versions of a specific collection.

        Args:
            namespace: Namespace name
            name: Collection name

        Returns:
            List of CollectionVersion objects, sorted by version (newest first)

        Raises:
            GalaxyAPIError: If API request fails
        """
        logger.debug("getting_collection_versions", namespace=namespace, name=name)

        url = "/api/galaxy/pulp/api/v3/content/ansible/collection_versions/"
        params = {"namespace": namespace, "name": name}

        raw_data = await self._paginated_get(url, params=params)

        versions = [CollectionVersion.from_api(v) for v in raw_data]

        logger.debug(
            "collection_versions_retrieved",
            namespace=namespace,
            name=name,
            count=len(versions),
        )
        return versions

    async def download_collection_artifact(
        self,
        download_url: str,
        output_path: Path,
        chunk_size: int = 1024 * 1024,  # 1MB chunks
    ) -> Path:
        """Download collection artifact (.tar.gz).

        Args:
            download_url: URL to download artifact from
            output_path: Local path to save artifact
            chunk_size: Download chunk size in bytes

        Returns:
            Path to downloaded artifact

        Raises:
            GalaxyAPIError: If download fails
        """
        logger.info("downloading_artifact", url=download_url, output=str(output_path))

        try:
            async with self._client.stream("GET", download_url) as response:
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(output_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size):
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size and downloaded % (10 * chunk_size) == 0:
                            percent = (downloaded / total_size) * 100
                            logger.debug(
                                "download_progress",
                                percent=f"{percent:.1f}%",
                                downloaded=downloaded,
                                total=total_size,
                            )

            logger.info(
                "artifact_downloaded",
                output=str(output_path),
                size=downloaded,
            )
            return output_path

        except httpx.HTTPError as e:
            raise GalaxyAPIError(
                f"Failed to download artifact: {e}",
                status_code=getattr(e.response, "status_code", None),
            ) from e

    async def upload_collection_artifact(
        self,
        artifact_path: Path,
        sha256: str,
    ) -> dict:
        """Upload collection artifact to target.

        Args:
            artifact_path: Path to .tar.gz artifact
            sha256: SHA256 checksum of artifact

        Returns:
            Upload response data

        Raises:
            GalaxyAPIError: If upload fails
        """
        logger.info(
            "uploading_artifact",
            path=str(artifact_path),
            sha256=sha256,
        )

        url = "/api/galaxy/v3/artifacts/collections/"

        try:
            with open(artifact_path, "rb") as f:
                files = {"file": (artifact_path.name, f, "application/gzip")}
                data = {"sha256": sha256}

                # Note: Need to remove Content-Type header for multipart
                headers = {k: v for k, v in self._client.headers.items() if k.lower() != "content-type"}

                # Add authentication header based on auth method
                if self.token:
                    headers["Authorization"] = f"Bearer {self.token}"
                # If using basic auth, httpx.BasicAuth is already set on client

                response = await self._client.post(
                    url,
                    files=files,
                    data=data,
                    headers=headers,
                )
                response.raise_for_status()

            result = response.json()
            logger.info("artifact_uploaded", artifact=artifact_path.name)
            return result

        except httpx.HTTPError as e:
            raise GalaxyAPIError(
                f"Failed to upload artifact: {e}",
                status_code=getattr(e.response, "status_code", None),
            ) from e

    # =========================================================================
    # Repository Operations
    # =========================================================================

    async def list_repositories(self) -> list[Repository]:
        """List Ansible repositories.

        Returns:
            List of Repository objects

        Raises:
            GalaxyAPIError: If API request fails
        """
        logger.info("listing_repositories")

        url = "/api/galaxy/pulp/api/v3/repositories/ansible/ansible/"
        raw_data = await self._paginated_get(url)

        repositories = [Repository.from_api(repo) for repo in raw_data]

        logger.info("repositories_listed", count=len(repositories))
        return repositories

    async def get_repository(self, pulp_href: str) -> Repository:
        """Get repository details.

        Args:
            pulp_href: Pulp href of the repository

        Returns:
            Repository object

        Raises:
            GalaxyAPIError: If repository not found or API request fails
        """
        logger.debug("getting_repository", pulp_href=pulp_href)

        data = await self._get(pulp_href)
        repository = Repository.from_api(data)

        logger.debug("repository_retrieved", name=repository.name)
        return repository

    async def create_repository(self, repository: Repository) -> Repository:
        """Create a repository.

        Args:
            repository: Repository object to create

        Returns:
            Created Repository object

        Raises:
            GalaxyAPIError: If creation fails
        """
        logger.info("creating_repository", name=repository.name)

        url = "/api/galaxy/pulp/api/v3/repositories/ansible/ansible/"
        data = await self._post(url, json=repository.to_dict())

        created = Repository.from_api(data)
        logger.info("repository_created", name=repository.name, href=created.pulp_href)
        return created

    # =========================================================================
    # Remote Registry Operations
    # =========================================================================

    async def list_remotes(self) -> list[RemoteRegistry]:
        """List collection remotes.

        Returns:
            List of RemoteRegistry objects

        Raises:
            GalaxyAPIError: If API request fails
        """
        logger.info("listing_remotes")

        url = "/api/galaxy/pulp/api/v3/remotes/ansible/collection/"
        raw_data = await self._paginated_get(url)

        remotes = [RemoteRegistry.from_api(remote) for remote in raw_data]

        logger.info("remotes_listed", count=len(remotes))
        return remotes

    async def create_remote(self, remote: RemoteRegistry) -> RemoteRegistry:
        """Create a remote registry.

        Args:
            remote: RemoteRegistry object to create

        Returns:
            Created RemoteRegistry object

        Raises:
            GalaxyAPIError: If creation fails
        """
        logger.info("creating_remote", name=remote.name, url=remote.url)

        url = "/api/galaxy/pulp/api/v3/remotes/ansible/collection/"
        data = await self._post(url, json=remote.to_dict())

        created = RemoteRegistry.from_api(data)
        logger.info("remote_created", name=remote.name, href=created.pulp_href)
        return created

    # =========================================================================
    # Pulp Task Operations
    # =========================================================================

    async def wait_for_task(
        self,
        task_href: str,
        poll_interval: int = 2,
        timeout: int = 600,
    ) -> dict:
        """Wait for Pulp async task to complete.

        Args:
            task_href: Pulp task href
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait

        Returns:
            Completed task data

        Raises:
            TaskTimeoutError: If task doesn't complete within timeout
            TaskFailedError: If task fails
            GalaxyAPIError: If API request fails
        """
        logger.info("waiting_for_task", task_href=task_href, timeout=timeout)

        elapsed = 0
        while elapsed < timeout:
            task = await self._get(task_href)
            state = task.get("state")

            logger.debug("task_status", state=state, elapsed=elapsed)

            if state == "completed":
                logger.info("task_completed", task_href=task_href)
                return task

            elif state == "failed":
                error = task.get("error", {}).get("description", "Unknown error")
                raise TaskFailedError(
                    f"Task failed: {error}",
                    task_data=task,
                )

            elif state in ("canceled", "canceling"):
                raise TaskFailedError(
                    "Task was canceled",
                    task_data=task,
                )

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TaskTimeoutError(
            f"Task did not complete within {timeout}s: {task_href}"
        )

    # =========================================================================
    # HTTP Helper Methods
    # =========================================================================

    async def _get(self, url: str, **kwargs) -> dict:
        """Perform GET request.

        Args:
            url: URL to request (can be absolute or relative)
            **kwargs: Additional arguments for httpx

        Returns:
            JSON response data

        Raises:
            GalaxyAPIError: If request fails
        """
        try:
            response = await self._client.get(url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            status_code = getattr(e.response, "status_code", None) if hasattr(e, "response") else None
            response_text = e.response.text if hasattr(e, "response") else str(e)
            raise GalaxyAPIError(
                f"GET {url} failed: {response_text}",
                status_code=status_code,
            ) from e

    async def _post(self, url: str, **kwargs) -> dict:
        """Perform POST request.

        Args:
            url: URL to request
            **kwargs: Additional arguments for httpx (e.g., json=data)

        Returns:
            JSON response data

        Raises:
            GalaxyAPIError: If request fails
        """
        try:
            response = await self._client.post(url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            status_code = getattr(e.response, "status_code", None) if hasattr(e, "response") else None
            response_text = e.response.text if hasattr(e, "response") else str(e)
            raise GalaxyAPIError(
                f"POST {url} failed: {response_text}",
                status_code=status_code,
            ) from e

    async def _paginated_get(
        self,
        url: str,
        params: Optional[dict] = None,
    ) -> list[dict]:
        """Handle paginated API responses.

        Galaxy API uses "next" field for pagination.

        Args:
            url: Initial URL to request
            params: Query parameters for first request

        Returns:
            List of all results across all pages

        Raises:
            GalaxyAPIError: If request fails
        """
        results = []
        next_url = url

        while next_url:
            response = await self._get(next_url, params=params)
            results.extend(response.get("results", []))

            next_url = response.get("next")
            params = None  # Params already in next URL

            logger.debug(
                "pagination_progress",
                current_count=len(results),
                has_next=bool(next_url),
            )

        return results
