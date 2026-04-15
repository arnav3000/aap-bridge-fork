# Organization Filter API Testing

## Purpose

This script tests AAP API organization filtering capabilities to determine what filtering strategies are supported for implementing the `-o` organization flag.

## Prerequisites

1. AAP source instance with multiple organizations
2. Source API token (superuser or org admin)
3. Python environment with aap-migration dependencies

## How to Run

### Option 1: Using Existing .env File (Easiest)

The script automatically loads `SOURCE__URL` and `SOURCE__TOKEN` from `.env` file!

**Run directly:**
```bash
# Test by organization ID (Default org is usually ID 1)
./run_org_filter_test.sh --org-id 1

# Test by organization name
./run_org_filter_test.sh --org-name "Default"
```

### Option 2: Manual Environment Variables

If you want to override .env or test different credentials:

```bash
# Set your source AAP credentials
export SOURCE__URL=https://your-aap-24-instance/api/v2
export SOURCE__TOKEN=your_api_token_here

# Run test
./run_org_filter_test.sh --org-name "Engineering"
```

### Option 3: Run in Container

If running in the container environment:

```bash
# Inside container
cd /app/aap-bridge
python3 test_organization_filters.py --org-id 1
```

### Option 4: Direct Python (if dependencies installed)

```bash
# Activate venv if you have one
source .venv/bin/activate  # or source venv/bin/activate

# Run test
python3 test_organization_filters.py --org-name "Engineering"
```

**Note:** The script needs `httpx`, `python-dotenv`, and other aap-migration dependencies.

## What It Tests

The script tests 13 different filtering scenarios:

1. ✅ Organizations - filter by ID and name
2. ✅ Projects - filter by organization
3. ✅ Inventories - filter by organization
4. ✅ Credentials - filter by org (and global credentials)
5. ✅ Teams - filter by organization
6. ✅ Job Templates - filter by org (direct and via project)
7. ✅ Workflow Templates - filter by organization
8. ✅ Hosts - filter by inventory__organization (parent-scoped)
9. ✅ Inventory Groups - filter by inventory__organization
10. ✅ Inventory Sources - filter by inventory__organization
11. ✅ Users - filter by organization membership
12. ✅ Schedules - filter by template organization
13. ✅ Multiple organizations - using id__in syntax

## Output

The script generates two files:

1. **Markdown Report** (`org_filter_test_results.md`)
   - Summary of successful and failed filters
   - Recommendations for implementation
   - Easy to read and share

2. **JSON Results** (`org_filter_test_results.json`)
   - Machine-readable test results
   - Includes full error messages
   - Can be used for programmatic analysis

## Example Output

```
======================================================================
AAP Organization Filter API Tests
======================================================================
Organization: Engineering (ID: 5)
Started: 2026-04-15T11:30:00
======================================================================

1. Testing Organizations
  Testing: Filter by exact ID
    → 1 resources found
  Testing: Filter by exact name
    → 1 resources found

2. Testing Projects
  Testing: Filter by organization ID
    → 10 resources found
  Testing: Filter by organization name
    → 10 resources found

3. Testing Inventories
  Testing: Filter by organization ID
    → 12 resources found

...

======================================================================
SUMMARY
======================================================================
Total Tests:  15
Successful:   13
Failed:       2
======================================================================
```

## Interpreting Results

### ✅ Success = Filter Works
If a test succeeds, that filter syntax is supported by AAP API and can be used in the implementation.

### ❌ Failure = Filter Not Supported
If a test fails, we need an alternative approach:
- Two-step query (fetch IDs first, then filter by ID list)
- Alternative filter syntax
- Export all resources (if dataset is small)

## Next Steps After Testing

1. **Review the generated report** (`org_filter_test_results.md`)
2. **Share results** with the development team
3. **Design implementation** based on what filters work
4. **Handle edge cases** for filters that don't work

## Common Issues

### Issue: "SOURCE__URL and SOURCE__TOKEN must be set"
**Solution:** Export environment variables before running:
```bash
export SOURCE__URL=https://aap24.example.com
export SOURCE__TOKEN=abc123...
```

### Issue: "Organization 'X' not found"
**Solution:** Check organization name spelling or use `--org-id` instead

### Issue: Multiple organizations with same name
**Solution:** Use `--org-id` to specify exact organization

### Issue: Permission denied errors
**Solution:** Use a token with sufficient permissions (superuser or org admin for the tested org)

## For Development

The test results will directly inform the implementation strategy for the `-o` organization filter feature.

**Key questions answered:**
- ✅ Which filters work out of the box?
- ❌ Which filters need workarounds?
- 🔍 What's the best strategy for each resource type?
- 📊 How many resources are in each organization? (for testing)

---

**Ready to test?** Run the script and review the generated report!
