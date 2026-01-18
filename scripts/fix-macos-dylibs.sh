#!/bin/bash
#
# Fix macOS Dynamic Library Dependencies for Distribution
# 
# This script bundles Homebrew dylibs with Radiant Core binaries and rewrites
# library paths to use @loader_path, making the binaries portable.
#
# Usage: ./scripts/fix-macos-dylibs.sh <binaries_directory>
# Example: ./scripts/fix-macos-dylibs.sh ./gui/binaries/radiant-core-macos-arm64
#

set -e

BINARIES_DIR="${1:-.}"
LIBS_DIR="$BINARIES_DIR/libs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=============================================="
echo "  macOS Dynamic Library Fixer"
echo "=============================================="
echo ""
echo "Binaries directory: $BINARIES_DIR"

# Check if we're on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo -e "${RED}Error: This script must be run on macOS${NC}"
    exit 1
fi

# Check for required tools
if ! command -v install_name_tool &> /dev/null; then
    echo -e "${RED}Error: install_name_tool not found (requires Xcode Command Line Tools)${NC}"
    exit 1
fi

if ! command -v otool &> /dev/null; then
    echo -e "${RED}Error: otool not found (requires Xcode Command Line Tools)${NC}"
    exit 1
fi

# Create libs directory
mkdir -p "$LIBS_DIR"

# Function to get non-system dylib dependencies (including @loader_path/@rpath for transitive deps)
get_dylib_deps() {
    local binary="$1"
    local include_loader_path="${2:-false}"
    
    if [[ "$include_loader_path" == "true" ]]; then
        # Include @loader_path and @rpath for finding transitive deps in copied libs
        otool -L "$binary" 2>/dev/null | tail -n +2 | awk '{print $1}' | \
            grep -v "^/usr/lib" | \
            grep -v "^/System" | \
            grep -v "^@executable_path" || true
    else
        # Exclude @loader_path/@rpath for initial binary scan
        otool -L "$binary" 2>/dev/null | tail -n +2 | awk '{print $1}' | \
            grep -v "^/usr/lib" | \
            grep -v "^/System" | \
            grep -v "^@executable_path" | \
            grep -v "^@loader_path" | \
            grep -v "^@rpath" || true
    fi
}

# Function to find a dylib in common Homebrew locations
find_dylib() {
    local dylib_path="$1"
    local dylib_name=$(basename "$dylib_path")
    
    # If the exact path exists, use it
    if [[ -f "$dylib_path" ]]; then
        echo "$dylib_path"
        return 0
    fi
    
    # Try common Homebrew locations
    local search_paths=(
        "/opt/homebrew/lib/$dylib_name"
        "/opt/homebrew/opt/*/lib/$dylib_name"
        "/usr/local/lib/$dylib_name"
        "/usr/local/opt/*/lib/$dylib_name"
    )
    
    for pattern in "${search_paths[@]}"; do
        for found in $pattern; do
            if [[ -f "$found" ]]; then
                echo "$found"
                return 0
            fi
        done
    done
    
    return 1
}

