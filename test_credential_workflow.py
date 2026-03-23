#!/usr/bin/env python3
"""Quick validation script for credential-first workflow implementation."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_imports():
    """Test that all new modules can be imported."""
    print("Testing imports...")

    try:
        from aap_migration.migration.credential_comparator import (
            CredentialComparator,
            CredentialComparisonResult,
            CredentialDiff,
        )

        print("✓ credential_comparator module imports successfully")
    except Exception as e:
        print(f"✗ Failed to import credential_comparator: {e}")
        return False

    try:
        from aap_migration.cli.commands.credentials import credentials

        print("✓ credentials CLI commands import successfully")
    except Exception as e:
        print(f"✗ Failed to import credentials commands: {e}")
        return False

    try:
        from aap_migration.migration.coordinator import MigrationCoordinator

        print("✓ coordinator imports successfully (with credential integration)")
    except Exception as e:
        print(f"✗ Failed to import coordinator: {e}")
        return False

    return True


def test_coordinator_has_method():
    """Test that coordinator has the new method."""
    print("\nTesting coordinator integration...")

    try:
        from aap_migration.migration.coordinator import MigrationCoordinator

        # Check if method exists
        if hasattr(MigrationCoordinator, "compare_and_verify_credentials"):
            print("✓ MigrationCoordinator.compare_and_verify_credentials() exists")
        else:
            print("✗ MigrationCoordinator missing compare_and_verify_credentials()")
            return False

        # Check if MIGRATION_PHASES has credentials early
        phases = MigrationCoordinator.MIGRATION_PHASES
        phase_names = [p["name"] for p in phases]

        if "credentials" in phase_names:
            cred_idx = phase_names.index("credentials")
            org_idx = phase_names.index("organizations")

            if cred_idx == org_idx + 1:
                print("✓ Credentials phase is immediately after organizations")
            else:
                print(
                    f"✗ Credentials phase is at position {cred_idx}, "
                    f"organizations at {org_idx}"
                )
                return False
        else:
            print("✗ Credentials phase not found in MIGRATION_PHASES")
            return False

    except Exception as e:
        print(f"✗ Error testing coordinator: {e}")
        return False

    return True


def test_cli_registration():
    """Test that CLI commands are registered."""
    print("\nTesting CLI registration...")

    try:
        from aap_migration.cli.main import cli

        # Get registered commands
        commands = cli.commands

        if "credentials" in commands:
            print("✓ 'credentials' command group registered in CLI")

            # Check subcommands
            cred_cmd = commands["credentials"]
            subcommands = cred_cmd.commands

            expected_subcommands = ["compare", "migrate", "report"]
            for subcmd in expected_subcommands:
                if subcmd in subcommands:
                    print(f"✓ 'credentials {subcmd}' subcommand exists")
                else:
                    print(f"✗ 'credentials {subcmd}' subcommand missing")
                    return False
        else:
            print("✗ 'credentials' command not registered in CLI")
            return False

    except Exception as e:
        print(f"✗ Error testing CLI registration: {e}")
        return False

    return True


def test_documentation_exists():
    """Test that documentation files exist."""
    print("\nTesting documentation...")

    docs = [
        "CREDENTIAL-FIRST-WORKFLOW.md",
        "CREDENTIAL-FIRST-IMPLEMENTATION-SUMMARY.md",
    ]

    all_exist = True
    for doc in docs:
        doc_path = Path(__file__).parent / doc
        if doc_path.exists():
            print(f"✓ {doc} exists")
        else:
            print(f"✗ {doc} not found")
            all_exist = False

    return all_exist


def main():
    """Run all validation tests."""
    print("=" * 70)
    print("CREDENTIAL-FIRST WORKFLOW - VALIDATION")
    print("=" * 70)

    results = []

    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Coordinator Integration", test_coordinator_has_method()))
    results.append(("CLI Registration", test_cli_registration()))
    results.append(("Documentation", test_documentation_exists()))

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:30} {status}")
        if not passed:
            all_passed = False

    print("=" * 70)

    if all_passed:
        print("\n✓ ALL TESTS PASSED - Implementation is ready!")
        print("\nNext steps:")
        print("  1. Run: aap-bridge credentials compare")
        print("  2. Run: aap-bridge credentials migrate --dry-run")
        print("  3. Run: aap-bridge migrate full")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED - Please review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
