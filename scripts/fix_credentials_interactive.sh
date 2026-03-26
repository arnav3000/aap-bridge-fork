#!/bin/bash

#
# Interactive Credential Recreation Script
# Helps you recreate AAP credentials with actual secrets
#

set -e

TARGET_URL="https://localhost:10443/api/controller/v2"
TARGET_TOKEN="YOUR_TARGET_AAP_TOKEN"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

clear

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}    AAP Credential Recreation - Interactive Mode${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${CYAN}This script will help you recreate 6 credentials:${NC}"
echo ""
echo "  1. Demo Credential (SSH) - needs password or SSH key"
echo "  2. Automation Hub Validated - needs token"
echo "  3. Automation Hub Published - needs token"
echo "  4. Automation Hub RH Certified - needs token"
echo "  5. Automation Hub Community - needs token"
echo "  6. Automation Hub Container Registry - needs password"
echo "  7. test_A (SSH) - uses runtime prompts (optional)"
echo ""

read -p "Press Enter to start..."
clear

# Helper function to create credential
create_credential() {
    local name="$1"
    local type="$2"
    local org="${3:-null}"
    local inputs="$4"

    echo -e "\n${YELLOW}Creating: $name${NC}"

    response=$(curl -sk -X POST \
        -H "Authorization: Bearer $TARGET_TOKEN" \
        -H "Content-Type: application/json" \
        "$TARGET_URL/credentials/" \
        -d "{
            \"name\": \"$name\",
            \"credential_type\": $type,
            \"organization\": $org,
            \"inputs\": $inputs
        }")

    if echo "$response" | jq -e '.id' > /dev/null 2>&1; then
        cred_id=$(echo "$response" | jq -r '.id')
        echo -e "${GREEN}✓ Created credential ID: $cred_id${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to create credential${NC}"
        echo "$response" | jq .
        return 1
    fi
}

# ========================================
# 1. Demo Credential (SSH)
# ========================================
clear
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Credential 1/7: Demo Credential (SSH)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "This is an SSH credential for machine access."
echo "Username: admin"
echo ""
echo "You need to provide EITHER:"
echo "  A) Password"
echo "  B) SSH private key"
echo ""

read -p "Do you have the password for 'Demo Credential'? (y/n): " has_password

if [[ $has_password =~ ^[Yy]$ ]]; then
    echo ""
    read -s -p "Enter password: " demo_password
    echo ""

    create_credential \
        "Demo Credential" \
        1 \
        "null" \
        "{\"username\": \"admin\", \"password\": \"$demo_password\"}"
else
    echo ""
    echo "Do you have the SSH private key?"
    read -p "Path to SSH key file (or press Enter to skip): " key_path

    if [ -n "$key_path" ] && [ -f "$key_path" ]; then
        ssh_key=$(cat "$key_path" | jq -Rs .)

        create_credential \
            "Demo Credential" \
            1 \
            "null" \
            "{\"username\": \"admin\", \"ssh_key_data\": $ssh_key}"
    else
        echo -e "${YELLOW}⊘ Skipping Demo Credential (no password or key provided)${NC}"
    fi
fi

read -p "Press Enter to continue..."

# ========================================
# 2-5. Automation Hub Credentials (Galaxy tokens)
# ========================================
clear
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Credentials 2-5: Automation Hub Galaxy Repositories${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "These credentials connect to your Automation Hub at:"
echo "  ${CYAN}https://192.168.100.26${NC}"
echo ""
echo "You need an API token from Automation Hub."
echo ""
echo "To get the token:"
echo "  1. Go to: https://192.168.100.26"
echo "  2. Log in"
echo "  3. Click: Collections → API Token (or User → Token)"
echo "  4. Copy the token"
echo ""

read -p "Do you have the Automation Hub API token? (y/n): " has_hub_token

if [[ $has_hub_token =~ ^[Yy]$ ]]; then
    echo ""
    read -s -p "Enter Automation Hub API token: " hub_token
    echo ""
    echo ""

    # Automation Hub Validated
    create_credential \
        "Automation Hub Validated Repository" \
        19 \
        "null" \
        "{\"url\": \"https://192.168.100.26/api/galaxy/content/validated/\", \"token\": \"$hub_token\"}"

    # Automation Hub Published
    create_credential \
        "Automation Hub Published Repository" \
        19 \
        "null" \
        "{\"url\": \"https://192.168.100.26/api/galaxy/content/published/\", \"token\": \"$hub_token\"}"

    # Automation Hub RH Certified
    create_credential \
        "Automation Hub RH Certified Repository" \
        19 \
        "null" \
        "{\"url\": \"https://192.168.100.26/api/galaxy/content/rh-certified/\", \"token\": \"$hub_token\"}"

    # Automation Hub Community
    create_credential \
        "Automation Hub Community Repository" \
        19 \
        "null" \
        "{\"url\": \"https://192.168.100.26/api/galaxy/content/community/\", \"token\": \"$hub_token\"}"
else
    echo -e "${YELLOW}⊘ Skipping Automation Hub credentials (no token provided)${NC}"
fi

read -p "Press Enter to continue..."

# ========================================
# 6. Automation Hub Container Registry
# ========================================
clear
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Credential 6/7: Automation Hub Container Registry${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "This credential connects to the container registry at:"
echo "  Host: ${CYAN}192.168.100.26${NC}"
echo "  Username: ${CYAN}admin${NC}"
echo ""

read -p "Do you have the password for the container registry? (y/n): " has_registry_password

if [[ $has_registry_password =~ ^[Yy]$ ]]; then
    echo ""
    read -s -p "Enter container registry password: " registry_password
    echo ""

    create_credential \
        "Automation Hub Container Registry" \
        18 \
        "null" \
        "{\"host\": \"192.168.100.26\", \"username\": \"admin\", \"password\": \"$registry_password\", \"verify_ssl\": true}"
else
    echo -e "${YELLOW}⊘ Skipping Container Registry credential (no password provided)${NC}"
fi

read -p "Press Enter to continue..."

# ========================================
# 7. test_A (SSH with runtime prompts)
# ========================================
clear
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Credential 7/7: test_A (SSH)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "This SSH credential uses runtime prompts (ASK)."
echo "  Username: ${CYAN}arnav${NC}"
echo "  Organization: ${CYAN}org_A${NC}"
echo ""
echo "The source credential uses 'ASK' for password, which means"
echo "it prompts at runtime. This is already handled correctly."
echo ""

read -p "Do you want to create test_A with runtime prompts? (y/n): " create_test_a

if [[ $create_test_a =~ ^[Yy]$ ]]; then
    create_credential \
        "test_A" \
        1 \
        2 \
        "{\"username\": \"arnav\", \"password\": \"\", \"become_username\": \"arnav\", \"become_method\": \"\"}"
else
    echo -e "${YELLOW}⊘ Skipping test_A${NC}"
fi

# ========================================
# Summary
# ========================================
clear
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Credential Recreation Complete!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

echo "Checking credentials in target AAP..."
echo ""

curl -sk -H "Authorization: Bearer $TARGET_TOKEN" \
    "$TARGET_URL/credentials/" | jq -r '.results[] | "\(.id): \(.name)"'

echo ""
echo -e "${GREEN}✓ Done!${NC}"
echo ""
echo "Next steps:"
echo "  1. Verify credentials work by testing them in AAP UI"
echo "  2. Associate galaxy credentials to organizations"
echo "  3. Migrate projects and job templates"
echo ""
echo "To associate galaxy credentials to org_A:"
echo "  ${CYAN}https://localhost:10443/#/organizations/2/edit${NC}"
echo "  → Galaxy Credentials → Add → Select credentials → Save"
echo ""
