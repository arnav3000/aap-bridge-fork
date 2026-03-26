#!/usr/bin/env python3
"""
Fill test secrets in the migration playbook for testing purposes.

This replaces all REPLACE_WITH_ACTUAL_* placeholders with test values
so we can validate the migration process.
"""

import re
import sys
from pathlib import Path


def generate_test_secret(field_type):
    """Generate appropriate test value for each secret type."""

    if 'PASSWORD' in field_type:
        return 'TestPassword123!@#'
    elif 'TOKEN' in field_type:
        return 'test_token_' + 'x' * 40
    elif 'SECRET' in field_type:
        return 'test_secret_' + 'y' * 40
    elif 'API_TOKEN' in field_type:
        return 'test_api_token_' + 'z' * 40
    elif 'DB_PASSWORD' in field_type:
        return 'TestDBPass123!@#'
    elif 'GIT_TOKEN' in field_type:
        return 'ghp_' + 'a' * 40  # GitHub token format
    elif 'SNOW_PASSWORD' in field_type:
        return 'TestSnowPass123!@#'
    elif 'SECRET_ID' in field_type:
        return 'test-secret-id-12345'
    elif 'WEBHOOK_URL' in field_type:
        return 'https://test-webhook.example.com/notify'
    else:
        return 'test_value_placeholder'


def fill_test_secrets(playbook_file):
    """Fill all REPLACE_WITH_ACTUAL_* placeholders with test values."""

    print(f"📝 Reading playbook: {playbook_file}")
    with open(playbook_file, 'r') as f:
        content = f.read()

    # Find all unique placeholders
    placeholders = re.findall(r'REPLACE_WITH_ACTUAL_[A-Z_]*', content)
    unique_placeholders = sorted(set(placeholders))

    print(f"\n🔍 Found {len(placeholders)} secret placeholders ({len(unique_placeholders)} unique types)")

    # Replace each placeholder with appropriate test value
    replacements = {}
    for placeholder in unique_placeholders:
        field_type = placeholder.replace('REPLACE_WITH_ACTUAL_', '')
        test_value = generate_test_secret(field_type)
        replacements[placeholder] = test_value
        count = placeholders.count(placeholder)
        print(f"   {placeholder:45s} -> {test_value[:30]:30s} ({count}x)")

    # Perform replacements
    modified_content = content
    for placeholder, test_value in replacements.items():
        modified_content = modified_content.replace(placeholder, test_value)

    # Verify all replacements done
    remaining = re.findall(r'REPLACE_WITH_ACTUAL_[A-Z_]*', modified_content)
    if remaining:
        print(f"\n⚠️  Warning: {len(remaining)} placeholders still remain!")
        for r in set(remaining):
            print(f"   - {r}")

    # Save modified playbook
    output_file = playbook_file.parent / 'migrate_credentials_filled.yml'
    print(f"\n💾 Saving filled playbook to: {output_file}")
    with open(output_file, 'w') as f:
        f.write(modified_content)

    print(f"✅ Successfully filled {len(unique_placeholders)} secret types!")
    print(f"\n📋 Ready to migrate:")
    print(f"   ansible-playbook {output_file}")

    return output_file


def main():
    playbook_file = Path('credential_migration/migrate_credentials.yml')

    if not playbook_file.exists():
        print(f"❌ ERROR: Playbook not found: {playbook_file}")
        sys.exit(1)

    print("🔐 Filling Test Secrets for Migration Testing")
    print("=" * 60)
    print("⚠️  NOTE: Using test values only - not production secrets!\n")

    output_file = fill_test_secrets(playbook_file)

    print("\n" + "=" * 60)
    print("✅ Test secrets filled successfully!")
    print("\n🚀 Next step: Run migration to target AAP")
    print(f"   export TARGET__URL='https://localhost:10443/api/controller/v2'")
    print(f"   export TARGET__TOKEN='<your_target_token>'")
    print(f"   ansible-playbook {output_file}")


if __name__ == '__main__':
    main()
