#!/bin/bash
# Wrapper script to run organization filter test
# Can be run locally (if deps installed) or in container

set -e

# Check if we're in a container (has /app/aap-bridge)
if [ -d "/app/aap-bridge" ]; then
    cd /app/aap-bridge
    python3 test_organization_filters.py "$@"
else
    # Running locally - try to use venv if it exists
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$SCRIPT_DIR"

    # Try to find and activate venv
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    elif [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi

    python3 test_organization_filters.py "$@"
fi
