#!/bin/bash
# Test building the package locally

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Testing package build...${NC}"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info

# Install build tools
echo "Installing build tools..."
pip install --quiet build twine

# Build the package
echo "Building package..."
python -m build

# Check the built files
echo -e "\n${GREEN}Built files:${NC}"
ls -la dist/

# Check package with twine
echo -e "\n${YELLOW}Checking package with twine...${NC}"
python -m twine check dist/*

echo -e "\n${GREEN}✓ Package build successful!${NC}"
echo "The package is ready to be published."
