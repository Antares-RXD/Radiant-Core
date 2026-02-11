#!/usr/bin/env python3
# Copyright (c) 2026 The Radiant developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""
Test OP_BLAKE3 (0xee) and OP_K12 (0xef) hash opcodes introduced in V2 Hard Fork.
Also tests re-enabled OP_LSHIFT (0x98) and OP_RSHIFT (0x99).

Test cases:
  1. OP_BLAKE3 produces correct 32-byte hash for empty input
  2. OP_BLAKE3 produces correct 32-byte hash for "abc"
  3. OP_K12 produces correct 32-byte hash for empty input
  4. OP_K12 produces correct 32-byte hash for "abc"
  5. OP_BLAKE3 output size is always 32 bytes
  6. OP_K12 output size is always 32 bytes
  7. OP_LSHIFT performs left bit-shift correctly (1 << 3 = 8)
  8. OP_RSHIFT performs right bit-shift correctly (16 >> 2 = 4)
  9. OP_2MUL multiplies by 2 correctly (5 * 2 = 10)
 10. OP_2DIV divides by 2 correctly (10 / 2 = 5)
 11. OP_2DIV truncates toward zero (7 / 2 = 3)
 12. OP_2MUL then OP_2DIV round-trip (3 * 2 / 2 = 3)
 13. OP_2DIV(-3) == -1 (negative truncation toward zero)
 14. OP_2MUL(INT64_MAX) overflows → script error (expect disconnect)

Note: Pre-activation height rejection cannot be tested here because
SCRIPT_ENHANCED_REFERENCES is gated on ERHeight (=10 in regtest),
and coinbase maturity (100 blocks) prevents spending below that height.
A pre-activation test would require custom chainparams or a dedicated test.

Uses P2SH funding+spending pattern from feature_int64_cscriptnum.py.
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
    OP_DROP,
    OP_EQUAL,
    OP_EQUALVERIFY,
    OP_HASH160,
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
from test_framework.util import assert_equal

# INT64_MAX as a CScriptNum: 0x7fffffffffffffff in little-endian = ff ff ff ff ff ff ff 7f
INT64_MAX_SCRIPTNUM = CScriptNum(0x7fffffffffffffff)


# Known test vectors (verified against b3sum and pycryptodome KangarooTwelve)
BLAKE3_EMPTY_HASH = bytes.fromhex(
    'af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262')
BLAKE3_ABC_HASH = bytes.fromhex(
    '6437b3ac38465133ffb63b75273a8db548c558465d79db03fd359c6cd5bd9d85')
K12_EMPTY_HASH = bytes.fromhex(
    '1ac2d450fc3b4205d19da7bfca1b37513c0803577ac7167f06fe2ce1f0ef39e5')
K12_ABC_HASH = bytes.fromhex(
    'ab174f328c55a5510b0b209791bf8b60e801a7cfc2aa42042dcb8f547fbe3a7d')


