#!/bin/bash

# Radiant Mining Suite Installer
# Sets up dependencies and configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Radiant Mining Suite Installer ===${NC}"
echo

# Detect Python versions
echo -e "${BLUE}Detecting Python installation...${NC}"

PYTHON311=$(command -v python3.11 2>/dev/null || echo "")
PYTHON3=$(command -v python3 2>/dev/null || echo "")
PYTHON=$(command -v python 2>/dev/null || echo "")

# Choose best Python
if [ ! -z "$PYTHON311" ]; then
    PYTHON="$PYTHON311"
    echo -e "${GREEN}✓ Found Python 3.11: $PYTHON${NC}"
elif [ ! -z "$PYTHON3" ]; then
    PYTHON="$PYTHON3"
    PYTHON_VERSION=$($PYTHON --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)
    echo -e "${YELLOW}✓ Found Python $PYTHON_VERSION: $PYTHON${NC}"
    if [ "${PYTHON_VERSION%%.*}" -lt 3 ] || [ "${PYTHON_VERSION#*.}" -lt 8 ]; then
        echo -e "${RED}Warning: Python 3.8+ recommended for best compatibility${NC}"
    fi
elif [ ! -z "$PYTHON" ]; then
    echo -e "${YELLOW}✓ Found Python: $PYTHON${NC}"
    echo -e "${YELLOW}Note: python3.11 recommended for PyOpenCL compatibility${NC}"
else
    echo -e "${RED}✗ No Python found${NC}"
    echo "Please install Python 3.11+ first"
    exit 1
fi

echo

# Check pip
echo -e "${BLUE}Checking pip installation...${NC}"
if ! $PYTHON -m pip --version >/dev/null 2>&1; then
    echo -e "${RED}✗ pip not found${NC}"
    echo "Installing pip..."
    if command -v curl >/dev/null 2>&1; then
        curl https://bootstrap.pypa.io/get-pip.py | $PYTHON
    else
        echo "Please install pip manually"
        exit 1
    fi
else
    echo -e "${GREEN}✓ pip available${NC}"
fi

echo

# Install dependencies
echo -e "${BLUE}Installing Python dependencies...${NC}"

# Core dependencies
echo "Installing core dependencies..."
$PYTHON -m pip install --upgrade pip
$PYTHON -m pip install numpy

# GPU dependencies (optional)
echo -n "Checking GPU support... "
if $PYTHON -c "import pyopencl" 2>/dev/null; then
    echo -e "${GREEN}✓ PyOpenCL already installed${NC}"
else
    echo -e "${YELLOW}Installing PyOpenCL (GPU mining)...${NC}"
    if $PYTHON -m pip install pyopencl; then
        echo -e "${GREEN}✓ PyOpenCL installed successfully${NC}"
    else
        echo -e "${YELLOW}⚠ PyOpenCL installation failed (GPU mining unavailable)${NC}"
        echo "CPU mining will still work"
    fi
fi

echo

# Create config directory
CONFIG_DIR="$HOME/.radiant_mining"
mkdir -p "$CONFIG_DIR"

# Create default config
CONFIG_FILE="$CONFIG_DIR/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${BLUE}Creating default configuration...${NC}"
    cat > "$CONFIG_FILE" << EOF
{
  "network": "testnet",
  "genesis_hash": "000000000d8ada264d16f87a590b2af320cd3c7e3f9be5482163e830fd00aca2",
  "rpc": {
    "user": "testnet",
    "pass": "testnetpass123",
    "port": 27332,
    "timeout": 30
  },
  "gpu": {
    "enabled": true,
    "batch_size": 4194304,
    "device": "auto",
    "platform": "auto"
  },
  "cpu": {
    "enabled": false,
    "threads": 4,
    "priority": "low"
  },
  "monitoring": {
    "update_interval": 5,
    "log_level": "info",
    "save_stats": true
  }
}
EOF
    echo -e "${GREEN}✓ Config created: $CONFIG_FILE${NC}"
else
    echo -e "${YELLOW}✓ Config already exists: $CONFIG_FILE${NC}"
fi

echo

# Test installation
echo -e "${BLUE}Testing installation...${NC}"

# Test basic Python
echo -n "Testing Python... "
if $PYTHON -c "import sys; print(f'Python {sys.version.split()[0]}')" >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    exit 1
fi

# Test NumPy
echo -n "Testing NumPy... "
if $PYTHON -c "import numpy; print(f'NumPy {numpy.__version__}')" >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    exit 1
fi

# Test PyOpenCL (optional)
echo -n "Testing PyOpenCL... "
if $PYTHON -c "import pyopencl; print(f'PyOpenCL {pyopencl.VERSION_TEXT}')" >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠ Not available (CPU mining only)${NC}"
fi

echo

# Installation summary
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo
echo "Configuration: $CONFIG_FILE"
echo "Python: $PYTHON"
echo
echo "Next steps:"
echo "1. Start Radiant node:"
echo "   ./mining/start_mining_node.sh"
echo
echo "2. Start mining:"
echo "   ./mining/start_mining.sh"
echo
echo "3. Monitor:"
echo "   ./mining/monitor.sh"
echo
echo "For more information, see: mining/README.md"
