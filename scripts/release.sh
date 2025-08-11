#!/bin/bash
# Release script for Olive package

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if version argument is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Version number required${NC}"
    echo "Usage: ./scripts/release.sh <version>"
    echo "Example: ./scripts/release.sh 1.0.1"
    exit 1
fi

VERSION=$1

# Validate version format
if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo -e "${RED}Error: Invalid version format${NC}"
    echo "Version must be in format X.Y.Z (e.g., 1.0.1)"
    exit 1
fi

echo -e "${YELLOW}Preparing release v$VERSION...${NC}"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}Error: You have uncommitted changes${NC}"
    echo "Please commit or stash your changes before releasing"
    exit 1
fi

# Update version in pyproject.toml
echo "Updating version in pyproject.toml..."
sed -i.bak "s/version = \".*\"/version = \"$VERSION\"/" pyproject.toml
rm pyproject.toml.bak

# Commit version change
echo "Committing version change..."
git add pyproject.toml
git commit -m "Bump version to $VERSION"

# Create and push tag
echo "Creating tag v$VERSION..."
git tag -a "v$VERSION" -m "Release version $VERSION"

# Push changes and tag
echo "Pushing to GitHub..."
git push origin main
git push origin "v$VERSION"

echo -e "${GREEN}✓ Release v$VERSION completed!${NC}"
echo ""
echo "The GitHub Actions workflow will now:"
echo "1. Build the package"
echo "2. Publish it to GitHub Package Registry"
echo ""
echo "You can monitor the progress at:"
echo "https://github.com/YaVendio/olive/actions"
echo ""
echo "Once published, install with:"
echo "pip install olive===$VERSION --index-url https://USERNAME:TOKEN@pypi.pkg.github.com/YaVendio"