class V2HashOpcodesTest(BitcoinTestFramework):

    def set_test_params(self):
        self.num_nodes = 1
        self.block_heights = {}
        self.extra_args = [[
            '-acceptnonstdtxn=1',
        ]]

    def bootstrap_p2p(self, *, num_connections=1):
        """Add a P2P connection to the node."""
        for _ in range(num_connections):
            self.nodes[0].add_p2p_connection(P2PDataStore())
        for p2p in self.nodes[0].p2ps:
            p2p.wait_for_getheaders()

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

    def run_test(self):
        node = self.nodes[0]

        self.bootstrap_p2p()

        self.log.info("Create some blocks with OP_1 coinbase for spending.")
        tip = self.getbestblock(node)
        blocks = []
        for _ in range(20):
            tip = self.build_block(tip)
            blocks.append(tip)
        node.p2p.send_blocks_and_test(blocks, node, success=True)
        spendable_txns = [block.vtx[0] for block in blocks]

        self.log.info("Mature the blocks and get out of IBD.")
        self.generatetoaddress(node, 100, node.get_deterministic_priv_key().address)

        # Generate a key pair for P2SH signing
        privkeybytes = b"V2HASH!!" * 4
        private_key = ECKey()
        private_key.set(privkeybytes, True)
        public_key = private_key.get_pubkey().get_bytes()

        def create_fund_and_spend_tx(scriptsigextra, redeemextra) -> Tuple[CTransaction, CTransaction]:
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
            dummy = OP_1  # Required for 1-of-1 schnorr sig
            txspend.vin[0].scriptSig = CScript([dummy, txsig] + scriptsigextra + [redeem_script])
            txspend.rehash()

            return txfund, txspend

        test_cases = [
            ("OP_BLAKE3 on empty input", [b''], [OP_BLAKE3, BLAKE3_EMPTY_HASH, OP_EQUALVERIFY]),
            ("OP_BLAKE3 on 'abc'", [b'abc'], [OP_BLAKE3, BLAKE3_ABC_HASH, OP_EQUALVERIFY]),
            ("OP_K12 on empty input", [b''], [OP_K12, K12_EMPTY_HASH, OP_EQUALVERIFY]),
            ("OP_K12 on 'abc'", [b'abc'], [OP_K12, K12_ABC_HASH, OP_EQUALVERIFY]),
            ("OP_BLAKE3 output size = 32", [b'test data'], [OP_BLAKE3, OP_SIZE, CScriptNum(32), OP_EQUALVERIFY, OP_DROP]),
            ("OP_K12 output size = 32", [b'test data'], [OP_K12, OP_SIZE, CScriptNum(32), OP_EQUALVERIFY, OP_DROP]),
            ("OP_LSHIFT(1, 3) == 8", [CScriptNum(1), OP_3], [OP_LSHIFT, CScriptNum(8), OP_EQUALVERIFY]),
            ("OP_RSHIFT(16, 2) == 4", [CScriptNum(16), OP_2], [OP_RSHIFT, CScriptNum(4), OP_EQUALVERIFY]),
            ("OP_2MUL(5) == 10", [CScriptNum(5)], [OP_2MUL, CScriptNum(10), OP_EQUALVERIFY]),
            ("OP_2DIV(10) == 5", [CScriptNum(10)], [OP_2DIV, CScriptNum(5), OP_EQUALVERIFY]),
            ("OP_2DIV(7) == 3 (truncation)", [CScriptNum(7)], [OP_2DIV, CScriptNum(3), OP_EQUALVERIFY]),
            ("OP_2MUL then OP_2DIV round-trip", [CScriptNum(3)], [OP_2MUL, OP_2DIV, CScriptNum(3), OP_EQUALVERIFY]),
            ("OP_2DIV(-3) == -1 (negative truncation)", [CScriptNum(-3)], [OP_2DIV, CScriptNum(-1), OP_EQUALVERIFY]),
        ]

        for i, (desc, ssextra, rsextra) in enumerate(test_cases, 1):
            self.log.info(f"Test {i}: {desc}")
            tx0, tx = create_fund_and_spend_tx(ssextra, rsextra)

            # Send and mine funding tx first
            node.p2p.send_txs_and_test([tx0], node)
            self.log.info(f"  Funding tx {tx0.hash} accepted")
            self.generatetoaddress(node, 1, node.get_deterministic_priv_key().address)
            assert_equal(node.getrawmempool(), [])

            # Now send the spending tx
            node.p2p.send_txs_and_test([tx], node)
            self.log.info(f"  Spending tx {tx.hash} accepted")
            spendable_txns.insert(0, tx)

            # Mine the spending tx
            self.generatetoaddress(node, 1, node.get_deterministic_priv_key().address)
            assert_equal(node.getrawmempool(), [])
            self.log.info(f"  Test {i} PASSED")

        self.log.info(f"All {len(test_cases)} V2 opcode tests passed!")

        # --- Edge case: OP_2MUL overflow (INT64_MAX * 2) should fail ---
        overflow_test_num = len(test_cases) + 1
        self.log.info(f"Test {overflow_test_num}: OP_2MUL(INT64_MAX) overflow → script error")
        ssextra_overflow = [INT64_MAX_SCRIPTNUM]
        rsextra_overflow = [OP_2MUL, OP_DROP]
        tx0_overflow, tx_overflow = create_fund_and_spend_tx(ssextra_overflow, rsextra_overflow)

        # Fund the overflow test via RPC (avoids P2P connection issues)
        node.sendrawtransaction(tx0_overflow.serialize().hex())
        self.generatetoaddress(node, 1, node.get_deterministic_priv_key().address)
        assert_equal(node.getrawmempool(), [])
        self.log.info("  Funding tx mined")

        # Re-establish P2P connection for the failure test
        node.disconnect_p2ps()
        self.bootstrap_p2p()

        node.p2p.send_txs_and_test(
            [tx_overflow], node, success=False, expect_disconnect=True,
            reject_reason='mandatory-script-verify-flag-failed')
        self.log.info("  OP_2MUL overflow correctly rejected (peer disconnected)")
        self.log.info(f"  Test {overflow_test_num} PASSED")


if __name__ == '__main__':
    V2HashOpcodesTest().main()
