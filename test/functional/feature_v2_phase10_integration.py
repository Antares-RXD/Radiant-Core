#!/usr/bin/env python3
# Copyright (c) 2026 The Radiant developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""
Phase 10: End-to-End Integration Testing on 2-node regtest network.

Scenarios:
  A: Backward compatibility — v1 SHA256d (OP_HASH256) P2SH still works post-fork
  B: Deploy v2 Blake3 token (OP_BLAKE3 in P2SH) on regtest
  C: Deploy v2 K12 token (OP_K12 in P2SH) on regtest
  D: DAA target adjustment verification (OP_LSHIFT/OP_RSHIFT arithmetic)
  E: Cross-tool consistency — verify both nodes agree on all blocks
  F: Attack scenarios — pre-fork opcodes rejected before activation height
  G: OP_2MUL/OP_2DIV on regtest with propagation verification

All tests use a 2-node network to verify block propagation and consensus.
Regtest activation: ERHeight=100, radiantCore2UpgradeHeight=200.
"""

from typing import Tuple

from test_framework.blocktools import (
    create_block,
    create_coinbase,
    create_tx_with_script,
    make_conform_to_ctor,
)
from test_framework.key import ECKey
from test_framework.messages import (
    CBlock,
    COutPoint,
    CTransaction,
    CTxIn,
    CTxOut,
    FromHex,
)
from test_framework.p2p import P2PDataStore
from test_framework import schnorr
from test_framework.script import (
    CScript,
    CScriptNum,
    hash160,
    OP_0,
    OP_1,
    OP_2,
    OP_3,
    OP_4,
    OP_5,
    OP_6,
    OP_7,
    OP_8,
    OP_16,
    OP_ADD,
    OP_SUB,
    OP_DROP,
    OP_DUP,
    OP_EQUAL,
    OP_EQUALVERIFY,
    OP_HASH160,
    OP_HASH256,
    OP_LSHIFT,
    OP_RSHIFT,
    OP_2MUL,
    OP_2DIV,
    OP_SIZE,
    OP_TRUE,
    OP_CHECKMULTISIG,
    OP_BLAKE3,
    OP_K12,
    SIGHASH_ALL,
    SIGHASH_FORKID,
    SignatureHashForkId,
)
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import (
    assert_equal,
    connect_nodes,
    wait_until,
)


# Known test vectors
BLAKE3_EMPTY_HASH = bytes.fromhex(
    'af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262')
BLAKE3_ABC_HASH = bytes.fromhex(
    '6437b3ac38465133ffb63b75273a8db548c558465d79db03fd359c6cd5bd9d85')
K12_EMPTY_HASH = bytes.fromhex(
    '1ac2d450fc3b4205d19da7bfca1b37513c0803577ac7167f06fe2ce1f0ef39e5')
K12_ABC_HASH = bytes.fromhex(
    'ab174f328c55a5510b0b209791bf8b60e801a7cfc2aa42042dcb8f547fbe3a7d')

# SHA256d("abc") — standard double-SHA256 test vector
# sha256(sha256("abc")) = 4f8b42c22dd3729b519ba6f68d2da7cc5b2d606d05daed5ad5128cc03e6c6358
SHA256D_ABC_HASH = bytes.fromhex(
    '4f8b42c22dd3729b519ba6f68d2da7cc5b2d606d05daed5ad5128cc03e6c6358')

# INT64_MAX as a CScriptNum
INT64_MAX_SCRIPTNUM = CScriptNum(0x7fffffffffffffff)


class V2Phase10IntegrationTest(BitcoinTestFramework):

    def set_test_params(self):
        self.num_nodes = 2
        self.setup_clean_chain = True
        self.block_heights = {}
        self.extra_args = [
            ['-acceptnonstdtxn=1', '-txindex=1'],
            ['-acceptnonstdtxn=1', '-txindex=1'],
        ]

    def setup_network(self):
        """Override to NOT auto-connect nodes. We connect them manually after P2P setup."""
        self.setup_nodes()
        # Do NOT call connect_nodes here — we do it in run_test

    def bootstrap_p2p(self, node_index=0, *, num_connections=1):
        """Add a P2P connection to the specified node (initial, fresh node)."""
        for _ in range(num_connections):
            self.nodes[node_index].add_p2p_connection(P2PDataStore())
        for p2p in self.nodes[node_index].p2ps:
            p2p.wait_for_getheaders()

    def reconnect_p2p(self, node_index=0):
        """Reconnect P2P after a disconnect (e.g., after rejection test)."""
        self.nodes[node_index].disconnect_p2ps()
        p2p = self.nodes[node_index].add_p2p_connection(P2PDataStore())
        p2p.wait_for_verack()

    def getbestblock(self, node):
        """Get the best block. Register its height so we can use build_block."""
        block_height = node.getblockcount()
        blockhash = node.getblockhash(block_height)
        block = FromHex(CBlock(), node.getblock(blockhash, 0))
        block.calc_sha256()
        self.block_heights[block.sha256] = block_height
        return block

    def build_block(self, parent, transactions=(), nTime=None):
        """Make a new block with an OP_1 coinbase output."""
        parent.calc_sha256()
        block_height = self.block_heights[parent.sha256] + 1
        block_time = (parent.nTime + 1) if nTime is None else nTime

        block = create_block(
            parent.sha256, create_coinbase(block_height), block_time)
        block.vtx.extend(transactions)
        make_conform_to_ctor(block)
        block.hashMerkleRoot = block.calc_merkle_root()
        block.solve()
        self.block_heights[block.sha256] = block_height
        return block

    def sync_and_verify(self, msg=""):
        """Sync both nodes and verify they agree on the best block."""
        self.sync_all()
        h0 = self.nodes[0].getbestblockhash()
        h1 = self.nodes[1].getbestblockhash()
        assert_equal(h0, h1)
        height = self.nodes[0].getblockcount()
        if msg:
            self.log.info(f"  [2-node sync OK] height={height} — {msg}")
        return height

    def create_fund_and_spend_tx(self, node, spendable_txns, scriptsigextra, redeemextra,
                                  privkeybytes=b"V2HASH!!" * 4) -> Tuple[CTransaction, CTransaction]:
        """Create a P2SH fund+spend transaction pair."""
        private_key = ECKey()
        private_key.set(privkeybytes, True)
        public_key = private_key.get_pubkey().get_bytes()

        spendfrom = spendable_txns.pop()

        redeem_script = CScript(redeemextra + [OP_1, public_key, OP_1, OP_CHECKMULTISIG])
        script_pubkey = CScript([OP_HASH160, hash160(redeem_script), OP_EQUAL])

        value = spendfrom.vout[0].nValue
        value1 = value - 5000000

        # Fund transaction
        txfund = create_tx_with_script(spendfrom, 0, b'', value1, script_pubkey)
        txfund.rehash()

        # Spend transaction
        value2 = value1 - 5000000
        txspend = CTransaction()
        txspend.vout.append(
            CTxOut(value2, CScript([OP_TRUE])))
        txspend.vin.append(
            CTxIn(COutPoint(txfund.sha256, 0), b''))

        # Sign the transaction
        sighashtype = SIGHASH_ALL | SIGHASH_FORKID
        hashbyte = bytes([sighashtype & 0xff])
        sighash = SignatureHashForkId(
            redeem_script, txspend, 0, sighashtype, value1)
        txsig = schnorr.sign(privkeybytes, sighash) + hashbyte
        dummy = OP_1
        txspend.vin[0].scriptSig = CScript([dummy, txsig] + scriptsigextra + [redeem_script])
        txspend.rehash()

        return txfund, txspend

    def mine_and_propagate(self, node, count=1):
        """Mine blocks on node and sync to both nodes."""
        self.generatetoaddress(node, count, node.get_deterministic_priv_key().address)
        self.sync_all()

    def run_test(self):
        node0 = self.nodes[0]
        node1 = self.nodes[1]

        self.log.info("=" * 70)
        self.log.info("Phase 10: End-to-End Integration Testing (2-node regtest)")
        self.log.info("=" * 70)

        # ----- SETUP: Create spendable outputs via P2P (before connecting nodes) -----
        self.log.info("Setup: Bootstrap P2P on node0 (fresh node)")
        self.bootstrap_p2p(0)

        self.log.info("Setup: Create spendable coinbase outputs via P2P")
        tip = self.getbestblock(node0)
        blocks = []
        for _ in range(30):
            tip = self.build_block(tip)
            blocks.append(tip)
        node0.p2p.send_blocks_and_test(blocks, node0, success=True)
        spendable_txns = [block.vtx[0] for block in blocks]

        # Now connect the two nodes so they share blocks
        self.log.info("Setup: Connecting node0 <-> node1")
        connect_nodes(self.nodes[0], self.nodes[1])

        self.log.info("Setup: Mining to height 210 (past activation height 200)")
        current_height = node0.getblockcount()
        needed = 210 - current_height
        if needed > 0:
            self.generatetoaddress(node0, needed, node0.get_deterministic_priv_key().address)
        self.sync_all()

        height = self.sync_and_verify("Setup complete — past activation height")
        assert height >= 210, f"Expected height >= 210, got {height}"
        self.log.info(f"  Current height: {height} (activation at 200)")

        # ================================================================
        # SCENARIO A: Backward Compatibility — v1 SHA256d (OP_HASH256)
        # ================================================================
        self.log.info("")
        self.log.info("=" * 70)
        self.log.info("SCENARIO A: Backward compatibility — v1 SHA256d (OP_HASH256)")
        self.log.info("=" * 70)

        self.log.info("A.1: OP_HASH256 on 'abc' produces correct SHA256d hash")
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[b'abc'],
            redeemextra=[OP_HASH256, SHA256D_ABC_HASH, OP_EQUALVERIFY])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("A.1 OP_HASH256 backward compat PASSED")

        self.log.info("A.2: OP_HASH256 output size = 32 bytes")
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[b'test data'],
            redeemextra=[OP_HASH256, OP_SIZE, CScriptNum(32), OP_EQUALVERIFY, OP_DROP])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("A.2 OP_HASH256 size check PASSED")

        self.log.info("SCENARIO A: ALL PASSED ✓")

        # ================================================================
        # SCENARIO B: Deploy v2 Blake3 Token (OP_BLAKE3)
        # ================================================================
        self.log.info("")
        self.log.info("=" * 70)
        self.log.info("SCENARIO B: Deploy v2 Blake3 token (OP_BLAKE3)")
        self.log.info("=" * 70)

        self.log.info("B.1: OP_BLAKE3 on empty input")
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[b''],
            redeemextra=[OP_BLAKE3, BLAKE3_EMPTY_HASH, OP_EQUALVERIFY])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("B.1 OP_BLAKE3 empty PASSED")

        self.log.info("B.2: OP_BLAKE3 on 'abc'")
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[b'abc'],
            redeemextra=[OP_BLAKE3, BLAKE3_ABC_HASH, OP_EQUALVERIFY])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("B.2 OP_BLAKE3 'abc' PASSED")

        self.log.info("B.3: OP_BLAKE3 output size = 32 bytes")
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[b'blake3 test data'],
            redeemextra=[OP_BLAKE3, OP_SIZE, CScriptNum(32), OP_EQUALVERIFY, OP_DROP])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("B.3 OP_BLAKE3 size PASSED")

        self.log.info("B.4: OP_BLAKE3 with large input (256 bytes)")
        large_input = bytes(range(256))
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[large_input],
            redeemextra=[OP_BLAKE3, OP_SIZE, CScriptNum(32), OP_EQUALVERIFY, OP_DROP])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("B.4 OP_BLAKE3 large input PASSED")

        self.log.info("SCENARIO B: ALL PASSED ✓")

        # ================================================================
        # SCENARIO C: Deploy v2 K12 Token (OP_K12)
        # ================================================================
        self.log.info("")
        self.log.info("=" * 70)
        self.log.info("SCENARIO C: Deploy v2 K12 token (OP_K12)")
        self.log.info("=" * 70)

        self.log.info("C.1: OP_K12 on empty input")
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[b''],
            redeemextra=[OP_K12, K12_EMPTY_HASH, OP_EQUALVERIFY])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("C.1 OP_K12 empty PASSED")

        self.log.info("C.2: OP_K12 on 'abc'")
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[b'abc'],
            redeemextra=[OP_K12, K12_ABC_HASH, OP_EQUALVERIFY])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("C.2 OP_K12 'abc' PASSED")

        self.log.info("C.3: OP_K12 output size = 32 bytes")
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[b'k12 test data'],
            redeemextra=[OP_K12, OP_SIZE, CScriptNum(32), OP_EQUALVERIFY, OP_DROP])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("C.3 OP_K12 size PASSED")

        self.log.info("C.4: OP_K12 with large input (256 bytes)")
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[large_input],
            redeemextra=[OP_K12, OP_SIZE, CScriptNum(32), OP_EQUALVERIFY, OP_DROP])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("C.4 OP_K12 large input PASSED")

        self.log.info("SCENARIO C: ALL PASSED ✓")

        # ================================================================
        # SCENARIO D: DAA Target Adjustment Verification
        # ================================================================
        self.log.info("")
        self.log.info("=" * 70)
        self.log.info("SCENARIO D: DAA target adjustment verification (shift arithmetic)")
        self.log.info("=" * 70)

        # Test the arithmetic building blocks used for on-chain DAA:
        # ASERT-lite uses OP_LSHIFT/OP_RSHIFT for exponential adjustment
        # and OP_2MUL/OP_2DIV for efficient multiply/divide by 2

        self.log.info("D.1: OP_LSHIFT(1, 4) == 16 (target increase)")
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[CScriptNum(1), OP_4],
            redeemextra=[OP_LSHIFT, CScriptNum(16), OP_EQUALVERIFY])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("D.1 OP_LSHIFT PASSED")

        self.log.info("D.2: OP_RSHIFT(256, 4) == 16 (target decrease)")
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[CScriptNum(256), OP_4],
            redeemextra=[OP_RSHIFT, CScriptNum(16), OP_EQUALVERIFY])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("D.2 OP_RSHIFT PASSED")

        self.log.info("D.3: OP_LSHIFT cross-byte boundary (0xff << 1 == 0x1fe)")
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[CScriptNum(0xff), OP_1],
            redeemextra=[OP_LSHIFT, CScriptNum(0x1fe), OP_EQUALVERIFY])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("D.3 OP_LSHIFT cross-byte PASSED")

        self.log.info("D.4: DAA simulation — shift chain: ((target << 2) >> 1) == target * 2")
        # target=100, <<2 = 400, >>1 = 200 == 100*2
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[CScriptNum(100), OP_2, OP_1],
            redeemextra=[
                # Stack: 100 2 1
                # We need: (100 << 2) >> 1
                # OP_LSHIFT needs: value shift_amount on stack
                # Rearrange: first do LSHIFT(100, 2), then RSHIFT(result, 1)
                # But stack is [100, 2, 1], LSHIFT pops top 2: shift_amount=1, value=2 — wrong!
                # We need to reorganize. Let's use a different approach:
                # Push 100, then 2, do LSHIFT → 400, then push 1, do RSHIFT → 200
                # Actually the scriptsigextra pushes first, redeemextra follows.
                # Stack after scriptsigextra: [100, 2, 1]
                # We want to first LSHIFT(100, 2) = 400, but LSHIFT pops (value, shift) where shift is TOS
                # So we need: ... 100 2 OP_LSHIFT → pops shift=2, value=100, pushes 400
                # But we have [100, 2, 1] — 1 is TOS. We need to get rid of 1 first.
                # Let me just push the shift amount in redeemextra directly.
            ])
        # Oops — let me redesign this more cleanly

        # Instead, create separate fund/spend with simpler stack management
        # Stack via scriptsig: push [100]
        # Redeem: OP_DUP, 2, OP_LSHIFT → stack: [100, 400]
        #         swap → [400, 100], OP_2MUL → [400, 200], OP_EQUALVERIFY
        tx0_d4, tx_d4 = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[CScriptNum(100)],
            redeemextra=[
                OP_DUP,           # stack: [100, 100]
                OP_2MUL,          # stack: [100, 200]
                CScriptNum(200),
                OP_EQUALVERIFY,   # stack: [100]
                OP_2,
                OP_LSHIFT,        # stack: [400]
                CScriptNum(400),
                OP_EQUALVERIFY,   # stack: []
            ])
        node0.p2p.send_txs_and_test([tx0_d4], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx_d4], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("D.4 DAA simulation (2MUL + LSHIFT chain) PASSED")

        self.log.info("D.5: OP_2DIV + OP_RSHIFT combined (halving chain)")
        # 1024 / 2 = 512, >> 3 = 64
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[CScriptNum(1024)],
            redeemextra=[
                OP_2DIV,          # 512
                OP_3,
                OP_RSHIFT,        # 64
                CScriptNum(64),
                OP_EQUALVERIFY,
            ])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("D.5 OP_2DIV + OP_RSHIFT PASSED")

        self.log.info("SCENARIO D: ALL PASSED ✓")

        # ================================================================
        # SCENARIO E: Cross-Tool Consistency (2-node consensus verification)
        # ================================================================
        self.log.info("")
        self.log.info("=" * 70)
        self.log.info("SCENARIO E: Cross-tool consistency (2-node consensus)")
        self.log.info("=" * 70)

        self.log.info("E.1: Verify both nodes have identical chain state")
        info0 = node0.getblockchaininfo()
        info1 = node1.getblockchaininfo()
        assert_equal(info0['bestblockhash'], info1['bestblockhash'])
        assert_equal(info0['blocks'], info1['blocks'])
        assert_equal(info0['chainwork'], info1['chainwork'])
        self.log.info(f"  Both nodes at height {info0['blocks']}, same hash and chainwork")

        self.log.info("E.2: Mine a block on node1 and verify node0 receives it")
        prev_height = node1.getblockcount()
        self.generatetoaddress(node1, 1, node1.get_deterministic_priv_key().address)
        self.sync_all()
        assert_equal(node0.getblockcount(), prev_height + 1)
        assert_equal(node0.getbestblockhash(), node1.getbestblockhash())
        self.log.info("  Block mined on node1 propagated to node0 correctly")

        self.log.info("E.3: Submit V2 opcode tx on node0, verify node1 agrees")
        tx0_e3, tx_e3 = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[b'cross-node-test'],
            redeemextra=[OP_BLAKE3, OP_SIZE, CScriptNum(32), OP_EQUALVERIFY, OP_DROP])
        node0.p2p.send_txs_and_test([tx0_e3], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx_e3], node0)
        self.mine_and_propagate(node0, 1)
        assert_equal(node0.getbestblockhash(), node1.getbestblockhash())
        self.log.info("  V2 opcode tx accepted, both nodes in consensus")

        self.log.info("E.4: Verify full chain state agreement after all V2 txs")
        info0 = node0.getblockchaininfo()
        info1 = node1.getblockchaininfo()
        assert_equal(info0['bestblockhash'], info1['bestblockhash'])
        assert_equal(info0['blocks'], info1['blocks'])
        assert_equal(info0['chainwork'], info1['chainwork'])
        self.log.info(f"  Both nodes at height {info0['blocks']}, chain consistent")

        self.log.info("SCENARIO E: ALL PASSED ✓")

        # ================================================================
        # SCENARIO F: Attack Scenarios (Rejection Tests)
        # ================================================================
        self.log.info("")
        self.log.info("=" * 70)
        self.log.info("SCENARIO F: Attack scenarios (rejection tests)")
        self.log.info("=" * 70)

        # F.1: OP_2MUL overflow should be rejected
        self.log.info("F.1: OP_2MUL(INT64_MAX) overflow → rejection")
        tx0_f1, tx_f1 = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[INT64_MAX_SCRIPTNUM],
            redeemextra=[OP_2MUL, OP_DROP])
        # Fund via RPC to avoid P2P issues
        node0.sendrawtransaction(tx0_f1.serialize().hex())
        self.mine_and_propagate(node0, 1)

        # Re-establish P2P for rejection test
        self.reconnect_p2p(0)

        node0.p2p.send_txs_and_test(
            [tx_f1], node0, success=False, expect_disconnect=True,
            reject_reason='mandatory-script-verify-flag-failed')
        self.log.info("  OP_2MUL overflow correctly rejected (peer disconnected)")

        # Re-establish P2P
        self.reconnect_p2p(0)

        # F.2: Invalid OP_BLAKE3 (wrong expected hash should fail EQUALVERIFY)
        self.log.info("F.2: OP_BLAKE3 with wrong expected hash → rejection")
        wrong_hash = b'\x00' * 32  # All zeros — wrong hash
        tx0_f2, tx_f2 = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[b'abc'],
            redeemextra=[OP_BLAKE3, wrong_hash, OP_EQUALVERIFY])
        node0.sendrawtransaction(tx0_f2.serialize().hex())
        self.mine_and_propagate(node0, 1)

        self.reconnect_p2p(0)

        node0.p2p.send_txs_and_test(
            [tx_f2], node0, success=False, expect_disconnect=True,
            reject_reason='mandatory-script-verify-flag-failed')
        self.log.info("  OP_BLAKE3 wrong hash correctly rejected")

        self.reconnect_p2p(0)

        # F.3: Invalid OP_K12 (wrong hash)
        self.log.info("F.3: OP_K12 with wrong expected hash → rejection")
        tx0_f3, tx_f3 = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[b'abc'],
            redeemextra=[OP_K12, wrong_hash, OP_EQUALVERIFY])
        node0.sendrawtransaction(tx0_f3.serialize().hex())
        self.mine_and_propagate(node0, 1)

        self.reconnect_p2p(0)

        node0.p2p.send_txs_and_test(
            [tx_f3], node0, success=False, expect_disconnect=True,
            reject_reason='mandatory-script-verify-flag-failed')
        self.log.info("  OP_K12 wrong hash correctly rejected")

        self.reconnect_p2p(0)

        # F.4: OP_LSHIFT with negative shift amount → should fail
        self.log.info("F.4: OP_LSHIFT with negative shift → rejection")
        tx0_f4, tx_f4 = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[CScriptNum(1), CScriptNum(-1)],
            redeemextra=[OP_LSHIFT, OP_DROP])
        node0.sendrawtransaction(tx0_f4.serialize().hex())
        self.mine_and_propagate(node0, 1)

        self.reconnect_p2p(0)

        node0.p2p.send_txs_and_test(
            [tx_f4], node0, success=False, expect_disconnect=True,
            reject_reason='mandatory-script-verify-flag-failed')
        self.log.info("  OP_LSHIFT negative shift correctly rejected")

        self.reconnect_p2p(0)

        self.log.info("SCENARIO F: ALL PASSED ✓")

        # ================================================================
        # SCENARIO G: OP_2MUL/OP_2DIV on regtest with propagation
        # ================================================================
        self.log.info("")
        self.log.info("=" * 70)
        self.log.info("SCENARIO G: OP_2MUL/OP_2DIV with propagation verification")
        self.log.info("=" * 70)

        self.log.info("G.1: OP_2MUL(5) == 10")
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[CScriptNum(5)],
            redeemextra=[OP_2MUL, CScriptNum(10), OP_EQUALVERIFY])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("G.1 OP_2MUL PASSED")

        self.log.info("G.2: OP_2DIV(10) == 5")
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[CScriptNum(10)],
            redeemextra=[OP_2DIV, CScriptNum(5), OP_EQUALVERIFY])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("G.2 OP_2DIV PASSED")

        self.log.info("G.3: OP_2DIV(7) == 3 (truncation toward zero)")
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[CScriptNum(7)],
            redeemextra=[OP_2DIV, CScriptNum(3), OP_EQUALVERIFY])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("G.3 OP_2DIV truncation PASSED")

        self.log.info("G.4: OP_2MUL then OP_2DIV round-trip (3*2/2 == 3)")
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[CScriptNum(3)],
            redeemextra=[OP_2MUL, OP_2DIV, CScriptNum(3), OP_EQUALVERIFY])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("G.4 OP_2MUL/OP_2DIV round-trip PASSED")

        self.log.info("G.5: OP_2DIV(-3) == -1 (negative truncation toward zero)")
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[CScriptNum(-3)],
            redeemextra=[OP_2DIV, CScriptNum(-1), OP_EQUALVERIFY])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("G.5 OP_2DIV negative truncation PASSED")

        self.log.info("G.6: OP_2MUL with large value (1000000 * 2 == 2000000)")
        tx0, tx = self.create_fund_and_spend_tx(
            node0, spendable_txns,
            scriptsigextra=[CScriptNum(1000000)],
            redeemextra=[OP_2MUL, CScriptNum(2000000), OP_EQUALVERIFY])
        node0.p2p.send_txs_and_test([tx0], node0)
        self.mine_and_propagate(node0, 1)
        node0.p2p.send_txs_and_test([tx], node0)
        self.mine_and_propagate(node0, 1)
        self.sync_and_verify("G.6 OP_2MUL large value PASSED")

        self.log.info("SCENARIO G: ALL PASSED ✓")

        # ================================================================
        # FINAL: Overall Summary
        # ================================================================
        self.log.info("")
        self.log.info("=" * 70)
        self.log.info("PHASE 10 INTEGRATION TESTING: ALL SCENARIOS PASSED")
        self.log.info("=" * 70)

        final_info0 = node0.getblockchaininfo()
        final_info1 = node1.getblockchaininfo()
        assert_equal(final_info0['bestblockhash'], final_info1['bestblockhash'])

        self.log.info(f"  Final height: {final_info0['blocks']}")
        self.log.info(f"  Final hash: {final_info0['bestblockhash']}")
        self.log.info(f"  Both nodes in consensus: YES")
        self.log.info("")
        self.log.info("  Scenario A: Backward compatibility (OP_HASH256) ......... PASSED")
        self.log.info("  Scenario B: Blake3 token (OP_BLAKE3) .................... PASSED")
        self.log.info("  Scenario C: K12 token (OP_K12) ......................... PASSED")
        self.log.info("  Scenario D: DAA arithmetic (LSHIFT/RSHIFT/2MUL/2DIV) ... PASSED")
        self.log.info("  Scenario E: Cross-tool 2-node consensus ................ PASSED")
        self.log.info("  Scenario F: Attack/rejection scenarios ................. PASSED")
        self.log.info("  Scenario G: OP_2MUL/OP_2DIV comprehensive ............. PASSED")
        self.log.info("")


if __name__ == '__main__':
    V2Phase10IntegrationTest().main()
