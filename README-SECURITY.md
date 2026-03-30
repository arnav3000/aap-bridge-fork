# Security & Scanning Setup - Quick Reference

This document provides a quick reference for the security scanning setup in AAP Bridge.

## Files Created

| File | Purpose |
|------|---------|
| `.github/workflows/security-scan.yml` | GitHub Actions workflow for automated security scanning |
| `.gitleaks.toml` | Configuration for Gitleaks secret detection |
| `.pre-commit-config.yaml` | Pre-commit hooks configuration |
| `.markdownlint.yaml` | Markdown linting configuration |
| `.github/dependabot.yml` | Dependabot configuration for automated dependency updates |
| `pyproject.toml` | Updated with Bandit security linting configuration |
| `SECURITY.md` | Security policy and vulnerability reporting |
| `docs/SECURITY-SETUP.md` | Comprehensive security setup guide |

## Quick Setup (3 steps)

```bash
# 1. Install pre-commit hooks
pip install pre-commit
pre-commit install

# 2. Run initial scan
pre-commit run --all-files

# 3. Done! Hooks will run automatically on every commit
```

## What Gets Scanned

### Every Commit (Pre-commit Hooks)
- **Secrets**: Gitleaks detects 140+ secret types (API keys, tokens, passwords)
- **Security Issues**: Bandit finds Python security vulnerabilities
- **Code Quality**: Ruff lints and formats code
- **Type Safety**: mypy checks types
- **Common Issues**: Large files, merge conflicts, trailing whitespace

### Every Push/PR (GitHub Actions)
- **Dependency Vulnerabilities**: pip-audit checks for CVEs
- **Secret Detection**: Gitleaks scans entire git history
- **SAST**: Bandit + Semgrep find security bugs
- **Code Quality**: Ruff enforces standards
- **License Compliance**: Ensures GPL compatibility
- **SBOM Generation**: Software Bill of Materials
- **Filesystem Scan**: Trivy finds vulnerabilities

### Weekly (GitHub Actions Schedule)
- All scans run automatically every Sunday at midnight UTC

## Manual Scans

```bash
# Secret detection
gitleaks detect --source . --verbose

# Dependency vulnerabilities
pip-audit --requirement requirements.txt

# Security linting
bandit -r src/

# Pattern-based analysis
semgrep scan --config auto

# Filesystem scan
trivy fs .

# License check
pip-licenses --format=markdown
```

## Common Commands

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Run specific hook
pre-commit run gitleaks --all-files
pre-commit run bandit --all-files

# Update hooks to latest
pre-commit autoupdate

# Skip hooks (emergency only)
git commit --no-verify -m "emergency fix"
```

## GitHub Actions Results

View results in:
1. **Actions Tab**: Workflow runs and logs
2. **Security Tab**: Code scanning alerts (Trivy, Semgrep)
3. **Artifacts**: Downloadable reports (JSON, SARIF)

## Dependabot

Automatically creates PRs for:
- Python package updates (weekly, Mondays 9am UTC)
- GitHub Actions updates (weekly, Mondays 9am UTC)
- Groups minor/patch updates to reduce PR noise

## Configuration Files

### Gitleaks (`.gitleaks.toml`)
```toml
[extend]
useDefault = true

[allowlist]
paths = ["tests/fixtures/.*"]
```

### Bandit (`pyproject.toml`)
```toml
[tool.bandit]
exclude_dirs = ["tests", ".venv"]
skips = ["B101"]  # Allow assert in tests
severity = "MEDIUM"
```

### Markdownlint (`.markdownlint.yaml`)
```yaml
default: true
MD013:
  line_length: 120
```

## Troubleshooting

### False Positives

**Gitleaks**: Add to `.gitleaks.toml` allowlist
```toml
[allowlist]
paths = ["path/to/file"]
```

**Bandit**: Inline comment
```python
secret = get_secret()  # nosec B123
```

**Semgrep**: Inline comment
```python
result = eval(code)  # nosemgrep: python.lang.security.audit.eval-use
```

### Pre-commit Failures

```bash
# Clear cache and reinstall
pre-commit clean
pre-commit install
```

## Security Best Practices

1. ✅ Install pre-commit hooks immediately
2. ✅ Never commit secrets (use `.env` files)
3. ✅ Review security findings (don't auto-dismiss)
4. ✅ Update dependencies regularly (accept Dependabot PRs)
5. ✅ Run scans locally before pushing
6. ✅ Set file permissions: `chmod 600 .env`

## Learn More

- **Full Documentation**: `docs/SECURITY-SETUP.md`
- **Security Policy**: `SECURITY.md`
- **Report Vulnerability**: aap.bridge.183yy@simplelogin.com

---

**Last Updated**: 2026-03-30
