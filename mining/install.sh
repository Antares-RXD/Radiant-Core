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
    echo "Installing pip securely..."
    if command -v curl >/dev/null 2>&1; then
        # Download pip installer securely
        curl --fail --location --output /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py
        if [ $? -eq 0 ]; then
            $PYTHON /tmp/get-pip.py
            rm -f /tmp/get-pip.py
        else
            echo -e "${RED}Failed to download pip installer${NC}"
            echo "Please install pip manually: https://pip.pypa.io/en/stable/installation/"
            exit 1
        fi
    else
        echo "Please install pip manually: https://pip.pypa.io/en/stable/installation/"
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
    
    # Generate random credentials for security
    if command -v openssl >/dev/null 2>&1; then
        RPC_USER_GENERATED=$(openssl rand -hex 8)
        RPC_PASS_GENERATED=$(openssl rand -hex 16)
    else
        # Fallback if openssl not available
        RPC_USER_GENERATED="radiant_$(date +%s)"
        RPC_PASS_GENERATED="$(date +%s%N | sha256sum | head -c 32)"
    fi
    
    cat > "$CONFIG_FILE" << EOF
{
  "network": "testnet",
  "genesis_hash": "000000000d8ada264d16f87a590b2af320cd3c7e3f9be5482163e830fd00aca2",
  "rpc": {
    "user": "$RPC_USER_GENERATED",
    "pass": "$RPC_PASS_GENERATED",
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
    echo -e "${YELLOW}✓ Random RPC credentials generated${NC}"
    echo -e "${RED}IMPORTANT: These credentials are also stored in your radiant.conf${NC}"
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

# Create radiant.conf if it doesn't exist
RADIANT_CONF="$HOME/.radiant/radiant.conf"
if [ ! -f "$RADIANT_CONF" ] && [ -f "$CONFIG_FILE" ]; then
    echo -e "${BLUE}Creating radiant.conf with matching credentials...${NC}"
    mkdir -p "$(dirname "$RADIANT_CONF")"
    
    # Extract credentials from config.json
    if command -v python3 >/dev/null 2>&1; then
        RPC_USER_FROM_CONFIG=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['rpc']['user'])" 2>/dev/null)
        RPC_PASS_FROM_CONFIG=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['rpc']['pass'])" 2>/dev/null)
        
        cat > "$RADIANT_CONF" << EOF
# Radiant Configuration File
# Generated by mining setup

# RPC Settings (must match mining config)
server=1
rpcuser=$RPC_USER_FROM_CONFIG
rpcpassword=$RPC_PASS_FROM_CONFIG
rpcallowip=127.0.0.1
rpcbind=127.0.0.1

# Mining optimizations
maxconnections=50

# Testnet (comment out for mainnet)
testnet=1
EOF
        echo -e "${GREEN}✓ Created: $RADIANT_CONF${NC}"
    fi
fi

echo

# Installation summary
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo
echo "Configuration: $CONFIG_FILE"
echo "Node config: $RADIANT_CONF"
echo "Python: $PYTHON"
echo
echo -e "${YELLOW}SECURITY NOTES:${NC}"
echo "• Random RPC credentials have been generated"
echo "• Credentials are in: $CONFIG_FILE"
echo "• Node config is in: $RADIANT_CONF"
echo "• Keep these files secure and backed up"
echo "• Never commit these files to version control"
echo
echo "Next steps:"
echo "1. Review configuration:"
echo "   cat $CONFIG_FILE"
echo
echo "2. Set environment variables (or use config file):"
echo "   export RPC_USER=<from config>"
echo "   export RPC_PASS=<from config>"
echo
echo "3. Start Radiant node:"
echo "   ./mining/start_mining_node.sh"
echo
echo "4. Start mining:"
echo "   ./mining/start_mining.sh"
echo
echo "For more information, see: mining/README.md"
