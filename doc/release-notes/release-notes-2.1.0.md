# Radiant Core 2.1.0 Release Notes

**Release Date**: February 12, 2026  
**Hard Fork Activation**: Block 410,000 (same as v2.0.1)  
**Git Tag**: v2.1.0

> **Note**: This release builds on v2.0.1 by adding 6 new and re-enabled opcodes for the V2 hard fork. The activation height remains block 410,000. All node operators **must upgrade** before block 410,000 to remain on the main chain.

---

## Overview

Radiant Core 2.1.0 is a **mandatory upgrade** that adds consensus-level support for 6 new and re-enabled opcodes, activated at block height **410,000** alongside the ASERT and fee policy changes from v2.0.1. These opcodes enable fully on-chain proof-of-work validation for Glyph v2 decentralized minting (dMint) tokens, eliminating indexer trust dependency.

### What's New in 2.1.0

- **4 new/re-enabled opcodes**: OP_BLAKE3, OP_K12, OP_2MUL, OP_2DIV
- **2 re-enabled opcodes**: OP_LSHIFT, OP_RSHIFT
- **On-chain dMint v2**: Alternative hash algorithm tokens (Blake3, KangarooTwelve) validated entirely by consensus
- **On-chain DAA**: ASERT-lite difficulty adjustment computed in script via bitwise shifts
- **Full ecosystem update**: All 9 ecosystem repositories updated for V2 compatibility
- **Comprehensive testing**: 26/26 opcode functional tests + 29 integration tests across 7 scenarios

---

## ⚠️ IMPORTANT: Upgrade Deadline

**All participants MUST upgrade before block 410,000.**

This release shares the same activation height as v2.0.1. If you are already running v2.0.1, upgrading to v2.1.0 adds the new opcode support that activates at the same height.

| Participant | Urgency | Action Required |
|-------------|---------|-----------------|
| **Miners** | 🔴 Critical | Upgrade to validate V2 opcode transactions after activation |
| **Exchanges** | 🟠 High | Upgrade to accept transactions using new opcodes |
| **Node Operators** | 🟠 High | Upgrade to remain on the main chain |
| **Wallet Developers** | 🟡 Medium | Update fee estimation (0.1 RXD/kB after block 415,000) |
| **dApp Developers** | 🟡 Medium | New opcodes available for smart contracts post-activation |

---

## Consensus Changes (Activate at Block 410,000)

### New Opcodes

Six opcodes are gated behind the `SCRIPT_ENHANCED_REFERENCES` flag and activate at the V2 hard fork height:

| Opcode | Hex | Stack Effect | Type | Description |
|--------|-----|-------------|------|-------------|
| **OP_BLAKE3** | `0xee` | `data → hash` | New | Blake3 cryptographic hash (32-byte output) |
| **OP_K12** | `0xef` | `data → hash` | New | KangarooTwelve hash (32-byte output) |
| **OP_LSHIFT** | `0x98` | `a b → (a << b)` | Re-enabled | Bitwise left shift |
| **OP_RSHIFT** | `0x99` | `a b → (a >> b)` | Re-enabled | Bitwise right shift |
| **OP_2MUL** | `0x8d` | `a → (a * 2)` | Re-enabled | Multiply by 2 |
| **OP_2DIV** | `0x8e` | `a → (a / 2)` | Re-enabled | Divide by 2 (truncation toward zero) |

### OP_BLAKE3 (`0xee`)

