#!/usr/bin/env python3
"""
Database State Reconciliation Tool

Fixes inconsistencies between migration database state and actual target AAP state.
This ensures the database accurately reflects what exists on the target.

Usage:
    python3 reconcile_database_state.py --resource-type credentials
    python3 reconcile_database_state.py --all
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from aap_migration.client.aap_target_client import AAPTargetClient
from aap_migration.config import AAPInstanceConfig, StateConfig
from aap_migration.migration.state import MigrationState
from aap_migration.migration.database import get_session
from aap_migration.migration.models import MigrationProgress, IDMapping
import os


async def reconcile_credentials(client: AAPTargetClient, state: MigrationState, dry_run: bool = False):
    """Reconcile credential migration state with actual target state."""

    print("\n" + "=" * 70)
    print("CREDENTIAL MIGRATION STATE RECONCILIATION")
    print("=" * 70)

    # Get all credential records from database
    with get_session(state.database_url) as session:
        # Get migration_progress entries
        db_records = session.query(
            MigrationProgress.source_id,
            MigrationProgress.source_name,
            MigrationProgress.target_id,
            MigrationProgress.status,
            MigrationProgress.error_message
        ).filter(
            MigrationProgress.resource_type == "credentials"
        ).order_by(MigrationProgress.source_id).all()

        # Get id_mappings entries
        id_mapping_records = session.query(
            IDMapping.source_id,
            IDMapping.target_id
        ).filter(
            IDMapping.resource_type == "credentials"
        ).all()

        id_mappings = {row[0]: row[1] for row in id_mapping_records}

        print(f"\n📊 Database State:")
        print(f"  - migration_progress entries: {len(db_records)}")
        print(f"  - id_mappings entries: {len(id_mappings)}")

    # Fetch all credentials from target
    print(f"\n🔍 Fetching credentials from target AAP...")
    all_target_credentials = []
    page = 1
    while True:
        result = await client.get("credentials/", params={"page": page, "page_size": 200})
        all_target_credentials.extend(result.get("results", []))
        if not result.get("next"):
            break
        page += 1

    # Build lookup: name -> target_id
    target_by_name = {cred["name"]: cred["id"] for cred in all_target_credentials}
    target_by_id = {cred["id"]: cred for cred in all_target_credentials}

    print(f"  - Total credentials on target: {len(all_target_credentials)}")

    # Analyze inconsistencies
    fixes_needed = []

    print(f"\n🔎 Analyzing inconsistencies...")
    print(f"-" * 70)

    for db_row in db_records:
        source_id, source_name, db_target_id, status, error_msg = db_row
        mapped_target_id = id_mappings.get(source_id)

        # Check if credential exists on target
        actual_target_id = target_by_name.get(source_name)

        # Case 1: Status is "in_progress" but credential exists on target
        if status == "in_progress" and actual_target_id:
            fixes_needed.append({
                "type": "mark_completed",
                "source_id": source_id,
                "source_name": source_name,
                "target_id": actual_target_id,
                "reason": f"Status '{status}' but credential exists on target",
            })
            print(f"❌ {source_name} (source:{source_id})")
            print(f"   Status: {status} → Should be 'completed'")
            print(f"   Target ID: {actual_target_id}")
            print(f"   Fix: Mark as completed")
            print()

        # Case 2: Status is "pending" but credential exists on target
        elif status == "pending" and actual_target_id:
            fixes_needed.append({
                "type": "mark_completed",
                "source_id": source_id,
                "source_name": source_name,
                "target_id": actual_target_id,
                "reason": f"Status '{status}' but credential exists on target",
            })
            print(f"❌ {source_name} (source:{source_id})")
            print(f"   Status: {status} → Should be 'completed'")
            print(f"   Target ID: {actual_target_id}")
            print(f"   Fix: Mark as completed")
            print()

        # Case 3: Status is "in_progress" and credential does NOT exist
        elif status == "in_progress" and not actual_target_id:
            fixes_needed.append({
                "type": "mark_failed",
                "source_id": source_id,
                "source_name": source_name,
                "reason": f"Status '{status}' but credential not found on target",
            })
            print(f"❌ {source_name} (source:{source_id})")
            print(f"   Status: {status} → Should be 'failed'")
            print(f"   Reason: Credential not found on target")
            print(f"   Fix: Mark as failed, remove NULL ID mapping")
            print()

        # Case 4: ID mapping has NULL target_id but credential exists
        elif mapped_target_id is None and actual_target_id:
            fixes_needed.append({
                "type": "update_mapping",
                "source_id": source_id,
                "source_name": source_name,
                "target_id": actual_target_id,
                "reason": "ID mapping has NULL target_id but credential exists",
            })
            print(f"❌ {source_name} (source:{source_id})")
            print(f"   ID mapping: NULL → Should be {actual_target_id}")
            print(f"   Fix: Update ID mapping")
            print()

        # Case 5: Status is "completed" but credential not found on target
        elif status == "completed" and not actual_target_id:
            print(f"⚠️  {source_name} (source:{source_id})")
            print(f"   Status: {status} but credential NOT on target")
            print(f"   This may indicate manual deletion on target")
            print()

    # Summary
    print("=" * 70)
    print(f"\n📋 Summary:")
    print(f"  - Inconsistencies found: {len(fixes_needed)}")

    if not fixes_needed:
        print(f"\n✅ Database state is consistent with target!")
        return

    print(f"\n🔧 Fixes to apply:")
    fix_types = {}
    for fix in fixes_needed:
        fix_types[fix['type']] = fix_types.get(fix['type'], 0) + 1
    for fix_type, count in fix_types.items():
        print(f"  - {fix_type}: {count}")

    if dry_run:
        print(f"\n⚠️  DRY RUN MODE - No changes will be made")
        return

    # Ask for confirmation
    print()
    confirm = input("Apply these fixes? (yes/no): ")
    if confirm.lower() != "yes":
        print("Reconciliation cancelled.")
        return

    # Apply fixes
    print(f"\n🔨 Applying fixes...")
    fixed_count = 0

    for fix in fixes_needed:
        if fix['type'] == "mark_completed":
            # Update migration_progress to completed
            state.mark_completed(
                resource_type="credentials",
                source_id=fix['source_id'],
                target_id=fix['target_id'],
                target_name=fix['source_name'],
            )
            print(f"  ✓ Marked as completed: {fix['source_name']}")
            fixed_count += 1

        elif fix['type'] == "mark_failed":
            # Update migration_progress to failed
            state.mark_failed(
                resource_type="credentials",
                source_id=fix['source_id'],
                error_message="Reconciliation: Credential not found on target after in_progress status",
            )
            print(f"  ✓ Marked as failed: {fix['source_name']}")
            fixed_count += 1

        elif fix['type'] == "update_mapping":
            # Use state method to save mapping (will update if exists)
            state.save_id_mapping(
                resource_type="credentials",
                source_id=fix['source_id'],
                target_id=fix['target_id'],
                source_name=fix['source_name'],
                target_name=fix['source_name'],
            )
            print(f"  ✓ Updated ID mapping: {fix['source_name']} → {fix['target_id']}")
            fixed_count += 1

    print(f"\n✅ Applied {fixed_count} fixes!")

    # Show final status
    with get_session(state.database_url) as session:
        from sqlalchemy import func
        final_status = session.query(
            MigrationProgress.status,
            func.count(MigrationProgress.id).label('count')
        ).filter(
            MigrationProgress.resource_type == "credentials"
        ).group_by(MigrationProgress.status).all()

        print(f"\n📊 Final Credential Migration Status:")
        for status, count in final_status:
            print(f"  - {status}: {count}")


async def main():
    parser = argparse.ArgumentParser(description="Reconcile migration database with target AAP")
    parser.add_argument(
        "--resource-type",
        choices=["credentials", "all"],
        default="credentials",
        help="Resource type to reconcile (default: credentials)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fixed without making changes"
    )

    args = parser.parse_args()

    # Initialize client and state
    target_config = AAPInstanceConfig(
        url=os.getenv("TARGET__URL"),
        token=os.getenv("TARGET__TOKEN"),
        verify_ssl=False,
        timeout=30
    )

    state_config = StateConfig(db_path=os.getenv("MIGRATION_STATE_DB_PATH", "sqlite:///./migration_state.db"))

    client = AAPTargetClient(target_config)
    state = MigrationState(state_config)

    try:
        if args.resource_type == "credentials" or args.resource_type == "all":
            await reconcile_credentials(client, state, dry_run=args.dry_run)

        if args.resource_type == "all":
            print("\n⚠️  Only credential reconciliation implemented for now")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
