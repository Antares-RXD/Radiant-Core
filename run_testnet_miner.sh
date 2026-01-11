#!/bin/bash
set -e

# Change to the script's directory (project root)
cd "$(dirname "$0")"

# Configuration
export PROJECT_DIR=$(pwd)
export RPC_USER=testnet
export RPC_PASS=testnetpass123
export RPC_PORT=27332
export NETWORK=testnet
# Fix for PyOpenCL caching error
export PYOPENCL_NO_CACHE=1
export PYOPENCL_COMPILER_OUTPUT=1

echo "--- Starting Radiant Testnet Environment ---"
echo "Project Dir: $PROJECT_DIR"

# 1. Start Radiant Node
if pgrep -x "radiantd" > /dev/null; then
    echo "radiantd is already running."
else
    echo "Starting radiantd..."
    if [ ! -f "./build/src/radiantd" ]; then
        echo "Error: ./build/src/radiantd not found!"
        exit 1
    fi
    ./build/src/radiantd -conf=$(pwd)/radiant-testnet.conf -daemon
    echo "Waiting 15s for node to initialize..."
    sleep 15
fi

# 2. Add Peers Manually (DNS seeds resolved)
echo "Adding known peers..."
./build/src/radiant-cli -conf=$(pwd)/radiant-testnet.conf -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS addnode "65.21.202.110" "add" || true
./build/src/radiant-cli -conf=$(pwd)/radiant-testnet.conf -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS addnode "158.69.117.205" "add" || true
./build/src/radiant-cli -conf=$(pwd)/radiant-testnet.conf -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS addnode "194.163.159.47" "add" || true

# 3. Check Connection
echo "Verifying RPC connection..."
./build/src/radiant-cli -conf=$(pwd)/radiant-testnet.conf -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS getblockchaininfo

echo "Waiting for connections (will proceed anyway after timeout)..."
MAX_RETRIES=6
count=0
while [ $count -lt $MAX_RETRIES ]; do
    CONN=$(./build/src/radiant-cli -conf=$(pwd)/radiant-testnet.conf -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS getconnectioncount)
    echo "Connection count: $CONN"
    if [ "$CONN" -gt 0 ]; then
        break
    fi
    sleep 5
    count=$((count+1))
done

# 4. Create/Load Wallet (miner needs an address)
echo "Ensuring wallet exists and is loaded..."
# Try to create wallet (fails if exists)
./build/src/radiant-cli -conf=$(pwd)/radiant-testnet.conf -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS createwallet "miner" || \
# If create failed, try to load it (fails if already loaded or doesn't exist, but create would have succeeded if it didn't exist)
./build/src/radiant-cli -conf=$(pwd)/radiant-testnet.conf -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS loadwallet "miner" || \
echo "Wallet 'miner' likely already loaded or error occurred."

# 5. Start Miner
echo "Starting GPU Miner..."
# Ensure no other miner instance is running
pkill -f radiant_gpu_miner.py || true
python3 mining/radiant_gpu_miner.py
