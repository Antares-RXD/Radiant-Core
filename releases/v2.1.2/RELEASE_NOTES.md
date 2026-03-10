# Radiant Core v2.1.2 Release Notes

**Release Date:** March 10, 2026  
**Critical Mining Fix**

---

## Critical Issue Resolution

This is a **critical hotfix release** to resolve empty block mining and ASIC mining issues caused by a fee policy mismatch between the mempool and block template creation.

### Problem Summary

Radiant Core v2.1.1 had a critical bug where:
- **Mempool/relay policy** accepted transactions with 0.01 RXD/kB fees during the 5000-block grace period (blocks 410,000-414,999)
- **Block template creation** immediately enforced 0.1 RXD/kB minimum fee at block 410,000

This mismatch caused **all transactions to be excluded from blocks**, resulting in miners producing empty blocks and invalid shares despite 1900+ transactions waiting in the mempool.

### Solution

**v2.1.2 aligns the miner fee enforcement with the relay grace period:**
- **Blocks 410,000-414,999 (grace period):** Accept 0.01 RXD/kB fees in blocks
- **Block 415,000+:** Enforce 0.1 RXD/kB minimum fee in blocks
- **V2 opcodes still activate at block 410,000** - OP_BLAKE3, OP_K12, OP_LSHIFT, OP_RSHIFT, OP_2MUL, OP_2DIV

This ensures transactions are included in blocks during the transition period.

---

## Upgrade Instructions

**All mining pools and nodes should upgrade to v2.1.2 immediately**

### Standard Upgrade (No Rollback Required)

1. **Stop your node:**
   ```bash
   radiant-cli stop
   ```

2. **Backup your data directory** (optional but recommended):
   ```bash
   # macOS
   cp -r ~/Library/Application\ Support/Radiant ~/Library/Application\ Support/Radiant.backup
   
   # Linux
   cp -r ~/.radiant ~/.radiant.backup
   ```

3. **Install v2.1.2 binaries** (replace your existing v2.1.1 installation)

4. **Start the node:**
   ```bash
   radiantd -daemon
   ```

5. **Verify upgrade:**
   ```bash
   radiant-cli getnetworkinfo | grep subversion
   ```
   
   You should see: `"subversion": "/Radiant:2.1.2/"`

6. **Resume mining** - Blocks will now include transactions

### Impact

**No blockchain rollback required** - this is a forward-compatible fix. Nodes running v2.1.2 will immediately start including transactions in new blocks.

**Existing empty blocks remain valid** - blocks mined with v2.1.1 that contain only coinbase transactions are consensus-valid and will not be invalidated.

---

## Changes in v2.1.2

### Policy Changes

**Modified:**
- Block template creation now respects the 5000-block grace period for minimum fees
- During grace period (blocks 410,000-414,999): 0.01 RXD/kB minimum
- After grace period (block 415,000+): 0.1 RXD/kB minimum

**Unchanged:**
- V2 opcode activation at block 410,000
- OP_BLAKE3 (0xee), OP_K12 (0xef), OP_LSHIFT (0x98), OP_RSHIFT (0x99), OP_2MUL (0x8d), OP_2DIV (0x8e)
- Relay/mempool fee policy (already had grace period logic)
- All consensus rules

### Code Changes

**Modified Files:**
- `src/miner.cpp` - Added grace period logic to `CreateNewBlock()`
- `CMakeLists.txt` - Version bump to 2.1.2

**Lines Changed:** 14 insertions, 4 deletions in `src/miner.cpp`

---

## Testing Verification

**Validation tests:**
```bash
./build/src/test/test_bitcoin --run_test=validation_tests
```
All tests pass, confirming grace period logic works correctly.

**Expected behavior:**
- ✅ Transactions with 0.01 RXD/kB fees accepted into mempool during grace period
- ✅ Same transactions included in block templates during grace period
- ✅ After block 415,000, only 0.1 RXD/kB+ fees accepted
- ✅ V2 opcodes activate correctly at block 410,000

---

## Upgrade Timeline

**Immediate action required:**

1. **Mining pools** - Upgrade ASAP to start including transactions in blocks
2. **Node operators** - Upgrade within 24 hours for consistent mempool behavior
3. **Miners** - No action required, pools will handle the upgrade

**Expected results:**
- Blocks immediately start including transactions after pool upgrade
- Mempool clears as pending transactions are mined
- Normal 5-minute block times with full blocks

---

## Credits

**Issue identified by:**
- Community member CraigD who analyzed the empty block problem
- Mining pool operators who reported the transaction exclusion

**Fix developed by:**
- CraigD 

**Special thanks to:**
- Pool operators for rapid deployment testing
- Node operators for network monitoring

---

## Download

**Source code:**
- GitHub: https://github.com/Radiant-Core/Radiant-Core/releases/tag/v2.1.2

**Binaries:**
- macOS (ARM64): `radiant-core-macos-arm64-v2.1.2.tar.gz`
- GUI Wallet (macOS ARM64): `radiant-core-qt-wallet-macos-arm64-v2.1.2.zip`
- Node Web GUI: `radiant-core-node-web-gui-v2.1.2.tar.gz`

**SHA256 checksums:** See `SHA256SUMS.txt` in release folder

---

## Support

**Questions or issues?**
- Discord: https://discord.gg/radiantblockchain
- Telegram: https://t.me/RadiantBlockchain
- GitHub Issues: https://github.com/Radiant-Core/Radiant-Core/issues

---

## Version History

- **v2.1.2** (2026-03-10) - Critical fix: align miner fee enforcement with grace period
- **v2.1.1** (2026-03-09) - Emergency fix for difficulty spike and getblocktemplate cache
- **v2.1.0** (2026-02-12) - V2 hard fork with new opcodes (OP_BLAKE3, OP_K12, etc.)
- **v2.0.1** (2025-11-15) - Maintenance release
