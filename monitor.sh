#!/bin/bash

echo "=== Radiant Testnet Monitor ==="
echo "Time: $(date)"
echo

echo "📊 Blockchain Info:"
./build/src/radiant-cli -testnet -rpcuser=testnet -rpcpassword=testnetpass123 -rpcport=17332 getblockchaininfo | jq -r '"  Blocks: \(.blocks) | Height: \(.headers) | Best: \(.bestblockhash[:16])..."'
echo

echo "⛏️ Mining Info:"
./build/src/radiant-cli -testnet -rpcuser=testnet -rpcpassword=testnetpass123 -rpcport=17332 getmininginfo | jq -r '"  Difficulty: \(.difficulty) | Network Hash: \(.networkhashps) H/s"'
echo

echo "🌐 Peers:"
./build/src/radiant-cli -testnet -rpcuser=testnet -rpcpassword=testnetpass123 -rpcport=17332 getpeerinfo | jq -r '.[] | "  \(.addr) | Height: \(.startingheight) | Synced: \(.synced_headers)"'
echo

echo "🔥 Recent Blocks:"
for i in {0..4}; do
    hash=$(./build/src/radiant-cli -testnet -rpcuser=testnet -rpcpassword=testnetpass123 -rpcport=17332 getblockhash $i 2>/dev/null)
    if [ ! -z "$hash" ] && [ "$hash" != "" ]; then
        block=$(./build/src/radiant-cli -testnet -rpcuser=testnet -rpcpassword=testnetpass123 -rpcport=17332 getblockheader $hash false 2>/dev/null)
        time=$(echo "$block" | grep -o '"time":[0-9]*' | cut -d: -f2)
        if [ ! -z "$time" ]; then
            formatted=$(date -r $time "+%H:%M:%S" 2>/dev/null || echo "Unknown")
            echo "  Block $i: $formatted | ${hash:0:16}..."
        fi
    fi
done
echo
