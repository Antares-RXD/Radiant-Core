# Radiant Core Testnet Guide

This guide covers how to create and run a testnet for testing Radiant Core node software and changes.

---

## Quick Answer: Do You Need a Pool?

**No, you do NOT need a mining pool for testing.** 

For local testing, use **regtest mode** which allows instant block generation via RPC commands. For multi-node testing across networks, you can use the public testnets or create a private testnet where CPU mining works fine.

---

## Available Test Networks

Radiant Core supports multiple test networks:

| Network    | Flag        | P2P Port | RPC Port | Use Case |
|------------|-------------|----------|----------|----------|
| **Regtest**| `-regtest`  | 18444    | 17443    | Local dev, instant blocks, isolated testing |
| Testnet    | `-testnet`  | 27333    | 27332    | Public testnet (current stable) |
| Scalenet   | `-scalenet` | 38333    | 37332    | High-throughput stress testing |

**Recommended for testing changes: Use `regtest` mode first, then `testnet` for broader testing.**

---

## Option 1: Regtest Mode (Recommended for Local Testing)

Regtest (regression test) mode is ideal for:
- Testing code changes locally
- Instant block generation (no mining required)
- Complete control over the blockchain
- Isolated environment

### Step 1: Create Regtest Configuration

Create a configuration file (see `contrib/conf/radiant-regtest.conf` for example):

```ini
# Regtest Configuration
regtest=1
server=1
daemon=0
txindex=1

# RPC Settings
rpcuser=regtest
rpcpassword=regtest123
rpcallowip=127.0.0.1
rpcport=17443

# Network
listen=1
port=18444

# Logging
debug=1
printtoconsole=1

# Data directory (optional - use separate dir for regtest)
# datadir=./data-regtest
```

### Step 2: Start the Node

```bash
# Windows (via WSL2, from build directory)
./radiantd -conf=radiant-regtest.conf

# Or with flags directly
./radiantd -regtest -server -rpcuser=regtest -rpcpassword=regtest123
```

### Step 3: Generate Blocks (No Mining Pool Needed!)

In regtest mode, use the `generatetoaddress` RPC command to instantly create blocks:

```bash
# First, create a wallet and get an address
./radiant-cli -regtest -rpcuser=regtest -rpcpassword=regtest123 createwallet "testwallet"
./radiant-cli -regtest -rpcuser=regtest -rpcpassword=regtest123 getnewaddress

# Generate 101 blocks to your address (101 needed for coinbase maturity)
./radiant-cli -regtest -rpcuser=regtest -rpcpassword=regtest123 generatetoaddress 101 "YOUR_ADDRESS_HERE"

# Check your balance
./radiant-cli -regtest -rpcuser=regtest -rpcpassword=regtest123 getbalance
```

### Step 4: Useful Regtest RPC Commands

```bash
# Get blockchain info
radiant-cli -regtest getblockchaininfo

# Get mining info
radiant-cli -regtest getmininginfo

# Generate more blocks
radiant-cli -regtest generatetoaddress 10 "YOUR_ADDRESS"

# Send transaction
radiant-cli -regtest sendtoaddress "DESTINATION_ADDRESS" 10

# Generate a block to confirm transaction
radiant-cli -regtest generatetoaddress 1 "YOUR_ADDRESS"

# Get mempool info
radiant-cli -regtest getmempoolinfo
```

---

## Option 2: Private Multi-Node Testnet

For testing with multiple nodes (e.g., simulating network conditions):

### Node 1 Configuration (`node1.conf`)

```ini
regtest=1
server=1
daemon=0
txindex=1
rpcuser=node1
rpcpassword=node1pass
rpcport=17443
port=18444
listen=1
datadir=./data-node1
debug=1
```

### Node 2 Configuration (`node2.conf`)

```ini
regtest=1
server=1
daemon=0
txindex=1
rpcuser=node2
rpcpassword=node2pass
rpcport=17444
port=18445
listen=1
datadir=./data-node2
connect=127.0.0.1:18444
debug=1
```

### Start Both Nodes

