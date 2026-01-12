#!/bin/bash
set -e

# Start radiantd in background
echo "Starting Radiant Node (Testnet)..."
./build/src/radiantd -conf=/home/radiant/radiant-testnet.conf -daemon

# Wait for node to warm up
echo "Waiting for node to initialize..."
sleep 15

# Verify connection
echo "Checking node status..."
./build/src/radiant-cli -conf=/home/radiant/radiant-testnet.conf -rpcuser=testnet -rpcpassword=testnetpass123 getblockchaininfo || echo "Node not ready yet..."

# Setup wallet for mining
echo "Setting up mining wallet..."
./build/src/radiant-cli -conf=/home/radiant/radiant-testnet.conf -rpcuser=testnet -rpcpassword=testnetpass123 createwallet "miner" 2>/dev/null || echo "Wallet may already exist"
./build/src/radiant-cli -conf=/home/radiant/radiant-testnet.conf -rpcuser=testnet -rpcpassword=testnetpass123 loadwallet "miner" 2>/dev/null || echo "Wallet already loaded"

# Test wallet
echo "Testing wallet..."
MINING_ADDRESS=$(./build/src/radiant-cli -conf=/home/radiant/radiant-testnet.conf -rpcuser=testnet -rpcpassword=testnetpass123 -rpcwallet=miner getnewaddress)
echo "Mining address: $MINING_ADDRESS"

# Start Miner in background
echo "Starting Miner..."
export PROJECT_DIR=/home/radiant
export RPC_USER=testnet
export RPC_PASS=testnetpass123
export RPC_PORT=27332
export NETWORK=testnet

python3 mining/radiant_gpu_miner.py
