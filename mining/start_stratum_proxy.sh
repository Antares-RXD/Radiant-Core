#!/bin/bash

# Radiant Stratum Proxy Starter
# Bridges ASIC miners to Radiant node

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Radiant Stratum Proxy Starter ===${NC}"
echo

# Default settings
NETWORK="testnet"
RPC_USER="${RPC_USER:-}"
RPC_PASS="${RPC_PASS:-}"
RPC_PORT="27332"

# Validate credentials
if [ -z "$RPC_USER" ] || [ -z "$RPC_PASS" ]; then
    echo -e "${RED}ERROR: RPC_USER and RPC_PASS environment variables are required${NC}"
    echo "Set them before running:"
    echo "  export RPC_USER=your_rpc_username"
    echo "  export RPC_PASS=your_rpc_password"
    exit 1
fi
STRATUM_PORT="3333"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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
        --port=*)
            STRATUM_PORT="${1#*=}"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --mainnet        Use mainnet instead of testnet"
            echo "  --rpc-user=USER  RPC username"
            echo "  --rpc-pass=PASS  RPC password"
            echo "  --port=PORT      Stratum port (default: 3333)"
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
echo "  Stratum Port: $STRATUM_PORT"
echo "  Project Dir: $PROJECT_DIR"
echo

# Check if node is running
echo -e "${BLUE}Checking node connection...${NC}"
if ! $PROJECT_DIR/build/src/radiant-cli -$NETWORK -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS -rpcport=$RPC_PORT getblockcount >/dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to Radiant node${NC}"
    echo "Make sure the node is running with:"
    echo "  ./mining/start_mining_node.sh"
    exit 1
fi

# Get node info
BLOCK_COUNT=$($PROJECT_DIR/build/src/radiant-cli -$NETWORK -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS -rpcport=$RPC_PORT getblockcount)
echo -e "${GREEN}Connected to node (block height: $BLOCK_COUNT)${NC}"

# Get node IP
NODE_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || hostname -I | awk '{print $1}')
if [ -z "$NODE_IP" ]; then
    NODE_IP="localhost"
fi

echo
echo -e "${GREEN}Starting Stratum Proxy...${NC}"
echo -e "${YELLOW}ASIC Connection Details:${NC}"
echo "  URL: stratum+tcp://$NODE_IP:$STRATUM_PORT"
echo "  Worker: radiant.YOUR_WORKER_NAME"
echo "  Password: (any value or leave blank)"
echo
echo -e "${YELLOW}ASIC Configuration Examples:${NC}"
echo
echo "Antminer:"
echo "  URL: stratum+tcp://$NODE_IP:$STRATUM_PORT"
echo "  Worker: radiant.ASIC_01"
echo
echo "WhatsMiner:"
echo "  Pool URL: stratum+tcp://$NODE_IP:$STRATUM_PORT"
echo "  Worker: radiant.ASIC_01"
echo
echo "cgminer:"
echo "  cgminer --url stratum+tcp://$NODE_IP:$STRATUM_PORT \\"
echo "           --user radiant.ASIC_01 \\"
echo "           --pass x"
echo
echo -e "${BLUE}Press Ctrl+C to stop the proxy${NC}"
echo

# Set environment variables
export RPC_USER=$RPC_USER
export RPC_PASS=$RPC_PASS
export RPC_PORT=$RPC_PORT
export PROJECT_DIR=$PROJECT_DIR
export NETWORK=$NETWORK

# Start the stratum proxy
cd "$PROJECT_DIR/mining"
exec python3 stratum_proxy.py