```bash
# Terminal 1
./radiantd -conf=node1.conf

# Terminal 2
./radiantd -conf=node2.conf
```

### Verify Connection

```bash
./radiant-cli -rpcport=17443 -rpcuser=node1 -rpcpassword=node1pass getpeerinfo
./radiant-cli -rpcport=17444 -rpcuser=node2 -rpcpassword=node2pass getpeerinfo
```

---

## Option 3: Public Testnet

For testing with the wider community on a shared testnet:

### Configuration (see `contrib/conf/radiant-testnet.conf`)

```ini
testnet=1
server=1
daemon=0
txindex=1
rpcuser=testnetuser
rpcpassword=testnetpass
rpcallowip=127.0.0.1
rpcport=27332
debug=1
```

### Start Node

```bash
./radiantd -conf=radiant-testnet.conf
```

### Get Testnet Coins

- Use a testnet faucet (if available)
- CPU mine on testnet (low difficulty, designed to be CPU-mineable)

---

## Key Chain Parameters Reference

From `src/chainparams.cpp` and `src/chainparamsbase.cpp`:

### Regtest Parameters
- **Network ID**: `regtest`
- **P2P Port**: 18444
- **RPC Port**: 17443
- **POW Limit**: `0x7fff...` (very easy - instant mining)
- **Block Target**: 5 minutes
- **Halving Interval**: 150 blocks
- **No retargeting**: true (difficulty stays constant)
- **Genesis Block**: Pre-defined test genesis

### Key Consensus Heights (Regtest)
- **BIP16**: 0 (always active)
- **BIP65**: 1351
- **BIP66**: 1251
- **CSV**: 576
- **ERHeight**: 100
- **PushTXStateHeight**: 110
- **radiantCore2UpgradeHeight**: 200

---

## Testing Workflow

### Basic Testing Workflow

1. **Start regtest node**
2. **Create wallet**: `createwallet "test"`
3. **Get address**: `getnewaddress`
4. **Generate initial blocks**: `generatetoaddress 101 "ADDRESS"` (maturity)
5. **Test your changes** (transactions, scripts, etc.)
6. **Generate blocks as needed** to confirm transactions

### Testing Specific Features

For testing consensus changes:
```bash
# Generate blocks up to a specific height to trigger upgrades
# e.g., to test ERHeight (100) in regtest:
radiant-cli -regtest generatetoaddress 100 "ADDRESS"
```

### Running Functional Tests

The project includes functional tests in `test/functional/`:

```bash
# Run all functional tests
python test/functional/test_runner.py

# Run specific test
python test/functional/test_runner.py abc-cmdline.py

# Run with regtest
python test/functional/feature_block.py
```

---

## Troubleshooting

### Common Issues

1. **"Cannot obtain a lock on data directory"**
   - Another instance is running, or stale lock file
   - Solution: Stop other instance or delete `.lock` file in datadir

2. **"Error: Unable to bind to 0.0.0.0:18444"**
   - Port already in use
   - Solution: Change port or stop conflicting process

3. **RPC connection refused**
   - Node not running or RPC not enabled
   - Solution: Ensure `server=1` and check rpcport

4. **Blocks not generating**
   - Only works in regtest mode
   - Solution: Verify `-regtest` flag is set

### Reset Regtest Chain

To start fresh:
```bash
# Stop node first, then delete data directory
rm -rf ./data-regtest
# Or on Windows:
rmdir /s /q data-regtest
```

---

## Quick Start Commands Summary

```bash
# === START REGTEST NODE ===
./radiantd -regtest -server -rpcuser=test -rpcpassword=test123 -printtoconsole

# === IN ANOTHER TERMINAL ===
# Create wallet
./radiant-cli -regtest -rpcuser=test -rpcpassword=test123 createwallet "testwallet"

# Get new address
./radiant-cli -regtest -rpcuser=test -rpcpassword=test123 getnewaddress
# Example output: mkESjLZW66TmHhiFX8MCaBjrhZ543PPh9a

# Generate 101 blocks (replace with your address)
./radiant-cli -regtest -rpcuser=test -rpcpassword=test123 generatetoaddress 101 "mkESjLZW66TmHhiFX8MCaBjrhZ543PPh9a"

# Check balance (should have ~50000 RAD per mature block)
./radiant-cli -regtest -rpcuser=test -rpcpassword=test123 getbalance

# Get blockchain info
./radiant-cli -regtest -rpcuser=test -rpcpassword=test123 getblockchaininfo
```

