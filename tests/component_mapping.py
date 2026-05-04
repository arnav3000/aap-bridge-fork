"""
Test Component Mapping for AAP Bridge

Maps code components (files, functions, features) to test IDs.
Used by AI test agent to intelligently select relevant tests based on code changes.
"""

# File patterns → Test IDs
FILE_TO_TESTS = {
    # Importer - Schedule safety critical
    "importer.py": {
        "ScheduleImporter": ["SCHED-001"],
        "InventorySourceImporter": ["SCHED-001"],  # Has schedule handling
        "ProjectImporter": ["SCHED-001"],  # Has schedule handling
        "JobTemplateImporter": ["SCHED-001"],  # Has schedule handling
        "WorkflowImporter": ["SCHED-001"],  # Has schedule handling
        "batch_precheck_resources": ["STATE-001", "CRED-001"],
        "_resolve_dependencies": ["SCHED-001", "WF-001"],
        "import_resource": ["STATE-001"],  # Base import method
        "survey": ["SURVEY-001"],  # Survey import logic
        "credential": ["CRED-001"],
    },

    # Transformer - Data transformation
    "transformer.py": {
        "ScheduleTransformer": ["SCHED-001"],
        "credential": ["CRED-001"],
        "survey": ["SURVEY-001"],  # Survey transformation
        "SurveyTransformer": ["SURVEY-001"],
    },

    # Exporter - Data collection
    "exporter.py": {
        "survey": ["SURVEY-001"],  # Survey export logic
        "schedule": ["SCHED-001"],
        "credential": ["CRED-001"],
    },

    # State management - Database operations
    "state.py": {
        "mark_completed": ["STATE-001"],
        "mark_skipped": ["CRED-001", "STATE-001"],
        "get_session": ["STATE-001"],
        "save_id_mapping": ["STATE-001"],
    },

    # Migration report - Reporting accuracy
    "migration_report.py": {
        "skipped": ["CRED-001", "REPORT-001"],
        "discrepancy": ["REPORT-001"],
        "generate": ["REPORT-001"],
    },

    # Resources - Resource definitions
    "resources.py": {
        "PARENT_SCOPED_RESOURCES": ["STATE-001"],
        "ORGANIZATION_SCOPED_RESOURCES": ["STATE-001"],
    },

    # Client - API interactions
    "aap_target_client.py": {
        "find_resource_by_name": ["STATE-001", "CRED-001"],
        "post": ["STATE-001"],
        "get": ["STATE-001"],
    },
}

# Critical function patterns → Priority level
CRITICAL_PATTERNS = {
    "enabled": "HIGH",  # Schedule safety (always disable)
    "duplicate": "HIGH",  # Data integrity
    "skipped": "MEDIUM",  # State tracking
    "import_resource": "HIGH",  # Core import logic
    "survey": "MEDIUM",  # Survey migration
    "parent": "HIGH",  # Parent-scoped resources
}

# Test definitions
TESTS = {
    "SCHED-001": {
        "name": "All Schedules Disabled on Import",
        "description": "Verify all schedules imported with enabled=false",
        "script": "tests/scripts/test-schedules-disabled.sh",
        "priority": "HIGH",
        "affected_by": [
            "importer.py (ScheduleImporter)",
            "importer.py (nested schedule creation)",
            "transformer.py (ScheduleTransformer)",
        ],
    },

    "CRED-001": {
        "name": "Duplicate Credential Detection",
        "description": "Verify credentials unique by (name, org, type)",
        "script": "tests/scripts/test-credential-duplicates.sh",
        "priority": "HIGH",
        "affected_by": [
            "importer.py (batch_precheck)",
            "state.py (mark_skipped)",
            "migration_report.py (skipped count)",
        ],
    },

    "STATE-001": {
        "name": "Re-run Import Consistency",
        "description": "Verify re-running import doesn't overwrite 'skipped' status",
        "script": "tests/scripts/test-rerun-consistency.sh",
        "priority": "HIGH",
        "affected_by": [
            "state.py (mark_completed, mark_skipped)",
            "importer.py (import_resource)",
            "importer.py (batch_precheck)",
        ],
    },

    "WF-001": {
        "name": "Workflow Dependency Validation",
        "description": "Verify workflow nodes resolve dependencies correctly",
        "script": "tests/scripts/test-workflow-dependencies.sh",
        "priority": "MEDIUM",
        "affected_by": [
            "importer.py (WorkflowImporter)",
            "importer.py (_resolve_dependencies)",
        ],
    },

    "REPORT-001": {
        "name": "Migration Report Accuracy",
        "description": "Verify migration report shows correct counts",
        "script": "tests/scripts/test-migration-report.sh",
        "priority": "MEDIUM",
        "affected_by": [
            "migration_report.py (all functions)",
            "state.py (mark_* functions)",
        ],
    },

    "SURVEY-001": {
        "name": "Survey Migration Complete",
        "description": "Verify surveys migrate including disabled and password types",
        "script": "tests/scripts/test-survey-migration.sh",
        "priority": "HIGH",
        "affected_by": [
            "exporter.py (survey fetch)",
            "transformer.py (survey cleaning)",
            "importer.py (survey import)",
        ],
    },
}


def get_tests_for_file(filename: str, changed_functions: list[str] = None) -> list[str]:
    """
    Get relevant test IDs for a changed file.

    Args:
        filename: Name of the changed file (e.g., "importer.py")
        changed_functions: List of function names that changed (optional)

    Returns:
        List of test IDs to run
    """
    tests = set()

    if filename not in FILE_TO_TESTS:
        return []

    file_mapping = FILE_TO_TESTS[filename]

    # If no specific functions provided, check for wildcard
    if not changed_functions:
        if "*" in file_mapping:
            tests.update(file_mapping["*"])
        return list(tests)

    # Check each changed function
    for func in changed_functions:
        for pattern, test_ids in file_mapping.items():
            if pattern == "*" or pattern.lower() in func.lower():
                tests.update(test_ids)

    return list(tests)


def get_test_priority(test_id: str) -> str:
    """Get priority level for a test."""
    return TESTS.get(test_id, {}).get("priority", "MEDIUM")


def get_test_info(test_id: str) -> dict:
    """Get full test information."""
    return TESTS.get(test_id, {})
