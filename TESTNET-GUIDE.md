# Radiant Core Testnet Guide

This guide covers how to create and run a testnet for testing Radiant Core node software and changes.

---

## CRITICAL: Build Bug Discovered

**Date:** January 8, 2026

**Issue:** The current release build (`release/radiant-cli.exe`) is linked against `libevent-stubs.c` instead of real libevent. This causes an assertion failure:
```
Assertion failed: output_headers, file bitcoin-cli.cpp, line 403
```

**Root Cause:** `libevent-stubs.c` (line 105) returns NULL for `evhttp_request_get_output_headers()`.

**Impact:** CLI cannot communicate with the node via RPC. All RPC commands fail.

**Fix Required:** Rebuild with proper libevent linkage:
```bash
# Option 1: MSYS2 MinGW (see BUILD-WINDOWS-PORTABLE.md)
pacman -S mingw-w64-x86_64-libevent

# Option 2: vcpkg
.\vcpkg install libevent:x64-windows
```

**Workaround:** Until fixed, use curl for RPC calls:
```bash
curl --user test:test123 --data-binary '{"jsonrpc":"1.0","method":"getblockchaininfo","params":[]}' http://127.0.0.1:17443/
```

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
| Testnet3   | `-testnet`  | 18333    | 17332    | Historical testnet (large, slow to sync) |
| Testnet4   | `-testnet4` | 28333    | 27332    | Lightweight public testnet |
| Scalenet   | `-scalenet` | 38333    | 37332    | High-throughput stress testing |

**Recommended for testing changes: Use `regtest` mode first, then `testnet4` for broader testing.**

---

## Option 1: Regtest Mode (Recommended for Local Testing)

Regtest (regression test) mode is ideal for:
- Testing code changes locally
- Instant block generation (no mining required)
- Complete control over the blockchain
- Isolated environment

### Step 1: Create Regtest Configuration

Create a configuration file `radiant-regtest.conf`:

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
# Windows (from build directory)
radiantd.exe -conf=radiant-regtest.conf

# Or with flags directly
radiantd.exe -regtest -server -rpcuser=regtest -rpcpassword=regtest123
```

### Step 3: Generate Blocks (No Mining Pool Needed!)

In regtest mode, use the `generatetoaddress` RPC command to instantly create blocks:

```bash
# First, create a wallet and get an address
radiant-cli.exe -regtest -rpcuser=regtest -rpcpassword=regtest123 createwallet "testwallet"
radiant-cli.exe -regtest -rpcuser=regtest -rpcpassword=regtest123 getnewaddress

# Generate 101 blocks to your address (101 needed for coinbase maturity)
radiant-cli.exe -regtest -rpcuser=regtest -rpcpassword=regtest123 generatetoaddress 101 "YOUR_ADDRESS_HERE"

# Check your balance
radiant-cli.exe -regtest -rpcuser=regtest -rpcpassword=regtest123 getbalance
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
radiantd.exe -conf=node1.conf