---

## Notes

- **Regtest coins have no value** - they're for testing only
- **Regtest is isolated** - no connection to mainnet or public testnets
- **Block reward in regtest**: 50,000 RAD per block (same as mainnet)
- **Coinbase maturity**: 100 blocks (need 101 blocks to spend first coinbase)
- **No mining pool needed** for regtest - use `generatetoaddress` RPC

---

---

## Public Testnet Strategy for ASERT Upgrade Testing

### The Critical Test: `radiantCore2UpgradeHeight`

The ASERT half-life tuning change activates at different heights per network:

| Network   | radiantCore2UpgradeHeight | Current Status |
|-----------|---------------------------|-----------------|
| Mainnet   | 410,000                   | Production     |
| Testnet   | **1,000**                 | Fast testing   |
| Scalenet  | 410,000                   | Variable       |
| Regtest   | **200**                   | Easy to test   |

### Options for Testing ASERT Change

#### Option A: Use Regtest (Fastest)

Regtest has `radiantCore2UpgradeHeight = 200`, so you can test the upgrade with:
```bash
radiant-cli -regtest generatetoaddress 201 "ADDRESS"
# Now past the upgrade height - test ASERT behavior
```

#### Option B: Fresh Testnet (Recommended for Community Proof)

Testnet is designed to be lightweight and restartable. Since block 1000 is the target:

1. **Check current testnet height** (if running)
2. **If testnet < 1,000 blocks:** Continue mining to reach 1k
3. **If testnet > 1,000 blocks:** Upgrade already active

**To reset testnet (if needed):**
- Invalidate a block and checkpoint a new one
- Or start fresh genesis (requires code change + coordination)

#### Option C: Private Testnet with Custom Upgrade Height

For faster testing, modify `chainparams.cpp` to set a lower upgrade height:

```cpp
// In CTestNetParams constructor:
consensus.radiantCore2UpgradeHeight = 100;  // Instead of 1000
```

Then rebuild and run a private testnet.

### Checking Testnet Status

**Testnet DNS Seeds (from chainparams.cpp):**
- `node-testnet.radiantblockchain.org`
- `node-testnet.radiantone.org`
- `node-testnet.radiantlayerone.com`
- `node-testnet.radiantchain.org`
- `node-testnet.radiantnode.org`

**To check if testnet is running:**
```bash
# Try connecting
radiantd -testnet -printtoconsole

# Or check DNS seeds
nslookup node-testnet.radiantblockchain.org
```

### Do You Need a Mining Pool?

**For public testnet: Depends on difficulty.**

- Testnet has `fPowAllowMinDifficultyBlocks = true` and 1-hour ASERT half-life
- After 20 minutes without blocks, difficulty drops to minimum
- **CPU mining should work** on testnet after difficulty drops

**For regtest: No pool needed** - use `generatetoaddress` RPC.

### Recommended Testing Workflow

1. **Fix the libevent build bug first** (critical)
2. **Test on regtest** - verify ASERT changes work at height 200+
3. **Run functional tests** - `test/functional/` has existing tests
4. **Deploy to testnet** - mine/sync to block 1k
5. **Document results** for community

---

## Action Items

- [ ] **FIX:** Rebuild with real libevent library
- [ ] **TEST:** Run regtest to height 201+ to verify ASERT upgrade
- [ ] **CHECK:** Query testnet DNS seeds to see if network is active
- [ ] **MINE:** If testnet is below 1k, mine to reach upgrade height
- [ ] **VERIFY:** Confirm ASERT behavior change at block 1000

---

*Last updated: January 8, 2026*
*Based on Radiant Core source code analysis*
*Build tested: v2.1.0*
