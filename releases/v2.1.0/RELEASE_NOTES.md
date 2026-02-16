# **Radiant Core 2.1.0 Release Notes**

> **Note**: This is a mandatory upgrade that adds 6 new/re-enabled opcodes for the V2 Hard Fork. All node operators must upgrade before block 410,000.

**Release Date**: February 2026  
**Hard Fork Activation**: Block 410,000 (~Late February 2026)

---

## Overview

Radiant Core 2.1.0 is a **mandatory upgrade** that introduces consensus-level changes activating at block height **410,000**. This release adds two new hash opcodes (OP_BLAKE3, OP_K12) and re-enables four arithmetic/bitwise opcodes (OP_LSHIFT, OP_RSHIFT, OP_2MUL, OP_2DIV), enabling fully on-chain Proof-of-Work validation for decentralized minting (dMint v2).

All node operators, miners, exchanges, and wallet providers **must upgrade before block 410,000** to remain on the main chain.

---

## Downloads

| Platform | File | Size |
|----------|------|------|
| Docker (x86_64) | radiant-core-docker-v2.1.0.tar.gz | ~35 MB |
| Linux x86_64 | radiant-core-linux-x64-v2.1.0.tar.gz | ~4.0 MB |
| macOS ARM64 | radiant-core-macos-arm64-v2.1.0.tar.gz | ~3.0 MB |
| macOS GUI App | Radiant-Core-GUI-2.1.0.dmg | ~19 MB |
| Windows x64 (all-in-one) | radiant-core-windows-x64.zip | ~65 MB |
| Windows GUI (standalone) | RadiantCoreNode+Wallet-v.2.1.0.exe | ~9.2 MB |
| Windows GUI (Qt classic) | RadiantCore.exe | ~30 MB |

### Verify Checksums
Each download includes a `.sha256` file for verification:
```bash
shasum -a 256 -c radiant-core-linux-x64-v2.1.0.tar.gz.sha256
```

### Build Configuration
All releases built with:
- ✅ Wallet support enabled
- ✅ ZMQ notifications enabled  
- ✅ UPnP port forwarding enabled
- ✅ Security hardening enabled

---

## Consensus Changes (Activate at Block 410,000)

### 1. New Hash Opcodes

Two new cryptographic hash opcodes are added for on-chain Proof-of-Work validation:

#### OP_BLAKE3 (0xee)
- **BLAKE3** hash function producing 32-byte output
- Input size limited to 1024 bytes (single-chunk mode)
- Enables on-chain PoW validation for Blake3-based dMint tokens
- ~500 LOC C++ implementation

#### OP_K12 (0xef)
- **KangarooTwelve** hash function producing 32-byte output
- Leverages existing KeccakF permutation from sha3.cpp
- Input size limited to 8192 bytes (single-leaf mode)
- Enables on-chain PoW validation for K12-based dMint tokens
- ~300 LOC C++ implementation

**Impact**:
- Eliminates indexer trust dependency for dMint v2 PoW validation
- ALL token Proof-of-Work is now validated on-chain (trustless, no griefing)
- Indexers become convenience/analytics layers only

### 2. Re-Enabled Arithmetic & Bitwise Opcodes

Four previously disabled opcodes are re-enabled for on-chain DAA (Difficulty Adjustment Algorithm) computation:

| Opcode | Hex | Description |
|--------|-----|-------------|
| OP_LSHIFT | 0x98 | Left bitwise shift (logical) |
| OP_RSHIFT | 0x99 | Right bitwise shift (logical) |
| OP_2MUL | 0x8d | Multiply by 2 |
| OP_2DIV | 0x8e | Integer divide by 2 (truncation toward zero) |

**Bounds & Safety**:
- LSHIFT/RSHIFT: shift amount must be 0 ≤ n ≤ 8×input_size (rejects negative or oversized shifts)
- 2MUL: overflow detection (INT64_MAX × 2 → script error)
- 2DIV: truncation toward zero for negative values (-3 / 2 = -1)

**Impact**:
- Enables ASERT-lite DAA computation on-chain using OP_MUL/OP_DIV + OP_LSHIFT/OP_RSHIFT
- Combined with OP_BLAKE3/OP_K12, allows fully trustless dMint v2 tokens

