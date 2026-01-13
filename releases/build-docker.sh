#!/bin/bash
# Build script for Radiant Core - Docker image
# Creates Docker image with wallet support enabled

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/Docker"
VERSION="v2.0.0"
IMAGE_NAME="radiant-core:$VERSION"
RELEASE_NAME="radiant-core-docker-$VERSION"

echo "========================================"
echo "Building Radiant Core Docker Image"
echo "========================================"
echo "Project root: $PROJECT_ROOT"
echo "Output dir: $OUTPUT_DIR"
echo "Image: $IMAGE_NAME"
echo ""

# Check for Docker
command -v docker >/dev/null 2>&1 || { echo "Error: docker is required"; exit 1; }

# Build the Docker image
echo "Building Docker image..."
cd "$PROJECT_ROOT"

docker build \
    --build-arg BUILD_RADIANT_WALLET=ON \
    --build-arg BUILD_RADIANT_ZMQ=ON \
    -t "$IMAGE_NAME" \
    -f "$SCRIPT_DIR/Dockerfile" \
    .

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Save image as tarball
echo ""
echo "Saving Docker image..."
rm -f "$OUTPUT_DIR/$RELEASE_NAME.tar.gz"
docker save "$IMAGE_NAME" | gzip > "$OUTPUT_DIR/$RELEASE_NAME.tar.gz"

# Generate checksum
cd "$OUTPUT_DIR"
if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$RELEASE_NAME.tar.gz" > "$RELEASE_NAME.tar.gz.sha256"
else
    shasum -a 256 "$RELEASE_NAME.tar.gz" > "$RELEASE_NAME.tar.gz.sha256"
fi
echo "Checksum: $(cat "$RELEASE_NAME.tar.gz.sha256" | cut -d' ' -f1)"
echo "File: $RELEASE_NAME.tar.gz"

# Verify wallet support
echo ""
echo "Verifying wallet support in Docker image..."
if docker run --rm "$IMAGE_NAME" radiant-cli -help 2>&1 | grep -q "wallet"; then
    echo "✓ Wallet support: ENABLED"
else
    if docker run --rm "$IMAGE_NAME" radiantd -help 2>&1 | grep -q "wallet"; then
        echo "✓ Wallet support: ENABLED"
    else
        echo "⚠ Warning: Could not verify wallet support"
    fi
fi

echo ""
echo "========================================"
echo "Build complete!"
echo "Output: $OUTPUT_DIR/$RELEASE_NAME.tar.gz"
echo ""
echo "To load: docker load < $OUTPUT_DIR/$RELEASE_NAME.tar.gz"
echo "To run:  docker run -d --name radiant-node $IMAGE_NAME"
echo "========================================"
