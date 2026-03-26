#!/bin/bash
# Debug script to manually create the failing Galaxy/Hub credentials

export TARGET__TOKEN=$(grep "^TARGET__TOKEN" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")

# Galaxy/Hub Token 47 - should use org "Global Engineering" (ID 6 in target)
echo "🧪 Creating Galaxy/Hub Token 47 manually..."
curl -sk -X POST \
  -H "Authorization: Bearer $TARGET__TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Galaxy/Hub Token 47",
    "description": "Automation Hub API token",
    "credential_type": 19,
    "organization": 6,
    "inputs": {
      "url": "https://console.redhat.com/api/automation-hub/",
      "token": "test_token_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    }
  }' \
  "https://localhost:10443/api/controller/v2/credentials/" | jq '.'

echo
echo "🧪 Creating Galaxy/Hub Token 48 manually..."
curl -sk -X POST \
  -H "Authorization: Bearer $TARGET__TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Galaxy/Hub Token 48",
    "description": "Automation Hub API token",
    "credential_type": 19,
    "organization": 8,
    "inputs": {
      "url": "https://galaxy.ansible.com/",
      "token": "test_token_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    }
  }' \
  "https://localhost:10443/api/controller/v2/credentials/" | jq '.'

echo
echo "🧪 Creating Galaxy/Hub Token 49 manually..."
curl -sk -X POST \
  -H "Authorization: Bearer $TARGET__TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Galaxy/Hub Token 49",
    "description": "Automation Hub API token",
    "credential_type": 19,
    "organization": 5,
    "inputs": {
      "url": "https://console.redhat.com/api/automation-hub/",
      "token": "test_token_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    }
  }' \
  "https://localhost:10443/api/controller/v2/credentials/" | jq '.'

echo
echo "🧪 Creating Galaxy/Hub Token 50 manually..."
curl -sk -X POST \
  -H "Authorization: Bearer $TARGET__TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Galaxy/Hub Token 50",
    "description": "Automation Hub API token",
    "credential_type": 19,
    "organization": 4,
    "inputs": {
      "url": "https://console.redhat.com/api/automation-hub/",
      "token": "test_token_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    }
  }' \
  "https://localhost:10443/api/controller/v2/credentials/" | jq '.'
