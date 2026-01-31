#!/bin/bash

# Radiant ASIC Mining Setup Helper
# Configures node for optimal ASIC mining

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Radiant ASIC Mining Setup ===${NC}"
echo

# Default settings
NETWORK="testnet"
RPC_USER="${RPC_USER:-}"
RPC_PASS="${RPC_PASS:-}"
RPC_PORT="27332"

# Validate credentials are set
if [ -z "$RPC_USER" ] || [ -z "$RPC_PASS" ]; then
    echo -e "${RED}ERROR: RPC_USER and RPC_PASS environment variables are required${NC}"
    echo "Set them before running:"
    echo "  export RPC_USER=your_rpc_username"
    echo "  export RPC_PASS=your_secure_password"
    exit 1
fi
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
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --mainnet        Use mainnet instead of testnet"
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
echo "  RPC Port: $RPC_PORT"
echo "  Project Dir: $PROJECT_DIR"
echo

# Get node IP
echo -e "${BLUE}Getting node IP address...${NC}"
NODE_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || hostname -I | awk '{print $1}')
if [ -z "$NODE_IP" ]; then
    echo -e "${RED}Could not determine node IP${NC}"
    echo "Please enter your node's IP address:"
    read -r NODE_IP
fi

echo -e "${GREEN}Node IP: $NODE_IP${NC}"

# Check if node is running
echo -e "${BLUE}Checking node status...${NC}"
if ! $PROJECT_DIR/build/src/radiant-cli -$NETWORK -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS -rpcport=$RPC_PORT getblockcount >/dev/null 2>&1; then
    echo -e "${YELLOW}Node is not running. Starting with ASIC-optimized settings...${NC}"
    
    # Stop any existing node
    pkill -f "radiantd.*$NETWORK" || true
    sleep 2
    
    # Start node with ASIC-optimized settings
    cd "$PROJECT_DIR"
    
    # Security warning for network binding
    echo -e "${YELLOW}SECURITY WARNING:${NC}"
    echo "RPC will be bound to localhost only for security."
    echo "ASICs connect via Stratum proxy (port 3333), not RPC directly."
    echo ""
    echo "Press ENTER to continue with secure configuration, or Ctrl+C to cancel"
    read -r
    
    ./build/src/radiantd \
        -$NETWORK \
        -nodeprofile=mining \
        -server \
        -rpcuser=$RPC_USER \
        -rpcpassword=$RPC_PASS \
        -rpcport=$RPC_PORT \
        -maxconnections=50 \
        -rpcallowip=127.0.0.1 \
        -rpcbind=127.0.0.1 \
        -daemon
    
    echo ""
    echo -e "${YELLOW}Note: RPC is bound to localhost for security.${NC}"
    echo "ASICs should connect to the Stratum proxy, not directly to RPC."
    echo "The Stratum proxy will communicate with the node via local RPC."
    
    echo -e "${GREEN}Node started with ASIC-optimized settings${NC}"
    sleep 5
else
    echo -e "${GREEN}Node is already running${NC}"
fi

# Verify node is ready
echo -e "${BLUE}Verifying node is ready for mining...${NC}"
for i in {1..10}; do
    if $PROJECT_DIR/build/src/radiant-cli -$NETWORK -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS -rpcport=$RPC_PORT getblockcount >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Node is ready${NC}"
        break
    else
        echo -n "."
        sleep 2
    fi
done

# Get mining info
MINING_INFO=$($PROJECT_DIR/build/src/radiant-cli -$NETWORK -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS -rpcport=$RPC_PORT getmininginfo 2>/dev/null || echo "{}")
BLOCK_COUNT=$(echo "$MINING_INFO" | grep -o '"blocks":[0-9]*' | cut -d: -f2 || echo "unknown")
DIFFICULTY=$(echo "$MINING_INFO" | grep -o '"difficulty":[0-9.]*' | cut -d: -f2 || echo "unknown")

echo
echo -e "${GREEN}=== ASIC Mining Configuration ===${NC}"
echo
echo -e "${YELLOW}Node Information:${NC}"
echo "  IP Address: $NODE_IP"
echo "  Network: $NETWORK"
echo "  Port: $RPC_PORT"
echo "  Block Height: $BLOCK_COUNT"
echo "  Difficulty: $DIFFICULTY"
echo
echo -e "${YELLOW}Stratum Proxy Setup:${NC}"
echo "  ASICs MUST connect via Stratum proxy, not directly to node RPC"
echo "  Start proxy with: ./mining/start_stratum_proxy.sh"
echo "  Default Stratum Port: 3333"
echo
echo -e "${YELLOW}ASIC Configuration Examples:${NC}"
echo
echo "1. Antminer Web Interface:"
echo "   - Go to Miner Configuration"
echo "   - URL: stratum+tcp://$NODE_IP:3333"
echo "   - Worker: your_worker_name"
echo "   - Password: x"
echo "   - Save and restart"
echo
echo "2. cgminer/sgminer:"
echo "   cgminer --url stratum+tcp://$NODE_IP:3333 \\"
echo "           --user your_worker_name \\"
echo "           --pass x"
echo
echo "3. WhatsMiner:"
echo "   - Pool URL: stratum+tcp://$NODE_IP:3333"
echo "   - Worker: your_worker_name"
echo "   - Password: x"
echo
echo -e "${RED}IMPORTANT: Configure ALLOWED_WORKERS before starting stratum proxy!${NC}"
echo "  export ALLOWED_WORKERS=worker1,worker2,worker3"
echo
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Configure allowed workers:"
echo "   export ALLOWED_WORKERS=worker1,worker2"
echo
echo "2. Start Stratum proxy:"
echo "   ./mining/start_stratum_proxy.sh"
echo
echo "3. Configure your ASICs to connect to:"
echo "   stratum+tcp://$NODE_IP:3333"
echo
echo -e "${YELLOW}Monitoring Commands:${NC}"
echo "# Check node status"
echo "./build/src/radiant-cli -$NETWORK getmininginfo"
echo
echo "# Check stratum proxy logs"
echo "tail -f stratum_proxy.log"
echo
echo -e "${GREEN}Setup complete! Configure your ASIC with the connection details above.${NC}"
