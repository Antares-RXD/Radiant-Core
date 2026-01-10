#!/bin/bash

# Radiant GPU Miner Starter
# Starts the GPU miner with proper configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Radiant GPU Miner Starter ===${NC}"
echo

# Default settings
NETWORK="testnet"
RPC_USER="testnet"
RPC_PASS="testnetpass123"
RPC_PORT="17332"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MINER_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mainnet)
            NETWORK="mainnet"
            RPC_PORT="8332"
            shift
            ;;
        --rpc-user=*)
            RPC_USER="${1#*=}"
            shift
            ;;
        --rpc-pass=*)
            RPC_PASS="${1#*=}"
            shift
            ;;
        --python=*)
            PYTHON="${1#*=}"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --mainnet        Use mainnet instead of testnet"
            echo "  --rpc-user=USER  RPC username"
            echo "  --rpc-pass=PASS  RPC password"
            echo "  --python=PATH    Python executable path"
            echo "  --help           Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${YELLOW}Configuration:${NC}"
echo "  Network: $NETWORK"
echo "  RPC Port: $RPC_PORT"
echo "  Miner Dir: $MINER_DIR"
echo "  Project Dir: $PROJECT_DIR"
echo

# Auto-detect Python if not specified
if [ -z "$PYTHON" ]; then
    # Try Python 3.11 first (for PyOpenCL compatibility)
    PYTHON=$(command -v python3.11 2>/dev/null || command -v python3 2>/dev/null || echo "python3")
fi

echo -e "${YELLOW}Using Python: $PYTHON${NC}"

# Check dependencies
echo "Checking dependencies..."
if ! $PYTHON -c "import pyopencl" 2>/dev/null; then
    echo -e "${RED}Error: PyOpenCL not installed${NC}"
    echo "Install with:"
    echo "  pip install pyopencl numpy"
    exit 1
fi

if ! $PYTHON -c "import numpy" 2>/dev/null; then
    echo -e "${RED}Error: NumPy not installed${NC}"
    echo "Install with:"
    echo "  pip install numpy"
    exit 1
fi

# Check if miner exists
MINER_SCRIPT="$MINER_DIR/radiant_gpu_miner.py"
if [ ! -f "$MINER_SCRIPT" ]; then
    echo -e "${RED}Error: GPU miner not found at $MINER_SCRIPT${NC}"
    exit 1
fi

# Check if node is running
echo "Checking node connection..."
if ! $PROJECT_DIR/build/src/radiant-cli -$NETWORK -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS -rpcport=$RPC_PORT getblockcount >/dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to Radiant node${NC}"
    echo "Make sure the node is running with:"
    echo "  ./mining/start_mining_node.sh"
    exit 1
fi

# Get block count
BLOCK_COUNT=$($PROJECT_DIR/build/src/radiant-cli -$NETWORK -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS -rpcport=$RPC_PORT getblockcount)
echo -e "${GREEN}Connected to node (block height: $BLOCK_COUNT)${NC}"

# Set environment variables
export RPC_USER=$RPC_USER
export RPC_PASS=$RPC_PASS
export RPC_PORT=$RPC_PORT
export PROJECT_DIR=$PROJECT_DIR
export NETWORK=$NETWORK

echo -e "${GREEN}Starting GPU miner...${NC}"
echo "Press Ctrl+C to stop mining"
echo

# Start the miner
cd "$MINER_DIR"
exec $PYTHON radiant_gpu_miner.py