### 3. All v2.0.1 Consensus Changes Retained

- **ASERT half-life tuning**: 12 hours (down from 2 days)
- **Minimum fee policy**: 10,000,000 sat/kB (0.1 RXD/kB) at height ≥ 410,000

---

## Security Fixes

| ID | Finding | Severity | Fix |
|----|---------|----------|-----|
| S-1 | BLAKE3 `assert()` crash on >1024 byte input | **CRITICAL** | `Finalize()` returns bool; interpreter guards input size |
| S-2 | LSHIFT/RSHIFT no upper bound on shift; `static_cast<int>` overflow | **HIGH** | Bound check: `n <= 8 * vch1.size()` |

---

## Non-Consensus Changes

All non-consensus features from v2.0.1 are retained:
- Core Node GUI (web-based)
- Prometheus metrics endpoint
- PSRT (Partially Signed Radiant Transactions) for atomic swaps
- Node profiles (archive/agent/mining)
- C++20, Ubuntu 24.04, OpenSSL 3.0.18, Boost 1.82
- MAX_TX_SIZE = 12 MB
- Base58Check addresses only (cashaddr removed)

---

## Test Coverage

| Test Suite | Result | Description |
|-----------|--------|-------------|
| crypto_tests | **15/15 pass** | Including blake3_tests + k12_tests |
| validation_tests | **4/4 pass** | Fee policy, activation height |
| feature_v2_hash_opcodes.py | **26/26 pass** | 22 succeed + 4 rejection tests |
| feature_v2_phase10_integration.py | **29/29 pass** | 7 scenarios (A-G), 2-node regtest |

### Functional Test Details (26 tests)

**Succeed tests (22)**:
1. OP_BLAKE3 empty input + "abc" + output size
2. OP_K12 empty input + "abc" + output size
3. OP_LSHIFT: (1,3)=8, (1,0)=1 identity, (3,5)=96 multi-bit, (1,6)=64 near-max, (1,8)=0x00 boundary
4. OP_RSHIFT: (16,2)=4, (-4,1)=66 logical shift
5. OP_2MUL: 5→10, -5→-10, -(2^62) boundary, round-trip with 2DIV
6. OP_2DIV: 10→5, 7→3 truncation, -3→-1, 1→0, -1→0

**Rejection tests (4)**:
1. OP_2MUL(INT64_MAX) overflow → peer disconnect
2. OP_BLAKE3 with >1024 byte input → rejection (S-1 fix)
3. OP_LSHIFT(1, 100) oversized shift → rejection (S-2 fix)
4. OP_RSHIFT(1, 9) oversized shift → rejection (S-2 fix)

---

## Replay Protection

Radiant maintains **strong replay protection** via `SIGHASH_FORKID`:

- All Radiant transactions include a chain-specific fork ID in the signature hash
- Transactions from other chains (BTC, BCH) cannot be replayed on Radiant
- Radiant transactions cannot be replayed on other chains
- **No additional replay protection is needed** for this upgrade

---

## Upgrade Instructions

### For Node Operators

#### Linux (x86_64)

```bash
# Stop current node
radiant-cli stop

# Download and extract
wget https://github.com/RadiantBlockchain/Radiant-Core/releases/download/v2.1.0/radiant-core-linux-x64-v2.1.0.tar.gz
tar xzf radiant-core-linux-x64-v2.1.0.tar.gz

# Install runtime dependencies (Ubuntu 22.04+)
sudo apt-get install libboost-chrono1.74.0 libboost-filesystem1.74.0 \
  libboost-thread1.74.0 libevent-2.1-7 libevent-pthreads-2.1-7 \
  libssl3 libdb5.3++ libminiupnpc17 libzmq5

# Start new node
cd radiant-core-linux-x64
./radiantd -server -txindex=1
```

#### macOS (Apple Silicon)

```bash
radiant-cli stop
tar xzf radiant-core-macos-arm64-v2.1.0.tar.gz
cd radiant-core-macos-arm64
xattr -rd com.apple.quarantine .
./radiantd -server -txindex=1
```