Computes the [BLAKE3](https://github.com/BLAKE3-team/BLAKE3) cryptographic hash of the top stack element.

- **Input**: Arbitrary-length byte string from top of stack
- **Output**: 32-byte hash pushed to stack
- **Implementation**: ~500 lines C++ in `src/crypto/blake3.cpp`
- **Test vectors**: Empty string → `af1349b9...`, `"abc"` → `6437b3ac...`
- **Use case**: On-chain PoW validation for Blake3 dMint tokens

### OP_K12 (`0xef`)

Computes the [KangarooTwelve](https://keccak.team/kangarootwelve.html) hash (a faster variant of SHA-3/Keccak) of the top stack element.

- **Input**: Arbitrary-length byte string from top of stack
- **Output**: 32-byte hash pushed to stack
- **Implementation**: ~300 lines C++ in `src/crypto/k12.cpp`, leveraging existing `KeccakF` permutation from `sha3.cpp`
- **Test vectors**: Empty string → `1ac2d450...`, `"abc"` → `ab174f32...`
- **Use case**: On-chain PoW validation for KangarooTwelve dMint tokens

### OP_LSHIFT (`0x98`) and OP_RSHIFT (`0x99`)

Bitwise shift operations, previously disabled in Bitcoin. Re-enabled for Radiant to support on-chain difficulty adjustment computation.

- **OP_LSHIFT**: `a b → (a << b)` — Shift `a` left by `b` bits
- **OP_RSHIFT**: `a b → (a >> b)` — Shift `a` right by `b` bits
- **Shift amount**: Must be non-negative; operates on the byte representation
- **Use case**: ASERT-lite DAA computation — power-of-2 target adjustments via bit shifting

### OP_2MUL (`0x8d`) and OP_2DIV (`0x8e`)

Numeric opcodes for multiply-by-2 and divide-by-2. Previously unconditionally disabled; now fork-gated behind `SCRIPT_ENHANCED_REFERENCES`.

- **OP_2MUL**: `a → (a * 2)` — Uses `safeMul(2)` with INT64 overflow protection
- **OP_2DIV**: `a → (a / 2)` — Truncation toward zero (e.g., `-3 / 2 = -1`)
- **Overflow**: OP_2MUL of `INT64_MAX` is correctly rejected
- **Use case**: Numeric scaling in DAA and contract arithmetic

### Why These Opcodes

**Problem**: Glyph v1 dMint tokens were limited to SHA256d proof-of-work because the indexer had to validate PoW for alternative algorithms. This created:
- **Trust dependency** on the indexer for consensus
- **Griefing vulnerability** where invalid work could consume token state
- **Consensus divergence risk** between indexers

**Solution**: OP_BLAKE3 and OP_K12 move PoW validation into the script engine, making it a consensus rule. The shift and arithmetic opcodes enable on-chain ASERT-lite difficulty adjustment. The indexer becomes an analytics/convenience layer only.

### Activation Heights

| Network | Height | `SCRIPT_ENHANCED_REFERENCES` |
|---------|--------|------------------------------|
| **Mainnet** | 410,000 | Opcodes available in scripts |
| **Testnet3** | 410,000 | Opcodes available in scripts |
| **Scalenet** | 1,000 | Active |
| **Regtest** | 200 | Active |

### Fee Policy (Unchanged from v2.0.1)

The minimum fee schedule from v2.0.1 remains in effect:

| Block Height | Minimum Fee | RXD/kB |
|--------------|-------------|--------|
| < 410,000 | 1,000,000 sat/kB | 0.01 RXD/kB |
| 410,000 - 414,999 | 1,000,000 sat/kB | 0.01 RXD/kB (grace period) |
| ≥ 415,000 | 10,000,000 sat/kB | 0.1 RXD/kB |

---

## Ecosystem Updates

All ecosystem tools have been updated for V2 compatibility:

| Repository | Version | V2 Changes |
|------------|---------|-----------|
| **Radiant Core** | 2.1.0 | `blake3.cpp`, `k12.cpp`, `interpreter.cpp` fork-gating, `chainparams.cpp` activation |
| **radiantjs** | 2.0.0 | Pure JS blake3/k12 implementations, interpreter V2 opcodes, stepListener fix, 560 test failures fixed |
| **radiantblockchain-constants** | — | V2 opcode values and names in `opcodes.ts` |
| **RadiantScript** | — | `blake3()`, `k12()` compiler globals with codegen |
| **rxdeb** | — | V2 VM execution for all 6 opcodes, test suite added |
| **RXinDexer** | — | Algorithm ID fixes, analytics-only role (no PoW validation needed) |
| **Photonic Wallet** | — | Per-algorithm contract bytecodes (`dMintScript`) |
| **Glyph-miner** | — | Blake3/K12 GPU WebGPU shaders, multi-algorithm mining, CPU verification |
| **Glyph Token Standards** | draft-6 | Whitepaper §11.4.1 on-chain DAA spec, Appendix E contract bytecodes |

---

## Testing

### Test Coverage

| Test Suite | Result | Description |
|-----------|--------|-------------|
| `crypto_tests` | 15/15 pass | Blake3 + K12 hash vectors |
| `validation_tests` | 4/4 pass | Fee policy enforcement |
| `feature_v2_hash_opcodes.py` | 14/14 pass | All 6 opcodes on regtest (P2SH funding + spending) |
| `feature_v2_phase10_integration.py` | 29/29 pass | 7 scenarios (A-G) on 2-node regtest |

### Integration Test Scenarios

All scenarios run on a 2-node regtest network with block propagation verification:

| Scenario | Description | Result |
|----------|-------------|--------|
| **A** | Backward compatibility — OP_HASH256 works post-fork | ✅ Pass |
| **B** | Blake3 token — OP_BLAKE3 on-chain PoW validation | ✅ Pass |
| **C** | K12 token — OP_K12 on-chain PoW validation | ✅ Pass |
| **D** | DAA arithmetic — LSHIFT/RSHIFT/2MUL/2DIV chain operations | ✅ Pass |
| **E** | Cross-node consensus — 2-node block propagation and acceptance | ✅ Pass |
| **F** | Attack/rejection — Overflow, wrong hash, negative shift correctly rejected | ✅ Pass |
| **G** | OP_2MUL/OP_2DIV comprehensive — Truncation, round-trip, negative values | ✅ Pass |

### Running Tests

```bash
# Build
mkdir -p build && cd build
cmake -GNinja ..
ninja

# Unit tests
./src/test/test_bitcoin --run_test=crypto_tests
./src/test/test_bitcoin --run_test=validation_tests

# Functional tests (opcode tests)
python3 test/functional/feature_v2_hash_opcodes.py --configfile=build/test/config.ini

# Integration tests (2-node regtest)
python3 test/functional/feature_v2_phase10_integration.py --configfile=build/test/config.ini

# Regtest quick test
./radiantd -regtest
./radiant-cli -regtest generatetoaddress 201 $(./radiant-cli -regtest getnewaddress)
# Opcodes now available (regtest activates at block 200)
```

---

## Downloads

| Platform | File | Size |
|----------|------|------|
| **Linux x64 (CLI)** | `radiant-core-linux-x64-v2.1.0.tar.gz` | ~4 MB |
| **Linux x64 (GUI)** | `radiant-core-gui-linux-x64-v2.1.0.tar.gz` | ~4 MB |
| **macOS ARM64 (DMG)** | `Radiant-Core-GUI-2.1.0.dmg` | ~20 MB |
| **macOS ARM64 (CLI)** | `radiant-core-macos-arm64-v2.1.0.tar.gz` | ~3 MB |
| **macOS ARM64 (GUI ZIP)** | `radiant-core-gui-macos-arm64-v2.1.0.zip` | ~3 MB |
| **Windows x64** | `radiant-core-windows-x64.zip` | ~25 MB |
| **Docker (x86_64)** | `radiant-core-docker-v2.1.0.tar.gz` | ~42 MB |

### SHA256 Checksums

Verify your download:
```bash
# Linux / macOS
shasum -a 256 <filename>
# or
sha256sum <filename>
```

> **Note**: SHA256 checksums will be published on the [GitHub Releases](https://github.com/Radiant-Core/Radiant-Core/releases/tag/v2.1.0) page when binaries are built.

---

## Upgrade Instructions

### For Node Operators

#### Linux (x86_64)

```bash
# Stop current node
radiant-cli stop

# Download and extract
wget https://github.com/Radiant-Core/Radiant-Core/releases/download/v2.1.0/radiant-core-linux-x64-v2.1.0.tar.gz
tar xzf radiant-core-linux-x64-v2.1.0.tar.gz

# Verify checksum (compare against release page)
sha256sum radiant-core-linux-x64-v2.1.0.tar.gz

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

# Extract the zip file
Expand-Archive radiant-core-windows-x64.zip -DestinationPath C:\RadiantCore

# Start the node
cd C:\RadiantCore
.\radiantd.exe -server -txindex=1
```

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
3. Post-activation: V2 dMint tokens using OP_BLAKE3/OP_K12 will appear in transactions
4. Fee policy automatically adjusts at activation (unchanged from v2.0.1)

### For Exchanges

1. Upgrade to Radiant Core 2.1.0
2. No action required for standard RXD transfers
3. V2 opcode transactions will be valid post-activation — ensure your node validates them
4. Fee estimation should account for 0.1 RXD/kB minimum after block 415,000

### For dApp / Wallet Developers

1. Update radiantjs to 2.0.0 for V2 opcode interpreter support
2. New opcodes available in scripts after block 410,000:
   - `OP_BLAKE3` (0xee), `OP_K12` (0xef) for on-chain hash verification
   - `OP_LSHIFT` (0x98), `OP_RSHIFT` (0x99) for bitwise shifts
   - `OP_2MUL` (0x8d), `OP_2DIV` (0x8e) for numeric scaling
3. Contracts using V2 opcodes must only be deployed after the activation height
4. Adjust fee estimation for 0.1 RXD/kB after block 415,000

### For Glyph Token Creators

1. After block 410,000, you can create dMint tokens with **Blake3** or **KangarooTwelve** PoW algorithms
2. On-chain DAA (ASERT-lite) is now possible using OP_LSHIFT/OP_RSHIFT
3. Use Photonic Wallet or Glyph-miner for token deployment and mining
4. See the [Glyph v2 Token Standard Whitepaper](https://github.com/Radiant-Core/Glyph-Token-Standards/blob/main/Glyph_v2_Token_Standard_Whitepaper.md) for contract specifications

---

## Replay Protection

Radiant maintains **strong replay protection** via `SIGHASH_FORKID`. No additional replay protection is needed for this upgrade.

---

## Changes Since v2.0.1

### Consensus
- Added OP_BLAKE3 (`0xee`) — Blake3 hash opcode
- Added OP_K12 (`0xef`) — KangarooTwelve hash opcode
- Re-enabled OP_LSHIFT (`0x98`) — Bitwise left shift (fork-gated)
- Re-enabled OP_RSHIFT (`0x99`) — Bitwise right shift (fork-gated)
- Re-enabled OP_2MUL (`0x8d`) — Multiply by 2 (fork-gated)
- Re-enabled OP_2DIV (`0x8e`) — Divide by 2 (fork-gated)
- All opcodes gated behind `SCRIPT_ENHANCED_REFERENCES` flag
- Activation at `radiantCore2UpgradeHeight` (block 410,000 mainnet/testnet3)

### Source Code
- `src/crypto/blake3.cpp` / `blake3.h` — BLAKE3 hash implementation
- `src/crypto/k12.cpp` / `k12.h` — KangarooTwelve hash implementation
- `src/script/interpreter.cpp` — Fork-gated opcode execution for all 6 opcodes
- `src/script/script_flags.h` — `SCRIPT_ENHANCED_REFERENCES` flag definition
- `src/consensus/validation.cpp` — Flag activation at upgrade height

### Tests
- `test/functional/feature_v2_hash_opcodes.py` — 14 opcode tests on regtest
- `test/functional/feature_v2_phase10_integration.py` — 29 integration tests (7 scenarios, 2-node)
- `src/test/crypto_tests.cpp` — Blake3 and K12 hash vector tests

### Documentation
- Updated version from 2.0.1 → 2.1.0 across all build scripts, Dockerfiles, and READMEs
- Added V2 Hard Fork section to Radiant Core README
- Updated all 9 ecosystem documents with V2 hard fork information
- Updated 4 repo READMEs (radiantjs, rxdeb, radiantblockchain-constants, Radiant Core)

---

## Known Issues

- **Testnet DNS seeds**: All 11 testnet seed nodes are currently offline. Testnet testing requires manual peer connection or regtest.
- **Pre-activation testing limitation**: In regtest, `ERHeight=10` and coinbase maturity (100 blocks) prevent testing pre-activation opcode rejection below height 10.

---

## Technical Reference

### Script Flag

```cpp
// script/script_flags.h
SCRIPT_ENHANCED_REFERENCES = (1U << 26),
```

This flag is set in `validation.cpp` when the block height reaches `radiantCore2UpgradeHeight`:

```cpp
if ((pindex->nHeight + 1) >= params.ERHeight) {
    flags |= SCRIPT_ENHANCED_REFERENCES;
}
```

### Opcode Gating

In `interpreter.cpp`, the 6 opcodes check for the `SCRIPT_ENHANCED_REFERENCES` flag:

```cpp
static bool IsOpcodeDisabled(opcodetype opcode, uint32_t flags) {
    switch (opcode) {
        case OP_2MUL:
        case OP_2DIV:
        case OP_LSHIFT:
        case OP_RSHIFT:
            // Fork-gated: disabled pre-activation, enabled post-activation
            return !(flags & SCRIPT_ENHANCED_REFERENCES);
        // ... OP_BLAKE3 and OP_K12 are new opcodes, not in the disabled list
    }
}
```

### Key Files

| File | Purpose |
|------|---------|
| `src/crypto/blake3.cpp` | BLAKE3 hash implementation |
| `src/crypto/k12.cpp` | KangarooTwelve hash implementation |
| `src/script/interpreter.cpp` | Opcode execution (all 6 V2 opcodes) |
| `src/script/script_flags.h` | SCRIPT_ENHANCED_REFERENCES flag |
| `src/validation.cpp` | Flag activation at upgrade height |
| `src/chainparams.cpp` | Activation heights per network |

---

## Support

- **Discord**: [Radiant Blockchain Discord](https://discord.com/invite/radiantblockchain)
- **Telegram**: [@RadiantBlockchain](https://t.me/RadiantBlockchain)
- **GitHub Issues**: [Radiant-Core/Radiant-Core](https://github.com/Radiant-Core/Radiant-Core/issues)

---

## Contributors

Thank you to all contributors to this release and the V2 hard fork ecosystem upgrade.

---

*This is a mandatory upgrade. Please upgrade before block 410,000 to remain on the Radiant main chain.*
