#!/bin/bash
# Test building the package locally with uv

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Testing package build with uv...${NC}"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed${NC}"
    echo "Install uv with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info

# Build the package
echo "Building package..."
uv build

# Check the built files
echo -e "\n${GREEN}Built files:${NC}"
ls -la dist/

# Verify the package
echo -e "\n${YELLOW}Package details:${NC}"
# Show package contents
if [ -f dist/*.whl ]; then
    echo "Wheel contents:"
    unzip -l dist/*.whl | head -20
fi

echo -e "\n${GREEN}✓ Package build successful!${NC}"
echo "The package is ready to be published."
echo ""
echo "To publish to GitHub Package Registry, use:"
echo "  uv publish --token <YOUR_GITHUB_TOKEN>"
