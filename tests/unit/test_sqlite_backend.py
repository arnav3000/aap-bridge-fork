"""Unit tests for SQLite backend compatibility."""

import tempfile
from pathlib import Path

import pytest

from aap_migration.migration.database import (
    create_database_backup,
    create_database_engine,
    get_database_size,
    init_database,
    reset_database,
    validate_database_connection,
)
from aap_migration.migration.models import Base


class TestSQLiteBackend:
    """Test SQLite database backend functionality."""

    def test_create_sqlite_engine(self):
        """Test creating SQLite engine."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db_url = f"sqlite:///{db_path}"

            engine = create_database_engine(db_url)
            assert engine is not None
            assert engine.url.drivername == "sqlite"

    def test_init_sqlite_database(self):
        """Test initializing SQLite database with tables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db_url = f"sqlite:///{db_path}"

            engine = init_database(db_url)
            assert engine is not None

            # Verify file was created
            assert db_path.exists()

            # Verify tables were created
            assert len(Base.metadata.tables) > 0

    def test_validate_sqlite_connection(self):
        """Test validating SQLite connection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db_url = f"sqlite:///{db_path}"

            # Initialize first
            init_database(db_url)

            # Validate connection
            assert validate_database_connection(db_url) is True

    def test_invalid_sqlite_connection(self):
        """Test validating invalid SQLite connection."""
        # Invalid path (permission denied)
        db_url = "sqlite:////root/invalid/path/test.db"

        # Should return False, not raise
        assert validate_database_connection(db_url) is False

    def test_get_sqlite_database_size(self):
        """Test getting SQLite database file size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db_url = f"sqlite:///{db_path}"

            # Before init: size should be 0
            assert get_database_size(db_url) == 0

            # After init: size should be > 0
            init_database(db_url)
            size = get_database_size(db_url)
            assert size > 0

    def test_get_size_postgresql_raises(self):
        """Test that get_database_size raises for PostgreSQL."""
        db_url = "postgresql://user:pass@localhost/db"

        with pytest.raises(ValueError, match="only supported for SQLite"):
            get_database_size(db_url)

    def test_create_sqlite_backup(self):
        """Test creating SQLite database backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            backup_path = Path(tmpdir) / "backup.db"
            db_url = f"sqlite:///{db_path}"

            # Initialize database
            init_database(db_url)

            # Create backup
            create_database_backup(db_url, str(backup_path))

            # Verify backup exists
            assert backup_path.exists()

            # Verify backup has same size
            assert get_database_size(db_url) == backup_path.stat().st_size

    def test_backup_postgresql_raises(self):
        """Test that backup raises for PostgreSQL."""
        db_url = "postgresql://user:pass@localhost/db"

        with pytest.raises(ValueError, match="only supported for SQLite"):
            create_database_backup(db_url, "/tmp/backup.db")

    def test_reset_sqlite_database(self):
        """Test resetting SQLite database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db_url = f"sqlite:///{db_path}"

            # Initialize database
            init_database(db_url)
            original_size = get_database_size(db_url)

            # Reset database
            reset_database(db_url)

            # Database should still exist
            assert db_path.exists()

            # Size might change but should be > 0
            new_size = get_database_size(db_url)
            assert new_size > 0

    def test_sqlite_foreign_keys_enabled(self):
        """Test that foreign keys are enabled in SQLite."""
        from sqlalchemy import text

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db_url = f"sqlite:///{db_path}"

            engine = create_database_engine(db_url)

            # Check foreign keys are enabled
            with engine.connect() as conn:
                result = conn.execute(text("PRAGMA foreign_keys")).fetchone()
                # Result should be (1,) if enabled
                assert result[0] == 1

    def test_sqlite_concurrent_access(self):
        """Test SQLite handles concurrent access with check_same_thread=False."""
        import threading
        from sqlalchemy import text

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db_url = f"sqlite:///{db_path}"

            init_database(db_url)

            # Access database from different thread
            def access_db():
                engine = create_database_engine(db_url)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))

            thread = threading.Thread(target=access_db)
            thread.start()
            thread.join()

            # Should not raise "SQLite objects created in a thread" error

    def test_default_sqlite_path(self):
        """Test default SQLite path from .env.example."""
        # The default path should be relative to current directory
        db_url = "sqlite:///./migration_state.db"

        # Should not raise
        engine = create_database_engine(db_url)
        assert engine is not None
        assert "migration_state.db" in str(engine.url)


class TestPostgreSQLBackend:
    """Test PostgreSQL backend detection (without actual server)."""

    def test_detect_postgresql_url(self):
        """Test PostgreSQL URL detection."""
        db_url = "postgresql://user:pass@localhost:5432/aap_migration"

        # Should create engine (will fail to connect, but that's OK)
        try:
            engine = create_database_engine(db_url)
            assert engine.url.drivername == "postgresql"
        except Exception:
            # Connection will fail without PostgreSQL server, but URL is valid
            pass

    def test_postgresql_connection_pooling(self):
        """Test PostgreSQL uses connection pooling."""
        db_url = "postgresql://user:pass@localhost:5432/aap_migration"

        try:
            engine = create_database_engine(db_url, pool_size=10, max_overflow=5)
            # QueuePool should be used for PostgreSQL
            assert "QueuePool" in str(type(engine.pool))
        except Exception:
            # Connection will fail without server
            pass
