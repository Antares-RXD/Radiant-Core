# Radiant Core 2.0.0 Release

**Release Date:** February 2, 2026  
**Git Tag:** v2.0.0  
**Commit:** 3dc076de

## Activation Heights

| Network   | Activation Height | Fee Enforcement |
|-----------|-------------------|-----------------|
| Mainnet   | 410,000           | 415,000         |
| Testnet   | 1,000             | 6,000           |
| Scalenet  | 410,000           | 415,000         |
| Regtest   | 200               | 5,200           |

## Key Changes

### Consensus Changes
- **ASERT Half-Life Tuning**: 12-hour half-life post-activation (was 2 days)
- **Minimum Fee Policy**: 0.1 RXD/kB after 5,000 block grace period

### Timeline (Mainnet)
- **Block 410,000**: ASERT half-life changes to 12 hours
- **Block 410,000 - 414,999**: Grace period (legacy 0.01 RXD/kB fees accepted)
- **Block 415,000+**: New 0.1 RXD/kB minimum fee enforced

## Release Artifacts

### Linux x64

| File | Size | SHA256 |
|------|------|--------|
| `radiant-core-linux-x64-v2.0.0.tar.gz` | 4.0 MB | `932baccba23fa1b8c3ec2068e352d4c52ef68b1c56a9e4ec8a584c593d1cbf03` |

### macOS ARM64 (Apple Silicon)

| File | Size | SHA256 |
|------|------|--------|
| `Radiant-Core-2.0.0-arm64.dmg` | 3.2 MB | `788173b6721a139041fc6990a185c7842397f01579be3bd8fd8a336762dc6147` |
| `radiant-core-macos-arm64-v2.0.0.tar.gz` | 2.8 MB | `960662ae7dd9ad0d8a515944586e32bc9010b20635e9a782ee8f8446957ecdb6` |

### Docker (Linux amd64)

| File | Size | SHA256 |
|------|------|--------|
| `radiant-core-docker-2.0.0.tar.gz` | 40 MB | `9bfda51edc65b7a35276ca3b6992b95dbd32adb55b1aabd8af584da5618546cc` |

**Docker Usage:**
```bash
# Load image
docker load < radiant-core-docker-2.0.0.tar.gz

# Run
docker run -d --name radiant-node \
  -p 7332:7332 -p 7333:7333 \
  -v radiant-data:/home/radiant/.radiant \
  radiant-core:2.0.0
```

## Upgrade Instructions

### Node Operators
1. Stop your current node: `radiant-cli stop`
2. Replace binaries with v2.0.0 release
3. Start node: `radiantd`
4. Verify version: `radiant-cli --version`

### Miners
- Update before block 410,000 to avoid orphaned blocks
- No configuration changes required

### Wallet/Exchange Integration
- Update fee estimation for 0.1 RXD/kB post-block 415,000
- Test on testnet first (activates at block 1,000)

## Verification

```bash
# Verify checksums
shasum -a 256 -c *.sha256

# Verify binary
./radiantd --version
# Expected: Radiant Core Daemon version v2.0.0
```

## Links

- **GitHub:** https://github.com/Radiant-Core/Radiant-Core
- **Website:** https://radiantblockchain.org
- **Documentation:** See `doc/` directory
