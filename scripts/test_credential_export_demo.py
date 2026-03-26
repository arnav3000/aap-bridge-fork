#!/usr/bin/env python3
"""
Demo of what the credential export script generates (without needing AAP connection).

This creates sample output so you can see what the migration process produces.
"""

import json
import os
from pathlib import Path
import yaml

# Sample data that would come from source AAP
SAMPLE_CREDENTIALS = [
    {
        "id": 1,
        "name": "Demo SSH Credential",
        "description": "SSH access for demo servers",
        "credential_type": 1,
        "organization": 2,
        "inputs": {
            "username": "admin",
            "password": "$encrypted$",  # Encrypted in source
            "ssh_key_unlock": "$encrypted$"
        }
    },
    {
        "id": 3,
        "name": "GitHub Access Token",
        "description": "GitHub SCM access",
        "credential_type": 2,
        "organization": None,
        "inputs": {
            "username": "github_user",
            "password": "$encrypted$"  # Token is encrypted
        }
    },
    {
        "id": 7,
        "name": "AWS Production Account",
        "description": "AWS credentials for production",
        "credential_type": 4,
        "organization": 3,
        "inputs": {
            "username": "AKIAIOSFODNN7EXAMPLE",
            "password": "$encrypted$"  # Secret key is encrypted
        }
    },
    {
        "id": 12,
        "name": "Automation Hub Token",
        "description": "Galaxy/Hub API access",
        "credential_type": 19,
        "organization": None,
        "inputs": {
            "url": "https://192.168.100.26/api/galaxy/content/validated/",
            "token": "$encrypted$"  # Token is encrypted
        }
    }
]

SAMPLE_CREDENTIAL_TYPES = {
    1: "Machine",
    2: "Source Control",
    4: "Amazon Web Services",
    19: "Ansible Galaxy/Automation Hub API Token"
}

SAMPLE_ORGANIZATIONS = {
    2: "Engineering",
    3: "Operations"
}


def generate_demo_output():
    """Generate demo migration files."""
    print("🎬 DEMO: Credential Export Script Output")
    print("=" * 60)
    print("(This shows what would be generated from a real source AAP)\n")

    # Create output directory
    output_dir = Path("credential_migration_demo")
    output_dir.mkdir(exist_ok=True)

    print(f"📁 Creating demo files in: {output_dir}/\n")

    # Generate playbook
    playbook_tasks = []
    for cred in SAMPLE_CREDENTIALS:
        cred_type_name = SAMPLE_CREDENTIAL_TYPES.get(cred["credential_type"], "Unknown")
        org_name = SAMPLE_ORGANIZATIONS.get(cred["organization"]) if cred["organization"] else None

        inputs = cred.get("inputs", {})
        task_inputs = {}
        secret_placeholders = []

        # Extract non-secret fields
        for field in ["username", "url", "host"]:
            if field in inputs and inputs[field] and inputs[field] != "$encrypted$":
                task_inputs[field] = inputs[field]

        # Mark secret fields
        for field, value in inputs.items():
            if value == "$encrypted$":
                secret_placeholders.append(field)
                task_inputs[field] = f"REPLACE_WITH_ACTUAL_{field.upper()}"

        task = {
            "name": f"Create credential: {cred['name']}",
            "awx.awx.credential": {
                "name": cred["name"],
                "description": cred.get("description", ""),
                "credential_type": cred_type_name,
                "state": "present",
                "controller_host": "{{ target_controller_host }}",
                "controller_oauthtoken": "{{ target_controller_token }}",
                "validate_certs": False,
            }
        }

        if org_name:
            task["awx.awx.credential"]["organization"] = org_name

        if task_inputs:
            task["awx.awx.credential"]["inputs"] = task_inputs

        if secret_placeholders:
            task["# SECRETS_NEEDED"] = f"Fill in: {', '.join(secret_placeholders)}"

        playbook_tasks.append(task)

    playbook = [
        {
            "name": "Migrate Credentials from Source AAP to Target AAP",
            "hosts": "localhost",
            "gather_facts": False,
            "vars": {
                "target_controller_host": "https://localhost:10443",
                "target_controller_token": "{{ lookup('env', 'TARGET__TOKEN') }}"
            },
            "tasks": playbook_tasks
        }
    ]

    # Save playbook
    playbook_file = output_dir / "migrate_credentials.yml"
    with open(playbook_file, 'w') as f:
        f.write("---\n")
        f.write("# DEMO CREDENTIAL MIGRATION PLAYBOOK\n")
        f.write("# This is what the export script generates\n\n")
        yaml.dump(playbook, f, default_flow_style=False, sort_keys=False)

    print(f"✅ Generated: {playbook_file}")

    # Generate secrets template
    secrets = []
    for cred in SAMPLE_CREDENTIALS:
        cred_type_name = SAMPLE_CREDENTIAL_TYPES.get(cred["credential_type"], "Unknown")
        inputs = cred.get("inputs", {})

        secret_fields = {}
        for field, value in inputs.items():
            if value == "$encrypted$":
                secret_fields[field] = "<FILL IN ACTUAL VALUE>"

        if secret_fields:
            secrets.append({
                "credential_name": cred["name"],
                "credential_type": cred_type_name,
                "source_id": cred["id"],
                "secrets": secret_fields,
                "notes": "Get from password manager or admin"
            })

    secrets_file = output_dir / "secrets_template.yml"
    with open(secrets_file, 'w') as f:
        f.write("# CREDENTIAL SECRETS TEMPLATE (DEMO)\n")
        f.write("# Fill in actual values for real migration\n\n")
        yaml.dump({"credentials": secrets}, f, default_flow_style=False, sort_keys=False)

    print(f"✅ Generated: {secrets_file}")

    # Save metadata
    metadata_file = output_dir / "credentials_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump({
            "credentials": SAMPLE_CREDENTIALS,
            "credential_types": SAMPLE_CREDENTIAL_TYPES,
            "organizations": SAMPLE_ORGANIZATIONS
        }, f, indent=2)

    print(f"✅ Generated: {metadata_file}")

    print(f"\n📋 Summary:")
    print(f"   Found: {len(SAMPLE_CREDENTIALS)} credentials")
    print(f"   Types: {len(SAMPLE_CREDENTIAL_TYPES)} credential types")
    print(f"   Orgs: {len(SAMPLE_ORGANIZATIONS)} organizations")

    print(f"\n🔍 Review the generated files:")
    print(f"\n   # View the playbook")
    print(f"   cat {playbook_file}")
    print(f"\n   # View what secrets are needed")
    print(f"   cat {secrets_file}")
    print(f"\n   # View full metadata")
    print(f"   jq '.' {metadata_file}")

    print(f"\n💡 This demonstrates what the real export script generates.")
    print(f"   When connected to actual AAP, it would export all credentials.")

    return output_dir


if __name__ == "__main__":
    output_dir = generate_demo_output()

    print(f"\n✅ Demo completed successfully!")
    print(f"\n📁 Files created in: {output_dir}/")
    print(f"   - migrate_credentials.yml")
    print(f"   - secrets_template.yml")
    print(f"   - credentials_metadata.json")