# Terminal 2
radiantd.exe -conf=node2.conf
```

### Verify Connection

```bash
radiant-cli.exe -rpcport=17443 -rpcuser=node1 -rpcpassword=node1pass getpeerinfo
radiant-cli.exe -rpcport=17444 -rpcuser=node2 -rpcpassword=node2pass getpeerinfo
```

---

## Option 3: Public Testnet (testnet4)

For testing with the wider community on a shared testnet:

### Configuration (`radiant-testnet4.conf`)

```ini
testnet4=1
server=1
daemon=0
txindex=1
rpcuser=testnet4user
rpcpassword=testnet4pass
rpcallowip=127.0.0.1
rpcport=27332
debug=1
```

### Start Node

```bash
radiantd.exe -conf=radiant-testnet4.conf
```

### Get Testnet Coins

- Use a testnet faucet (if available)
- CPU mine on testnet4 (low difficulty, designed to be CPU-mineable)

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
radiantd.exe -regtest -server -rpcuser=test -rpcpassword=test123 -printtoconsole

# === IN ANOTHER TERMINAL ===
# Create wallet
radiant-cli.exe -regtest -rpcuser=test -rpcpassword=test123 createwallet "testwallet"

# Get new address
radiant-cli.exe -regtest -rpcuser=test -rpcpassword=test123 getnewaddress
# Example output: mkESjLZW66TmHhiFX8MCaBjrhZ543PPh9a

# Generate 101 blocks (replace with your address)
radiant-cli.exe -regtest -rpcuser=test -rpcpassword=test123 generatetoaddress 101 "mkESjLZW66TmHhiFX8MCaBjrhZ543PPh9a"

# Check balance (should have ~50000 RAD per mature block)
radiant-cli.exe -regtest -rpcuser=test -rpcpassword=test123 getbalance

# Get blockchain info
radiant-cli.exe -regtest -rpcuser=test -rpcpassword=test123 getblockchaininfo
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

## Public Testnet Strategy for ASERT Block 400000 Testing

### The Critical Test: `radiantCore2UpgradeHeight = 400000`

The ASERT half-life tuning change activates at block 400000 on all networks:

| Network   | radiantCore2UpgradeHeight | Current Status |
|-----------|---------------------------|----------------|
| Mainnet   | 400,000                   | Production     |
| Testnet3  | 400,000                   | May be past it |
| Testnet4  | 400,000                   | Likely < 400k  |
| Scalenet  | 400,000                   | Variable       |
| Regtest   | **200**                   | Easy to test   |

### Options for Testing Block 400000 ASERT Change

#### Option A: Use Regtest (Fastest)

Regtest has `radiantCore2UpgradeHeight = 200`, so you can test the upgrade with:
```bash
radiant-cli -regtest generatetoaddress 201 "ADDRESS"
# Now past the upgrade height - test ASERT behavior
```

#### Option B: Fresh Testnet4 (Recommended for Community Proof)

Testnet4 is designed to be lightweight and restartable. Since block 400000 is the target:

1. **Check current testnet4 height** (if running)
2. **If testnet4 < 400,000 blocks:** Continue mining to reach 400k
3. **If testnet4 > 400,000 blocks:** Either use existing chain or reset

**To reset testnet4 (if needed):**
- Invalidate a block and checkpoint a new one
- Or start fresh genesis (requires code change + coordination)

#### Option C: Private Testnet with Custom Upgrade Height

For faster testing, modify `chainparams.cpp` to set a lower upgrade height:

```cpp
// In CTestNet4Params constructor:
consensus.radiantCore2UpgradeHeight = 100;  // Instead of 400000
```

Then rebuild and run a private testnet.

### Checking Testnet Status

**Testnet4 DNS Seeds (from chainparams.cpp):**
- `node-testnet.radiantblockchain.org`
- `node-testnet.radiantone.org`
- `node-testnet.radiantlayerone.com`
- `node-testnet.radiantchain.org`
- `node-testnet.radiantnode.org`

**To check if testnet is running:**
```bash
# Try connecting
radiantd -testnet4 -printtoconsole

# Or check DNS seeds
nslookup node-testnet.radiantblockchain.org
```

### Do You Need a Mining Pool?

**For public testnet: Depends on difficulty.**

- Testnet4 has `fPowAllowMinDifficultyBlocks = true` and 1-hour ASERT half-life
- After 20 minutes without blocks, difficulty drops to minimum
- **CPU mining should work** on testnet4 after difficulty drops

**For regtest: No pool needed** - use `generatetoaddress` RPC.

### Recommended Testing Workflow

1. **Fix the libevent build bug first** (critical)
2. **Test on regtest** - verify ASERT changes work at height 200+
3. **Run functional tests** - `test/functional/` has existing tests
4. **Deploy to testnet4** - mine/sync to block 400k
5. **Document results** for community

---

## Action Items

- [ ] **FIX:** Rebuild with real libevent library
- [ ] **TEST:** Run regtest to height 201+ to verify ASERT upgrade
- [ ] **CHECK:** Query testnet4 DNS seeds to see if network is active
- [ ] **MINE:** If testnet4 is below 400k, mine to reach upgrade height
- [ ] **VERIFY:** Confirm ASERT behavior change at block 400000

---

*Last updated: January 8, 2026*
*Based on Radiant Core source code analysis*
*Build tested: v2.0.0-7cfb963*
