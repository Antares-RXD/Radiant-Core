# Radiant Core v2.1.1 - Emergency ASERT DAA Fix (HOTFIX BUILD)

**Release Date**: March 9, 2026  
**Type**: CRITICAL EMERGENCY FIX + HOTFIX  
**Status**: MANDATORY UPGRADE  
**Build**: Includes getblocktemplate cache fix

---

## 🔥 HOTFIX APPLIED (Critical for Miners)

**Issue Found**: The initial v2.1.1 release fixed the ASERT difficulty calculation in `getblockchaininfo`, but `getblocktemplate` (used by miners) was returning **cached templates with the old broken difficulty** (148.9 trillion instead of 30.4 million).

**Hotfix Applied**: Added cache invalidation at ASERT half-life upgrade height in `src/rpc/mining.cpp` to force regeneration of block templates with correct difficulty.

**Impact**: Without this hotfix, miners would continue receiving incorrect difficulty targets even after upgrading nodes.

---

## ⚠️ CRITICAL: Network Halted - Immediate Action Required

The Radiant network halted at block 410,000 due to a catastrophic difficulty spike. **ALL NODE OPERATORS AND MINING POOLS MUST UPGRADE IMMEDIATELY** to restore network operation.

---

## What Happened

At block 410,000 (March 9, 2026 ~16:30 CDT), the ASERT difficulty adjustment algorithm experienced a catastrophic failure:

- **Difficulty spiked ~5000×** from ~30 million to ~152 billion
- **Block 410,001 became unmined** (would take ~52 years at current hashrate)
- **Network halted** for approximately 2 hours

**Root Cause**: The ASERT anchor block from July 2022 (block 18,206) was not reset when the half-life changed from 2 days to 12 hours at block 410,000. This caused the difficulty formula to use 2.5 years of accumulated time with a 4× smaller half-life parameter, resulting in an exponential explosion.

---

## The Fix

v2.1.1 implements a **dynamic anchor block reset** at the half-life upgrade height:

- When calculating difficulty for any block ≥ 410,000, the anchor automatically resets to block 409,999
- This prevents the massive time accumulation from the 2022 anchor
- Block 410,000's bad difficulty is effectively ignored for future calculations
- **No reorg required** - the fix works with the already-halted chain

**Implementation Details**:
- `src/pow.cpp` lines 125-151: Dynamic anchor reset using efficient `GetAncestor()` lookup
- `src/rpc/mining.cpp` lines 528-541: Cache invalidation to ensure miners receive correct templates
- Fallback logging if anchor block lookup fails (defensive programming)
- O(log n) performance using skip list instead of linear block traversal

---

## Recovery Process

### For Node Operators

**IMMEDIATE STEPS:**

1. **Download v2.1.1:**
   - macOS ARM64: `radiant-core-macos-arm64-v2.1.1.tar.gz` (4.7 MB)
   - Linux x64: `radiant-core-linux-x64-v2.1.1.tar.gz` (6.2 MB)
   - Docker: `radiant-core-docker-v2.1.1.tar.gz` (37 MB)

2. **Stop your node:**
   ```bash
   radiant-cli stop
   ```

3. **Replace binaries:**
   ```bash
   # macOS/Linux
   tar xzf radiant-core-*.tar.gz
   # Copy binaries to your installation directory
   ```

4. **Restart node:**
   ```bash
   radiantd -daemon
   ```

5. **Verify version:**
   ```bash
   radiant-cli --version
   # Should show: Radiant Core version v2.1.1
   ```

### For Mining Pools

**CRITICAL - NETWORK RECOVERY DEPENDS ON YOU:**

1. Stop all mining operations
2. Upgrade to v2.1.1 (see steps above)
3. Restart radiantd
4. Resume mining operations
5. Monitor for block 410,001

**Expected Behavior:**
- Block 410,001 will have ~10% **lower** difficulty (due to 2-hour halt)
- Should be mineable within 5-15 minutes after pools restart
- Subsequent blocks will adjust normally with 12-hour half-life

---

## Download Links

All release packages are in: `/Users/main/Downloads/Radiant-Core-main/releases/v2.1.1/`

### macOS ARM64
- **File**: `radiant-core-macos-arm64-v2.1.1.tar.gz`
- **Size**: 4.7 MB
- **SHA256**: See `radiant-core-macos-arm64-v2.1.1.tar.gz.sha256`

