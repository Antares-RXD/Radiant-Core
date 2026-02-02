# Radiant Core 2.0.0 (Phoenix) Release Notes

**Release Date**: February 2, 2026  
**Hard Fork Activation**: Block 410,000 (~Late February 2026)  
**Git Tag**: v2.0.0

---

## Overview

Radiant Core 2.0.0 is a **mandatory upgrade** that includes consensus changes activating at block height **410,000**. All node operators, miners, exchanges, and wallet providers **must upgrade before block 410,000** to remain on the main chain.

### Current Network Status
- **Current Block Height**: ~385,830 (as of December 12, 2025)
- **Blocks Until Activation**: ~24,170
- **Estimated Activation Date**: Late February / Early March 2026

---

## ⚠️ IMPORTANT: Upgrade Deadline

**All participants MUST upgrade before block 410,000.**

| Participant | Urgency | Impact of Not Upgrading |
|-------------|---------|-------------------------|
| **Miners** | 🔴 Critical | Blocks will be orphaned due to incorrect difficulty calculation |
| **Exchanges** | 🟠 High | May fork onto minority chain, risk of double-spend attacks |
| **Node Operators** | 🟠 High | Will follow wrong chain after activation |
| **Wallet Users** | 🟡 Medium | Transactions may not confirm on main chain |

---

## Consensus Changes (Activate at Block 410,000)

### 1. ASERT Difficulty Adjustment Half-Life Tuning

The ASERT (Absolutely Scheduled Exponentially Rising Targets) difficulty adjustment algorithm half-life is reduced from **2 days** to **12 hours**.

**Impact**:
- Faster difficulty adjustment to hashrate changes
- More stable block times during hashrate fluctuations
- Improved network responsiveness

**Technical Details**:
- Pre-upgrade: `nASERTHalfLife = 172,800 seconds` (2 days)
- Post-upgrade: `nASERTHalfLife = 43,200 seconds` (12 hours)
- Activation: Height-based at block 410,000

### 2. Minimum Fee Policy Enforcement

A new minimum transaction fee policy is enforced at the consensus level to protect against DoS attacks and ensure miner revenue sustainability.

**Fee Schedule**:
| Block Height | Minimum Fee | RXD/kB |
|--------------|-------------|--------|
| < 410,000 | 1,000,000 sat/kB | 0.01 RXD/kB |
| 410,000 - 414,999 | 1,000,000 sat/kB | 0.01 RXD/kB |
| ≥ 415,000 | 10,000,000 sat/kB | 0.1 RXD/kB |

**Impact**:
- Miners cannot set `-blockmintxfee` above the maximum for their height
- Prevents "empty block" attacks where miners reject all transactions
- Ensures minimum economic viability for miners

**Note**:
- The relay/mempool minimum fee (`minrelaytxfee`) and wallet required fee floor follow the same schedule, with a **5,000 block grace period** after 410,000. This improves pre-activation mempool compatibility.
- `minrelaytxfee` is a *policy/relay* setting (mempool admission and propagation), not a consensus rule.

**Credit**: Empty Block Miner vulnerability reported by **iotapi from Vipor.net**.

---

## Non-Consensus Changes

These changes do not affect consensus and are backward-compatible:

### Infrastructure & Build System
- Upgraded to **C++20** standard
- Upgraded Docker base image to **Ubuntu 24.04 LTS**
- Upgraded OpenSSL to **3.0.18 LTS**
- Upgraded Boost to **1.82.0**
- Upgraded CMake minimum to **3.22**

### Transaction & Network Limits
- **Transaction Size**: Increased `MAX_TX_SIZE` to **12 MB** (~81,000 P2PKH inputs per transaction)
  - 50% more capacity than the previous 8 MB limit
  - Resolves exchange consolidation issues with many inputs
- **Network Message Limits** (Security Enhancement):
  - Set `MAX_PROTOCOL_MESSAGE_LENGTH` to **2 MB** for most protocol messages (INV, PING, ADDR, etc.)
  - Added `MAX_TX_MESSAGE_LENGTH` of **16 MB** specifically for TX messages
  - Block-like messages remain unlimited (scale with block size)
  - Prevents DoS attacks via oversized non-transaction messages while allowing large transactions

### Branding & Naming
- Renamed from "Radiant Node" to **"Radiant Core"**
- Version bumped to **2.0.0**
- Removed "pre-release test build" warnings

### Address Format
- **Removed cashaddr support** (Bitcoin Cash address format)
- Radiant now uses **Base58Check addresses only** (legacy Bitcoin format)
- Payment URIs use `radiant:` prefix

### Monitoring & Observability
- Added native **Prometheus metrics** endpoint (`/metrics` on port 7332)
- Metrics: `radiant_block_height`, `radiant_peers_connected`, `radiant_mempool_size`

### Glyph Swap Broadcast (PSRT)
- Added native support for **Partially Signed Radiant Transactions (PSRT)** enabling trustless atomic swaps
- **SwapIndex**: New LevelDB-backed index tracks on-chain swap advertisements by Token ID
- **Enhanced RPCs with age filtering**:
  - `getopenorders <token_ref> [limit] [offset] [max_age]`: Returns active swap offers with optional age filtering
  - `getopenordersbywant <want_token_ref> [limit] [offset] [max_age]`: Find orders by wanted token with age filtering
  - `getswaphistory <token_ref> [limit] [offset]`: Returns executed/cancelled swap offers (spent UTXOs)
  - `getswapindexinfo`: Returns swap index status and performance metrics
