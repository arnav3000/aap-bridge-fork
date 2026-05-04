#!/usr/bin/env python3
"""
Test Selection Helper for AAP Bridge

Analyzes git changes and recommends relevant tests to run.
Used by AI testing agent to intelligently select tests based on code changes.

Usage:
    # Get tests for current changes
    python tests/select_tests.py

    # Get tests for specific commit
    python tests/select_tests.py --commit abc123

    # Get tests for files changed between commits
    python tests/select_tests.py --base main --head feature-branch
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Add parent directory to path to import component_mapping
sys.path.insert(0, str(Path(__file__).parent))

from component_mapping import (
    FILE_TO_TESTS,
    TESTS,
    get_test_priority,
    get_test_info,
    get_tests_for_file,
)


def get_changed_files(base="HEAD", head=None, commit=None):
    """
    Get list of changed files from git.

    Args:
        base: Base commit/branch to compare against
        head: Head commit/branch (if None, compares working directory)
        commit: Specific commit to analyze (if provided, shows changes in that commit)

    Returns:
        List of changed file paths
    """
    try:
        if commit:
            # Show changes in specific commit
            result = subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit],
                capture_output=True,
                text=True,
                check=True,
            )
        elif head:
            # Compare two commits/branches
            result = subprocess.run(
                ["git", "diff", "--name-only", f"{base}...{head}"],
                capture_output=True,
                text=True,
                check=True,
            )
        else:
            # Compare against working directory (staged + unstaged)
            result = subprocess.run(
                ["git", "diff", "--name-only", base],
                capture_output=True,
                text=True,
                check=True,
            )

        files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        return files
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e}", file=sys.stderr)
        return []


def extract_changed_content(filepath, base="HEAD", head=None, commit=None):
    """
    Extract changed content keywords from a file's diff.

    Args:
        filepath: Path to the file
        base: Base commit to compare against
        head: Head commit (if None, compares working directory)
        commit: Specific commit to analyze

    Returns:
        Set of keywords found in changed lines (lowercase)
    """
    try:
        if commit:
            result = subprocess.run(
                ["git", "diff", f"{commit}^", commit, "--", filepath],
                capture_output=True,
                text=True,
                check=True,
            )
        elif head:
            result = subprocess.run(
                ["git", "diff", f"{base}...{head}", "--", filepath],
                capture_output=True,
                text=True,
                check=True,
            )
        else:
            result = subprocess.run(
                ["git", "diff", base, "--", filepath],
                capture_output=True,
                text=True,
                check=True,
            )

        diff = result.stdout

        # Extract keywords from changed lines (+ or -)
        # Look for patterns like "survey", "credential", "schedule", function names, etc.
        keywords = set()
        for line in diff.split("\n"):
            if line.startswith("+") or line.startswith("-"):
                # Remove diff markers
                content = line[1:].strip().lower()

                # Extract identifiers (words/function names)
                # This will match function names, variable names, strings, comments
                words = re.findall(r'\b\w+\b', content)
                keywords.update(words)

        return keywords
    except subprocess.CalledProcessError as e:
        print(f"Error extracting content from {filepath}: {e}", file=sys.stderr)
        return set()


def select_tests(base="HEAD", head=None, commit=None):
    """
    Select tests based on changed files and functions.

    Args:
        base: Base commit/branch
        head: Head commit/branch
        commit: Specific commit to analyze

    Returns:
        Dict with test recommendations:
        {
            "tests": [test_id, ...],
            "high_priority": [test_id, ...],
            "details": {test_id: test_info, ...}
        }
    """
    changed_files = get_changed_files(base=base, head=head, commit=commit)

    if not changed_files:
        return {
            "tests": [],
            "high_priority": [],
            "details": {},
            "changed_files": [],
        }

    # Map to source files only (filter out non-source files)
    source_files = []
    for filepath in changed_files:
        # Extract just the filename for matching
        filename = Path(filepath).name
        if filename in FILE_TO_TESTS:
            source_files.append((filepath, filename))

    all_tests = set()
    test_details = {}

    # For each changed source file, get relevant tests
    for filepath, filename in source_files:
        # Extract changed content keywords
        keywords = extract_changed_content(filepath, base=base, head=head, commit=commit)

        # Match keywords against patterns in FILE_TO_TESTS
        file_mapping = FILE_TO_TESTS[filename]
        matched_tests = set()

        for pattern, test_ids in file_mapping.items():
            # pattern can be a function name, keyword like "survey", or "*"
            if pattern == "*":
                # Wildcard - always matches
                matched_tests.update(test_ids)
            else:
                # Check if pattern matches any keyword
                # Support both exact matches and substring matches
                pattern_lower = pattern.lower()
                for keyword in keywords:
                    # Match if pattern is in keyword OR keyword is in pattern
                    # e.g., "schedule" matches "schedules", "ScheduleImporter" matches "schedule"
                    if pattern_lower in keyword or keyword in pattern_lower:
                        matched_tests.update(test_ids)
                        break

        for test_id in matched_tests:
            all_tests.add(test_id)
            if test_id not in test_details:
                test_details[test_id] = get_test_info(test_id)

    # Separate by priority
    high_priority = [t for t in all_tests if get_test_priority(t) == "HIGH"]
    medium_priority = [t for t in all_tests if get_test_priority(t) == "MEDIUM"]

    # Sort: high priority first, then medium
    sorted_tests = sorted(high_priority) + sorted(medium_priority)

    return {
        "tests": sorted_tests,
        "high_priority": high_priority,
        "details": test_details,
        "changed_files": [f for f, _ in source_files],
    }


def format_test_report(selection_result):
    """Format test selection results as readable report."""
    tests = selection_result["tests"]
    high_priority = selection_result["high_priority"]
    details = selection_result["details"]
    changed_files = selection_result["changed_files"]

    report = []
    report.append("=" * 80)
    report.append("TEST SELECTION REPORT")
    report.append("=" * 80)
    report.append("")

    if not tests:
        report.append("✓ No tests needed - changes don't affect tested components")
        report.append("")
        return "\n".join(report)

    report.append(f"Changed files ({len(changed_files)}):")
    for f in changed_files:
        report.append(f"  - {f}")
    report.append("")

    report.append(f"Recommended tests ({len(tests)} total):")
    report.append("")

    # High priority tests
    if high_priority:
        report.append("🔴 HIGH PRIORITY:")
        for test_id in sorted(high_priority):
            info = details[test_id]
            report.append(f"  [{test_id}] {info['name']}")
            report.append(f"      {info['description']}")
            report.append(f"      Script: {info['script']}")
        report.append("")

    # Medium priority tests
    medium = [t for t in tests if t not in high_priority]
    if medium:
        report.append("🟡 MEDIUM PRIORITY:")
        for test_id in sorted(medium):
            info = details[test_id]
            report.append(f"  [{test_id}] {info['name']}")
            report.append(f"      {info['description']}")
            report.append(f"      Script: {info['script']}")
        report.append("")

    report.append("=" * 80)
    report.append(f"Run tests: {len(tests)} | High priority: {len(high_priority)}")
    report.append("=" * 80)

    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="Select tests based on git changes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check current uncommitted changes
  python tests/select_tests.py

  # Check specific commit
  python tests/select_tests.py --commit abc123

  # Check changes between branches
  python tests/select_tests.py --base main --head feature-branch

  # Output just test IDs (for scripting)
  python tests/select_tests.py --output ids
        """,
    )

    parser.add_argument(
        "--base",
        default="HEAD",
        help="Base commit/branch to compare against (default: HEAD)",
    )
    parser.add_argument(
        "--head",
        default=None,
        help="Head commit/branch (default: working directory)",
    )
    parser.add_argument(
        "--commit",
        default=None,
        help="Specific commit to analyze",
    )
    parser.add_argument(
        "--output",
        choices=["report", "ids", "scripts"],
        default="report",
        help="Output format (default: report)",
    )

    args = parser.parse_args()

    # Select tests
    result = select_tests(base=args.base, head=args.head, commit=args.commit)

    # Output based on format
    if args.output == "report":
        print(format_test_report(result))
    elif args.output == "ids":
        print("\n".join(result["tests"]))
    elif args.output == "scripts":
        for test_id in result["tests"]:
            script = result["details"][test_id]["script"]
            print(script)

    # Exit code: 0 if no tests, 1 if tests recommended
    sys.exit(1 if result["tests"] else 0)


if __name__ == "__main__":
    main()