### Linux x64
- **File**: `radiant-core-linux-x64-v2.1.1.tar.gz`
- **Size**: 6.2 MB
- **SHA256**: See `radiant-core-linux-x64-v2.1.1.tar.gz.sha256`

### Docker
- **File**: `radiant-core-docker-v2.1.1.tar.gz`
- **Size**: 37 MB
- **SHA256**: See `radiant-core-docker-v2.1.1.tar.gz.sha256`

**Docker Usage:**
```bash
# Load image
docker load < radiant-core-docker-v2.1.1.tar.gz

# Run
docker run -d --name radiantd \
  -v ~/.radiant:/root/.radiant \
  -p 7332:7332 -p 7333:7333 \
  radiant-core-builder-linux
```

---

## Verification

### Verify Binary Checksums

```bash
# macOS/Linux
shasum -a 256 -c radiant-core-*.tar.gz.sha256
```

### Verify Fix is Active

```bash
# Check version
radiant-cli --version

# Check current block (should be 410,000)
radiant-cli getblockcount

# When block 410,001 is mined, verify reasonable difficulty
HASH=$(radiant-cli getblockhash 410001)
radiant-cli getblock $HASH 1 | grep difficulty
# Should show ~20-40 million, NOT 152 billion
```

---

## What's Included

### Changes from v2.1.0

**Core Changes:**
- ✅ Fixed ASERT anchor block reset at half-life upgrade height
- ✅ Added dynamic anchor recalculation for blocks ≥ 410,000
- ✅ Prevents exponential difficulty spike from historical anchor

**No Other Changes:**
- All V2 opcodes remain enabled (OP_BLAKE3, OP_K12, OP_LSHIFT, OP_RSHIFT, OP_2MUL, OP_2DIV)
- ASERT 12-hour half-life still active at block 410,000
- No consensus rule changes beyond the bug fix
- Fully compatible with v2.1.0 for blocks < 410,000

---

## Expected Recovery Timeline

| Time | Event |
|------|-------|
| T+0 | Emergency fix deployed to your node |
| T+30min | Mining pools begin upgrading |
| T+1hr | First pools restart mining with fix |
| T+2hr | **Block 410,001 mined** (difficulty ~10% lower) |
| T+3hr | Network stabilizing |
| T+24hr | Full recovery confirmed |

---

## Technical Reference

### ASERT Formula

```
new_target = old_target * 2^((actual_time - ideal_time) / half_life)
```

**Before fix (at block 410,000):**
- Anchor: block 18,206 (July 2022)
- Height diff: 391,794 blocks
- Time diff: ~2.5 years
- Half-life: 43,200 seconds (12 hours)
- **Result**: Exponential explosion → difficulty spike

**After fix (at block 410,001):**
- Anchor: block 409,999 (dynamically reset)
- Height diff: 1 block
- Time diff: ~7,200 seconds (2 hours)
- Half-life: 43,200 seconds (12 hours)
- **Result**: Normal calculation → difficulty decrease (~10%)

---

## Support

### Emergency Contact

- **Discord**: https://discord.gg/radiant
- **Email**: support@radiantblockchain.org
- **GitHub Issues**: https://github.com/Radiant-Core/Radiant-Core/issues

### Build from Source

```bash
git clone https://github.com/Radiant-Core/Radiant-Core.git
cd Radiant-Core
git checkout v2.1.1
mkdir build && cd build
cmake -GNinja .. -DCMAKE_BUILD_TYPE=Release
ninja
```

---

## Additional Documentation

- [ASERT_ANCHOR_BUG_FIX.md](../../ASERT_ANCHOR_BUG_FIX.md) - Technical analysis
- [CHAIN_RECOVERY_PROCEDURE.md](../../CHAIN_RECOVERY_PROCEDURE.md) - Detailed recovery steps
- [ASERT_DIFFICULTY_SPIKE_POSTMORTEM.md](../../ASERT_DIFFICULTY_SPIKE_POSTMORTEM.md) - Incident timeline

---

**⚠️ UPGRADE IMMEDIATELY - Network recovery depends on rapid adoption of v2.1.1 ⚠️**

---

*Released: March 9, 2026*  
*Emergency Response Team: Radiant Core Developers*
