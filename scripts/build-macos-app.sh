#!/bin/bash
#
# Build Radiant Core GUI macOS Application
# Creates a standalone .app bundle and .dmg installer
#
# Requirements:
#   - macOS with Xcode Command Line Tools
#   - Python 3.9+
#   - pip install py2app pywebview
#
# Usage: ./scripts/build-macos-app.sh [version]
# Example: ./scripts/build-macos-app.sh 2.0.0
#

set -e

VERSION="${1:-2.0.0}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
GUI_DIR="$ROOT_DIR/gui"
BUILD_DIR="$ROOT_DIR/macos-app-build"
DMG_NAME="Radiant-Core-GUI-${VERSION}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=============================================="
echo "  Radiant Core macOS App Builder v${VERSION}"
echo "=============================================="
echo ""

# Check for macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo -e "${RED}Error: This script must be run on macOS${NC}"
    exit 1
fi

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required${NC}"
    exit 1
fi

echo "Step 1: Setting up build environment..."
echo "----------------------------------------"

# Create virtual environment for clean build
VENV_DIR="$BUILD_DIR/venv"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo "  Creating virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "  Installing build dependencies..."
pip install --upgrade pip > /dev/null
pip install py2app pywebview > /dev/null
echo -e "  ${GREEN}✓${NC} Dependencies installed"

echo ""
echo "Step 2: Building application bundle..."
echo "----------------------------------------"

# Copy GUI files to build directory
cp "$GUI_DIR/radiant_node_web.py" "$BUILD_DIR/"
cp "$GUI_DIR/bip39.py" "$BUILD_DIR/"
cp "$GUI_DIR/setup.py" "$BUILD_DIR/"

# Copy doc/images for logos and icon
mkdir -p "$BUILD_DIR/doc/images"
cp "$ROOT_DIR/doc/images/RXDCore.icns" "$BUILD_DIR/doc/images/" 2>/dev/null || true
cp "$ROOT_DIR/doc/images/RXD_light_logo.svg" "$BUILD_DIR/doc/images/" 2>/dev/null || true
cp "$ROOT_DIR/doc/images/RXD_dark_logo.svg" "$BUILD_DIR/doc/images/" 2>/dev/null || true

if [[ -f "$BUILD_DIR/doc/images/RXDCore.icns" ]]; then
    echo -e "  ${GREEN}✓${NC} Icon file found"
else
    echo "  Note: No icon file found, using default"
fi

cd "$BUILD_DIR"

# Build the app bundle
echo "  Running py2app..."
python setup.py py2app --dist-dir dist > build.log 2>&1 || {
    echo -e "${RED}Error: py2app build failed. Check $BUILD_DIR/build.log${NC}"
    cat build.log
    exit 1
}

APP_PATH="$BUILD_DIR/dist/Radiant Core.app"
if [[ ! -d "$APP_PATH" ]]; then
    echo -e "${RED}Error: App bundle not created${NC}"
    exit 1
fi

echo -e "  ${GREEN}✓${NC} App bundle created"

# Copy logo images to Resources folder
RESOURCES_DIR="$APP_PATH/Contents/Resources"
mkdir -p "$RESOURCES_DIR/images"
cp "$BUILD_DIR/doc/images/RXD_light_logo.svg" "$RESOURCES_DIR/images/" 2>/dev/null || true
cp "$BUILD_DIR/doc/images/RXD_dark_logo.svg" "$RESOURCES_DIR/images/" 2>/dev/null || true
echo -e "  ${GREEN}✓${NC} Logo images copied"

# Copy Radiant Core binaries into the app bundle
echo ""
echo "Step 3: Bundling Radiant Core binaries..."
echo "----------------------------------------"

RESOURCES_DIR="$APP_PATH/Contents/Resources"
BINARIES_DIR="$RESOURCES_DIR/binaries"
mkdir -p "$BINARIES_DIR"

# Download macOS binaries
BINARY_URL="https://github.com/Radiant-Core/Radiant-Core/releases/download/v${VERSION}/radiant-core-macos-arm64.zip"
echo "  Downloading binaries..."
curl -sL -o "$BUILD_DIR/binaries.zip" "$BINARY_URL" || {
    echo -e "${YELLOW}Warning: Could not download binaries. App will prompt user to download.${NC}"
}

if [[ -f "$BUILD_DIR/binaries.zip" ]]; then
    unzip -q "$BUILD_DIR/binaries.zip" -d "$BUILD_DIR/binary-extract"
    cp "$BUILD_DIR/binary-extract/radiant-core-macos-arm64"/* "$BINARIES_DIR/" 2>/dev/null || true
    chmod +x "$BINARIES_DIR"/* 2>/dev/null || true
    
    # Fix dynamic library paths for portable distribution
    if [[ -f "$ROOT_DIR/scripts/fix-macos-dylibs.sh" ]]; then
        echo "  Fixing dynamic library paths..."
        "$ROOT_DIR/scripts/fix-macos-dylibs.sh" "$BINARIES_DIR" || {
            echo -e "  ${YELLOW}Warning: Could not fix dylib paths. Binaries may require Homebrew.${NC}"
        }
    fi
    echo -e "  ${GREEN}✓${NC} Binaries bundled"
else
    echo "  Skipping binary bundling"
fi

echo ""
echo "Step 4: Creating DMG installer..."
echo "----------------------------------------"

DMG_PATH="$BUILD_DIR/$DMG_NAME.dmg"
DMG_TEMP="$BUILD_DIR/dmg-temp"

# Create DMG staging area
rm -rf "$DMG_TEMP"
mkdir -p "$DMG_TEMP"
cp -R "$APP_PATH" "$DMG_TEMP/"

# Create Applications symlink for drag-to-install
ln -s /Applications "$DMG_TEMP/Applications"

# Create README in DMG
cat > "$DMG_TEMP/README.txt" << 'EOF'
Radiant Core GUI
================

Installation:
  Drag "Radiant Core.app" to the Applications folder.

First Launch:
  If macOS blocks the app, right-click and select "Open",
  or run: xattr -rd com.apple.quarantine /Applications/Radiant\ Core.app

Support: https://radiantblockchain.org
EOF

# Create the DMG
echo "  Creating DMG..."
hdiutil create -volname "$DMG_NAME" \
    -srcfolder "$DMG_TEMP" \
    -ov -format UDZO \
    "$DMG_PATH" > /dev/null 2>&1

if [[ -f "$DMG_PATH" ]]; then
    echo -e "  ${GREEN}✓${NC} DMG created"
else
    echo -e "${RED}Error: DMG creation failed${NC}"
    exit 1
fi

# Generate checksum
cd "$BUILD_DIR"
shasum -a 256 "$DMG_NAME.dmg" > "$DMG_NAME.dmg.sha256"

# Get file size
DMG_SIZE=$(ls -lh "$DMG_PATH" | awk '{print $5}')

# Cleanup
deactivate
rm -rf "$DMG_TEMP" "$VENV_DIR" "$BUILD_DIR/build" "$BUILD_DIR/binary-extract"

echo ""
echo "=============================================="
echo -e "${GREEN}Build Complete!${NC}"
echo "=============================================="
echo ""
echo "Output files:"
echo "  $DMG_PATH ($DMG_SIZE)"
echo "  $BUILD_DIR/$DMG_NAME.dmg.sha256"
echo ""
echo "SHA256:"
cat "$BUILD_DIR/$DMG_NAME.dmg.sha256"
echo ""
echo "To upload to GitHub Release:"
echo "  gh release upload v${VERSION} $DMG_PATH $BUILD_DIR/$DMG_NAME.dmg.sha256"
echo ""
