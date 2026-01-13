#!/bin/bash
# Build script for Radiant Core - Linux x86_64
# Creates release binaries with wallet support enabled
# Run this on a Linux system or in Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build-release-linux"
OUTPUT_DIR="$SCRIPT_DIR/Linux"
RELEASE_NAME="radiant-core-linux-x64"

echo "========================================"
echo "Building Radiant Core for Linux x86_64"
echo "========================================"
echo "Project root: $PROJECT_ROOT"
echo "Build dir: $BUILD_DIR"
echo "Output dir: $OUTPUT_DIR"
echo ""

# Check for required tools
command -v cmake >/dev/null 2>&1 || { echo "Error: cmake is required"; exit 1; }
command -v make >/dev/null 2>&1 || { echo "Error: make is required"; exit 1; }

# Clean and create build directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Configure with recommended options
echo "Configuring build..."
cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_RADIANT_WALLET=ON \
    -DBUILD_RADIANT_DAEMON=ON \
    -DBUILD_RADIANT_CLI=ON \
    -DBUILD_RADIANT_TX=ON \
    -DBUILD_RADIANT_ZMQ=ON \
    -DBUILD_RADIANT_QT=OFF \
    -DBUILD_RADIANT_SEEDER=OFF \
    -DENABLE_HARDENING=ON \
    -DENABLE_UPNP=ON \
    -DENABLE_GLIBC_BACK_COMPAT=ON \
    "$PROJECT_ROOT"

# Build
echo ""
echo "Building (this may take a while)..."
make -j$(nproc)

# Create release package
echo ""
echo "Creating release package..."
mkdir -p "$OUTPUT_DIR"
rm -rf "$OUTPUT_DIR/$RELEASE_NAME"
mkdir -p "$OUTPUT_DIR/$RELEASE_NAME"

# Copy binaries
cp "$BUILD_DIR/src/radiantd" "$OUTPUT_DIR/$RELEASE_NAME/"
cp "$BUILD_DIR/src/radiant-cli" "$OUTPUT_DIR/$RELEASE_NAME/"
cp "$BUILD_DIR/src/radiant-tx" "$OUTPUT_DIR/$RELEASE_NAME/"

# Strip binaries to reduce size
strip "$OUTPUT_DIR/$RELEASE_NAME/radiantd"
strip "$OUTPUT_DIR/$RELEASE_NAME/radiant-cli"
strip "$OUTPUT_DIR/$RELEASE_NAME/radiant-tx"

# Create tarball
cd "$OUTPUT_DIR"
rm -f "$RELEASE_NAME.tar.gz"
tar -czf "$RELEASE_NAME.tar.gz" "$RELEASE_NAME"

# Generate checksum
sha256sum "$RELEASE_NAME.tar.gz" > "$RELEASE_NAME.tar.gz.sha256"
echo "Checksum: $(cat "$RELEASE_NAME.tar.gz.sha256" | cut -d' ' -f1)"
echo "File: $RELEASE_NAME.tar.gz"

# Verify wallet support
echo ""
echo "Verifying wallet support..."
if "$OUTPUT_DIR/$RELEASE_NAME/radiant-cli" -help 2>&1 | grep -q "wallet"; then
    echo "✓ Wallet support: ENABLED"
else
    if "$OUTPUT_DIR/$RELEASE_NAME/radiantd" -help 2>&1 | grep -q "wallet"; then
        echo "✓ Wallet support: ENABLED"
    else
        echo "⚠ Warning: Could not verify wallet support"
    fi
fi

echo ""
echo "========================================"
echo "Build complete!"
echo "Output: $OUTPUT_DIR/$RELEASE_NAME.tar.gz"
echo "========================================"