# Function to copy a dylib and fix its install name
copy_and_fix_dylib() {
    local dylib_path="$1"
    local dylib_name=$(basename "$dylib_path")
    local dest_path="$LIBS_DIR/$dylib_name"
    
    # Skip if already copied
    if [[ -f "$dest_path" ]]; then
        return 0
    fi
    
    # Try to find the library
    local actual_path=$(find_dylib "$dylib_path")
    if [[ -z "$actual_path" ]]; then
        echo -e "${YELLOW}  Warning: Library not found: $dylib_path${NC}"
        return 1
    fi
    
    dylib_path="$actual_path"
    
    echo "  Copying: $dylib_name"
    cp "$dylib_path" "$dest_path"
    chmod 755 "$dest_path"
    
    # Change the library's own install name to use @loader_path
    install_name_tool -id "@loader_path/libs/$dylib_name" "$dest_path" 2>/dev/null || true
    
    # Recursively process this library's dependencies (including @loader_path/@rpath refs)
    local deps=$(get_dylib_deps "$dest_path" true)
    for dep in $deps; do
        local dep_name=$(basename "$dep")
        
        # Handle @loader_path and @rpath references
        if [[ "$dep" == @loader_path/* ]] || [[ "$dep" == @rpath/* ]]; then
            # Try to find in Homebrew
            local actual_path=$(find_dylib "$dep_name")
            if [[ -n "$actual_path" ]]; then
                copy_and_fix_dylib "$actual_path"
            fi
            # Update to use @loader_path (already correct format for libs dir)
            install_name_tool -change "$dep" "@loader_path/$dep_name" "$dest_path" 2>/dev/null || true
        else
            # Copy the dependency if needed
            copy_and_fix_dylib "$dep"
            # Update the reference in the current library
            install_name_tool -change "$dep" "@loader_path/$dep_name" "$dest_path" 2>/dev/null || true
        fi
    done
    
    return 0
}

# Function to fix a binary's library references
fix_binary() {
    local binary="$1"
    local binary_name=$(basename "$binary")
    
    echo ""
    echo "Processing: $binary_name"
    echo "----------------------------------------"
    
    # Get all non-system dependencies
    local deps=$(get_dylib_deps "$binary")
    
    if [[ -z "$deps" ]]; then
        echo "  No external dependencies to fix"
        return 0
    fi
    
    for dep in $deps; do
        local dep_name=$(basename "$dep")
        
        echo "  Found dependency: $dep_name"
        
        # Copy the dylib
        copy_and_fix_dylib "$dep"
        
        # Update the binary to use @loader_path
        install_name_tool -change "$dep" "@loader_path/libs/$dep_name" "$binary" 2>/dev/null || {
            echo -e "${YELLOW}  Warning: Could not update reference to $dep_name${NC}"
        }
    done
}

# Process main binaries
BINARIES="radiantd radiant-cli radiant-tx"

for bin in $BINARIES; do
    bin_path="$BINARIES_DIR/$bin"
    if [[ -f "$bin_path" ]]; then
        fix_binary "$bin_path"
    else
        echo -e "${YELLOW}Skipping: $bin (not found)${NC}"
    fi
done

# Fix cross-references within the libs directory
echo ""
echo "Fixing cross-references in bundled libraries..."
echo "----------------------------------------"

for lib in "$LIBS_DIR"/*.dylib; do
    if [[ -f "$lib" ]]; then
        lib_name=$(basename "$lib")
        deps=$(get_dylib_deps "$lib")
        for dep in $deps; do
            dep_name=$(basename "$dep")
            if [[ -f "$LIBS_DIR/$dep_name" ]]; then
                install_name_tool -change "$dep" "@loader_path/$dep_name" "$lib" 2>/dev/null || true
            fi
        done
    fi
done

# Verify the fix
echo ""
echo "=============================================="
echo "Verification"
echo "=============================================="

all_good=true
for bin in $BINARIES; do
    bin_path="$BINARIES_DIR/$bin"
    if [[ -f "$bin_path" ]]; then
        echo ""
        echo "$bin dependencies:"
        remaining=$(get_dylib_deps "$bin_path")
        if [[ -z "$remaining" ]]; then
            echo -e "  ${GREEN}✓ All dependencies are bundled${NC}"
        else
            echo -e "  ${RED}✗ External dependencies remain:${NC}"
            echo "$remaining" | sed 's/^/    /'
            all_good=false
        fi
    fi
done

echo ""
if $all_good; then
    echo -e "${GREEN}=============================================="
    echo "  Success! All binaries are now portable."
    echo "==============================================${NC}"
else
    echo -e "${YELLOW}=============================================="
    echo "  Warning: Some external dependencies remain."
    echo "==============================================${NC}"
fi

# Code sign all binaries and libraries (required on macOS)
echo ""
echo "Code signing binaries and libraries..."
echo "----------------------------------------------"

for lib in "$LIBS_DIR"/*.dylib; do
    if [[ -f "$lib" ]]; then
        codesign --force -s - "$lib" 2>/dev/null && echo "  Signed: $(basename "$lib")" || true
    fi
done

for bin in $BINARIES; do
    bin_path="$BINARIES_DIR/$bin"
    if [[ -f "$bin_path" ]]; then
        codesign --force -s - "$bin_path" 2>/dev/null && echo "  Signed: $bin" || true
    fi
done

echo ""
echo "Bundled libraries in $LIBS_DIR:"
ls -la "$LIBS_DIR"
echo ""
echo -e "${GREEN}Done!${NC}"
