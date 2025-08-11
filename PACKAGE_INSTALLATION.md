# Installing Olive from GitHub Package Registry

This guide explains how to install the `olive` package from GitHub's private package registry.

## Prerequisites

1. A GitHub personal access token with `read:packages` permission
2. Python 3.13 or higher

## Creating a Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token" → "Generate new token (classic)"
3. Give your token a descriptive name
4. Select the `read:packages` scope
5. Click "Generate token"
6. Copy the token (you won't be able to see it again!)

## Installation Methods

### Method 1: Using pip with authentication

```bash
pip install olive --index-url https://USERNAME:TOKEN@pypi.pkg.github.com/YaVendio
```

Replace:

- `USERNAME` with your GitHub username
- `TOKEN` with your personal access token

### Method 2: Using pip configuration file

1. Create or edit `~/.pip/pip.conf` (Linux/Mac) or `%APPDATA%\pip\pip.ini` (Windows):

```ini
[global]
extra-index-url = https://USERNAME:TOKEN@pypi.pkg.github.com/YaVendio
```

2. Then install normally:

```bash
pip install olive
```

### Method 3: Using environment variables

```bash
export PIP_EXTRA_INDEX_URL="https://USERNAME:TOKEN@pypi.pkg.github.com/YaVendio"
pip install olive
```

### Method 4: In requirements.txt

Add to your `requirements.txt`:

```
--extra-index-url https://USERNAME:TOKEN@pypi.pkg.github.com/YaVendio
olive>=1.0.0
```

**Security Note**: Never commit tokens to version control. Use environment variables or GitHub Secrets in CI/CD.

### Method 5: Using .netrc file (Recommended for development)

1. Create or edit `~/.netrc`:

```
machine pypi.pkg.github.com
  login USERNAME
  password TOKEN
```

2. Set proper permissions:

```bash
chmod 600 ~/.netrc
```

3. Install the package:

```bash
pip install olive --index-url https://pypi.pkg.github.com/YaVendio
```

## Installing in CI/CD

### GitHub Actions

In your workflow file:

```yaml
- name: Install private packages
  run: |
    pip install olive --index-url https://oauth2:${{ secrets.GITHUB_TOKEN }}@pypi.pkg.github.com/YaVendio
```

### Other CI/CD systems

Use repository secrets to store your personal access token and reference it in your pipeline configuration.

## Troubleshooting

### 401 Unauthorized

- Ensure your token has `read:packages` permission
- Check that the token hasn't expired
- Verify the username and repository owner are correct

### Package not found

- The package might not be published yet
- Check the exact package name in the GitHub Packages tab of the repository

### SSL/TLS errors

Add `--trusted-host pypi.pkg.github.com` to your pip command if you encounter SSL issues.

## Publishing New Versions

The package is automatically published when:

1. A new tag starting with 'v' is pushed (e.g., `v1.0.1`)
2. The publish workflow is manually triggered from GitHub Actions

To publish a new version:

```bash
# Update version in pyproject.toml
git add pyproject.toml
git commit -m "Bump version to 1.0.1"
git tag v1.0.1
git push origin main --tags
```
