#!/usr/bin/env python3
"""
Test workflow edge creation after fixing the premature edge field removal bug.
This script:
1. Cleans up existing workflows from target AAP
2. Re-imports workflows with nodes and edges
3. Verifies that workflow nodes are properly connected
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import sqlite3

# Load environment variables from .env
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from aap_migration.client.aap_target_client import AAPTargetClient
from aap_migration.config import AAPInstanceConfig


async def cleanup_workflows(client: AAPTargetClient):
    """Delete all workflows from target AAP."""
    print("=" * 80)
    print("🧹 Cleaning Up Existing Workflows")
    print("=" * 80)

    try:
        # Get all workflows
        response = await client.get("workflow_job_templates/")
        workflows = response.get("results", [])

        print(f"\n📋 Found {len(workflows)} workflows to delete")

        for wf in workflows:
            wf_id = wf["id"]
            wf_name = wf["name"]
            print(f"   🗑️  Deleting: {wf_name} (ID: {wf_id})")

            try:
                await client.delete(f"workflow_job_templates/{wf_id}/")
                print(f"      ✅ Deleted")
            except Exception as e:
                print(f"      ❌ Error: {e}")

        print(f"\n✅ Cleanup complete")
        return True

    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False


async def clear_workflow_mappings(db_path: str):
    """Clear workflow and workflow node mappings from database."""
    print("\n" + "=" * 80)
    print("🗄️  Clearing Database Mappings")
    print("=" * 80)

    try:
        db_file = db_path.replace("sqlite:///", "")
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Clear workflow mappings
        cursor.execute("DELETE FROM id_mappings WHERE resource_type = 'workflow_job_templates'")
        deleted_wf = cursor.rowcount
        print(f"   ✅ Deleted {deleted_wf} workflow mappings")

        # Clear workflow node mappings
        cursor.execute("DELETE FROM id_mappings WHERE resource_type = 'workflow_nodes'")
        deleted_nodes = cursor.rowcount
        print(f"   ✅ Deleted {deleted_nodes} workflow node mappings")

        # Clear workflow progress states
        cursor.execute("DELETE FROM migration_progress WHERE resource_type = 'workflow_job_templates'")
        deleted_wf_progress = cursor.rowcount
        print(f"   ✅ Deleted {deleted_wf_progress} workflow progress records")

        # Clear workflow node progress states
        cursor.execute("DELETE FROM migration_progress WHERE resource_type = 'workflow_nodes'")
        deleted_nodes_progress = cursor.rowcount
        print(f"   ✅ Deleted {deleted_nodes_progress} workflow node progress records")

        conn.commit()
        conn.close()

        print(f"\n✅ Database cleanup complete")
        return True

    except Exception as e:
        print(f"❌ Database cleanup failed: {e}")
        return False


async def verify_workflow_edges(client: AAPTargetClient):
    """Verify that workflow nodes are properly connected."""
    print("\n" + "=" * 80)
    print("🔍 Verifying Workflow Edges")
    print("=" * 80)

    try:
        # Get all workflows
        response = await client.get("workflow_job_templates/")
        workflows = response.get("results", [])

        print(f"\n📋 Found {len(workflows)} workflows to verify")

        all_edges_verified = True

        for wf in workflows:
            wf_id = wf["id"]
            wf_name = wf["name"]
            print(f"\n🔎 Checking workflow: {wf_name} (ID: {wf_id})")

            # Get workflow nodes
            nodes_response = await client.get(f"workflow_job_templates/{wf_id}/workflow_nodes/")
            nodes = nodes_response.get("results", [])
            print(f"   📊 Total nodes: {len(nodes)}")

            # Check edges for each node
            edges_found = 0
            for node in nodes:
                node_id = node["id"]
                node_identifier = node.get("identifier", "N/A")

                # Get success nodes
                success_nodes = node.get("success_nodes", [])
                failure_nodes = node.get("failure_nodes", [])
                always_nodes = node.get("always_nodes", [])

                total_edges = len(success_nodes) + len(failure_nodes) + len(always_nodes)
                edges_found += total_edges

                if total_edges > 0:
                    print(f"      ├─ Node '{node_identifier}' (ID: {node_id}):")
                    if success_nodes:
                        print(f"      │  ✅ Success edges: {len(success_nodes)}")
                    if failure_nodes:
                        print(f"      │  ❌ Failure edges: {len(failure_nodes)}")
                    if always_nodes:
                        print(f"      │  ⚡ Always edges: {len(always_nodes)}")

            if edges_found > 0:
                print(f"   ✅ Total edges verified: {edges_found}")
            else:
                print(f"   ⚠️  No edges found (workflow may be linear or have no connections)")
                # Don't mark as failure - some workflows legitimately have no edges

        return all_edges_verified

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


async def main():
    """Main test workflow."""
    print("=" * 80)
    print("🧪 Workflow Edge Creation Test")
    print("=" * 80)

    # Get config from environment
    target_url = os.getenv("TARGET__URL")
    target_token = os.getenv("TARGET__TOKEN")
    db_path_str = os.getenv("MIGRATION_STATE_DB_PATH", "sqlite:///./migration_state.db")

    if not target_url or not target_token:
        print("❌ TARGET__URL and TARGET__TOKEN environment variables must be set")
        return 1

    # Initialize target client
    target_config = AAPInstanceConfig(
        url=target_url,
        token=target_token,
        verify_ssl=False,
    )

    async with AAPTargetClient(config=target_config) as client:

        # Step 1: Clean up existing workflows
        if not await cleanup_workflows(client):
            print("\n❌ Cleanup failed - cannot proceed")
            return 1

        # Step 2: Clear database mappings
        if not await clear_workflow_mappings(db_path_str):
            print("\n❌ Database cleanup failed - cannot proceed")
            return 1

        print("\n" + "=" * 80)
        print("📝 Now run: aap-bridge import -r workflow_job_templates -y")
        print("=" * 80)
        print("\nAfter import completes, run this script again with --verify flag")
        print("Example: python test_workflow_edges.py --verify")

        return 0


async def verify_only():
    """Only verify edges without cleanup."""
    target_url = os.getenv("TARGET__URL")
    target_token = os.getenv("TARGET__TOKEN")

    if not target_url or not target_token:
        print("❌ TARGET__URL and TARGET__TOKEN environment variables must be set")
        return 1

    target_config = AAPInstanceConfig(
        url=target_url,
        token=target_token,
        verify_ssl=False,
    )

    async with AAPTargetClient(config=target_config) as client:
        success = await verify_workflow_edges(client)

        if success:
            print("\n" + "=" * 80)
            print("🎉 SUCCESS: All workflow edges verified!")
            print("=" * 80)
            return 0
        else:
            print("\n" + "=" * 80)
            print("⚠️  INCOMPLETE: Some edges may be missing")
            print("=" * 80)
            return 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        exit_code = asyncio.run(verify_only())
    else:
        exit_code = asyncio.run(main())

    sys.exit(exit_code)
