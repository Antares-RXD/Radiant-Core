# Pool Operator Guide for Radiant Core

This guide covers common configuration issues and solutions for mining pool operators running Radiant Core nodes.

## Quick Start Configuration

A minimal `radiant.conf` for pool operations:

```ini
# Core settings
server=1
daemon=1
txindex=1
listen=1

# RPC (required for pool software)
rpcuser=youruser
rpcpassword=yourpassword
rpcallowip=127.0.0.1
rpcport=7332

# P2P
port=7333

# Performance (adjust based on hardware)
dbcache=2048
par=4
maxconnections=64

# ZMQ (if your pool software uses it)
zmqpubrawblock=tcp://127.0.0.1:29332
zmqpubrawtx=tcp://127.0.0.1:29333

# Logging
debug=0
```

## Common Issues and Solutions

### 1. "Daemon does not own pool-address"

**Error:**
```
Daemon does not own pool-address '1YourPoolAddress...'
```

**Cause:** The node's wallet doesn't have the private key for the pool payout address.

**Solutions:**

**Option A: Import the private key**
```bash
radiant-cli importprivkey "YOUR_PRIVATE_KEY_WIF" "pool-wallet" false
```

**Option B: Copy wallet from existing node**
1. Stop both daemons
2. Copy `~/.radiant/wallet.dat` from the old node
3. Restart the daemon

**Option C: Generate a new address** (if key is lost)
```bash
radiant-cli getnewaddress "pool-wallet"
```
Then update your pool software configuration with the new address.

---

### 2. "var idle" or Pool Not Receiving Work

**Symptoms:**
- Pool software shows "var idle"
- No "Share accepted" or "Broadcasting job" messages
- Miners connected but not receiving work

**Cause:** Pool software cannot connect to the daemon's RPC.

**Diagnostic Steps:**

1. **Verify daemon is synced:**
```bash
radiant-cli getblockchaininfo
```
Check that `blocks` equals `headers` and matches current network height.

2. **Test getblocktemplate:**
```bash
radiant-cli getblocktemplate
```
Should return JSON with block template data.

3. **Test RPC connectivity:**
```bash
curl --user youruser:yourpassword \
     --data-binary '{"jsonrpc":"1.0","method":"getblocktemplate","params":[]}' \
     -H 'content-type:text/plain;' \
     http://127.0.0.1:7332/
```

**Solution:** Ensure your pool software's daemon configuration matches your `radiant.conf`:

| Setting | Must Match |
|---------|------------|
| RPC Host | `rpcbind` value (usually `127.0.0.1`) |
| RPC Port | `rpcport` value |
| RPC User | `rpcuser` value |
| RPC Password | `rpcpassword` value |

Example pool software config:
```json
{
  "daemons": [{
    "host": "127.0.0.1",
    "port": 7332,
    "user": "youruser",
    "password": "yourpassword"
  }]
}
```

---

### 3. "Unable to bind to 127.0.0.1:7334"

**Error:**
```
Unable to bind to 127.0.0.1:7334 on this computer. Radiant Core is probably already running.
```

**Cause:** Port 7334 is the Tor onion service target port. If you're running multiple nodes on the same machine, they'll conflict on this port.

**Solution:** Disable Tor binding on the secondary node by adding to `radiant.conf`:
```ini
listenonion=0
```

---

### 4. Running Multiple Nodes on One Machine

When running multiple Radiant Core nodes on the same machine, each node needs unique ports:

**Node 1 (Primary):**
```ini
port=7333
rpcport=7332
zmqpubrawblock=tcp://127.0.0.1:29332
zmqpubrawtx=tcp://127.0.0.1:29333
```

**Node 2 (Secondary):**
```ini
port=7433
rpcport=7432
zmqpubrawblock=tcp://127.0.0.1:29432
zmqpubrawtx=tcp://127.0.0.1:29433
listenonion=0
datadir=/path/to/node2/data
```

**Important:** Update your pool software to connect to the correct `rpcport` for each node.

---

### 5. Block Rejection / Orphaned Blocks

**Symptoms:**
- Pool finds blocks but they show as "Invalid" or "Orphaned"
- Daemon logs show `bad-fork-prior-to-checkpoint` or similar errors

**Common Causes:**

1. **Node not synced:** Ensure your node is fully synced before mining
2. **Outdated node version:** Update to the latest Radiant Core release
3. **Network connectivity:** Ensure good connectivity to other nodes (`connections` should be 8+)

**Diagnostic:**
```bash
radiant-cli getblockchaininfo
radiant-cli getnetworkinfo
```

---

## Recommended Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB |
| Storage | 100 GB SSD | 500 GB NVMe |
| Network | 100 Mbps | 1 Gbps |

For high-volume pools, consider:
```ini
dbcache=4096
par=8
maxconnections=128
```

---

## Default Ports Reference

| Network | P2P Port | RPC Port | Onion Port |
|---------|----------|----------|------------|
| Mainnet | 7333 | 7332 | 7334 |
| Testnet | 27333 | 27332 | 27334 |
| Scalenet | 37333 | 37332 | 37334 |
| Regtest | 18444 | 18443 | 18445 |

---

## Useful Commands

```bash
# Check sync status
radiant-cli getblockchaininfo

# Check network connectivity
radiant-cli getnetworkinfo

# Check mempool
radiant-cli getmempoolinfo

# Get block template (what pools use)
radiant-cli getblocktemplate

# List wallet addresses
radiant-cli listreceivedbyaddress 0 true

# Check if address is in wallet
radiant-cli getaddressinfo "1YourAddress..."

# View recent log entries
tail -100 ~/.radiant/debug.log
```

---

## Getting Help

- GitHub Issues: https://github.com/radiantblockchain/radiant-node/issues
- Documentation: https://radiantblockchain.org/docs

---

*Last updated: January 2026*
