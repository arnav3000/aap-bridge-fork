# TUI Improvements - Enhanced Import Experience

## Date: 2026-03-31
## Branch: fix-tui

## Overview

Complete overhaul of the import experience with enhanced TUI, dependency validation, progress tracking, and smart retry capabilities.

## Problems Solved

### Before:
- ❌ Two-phase import was a blunt instrument (Phase 1/2)
- ❌ No visibility into what would fail before starting
- ❌ Generic error messages like "Phase 2 failed" with no details
- ❌ Lost all progress when errors occurred
- ❌ No way to retry only failed resources
- ❌ No dependency validation before import
- ❌ No granular progress tracking

### After:
- ✅ Enhanced import submenu with 7 options
- ✅ Pre-flight dependency validation
- ✅ Resource-level progress tracking with error details
- ✅ Smart retry for failed resources only
- ✅ Resume capability (don't lose progress)
- ✅ Detailed error reporting with root cause analysis
- ✅ Real-time progress display

## New Features

### 1. Enhanced Import Menu (`import_menu.py`)

**New submenu when selecting "Import Resources":**

```
Import Resources
├── 1. Pre-flight Check (Validate Dependencies)
├── 2. Import All Resources (Automatic)
├── 3. Granular Import (Step-by-Step Control) ⭐ NEW!
├── 4. Import Phase 1 (Base Resources)
├── 5. Import Phase 2 (Projects + Automation)
├── 6. Retry Failed Resources
├── 7. View Import Status
├── 8. View Failed Resources
└── b. Back to Main Menu
```

**Features:**
- Visual progress bars for each resource type
- Real-time success/failure counts
- Error summaries
- Interactive confirmation prompts

### 2. Pre-flight Dependency Validation (`dependency_validator.py`)

**What it does:**
- Validates dependencies **before** starting import
- Shows which resources will succeed/fail
- Identifies missing dependencies
- Displays dependency chains

**Example Output:**
```
Pre-Flight Dependency Validation

Resource Type          Total  Ready  Blocked  Warnings  Status
────────────────────────────────────────────────────────────────
organizations           15     15      -        -       ✓ READY
credentials             45     42      3        -       ✗ BLOCKED
job_templates           35     30      5        -       ✗ BLOCKED

Overall Summary:
  ✓ Ready to import: 87
  ✗ Blocked: 8

✗ Cannot proceed - fix dependency issues first

Detailed Issues:
  credentials
    ├─ "AWS Production" (source ID: 42)
    │   └─ ✗ Missing organizations: source ID 6
    └─ "SSH Deploy Key" (source ID: 48)
        └─ ✗ Missing credential_types: source ID 15
```

**Usage:**
```bash
# From TUI: Select option 1 in Import submenu
# From CLI:
aap-bridge import --check-dependencies
```

### 3. Enhanced Progress Display (`enhanced_progress.py`)

**Features:**
- Granular resource-type-level tracking
- Real-time progress bars
- Failed count per resource type
- Recent errors panel
- Overall summary statistics

**Example Output:**
```
Overall Progress
Total Resources: 200
Completed: 178
Failed: 22
Pending: 0
Progress: 89.0%

Resource Import Progress
organizations         ████████████████████ 100%  • 15/15  • ❌0
credentials          ████████████████░░░░  84%  • 42/50  • ❌8
job_templates        ███████████░░░░░░░░░  65%  • 23/35  • ❌12

Recent Errors (22 total)
Type           Resource                  Error
────────────────────────────────────────────────────────────
Credential     AWS Prod (ID:42)         Missing org ID: 6
Job Template   Deploy App (ID:89)       Missing credential: 42
Workflow       CI/CD Pipeline (ID:12)   Missing job template: 89
```

### 4. Smart Retry/Resume (`retry.py`)

**New Commands:**

```bash
# Retry all failed resources
aap-bridge retry failed

# Retry specific resource types
aap-bridge retry failed -r credentials -r projects

# See what would be retried
aap-bridge retry failed --dry-run

# Check retry status
aap-bridge retry status
```

**How it works:**
1. Identifies all resources with status='failed' in migration_progress
2. Groups by resource type
3. Shows summary of what will be retried
4. Clears failed status to allow re-import
5. Re-imports only the previously failed resources
6. Skips already-successful resources (doesn't lose progress)

**Example Output:**
```
Failed Resources to Retry:

Resource Type          Failed Count  Sample Resources
─────────────────────────────────────────────────────────────────
credentials            3             AWS Prod, SSH Key, Vault Token
job_templates          12            Deploy App, Database Backup ... and 10 more

Total Failed: 15

Retry these failed resources? [Y/n]:
```

### 5. Import Status Dashboard

**New option in Import submenu: "View Import Status"**

**Shows:**
- Progress for each resource type
- Completed/Failed/Pending counts
- Visual progress bars
- Overall completion percentage

**Example:**
```
Import Status

Resource Type          Total  Completed  Failed  Pending  Progress
──────────────────────────────────────────────────────────────────────
organizations           15      15        -        -      ████████████ 100.0%
users                   32      32        -        -      ████████████ 100.0%
credentials             50      42        8        -      ██████████░░  84.0%
projects                18      18        -        -      ████████████ 100.0%
job_templates           35      23       12        -      ████████░░░░  65.7%

Overall Progress:
  Total Resources: 150
  ✓ Completed: 130
  ✗ Failed: 20
```

### 6. Granular Micro-Phase Import ⭐ NEW!

**New option in Import submenu: "Granular Import (Step-by-Step Control)"**

**What it does:**
- Breaks import into 17 micro-phases
- Shows progress table for all phases
- User controls each phase individually
- Can skip, retry, view errors, or abort at any phase

**Micro-Phases:**

**Phase 1: Infrastructure**
- 1.1 Organizations
- 1.2 Labels
- 1.3 Users
- 1.4 Teams
- 1.5 Credential Types
- 1.6 Credentials
- 1.7 Execution Environments

**Phase 2: Inventory**
- 2.1 Inventories
- 2.2 Inventory Sources
- 2.3 Inventory Groups
- 2.4 Hosts

**Phase 3: Projects**
- 3.1 Projects

**Phase 4: Automation**
- 4.1 Notification Templates
- 4.2 Job Templates
- 4.3 Workflow Templates
- 4.4 Schedules
- 4.5 Applications

**Example Display:**

```
Import Progress

Phase  Resource Type           Total  ✓    ✗   ⧗   Progress              Status
──────────────────────────────────────────────────────────────────────────────
1.1    Organizations            15   15   -   -   ███████████████ 100%  ✓ Done
1.2    Labels                    0    -   -   -   ░░░░░░░░░░░░░░░   0%  ⧗ Pending
1.3    Users                    32   32   -   -   ███████████████ 100%  ✓ Done
1.4    Teams                    17   17   -   -   ███████████████ 100%  ✓ Done
1.5    Credential Types          8    8   -   -   ███████████████ 100%  ✓ Done
1.6    Credentials              50   42   8   -   ████████████░░░  84%  → Running
1.7    Execution Environments   12    -   -  12   ░░░░░░░░░░░░░░░   0%  ⧗ Pending

Phase 1.6: Credentials
  Total: 50
  Completed: 42
  Failed: 8
  Pending: 0

Actions:
  i - Import this phase
  s - Skip this phase (continue to next)
  r - Retry failed resources in this phase
  v - View errors for this phase
  a - Abort entire import

Select action [i/s/r/v/a] (i):
```

**User Actions Per Phase:**
- **i (Import)**: Import all resources in this phase
- **s (Skip)**: Skip this phase and move to next
- **r (Retry)**: Retry failed resources in this phase
- **v (View)**: Show error details for failed resources
- **a (Abort)**: Stop the entire import process

**Benefits:**
- 🎯 Fine-grained control over what gets imported
- 👀 See exactly which phase is running
- 🛑 Stop at any point if issues occur
- 🔍 View errors without leaving the flow
- ♻️ Retry only the problematic phase

### 7. Failed Resources Report

**New option in Import submenu: "View Failed Resources"**

**Shows:**
- All failed resources across all types
- Error messages
- Source IDs for tracking

**Example:**
```
Failed Resources

Type           Source ID  Name                   Error
────────────────────────────────────────────────────────────────
credentials    42         AWS Production         Missing organization mapping
credentials    48         SSH Deploy Key         Organization not found
job_templates  89         Deploy Application     Missing credential: 42
```

## Files Created/Modified

### New Files:

1. **`src/aap_migration/cli/import_menu.py`** (270 lines)
   - Enhanced import submenu with 8 options
   - Status and error viewers
   - Interactive import workflow
   - Integrated granular import

2. **`src/aap_migration/cli/granular_import.py`** (438 lines) ⭐ NEW!
   - Step-by-step micro-phase import
   - 17 granular phases with full control
   - Interactive phase-by-phase execution
   - Skip/Retry/View/Abort per phase

3. **`src/aap_migration/validation/dependency_validator.py`** (253 lines)
   - Pre-flight dependency validation
   - Dependency chain analysis
   - Formatted validation reports

4. **`src/aap_migration/reporting/enhanced_progress.py`** (233 lines)
   - Granular progress tracking
   - Error aggregation
   - Live display updates

5. **`src/aap_migration/cli/commands/retry.py`** (370 lines)
   - Smart retry for failed resources
   - Resume capability
   - Status reporting

### Modified Files:

6. **`src/aap_migration/cli/menu.py`**
   - Integrated enhanced import submenu
   - Simplified main menu
   - Better flow

7. **`src/aap_migration/cli/main.py`**
   - Registered retry command group
   - Imported retry commands

8. **`src/aap_migration/cli/commands/export_import.py`**
   - Integrated dependency validator
   - Enhanced --check-dependencies flag

9. **`src/aap_migration/validation/__init__.py`**
   - Exported DependencyValidator

## User Experience Improvements

### Old Workflow:
```
1. Run Phase 1
2. Wait for completion
3. Run Phase 2
4. Phase 2 fails with generic error
5. No way to know what failed or why
6. Have to start Phase 1 over
```

### New Workflow:
```
1. Run pre-flight check
2. See what will fail BEFORE importing
3. Fix dependency issues
4. Import all resources
5. See real-time progress per resource type
6. If some fail:
   - View failed resources with error details
   - Fix root causes
   - Retry only failed resources
   - Don't lose progress from successful imports
```

## Migration Path Benefits

### For Users:
- 🎯 **Know before you go**: Pre-flight validation catches issues early
- 📊 **See what's happening**: Real-time progress tracking
- 🔍 **Understand errors**: Detailed error reports with context
- ♻️ **Recover easily**: Smart retry doesn't lose progress
- 💾 **Resume anytime**: Interrupted imports can be resumed

### For Debugging:
- 🐛 Clear error messages tied to specific resources
- 📈 Resource-level tracking (not just phase-level)
- 🔗 Dependency chain visualization
- 📝 Detailed logs per resource type

## Testing

### Manual Testing Steps:

1. **Test Pre-flight Validation:**
   ```bash
   aap-bridge import --check-dependencies
   ```

2. **Test Enhanced Progress:**
   ```bash
   aap-bridge  # Launch TUI
   # Select: 4. Import Resources
   # Select: 2. Import All Resources
   ```

3. **Test Status Viewer:**
   ```bash
   aap-bridge  # Launch TUI
   # Select: 4. Import Resources
   # Select: 6. View Import Status
   ```

4. **Test Failed Resources Viewer:**
   ```bash
   aap-bridge  # Launch TUI
   # Select: 4. Import Resources
   # Select: 7. View Failed Resources
   ```

5. **Test Retry:**
   ```bash
   # From TUI
   # Select: 4. Import Resources
   # Select: 5. Retry Failed Resources

   # Or from CLI:
   aap-bridge retry failed
   aap-bridge retry status
   ```

## Known Limitations

1. **Dependency validation** is best-effort - some complex dependencies may not be caught
2. **Retry logic** assumes transformed files still exist in xformed/
3. **Progress display** updates every 0.25s which may be too fast for very large migrations

## Future Enhancements

### Possible additions:
- 🔄 Checkpoint/rollback system
- 📊 Dependency graph visualization
- 🎯 Auto-include dependencies option
- ⚡ Parallel import with dependency ordering
- 📁 Export error reports (JSON/CSV)
- 🔍 Search/filter in error viewer

## Commit Message

```
feat: comprehensive TUI improvements for import workflow

- Add enhanced import submenu with 8 interactive options
- Add granular micro-phase import (17 phases, step-by-step control)
- Implement pre-flight dependency validation
- Add granular resource-level progress tracking with error details
- Create smart retry system for failed resources only
- Add import status and failed resources viewers
- Improve error reporting with root cause analysis

Solves the "Phase 2 failed" problem by providing:
- Validation before import
- Real-time progress visibility
- Detailed error tracking
- Smart retry without losing progress

New commands:
- aap-bridge retry failed
- aap-bridge retry status
- aap-bridge import --check-dependencies (enhanced)

New TUI screens:
- Enhanced import submenu
- Pre-flight validation report
- Import status dashboard
- Failed resources report

Files:
- NEW: src/aap_migration/cli/import_menu.py
- NEW: src/aap_migration/cli/granular_import.py ⭐
- NEW: src/aap_migration/validation/dependency_validator.py
- NEW: src/aap_migration/reporting/enhanced_progress.py
- NEW: src/aap_migration/cli/commands/retry.py
- MODIFIED: menu.py, main.py, export_import.py
```

---

**Status:** ✅ Complete - All 4 priorities + Granular Import implemented
**Testing:** Ready for manual testing
**Branch:** fix-tui
**Ready to merge:** After testing
