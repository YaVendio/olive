# Installing Olive with uv from GitHub Package Registry

This guide explains how to install the `olive` package using `uv` from GitHub's private package registry.

## Prerequisites

1. [uv](https://github.com/astral-sh/uv) package manager installed
2. A GitHub personal access token with `read:packages` permission
3. Python 3.13 or higher

## Installing uv

If you haven't installed `uv` yet:

```bash
# On Unix-like systems (macOS, Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Creating a Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token" → "Generate new token (classic)"
3. Give your token a descriptive name
4. Select the `read:packages` scope
5. Click "Generate token"
6. Copy the token (you won't be able to see it again!)

## Installation Methods

### Method 1: Direct Installation from Git

Since the repository is private, you'll need to configure Git authentication:

```bash
# Install directly from the private Git repository
uv pip install git+ssh://git@github.com/YaVendio/olive.git

# Or with HTTPS (you'll be prompted for credentials)
uv pip install git+https://github.com/YaVendio/olive.git
```

### Method 2: From GitHub Releases

Download the latest wheel file from [GitHub Releases](https://github.com/YaVendio/olive/releases):

```bash
# Download the wheel file from the latest release
# Then install it locally
uv pip install path/to/olive-1.1.2-py3-none-any.whl
```

### Method 3: In pyproject.toml

Add to your `pyproject.toml`:

```toml
[project]
dependencies = [
    "olive @ git+ssh://git@github.com/YaVendio/olive.git",
]

# Or for a specific version tag
dependencies = [
    "olive @ git+ssh://git@github.com/YaVendio/olive.git@v1.1.2",
]
```

Then sync your project:

```bash
uv sync
```

### Method 4: Using .netrc for Authentication

Create or edit `~/.netrc`:

```
machine github.com
  login YOUR_GITHUB_USERNAME
  password YOUR_GITHUB_TOKEN

machine pypi.pkg.github.com
  login __token__
  password YOUR_GITHUB_TOKEN
```

Set proper permissions:

```bash
chmod 600 ~/.netrc
```

Then install:

```bash
uv pip install olive --index-url https://pypi.pkg.github.com/YaVendio
```

## Using in a uv Project

### Initialize a new project

```bash
uv init my-project
cd my-project
```

### Add olive as a dependency

```bash
# From Git repository
uv add git+ssh://git@github.com/YaVendio/olive.git

# Or from a specific tag
uv add git+ssh://git@github.com/YaVendio/olive.git@v1.1.2

# Or from GitHub Package Registry (after configuring authentication)
uv add olive --index-url https://pypi.pkg.github.com/YaVendio
```

### Install and sync

```bash
uv sync
```

## CI/CD Integration

### GitHub Actions

In your workflow file:

```yaml
- name: Install uv
  uses: astral-sh/setup-uv@v3
  with:
    enable-cache: true

- name: Install dependencies
  env:
    UV_EXTRA_INDEX_URL: https://pypi.org/simple
  run: |
    uv pip install olive --index-url https://__token__:${{ secrets.GITHUB_TOKEN }}@pypi.pkg.github.com/YaVendio
```

### GitLab CI

```yaml
before_script:
  - curl -LsSf https://astral.sh/uv/install.sh | sh
  - source $HOME/.cargo/env
  - uv pip install olive --index-url https://__token__:${CI_JOB_TOKEN}@pypi.pkg.github.com/YaVendio
```

## Troubleshooting

### Authentication Issues

If you encounter authentication errors:

1. Verify your token has `read:packages` permission
2. Check that the token hasn't expired
3. Ensure you're using the correct authentication method for your setup

### SSH Key Issues

For SSH-based installation:

```bash
# Ensure your SSH key is added to the agent
ssh-add ~/.ssh/id_rsa

# Test GitHub SSH connection
ssh -T git@github.com
```

### Cache Issues

Clear uv cache if you encounter stale package issues:

```bash
uv cache clean
```

## Development Setup

For development, clone and install in editable mode:

```bash
git clone git@github.com:YaVendio/olive.git
cd olive
uv pip install -e .
```

## Performance Tips

uv is significantly faster than pip. To maximize performance:

1. Use `uv sync` instead of `uv pip install` when possible
2. Enable caching in CI/CD environments
3. Use `--link-mode copy` for faster installs on some filesystems:
   ```bash
   uv pip install olive --link-mode copy
   ```
