#!/bin/bash
# Release script for Flutter Control MCP
# Usage: ./scripts/release.sh [patch|minor|major]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get current version from __version__.py
VERSION_FILE="flutter_control/__version__.py"
CURRENT_VERSION=$(python3 -c "exec(open('$VERSION_FILE').read()); print(__version__)")

if [ -z "$CURRENT_VERSION" ]; then
    echo -e "${RED}Error: Could not read current version from $VERSION_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}Current version: $CURRENT_VERSION${NC}"

# Parse version components
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Determine new version based on argument
BUMP_TYPE=${1:-patch}
case $BUMP_TYPE in
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    patch)
        PATCH=$((PATCH + 1))
        ;;
    *)
        echo -e "${RED}Usage: $0 [patch|minor|major]${NC}"
        exit 1
        ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"
echo -e "${GREEN}New version: $NEW_VERSION${NC}"

# Confirm
read -p "Proceed with release v$NEW_VERSION? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Update version in __version__.py
sed -i '' "s/__version__ = \"$CURRENT_VERSION\"/__version__ = \"$NEW_VERSION\"/" "$VERSION_FILE"
echo "Updated $VERSION_FILE"

# Update version in pyproject.toml
sed -i '' "s/^version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml
echo "Updated pyproject.toml"

# Update CHANGELOG.md - add new version header
TODAY=$(date +%Y-%m-%d)
# Use perl for more reliable multiline replacement
perl -i -pe "s/## \[Unreleased\]/## [Unreleased]\n\n## [$NEW_VERSION] - $TODAY/" CHANGELOG.md

# Update changelog links
perl -i -pe "s|\[Unreleased\]: (.*)/compare/v$CURRENT_VERSION\.\.\.HEAD|[Unreleased]: \$1/compare/v$NEW_VERSION...HEAD\n[$NEW_VERSION]: \$1/compare/v$CURRENT_VERSION...v$NEW_VERSION|" CHANGELOG.md
echo "Updated CHANGELOG.md"

# Commit version bump
git add "$VERSION_FILE" pyproject.toml CHANGELOG.md
git commit -m "chore: release v$NEW_VERSION"

# Create annotated tag
git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"

echo ""
echo -e "${GREEN}Release v$NEW_VERSION prepared!${NC}"
echo ""
echo "Next steps:"
echo "  1. Review the commit: git show HEAD"
echo "  2. Push to remote: git push && git push --tags"
echo "  3. Create GitHub release: gh release create v$NEW_VERSION --generate-notes"
