#!/usr/bin/env python3
"""
Generate a migration playbook that uses direct API calls instead of awx.awx collection.
This works around Platform Gateway path issues in awx.awx collection.
"""

import json
import yaml
from pathlib import Path


def convert_to_direct_api_playbook(filled_playbook_path, output_path):
    """Convert awx.awx.credential tasks to direct API uri tasks."""

    print(f"📝 Reading filled playbook: {filled_playbook_path}")
    with open(filled_playbook_path, 'r') as f:
        playbook_data = yaml.safe_load(f)

    play = playbook_data[0]
    original_tasks = play['tasks']

    print(f"🔄 Converting {len(original_tasks)} tasks to direct API calls...")

    # Update vars
    play['vars'] = {
        'target_controller_url': 'https://localhost:10443/api/controller/v2',
        'target_controller_token': "{{ lookup('env', 'TARGET__TOKEN') }}"
    }

    new_tasks = []

    # First, get credential type mappings
    new_tasks.append({
        'name': 'Get credential types from target AAP',
        'uri': {
            'url': '{{ target_controller_url }}/credential_types/',
            'method': 'GET',
            'headers': {
                'Authorization': 'Bearer {{ target_controller_token }}',
                'Content-Type': 'application/json'
            },
            'validate_certs': False,
            'status_code': 200
        },
        'register': 'credential_types_response'
    })

    new_tasks.append({
        'name': 'Build credential type name to ID mapping',
        'set_fact': {
            'credential_type_map': "{{ dict(credential_types_response.json.results | map(attribute='name') | zip(credential_types_response.json.results | map(attribute='id'))) }}"
        }
    })

    # Get organizations
    new_tasks.append({
        'name': 'Get organizations from target AAP',
        'uri': {
            'url': '{{ target_controller_url }}/organizations/',
            'method': 'GET',
            'headers': {
                'Authorization': 'Bearer {{ target_controller_token }}',
                'Content-Type': 'application/json'
            },
            'validate_certs': False,
            'status_code': 200
        },
        'register': 'organizations_response'
    })

    new_tasks.append({
        'name': 'Build organization name to ID mapping',
        'set_fact': {
            'organization_map': "{{ dict(organizations_response.json.results | map(attribute='name') | zip(organizations_response.json.results | map(attribute='id'))) }}"
        }
    })

    # Convert each credential task
    for idx, task in enumerate(original_tasks, 1):
        awx_params = task.get('awx.awx.credential', {})

        cred_name = awx_params.get('name', 'Unknown')
        cred_desc = awx_params.get('description', '')
        cred_type_name = awx_params.get('credential_type', 'Machine')
        org_name = awx_params.get('organization')
        inputs = awx_params.get('inputs', {})

        # Build API payload
        payload = {
            'name': cred_name,
            'description': cred_desc,
            'credential_type': f"{{{{ credential_type_map['{cred_type_name}'] | default(1) }}}}",
        }

        if org_name:
            payload['organization'] = f"{{{{ organization_map['{org_name}'] | default(omit) }}}}"

        if inputs:
            payload['inputs'] = inputs

        # Create task with direct API call
        new_task = {
            'name': f"Create credential: {cred_name}",
            'uri': {
                'url': '{{ target_controller_url }}/credentials/',
                'method': 'POST',
                'headers': {
                    'Authorization': 'Bearer {{ target_controller_token }}',
                    'Content-Type': 'application/json'
                },
                'body': payload,
                'body_format': 'json',
                'validate_certs': False,
                'status_code': [201, 400]  # 400 might be duplicate
            },
            'register': f'credential_{idx}_result',
            'failed_when': f"credential_{idx}_result.status not in [201, 400]"
        }

        new_tasks.append(new_task)

        # Add debug task for conflicts/duplicates
        new_tasks.append({
            'name': f"Show result for: {cred_name}",
            'debug': {
                'msg': f"{{{{ credential_{idx}_result.status == 201 and 'Created' or 'Already exists or error' }}}}"
            }
        })

    play['tasks'] = new_tasks

    # Save new playbook
    print(f"💾 Saving direct API playbook to: {output_path}")
    with open(output_path, 'w') as f:
        f.write("---\n")
        f.write("# CREDENTIAL MIGRATION PLAYBOOK - Direct API Version\n")
        f.write("# Uses direct REST API calls to work with AAP 2.6 Platform Gateway\n\n")
        yaml.dump([play], f, default_flow_style=False, sort_keys=False, width=120)

    print(f"✅ Generated playbook with {len(new_tasks)} tasks")
    print(f"   ({len(original_tasks)} credential tasks + 4 setup tasks + {len(original_tasks)} debug tasks)")

    return output_path


def main():
    filled_playbook = Path('credential_migration/migrate_credentials_filled.yml')
    output_playbook = Path('credential_migration/migrate_credentials_direct_api.yml')

    if not filled_playbook.exists():
        print(f"❌ ERROR: Filled playbook not found: {filled_playbook}")
        return 1

    print("🔄 Converting awx.awx playbook to direct API playbook")
    print("=" * 70)
    print()

    output_path = convert_to_direct_api_playbook(filled_playbook, output_playbook)

    print()
    print("=" * 70)
    print("✅ Direct API playbook generated successfully!")
    print()
    print("🚀 Run migration:")
    print(f"   export TARGET__TOKEN='<your_token>'")
    print(f"   ansible-playbook {output_path}")


if __name__ == '__main__':
    main()