- **Order expiration**: `max_age` parameter allows filtering stale orders (e.g., 720 blocks = 6 hours)
- **Performance monitoring**: `getswapindexinfo` provides index health, order counts, and configuration
- Makers broadcast transactions with OP_RETURN outputs containing swap details (UTXO, terms, partial signature)
- Enables decentralized order books for Glyph tokens without external infrastructure
- Enable with `-swapindex` flag

### Node Profiles
- Added `-nodeprofile=<profile>` for simplified configuration:
  - `archive` (default): Full history, txindex enabled
  - `agent`: Pruned (~550MB), txindex disabled
  - `mining`: Balanced (~4GB), txindex disabled

### Block Finality
- Changed `DEFAULT_MAX_REORG_DEPTH` from **10 to 6** blocks for quicker block finality

### Verification Progress Fix
- Fixed `verificationprogress` in `getblockchaininfo` showing ~5% on fully synced nodes
- Root cause: `chainTxData` was using stale Bitcoin values (337M txs from 2021) instead of actual Radiant values (~27M txs)
- Implemented automatic time-based progress calculation that no longer requires periodic manual updates
- Synced nodes now correctly report `verificationprogress: 1.0`

**Credit**: Issue reported by **eman from icminers.com**.

---

## Replay Protection

Radiant maintains **strong replay protection** via `SIGHASH_FORKID`:

- All Radiant transactions include a chain-specific fork ID in the signature hash
- Transactions from other chains (BTC, BCH) cannot be replayed on Radiant
- Radiant transactions cannot be replayed on other chains
- **No additional replay protection is needed** for this upgrade

---

## Upgrade Instructions

### Download Links

| Platform | File | Size | SHA256 |
|----------|------|------|--------|
| **Linux x64** | `radiant-core-linux-x64-v2.0.0.tar.gz` | 4.0 MB | `932baccba23fa1b8c3ec2068e352d4c52ef68b1c56a9e4ec8a584c593d1cbf03` |
| **macOS ARM64** | `Radiant-Core-2.0.0-arm64.dmg` | 3.2 MB | `788173b6721a139041fc6990a185c7842397f01579be3bd8fd8a336762dc6147` |
| **macOS ARM64** | `radiant-core-macos-arm64-v2.0.0.tar.gz` | 2.8 MB | `960662ae7dd9ad0d8a515944586e32bc9010b20635e9a782ee8f8446957ecdb6` |
| **Docker** | `radiant-core-docker-2.0.0.tar.gz` | 40 MB | `9bfda51edc65b7a35276ca3b6992b95dbd32adb55b1aabd8af584da5618546cc` |

### For Node Operators

```bash
# Stop current node
radiant-cli stop

# Download and install Radiant Core 2.0.0
# Linux x64
wget https://github.com/Radiant-Core/Radiant-Core/releases/download/v2.0.0/radiant-core-linux-x64-v2.0.0.tar.gz
tar xzf radiant-core-linux-x64-v2.0.0.tar.gz
cd radiant-core-linux-x64

# Verify checksum
sha256sum radiant-core-linux-x64-v2.0.0.tar.gz
# Expected: 932baccba23fa1b8c3ec2068e352d4c52ef68b1c56a9e4ec8a584c593d1cbf03

# Start new node
./radiantd
```

### Docker Deployment

```bash
# Load image
docker load < radiant-core-docker-2.0.0.tar.gz

# Run
docker run -d --name radiant-node \
  -p 7332:7332 -p 7333:7333 \
  -v radiant-data:/home/radiant/.radiant \
  radiant-core:2.0.0

# Check status
docker exec radiant-node radiant-cli getblockchaininfo
```

### For Miners

1. Upgrade to Radiant Core 2.0.0 **before block 410,000**
2. No configuration changes required
3. The fee policy will automatically adjust at activation

### For Exchanges

1. Upgrade to Radiant Core 2.0.0
2. Test deposit/withdrawal functionality on testnet
3. Monitor for any address format issues (cashaddr removed)

### For Wallet Developers

1. Update to use Base58Check addresses only
2. Update URI scheme to `radiant:`
3. Adjust fee estimation for new minimum (0.1 RXD/kB post-activation)

---

## Testing

### Testnet

Testnet activates at block **1,000** for faster testing. Use testnet to verify your integration before mainnet activation.

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

## Known Potential Issues

- **BIP70 Removed**: Payment protocol support has been removed. (Unused in the ecosystem)

---

## Full Changelog

This document.
For a complete list of Roadmap of future changes, see [upgrades.md](../upgrades.md).

---

## Support

- **Discord**: [Radiant Blockchain Discord](https://discord.com/invite/radiantblockchain)
- **Telegram**: [@RadiantBlockchain](https://t.me/RadiantBlockchain)

---

## Contributors

Thank you to all contributors to this release, with special thanks to:
- **iotapi from Vipor.net** for reporting the Empty Block Miner vulnerability 
- **CraigD** for reporting and assisting with the oversize transaction vulnerability 
- **eman from icminers.com** for reporting the verificationprogress display bug
- **Razoo** for all his work on Radiant and PSRT/Glyphs 
- **Antares** for all he does for Radiant 

---

*This is a mandatory upgrade. Please upgrade before block 410,000 to remain on the Radiant main chain.*
