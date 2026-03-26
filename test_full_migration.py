#!/usr/bin/env python3
"""Test script to demonstrate full migration workflow with credential-first approach."""

import asyncio
import sys
from pathlib import Path

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from aap_migration.client.aap_source_client import AAPSourceClient
from aap_migration.client.aap_target_client import AAPTargetClient
from aap_migration.config import load_config_from_yaml
from aap_migration.migration.coordinator import MigrationCoordinator
from aap_migration.migration.state import MigrationState


async def test_full_migration():
    """Test full migration workflow with credential-first approach."""

    print("=" * 80)
    print("FULL MIGRATION WORKFLOW TEST - CREDENTIAL-FIRST APPROACH")
    print("=" * 80)
    print()

    # Load configuration
    print("Loading configuration...")
    config = load_config_from_yaml(Path("config/config.yaml"))
    print(f"✓ Source: {config.source.url}")
    print(f"✓ Target: {config.target.url}")
    print()

    # Create clients
    print("Creating AAP clients...")
    source_client = AAPSourceClient(
        config=config.source,
        rate_limit=config.performance.rate_limit,
    )
    target_client = AAPTargetClient(
        config=config.target,
        rate_limit=config.performance.rate_limit,
    )
    print("✓ Clients created")
    print()

    # Create state manager
    print("Initializing migration state...")
    state = MigrationState(config=config.state)
    print(f"✓ State database: {config.state.db_path}")
    print(f"✓ Migration ID: {state.migration_id}")
    print()

    # Create coordinator
    print("Creating migration coordinator...")
    coordinator = MigrationCoordinator(
        config=config,
        source_client=source_client,
        target_client=target_client,
        state=state,
        enable_progress=True,
        show_stats=True,
    )
    print("✓ Coordinator initialized")
    print()

    # Run full migration with credential-first approach
    # This will migrate only the first few phases for testing
    print("=" * 80)
    print("STARTING MIGRATION - CREDENTIAL-FIRST WORKFLOW")
    print("=" * 80)
    print()
    print("The migration will:")
    print("  1. Compare credentials automatically before starting")
    print("  2. Display credential comparison results")
    print("  3. Migrate Phase 1: Organizations")
    print("  4. Migrate Phase 2: Credentials (CRITICAL - before other resources)")
    print("  5. Migrate Phase 3-4: Credential Input Sources and Identity")
    print()
    print("Note: Migrating only first 4 phases for testing...")
    print()

    try:
        # Migrate only first 4 phases to demonstrate credential-first
        result = await coordinator.migrate_all(
            only_phases=["organizations", "credentials", "credential_input_sources", "identity"],
            generate_report=True,
            report_dir="./reports",
        )

        print()
        print("=" * 80)
        print("MIGRATION COMPLETE!")
        print("=" * 80)
        print()
        print("Results:")
        print(f"  Status: {result['status']}")
        print(f"  Phases Completed: {result['phases_completed']}")
        print(f"  Phases Failed: {result['phases_failed']}")
        print(f"  Resources Exported: {result['total_resources_exported']}")
        print(f"  Resources Imported: {result['total_resources_imported']}")
        print(f"  Resources Failed: {result['total_resources_failed']}")
        print(f"  Resources Skipped: {result['total_resources_skipped']}")
        print()

        if result.get('report_files'):
            print("Reports Generated:")
            for report_file in result['report_files']:
                print(f"  - {report_file}")
        print()

        # Show credential mappings
        print("=" * 80)
        print("CREDENTIAL ID MAPPINGS (Sample)")
        print("=" * 80)
        print()

        import sqlite3
        db = sqlite3.connect(str(config.state.db_path))
        cursor = db.execute(
            """
            SELECT source_id, target_id, source_name
            FROM id_mappings
            WHERE resource_type='credentials'
            AND source_name LIKE 'REGRESSION_TEST%'
            ORDER BY source_id
            """
        )

        rows = cursor.fetchall()
        if rows:
            print("Regression Test Credentials:")
            print(f"{'Source ID':<12} {'Target ID':<12} {'Name'}")
            print("-" * 80)
            for source_id, target_id, name in rows:
                print(f"{source_id:<12} {target_id:<12} {name}")
        else:
            print("No regression test credential mappings found")

        db.close()
        print()

        return result

    except Exception as e:
        print()
        print("=" * 80)
        print("MIGRATION FAILED!")
        print("=" * 80)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = asyncio.run(test_full_migration())
    sys.exit(0 if result and result.get('phases_failed') == 0 else 1)