#### Windows (x64)

```powershell
# Stop current node (if running)
.\radiant-cli.exe stop

# Extract the zip file (contains all exes + DLLs)
Expand-Archive radiant-core-windows-x64.zip -DestinationPath C:\RadiantCore

# Start the node
cd C:\RadiantCore
.\radiantd.exe -server -txindex=1
```

**Windows GUI — Two Options:**

| Application | Description |
|-------------|-------------|
| **RadiantCoreNode+Wallet-v.2.1.0.exe** | **Recommended.** Standalone single-file GUI. No DLLs needed. Launches a browser-based interface at `http://127.0.0.1:8765` with one-click node control, built-in wallet, and BIP39 seed phrase backup. |
| **RadiantCore.exe** | Classic Qt desktop wallet and node manager. Requires Qt5/ICU/MinGW DLLs in the same folder (all included in the zip). |

#### Docker

```bash
# Load the image
docker load < radiant-core-docker-v2.1.0.tar.gz

# Run with wallet support
docker run -d --name radiant-node \
  -p 7332:7332 -p 7333:7333 \
  -v radiant-data:/home/radiant/.radiant \
  radiant-core:v2.1.0-amd64

# Check status
docker exec radiant-node radiant-cli getblockchaininfo
```

### For Miners

1. Upgrade to Radiant Core 2.1.0 **before block 410,000**
2. No configuration changes required
3. dMint v2 tokens (Blake3/K12 PoW) will be validated on-chain automatically after activation

### For Exchanges

1. Upgrade to Radiant Core 2.1.0
2. Test deposit/withdrawal functionality
3. No address format changes from v2.0.1

### For Wallet Developers

1. Upgrade node to v2.1.0
2. If supporting Glyph tokens: update to use new opcode IDs (0xee, 0xef, 0x98, 0x99, 0x8d, 0x8e)
3. Adjust fee estimation if needed (0.1 RXD/kB post-activation, unchanged from v2.0.1)

---

## Testing

### Testnet

Testnet activates at block 1,000:
```bash
./radiantd -testnet
```

### Regtest

Regtest activates at block 200 for rapid testing:
```bash
./radiantd -regtest
./radiant-cli -regtest generatetoaddress 201 <address>
```

---

## Ecosystem Updates

All ecosystem repositories have been updated for V2 compatibility:

| Repository | Key Changes |
|-----------|-------------|
| radiantblockchain-constants | V2 opcode IDs in opcodes.ts, algo IDs in glyph.ts (103/103 tests) |
| radiantjs | JS interpreter V2 opcodes, pure JS blake3/k12 (3399+ tests) |
| RadiantScript | blake3()/k12() compiler globals, tx.state.* induction proofs (268/268 tests) |
| rxdeb | Script interpreter + crypto layers mirrored |
| RXinDexer | Algorithm IDs updated, analytics-only role |
| Photonic Wallet | dMintScript per-algo bytecodes |
| Glyph-miner | Blake3/K12 GPU shaders + multi-algo miner |
| Glyph Token Standards | Whitepaper v2.0 (Release Candidate) |
| ElectrumX | V2 compatibility notes, Glyph API docs |

---

## Known Issues

- **Testnet**: All 11 seed nodes are currently offline. Use regtest for testing.
- **BIP70 Removed**: Payment protocol support has been removed (unused in ecosystem).

---

## Full Changelog

For a complete list of changes, see [doc/release-notes/release-notes-2.1.0.md](doc/release-notes/release-notes-2.1.0.md).

---

## Support

- **Discord**: [Radiant Blockchain Discord](https://discord.com/invite/radiantblockchain)
- **Telegram**: [@RadiantBlockchain](https://t.me/RadiantBlockchain)

---

## Contributors

Thank you to all contributors to this release, with special thanks to:
- **iotapi from Vipor.net** for reporting the Empty Block Miner vulnerability
- **CraigD** for reporting and assisting with the oversize transaction vulnerability
- **Razoo** for all his work on Radiant and PSRT/Glyphs
- **Antares** for all he does for Radiant

---

*This is a mandatory upgrade. Please upgrade before block 410,000 to remain on the Radiant main chain.*
