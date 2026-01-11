#!/bin/bash

# Radiant Mining Node Starter
# Starts radiantd with optimal mining configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Radiant Mining Node Starter ===${NC}"
echo

# Default settings
NETWORK="testnet"
PROFILE="mining"
RPC_USER="testnet"
RPC_PASS="testnetpass123"
RPC_PORT="27332"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mainnet)
            NETWORK="mainnet"
            RPC_PORT="8332"
            shift
            ;;
        --profile=*)
            PROFILE="${1#*=}"
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
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --mainnet        Use mainnet instead of testnet"
            echo "  --profile=PROFILE Node profile (archive|agent|mining)"
            echo "  --rpc-user=USER  RPC username"
            echo "  --rpc-pass=PASS  RPC password"
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
echo "  Profile: $PROFILE"
echo "  RPC Port: $RPC_PORT"
echo "  Project Dir: $PROJECT_DIR"
echo

# Check if radiantd exists
if [ ! -f "$PROJECT_DIR/build/src/radiantd" ]; then
    echo -e "${RED}Error: radiantd not found at $PROJECT_DIR/build/src/radiantd${NC}"
    echo "Please build Radiant first:"
    echo "  cd $PROJECT_DIR"
    echo "  mkdir -p build && cd build"
    echo "  cmake .. && make"
    exit 1
fi

# Check if node is already running
if pgrep -f "radiantd.*$NETWORK" > /dev/null; then
    echo -e "${YELLOW}Warning: radiantd is already running for $NETWORK${NC}"
    echo "Stopping existing node..."
    pkill -f "radiantd.*$NETWORK" || true
    sleep 2
fi

# Create data directory if needed
DATADIR="$HOME/.radiant_$NETWORK"
mkdir -p "$DATADIR"

echo -e "${GREEN}Starting Radiant node with mining profile...${NC}"

# Start the node
cd "$PROJECT_DIR"
./build/src/radiantd \
    -$NETWORK \
    -nodeprofile=$PROFILE \
    -server \
    -rpcuser=$RPC_USER \
    -rpcpassword=$RPC_PASS \
    -rpcport=$RPC_PORT \
    -datadir="$DATADIR" \
    -daemon

echo -e "${GREEN}Node started!${NC}"
echo
echo "RPC Settings:"
echo "  User: $RPC_USER"
echo "  Pass: $RPC_PASS"
echo "  Port: $RPC_PORT"
echo
echo "To start mining:"
echo "  ./mining/start_gpu_miner.sh"
echo
echo "To monitor:"
echo "  ./mining/monitor.sh"
