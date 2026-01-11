#!/bin/bash
set -e

# Start radiantd in daemon mode so we can run the miner in foreground
echo "Starting Radiant Node (Testnet)..."
./build/src/radiantd -conf=/home/radiant/radiant-testnet.conf -daemon

# Wait for node to warm up
echo "Waiting for node to initialize..."
sleep 15

# Verify connection
echo "Checking node status..."
./build/src/radiant-cli -conf=/home/radiant/radiant-testnet.conf -rpcuser=testnet -rpcpassword=testnetpass123 getblockchaininfo || echo "Node not ready yet..."

# Start Miner
echo "Starting Miner..."
export PROJECT_DIR=/home/radiant
export RPC_USER=testnet
export RPC_PASS=testnetpass123
export RPC_PORT=27332
export NETWORK=testnet

python3 mining/radiant_gpu_miner.py
