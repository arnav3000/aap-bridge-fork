#!/usr/bin/env python3
"""
AAP Organization Filter API Testing Script

This script tests various AAP API filters to determine what filtering
strategies are supported for organization-based migration.

Usage:
    python test_organization_filters.py --org-name "Engineering"
    python test_organization_filters.py --org-id 5
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from aap_migration.client.aap_source_client import AAPSourceClient
from aap_migration.config import AAPInstanceConfig


class OrganizationFilterTester:
    """Test AAP API organization filtering capabilities."""

    def __init__(self, client: AAPSourceClient, org_id: int, org_name: str):
        self.client = client
        self.org_id = org_id
        self.org_name = org_name
        self.results = []

    async def test_filter(
        self,
        resource_type: str,
        endpoint: str,
        filter_params: dict,
        description: str,
    ) -> dict:
        """Test a specific filter and return results."""
        print(f"  Testing: {description}")

        try:
            response = await self.client.get(
                endpoint,
                params={**filter_params, "page_size": 1}
            )
            count = response.get("count", 0)

            result = {
                "resource_type": resource_type,
                "endpoint": endpoint,
                "filter": filter_params,
                "description": description,
                "status": "✅ SUCCESS",
                "count": count,
                "error": None,
            }
            print(f"    → {count} resources found")

        except Exception as e:
            result = {
                "resource_type": resource_type,
                "endpoint": endpoint,
                "filter": filter_params,
                "description": description,
                "status": "❌ FAILED",
                "count": None,
                "error": str(e),
            }
            print(f"    → Error: {e}")

        self.results.append(result)
        return result

    async def run_all_tests(self):
        """Run all organization filter tests."""
        print("=" * 70)
        print("AAP Organization Filter API Tests")
        print("=" * 70)
        print(f"Organization: {self.org_name} (ID: {self.org_id})")
        print(f"Started: {datetime.now().isoformat()}")
        print("=" * 70)
        print()

        # Test 1: Organizations
        print("1. Testing Organizations")
        await self.test_filter(
            "organizations",
            "organizations/",
            {"id": self.org_id},
            "Filter by exact ID"
        )
        await self.test_filter(
            "organizations",
            "organizations/",
            {"name": self.org_name},
            "Filter by exact name"
        )
        print()

        # Test 2: Projects
        print("2. Testing Projects")
        await self.test_filter(
            "projects",
            "projects/",
            {"organization": self.org_id},
            "Filter by organization ID"
        )
        await self.test_filter(
            "projects",
            "projects/",
            {"organization__name": self.org_name},
            "Filter by organization name"
        )
        print()

        # Test 3: Inventories
        print("3. Testing Inventories")
        await self.test_filter(
            "inventories",
            "inventories/",
            {"organization": self.org_id},
            "Filter by organization ID"
        )
        print()

        # Test 4: Credentials
        print("4. Testing Credentials")
        await self.test_filter(
            "credentials",
            "credentials/",
            {"organization": self.org_id},
            "Filter by organization ID (org-scoped only)"
        )
        await self.test_filter(
            "credentials",
            "credentials/",
            {"organization__isnull": "true"},
            "Filter for global credentials (organization=null)"
        )
        print()

        # Test 5: Teams
        print("5. Testing Teams")
        await self.test_filter(
            "teams",
            "teams/",
            {"organization": self.org_id},
            "Filter by organization ID"
        )
        print()

        # Test 6: Job Templates
        print("6. Testing Job Templates")
        await self.test_filter(
            "job_templates",
            "job_templates/",
            {"organization": self.org_id},
            "Filter by organization ID (direct)"
        )
        await self.test_filter(
            "job_templates",
            "job_templates/",
            {"project__organization": self.org_id},
            "Filter by project__organization"
        )
        print()

        # Test 7: Workflow Job Templates
        print("7. Testing Workflow Job Templates")
        await self.test_filter(
            "workflow_job_templates",
            "workflow_job_templates/",
            {"organization": self.org_id},
            "Filter by organization ID (direct)"
        )
        print()

        # Test 8: Hosts (parent-scoped)
        print("8. Testing Hosts (parent-scoped)")
        await self.test_filter(
            "hosts",
            "hosts/",
            {"inventory__organization": self.org_id},
            "Filter by inventory__organization"
        )
        print()

        # Test 9: Inventory Groups (parent-scoped)
        print("9. Testing Inventory Groups (parent-scoped)")
        await self.test_filter(
            "groups",
            "groups/",
            {"inventory__organization": self.org_id},
            "Filter by inventory__organization"
        )
        print()

        # Test 10: Inventory Sources (parent-scoped)
        print("10. Testing Inventory Sources (parent-scoped)")
        await self.test_filter(
            "inventory_sources",
            "inventory_sources/",
            {"inventory__organization": self.org_id},
            "Filter by inventory__organization"
        )
        print()

        # Test 11: Users
        print("11. Testing Users")
        await self.test_filter(
            "users",
            "users/",
            {"organizations": self.org_id},
            "Filter by organization membership"
        )
        await self.test_filter(
            "users",
            "users/",
            {"organizations__name": self.org_name},
            "Filter by organization name"
        )
        print()

        # Test 12: Schedules
        print("12. Testing Schedules")
        await self.test_filter(
            "schedules",
            "schedules/",
            {"unified_job_template__organization": self.org_id},
            "Filter by unified_job_template__organization"
        )
        print()

        # Test 13: Multiple Organizations (with id__in)
        print("13. Testing Multiple Organizations")
        # Use org_id and org_id+1 (might not exist, but tests syntax)
        await self.test_filter(
            "organizations",
            "organizations/",
            {"id__in": f"{self.org_id},{self.org_id+1}"},
            "Filter by id__in (multiple org IDs)"
        )
        await self.test_filter(
            "projects",
            "projects/",
            {"organization__in": f"{self.org_id},{self.org_id+1}"},
            "Filter by organization__in (multiple orgs)"
        )
        print()

    def generate_report(self) -> str:
        """Generate markdown report of test results."""
        lines = [
            "# AAP Organization Filter API Test Results",
            "",
            f"**Organization:** {self.org_name} (ID: {self.org_id})",
            f"**Test Date:** {datetime.now().isoformat()}",
            "",
            "## Summary",
            "",
        ]

        # Count successes and failures
        successful = [r for r in self.results if r["status"] == "✅ SUCCESS"]
        failed = [r for r in self.results if r["status"] == "❌ FAILED"]

        lines.extend([
            f"- **Total Tests:** {len(self.results)}",
            f"- **Successful:** {len(successful)}",
            f"- **Failed:** {len(failed)}",
            "",
            "---",
            "",
        ])

        # Successful filters
        if successful:
            lines.extend([
                "## ✅ Supported Filters (Working)",
                "",
                "| Resource Type | Filter | Count | Description |",
                "|---------------|--------|-------|-------------|",
            ])
            for r in successful:
                filter_str = ", ".join(f"{k}={v}" for k, v in r["filter"].items())
                lines.append(
                    f"| {r['resource_type']} | `{filter_str}` | {r['count']} | {r['description']} |"
                )
            lines.append("")

        # Failed filters
        if failed:
            lines.extend([
                "## ❌ Unsupported Filters (Failed)",
                "",
                "| Resource Type | Filter | Error | Description |",
                "|---------------|--------|-------|-------------|",
            ])
            for r in failed:
                filter_str = ", ".join(f"{k}={v}" for k, v in r["filter"].items())
                error_short = r["error"][:60] + "..." if len(r["error"]) > 60 else r["error"]
                lines.append(
                    f"| {r['resource_type']} | `{filter_str}` | {error_short} | {r['description']} |"
                )
            lines.append("")

        # Recommendations
        lines.extend([
            "---",
            "",
            "## Recommendations for Implementation",
            "",
        ])

        # Analyze results and provide recommendations
        org_scoped_working = any(
            r["resource_type"] in ["projects", "inventories", "credentials", "teams"]
            and r["status"] == "✅ SUCCESS"
            and "organization" in r["filter"]
            for r in successful
        )

        parent_scoped_working = any(
            r["resource_type"] in ["hosts", "groups", "inventory_sources"]
            and r["status"] == "✅ SUCCESS"
            and "inventory__organization" in r["filter"]
            for r in successful
        )

        if org_scoped_working:
            lines.append("✅ **Organization-scoped resources** can be filtered directly using `organization=<id>`")
        else:
            lines.append("❌ **WARNING:** Organization filtering may not work as expected")

        if parent_scoped_working:
            lines.append("✅ **Parent-scoped resources** (hosts, groups) can be filtered using `inventory__organization=<id>`")
        else:
            lines.append("⚠️ **Parent-scoped resources** may need two-step filtering (get inventory IDs first)")

        # Check if global credentials filter works
        global_creds = next(
            (r for r in successful if r["resource_type"] == "credentials" and "isnull" in str(r["filter"])),
            None
        )
        if global_creds:
            lines.append("✅ **Global credentials** can be filtered using `organization__isnull=true`")
            lines.append("   → **Strategy:** Use two-pass export (org credentials + global credentials)")

        lines.extend([
            "",
            "---",
            "",
            "## Next Steps",
            "",
            "1. Review which filters are supported",
            "2. Design implementation strategy based on working filters",
            "3. Handle unsupported filters with alternative approaches (two-step queries, etc.)",
            "",
        ])

        return "\n".join(lines)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test AAP API organization filtering capabilities"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--org-name",
        type=str,
        help="Organization name to test (will be resolved to ID)",
    )
    group.add_argument(
        "--org-id",
        type=int,
        help="Organization ID to test",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="org_filter_test_results.md",
        help="Output file for test results (default: org_filter_test_results.md)",
    )

    args = parser.parse_args()

    # Load environment variables
    source_url = os.getenv("SOURCE__URL") or os.getenv("SOURCE__BASE_URL")
    source_token = os.getenv("SOURCE__TOKEN")

    if not source_url or not source_token:
        print("ERROR: SOURCE__URL and SOURCE__TOKEN environment variables must be set")
        print()
        print("Example:")
        print("  export SOURCE__URL=https://aap24.example.com")
        print("  export SOURCE__TOKEN=your_api_token_here")
        print("  python test_organization_filters.py --org-name 'Engineering'")
        return 1

    # Initialize client
    print("Connecting to AAP source...")
    config = AAPInstanceConfig(
        url=source_url,
        token=source_token,
        verify_ssl=False,
        timeout=30,
    )
    client = AAPSourceClient(config=config)

    # Resolve organization name to ID if needed
    if args.org_name:
        print(f"Resolving organization '{args.org_name}' to ID...")
        response = await client.get("organizations/", params={"name": args.org_name})
        results = response.get("results", [])

        if not results:
            print(f"ERROR: Organization '{args.org_name}' not found")
            return 1

        if len(results) > 1:
            print(f"WARNING: Multiple organizations found with name '{args.org_name}':")
            for org in results:
                print(f"  - ID {org['id']}: {org['name']}")
            print("Please use --org-id to specify which one to test")
            return 1

        org_id = results[0]["id"]
        org_name = results[0]["name"]
        print(f"✓ Found organization: {org_name} (ID: {org_id})")
    else:
        org_id = args.org_id
        # Fetch org name from ID
        response = await client.get(f"organizations/{org_id}/")
        org_name = response.get("name", f"Org-{org_id}")
        print(f"✓ Testing organization: {org_name} (ID: {org_id})")

    print()

    # Run tests
    tester = OrganizationFilterTester(client, org_id, org_name)
    await tester.run_all_tests()

    # Generate report
    print()
    print("=" * 70)
    print("Generating Report")
    print("=" * 70)

    report = tester.generate_report()

    # Save report
    output_path = Path(args.output)
    with open(output_path, "w") as f:
        f.write(report)

    print(f"✓ Report saved to: {output_path}")
    print()

    # Also save JSON results
    json_path = output_path.with_suffix(".json")
    with open(json_path, "w") as f:
        json.dump(tester.results, f, indent=2)

    print(f"✓ JSON results saved to: {json_path}")
    print()

    # Print summary
    successful = [r for r in tester.results if r["status"] == "✅ SUCCESS"]
    failed = [r for r in tester.results if r["status"] == "❌ FAILED"]

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total Tests:  {len(tester.results)}")
    print(f"Successful:   {len(successful)}")
    print(f"Failed:       {len(failed)}")
    print("=" * 70)

    if failed:
        print()
        print("⚠️  Some filters failed. Review the report for details.")
        print(f"   Report: {output_path}")
    else:
        print()
        print("✅ All filters passed!")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
