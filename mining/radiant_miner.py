#!/usr/bin/env python3

import hashlib
import json
import struct
import subprocess
import time

# --- Configuration ---
import os

RPC_USER = os.getenv("RPC_USER", "testnet")
RPC_PASS = os.getenv("RPC_PASS", "testnetpass123")
RPC_PORT = os.getenv("RPC_PORT", "17332")
PROJECT_DIR = os.getenv("PROJECT_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NETWORK = os.getenv("NETWORK", "testnet")

# --- Hashing --- #
def sha512_256(data):
    """Proper SHA-512/256 using correct initialization vectors."""
    return hashlib.new('sha512_256', data).digest()

def sha512_256d(data):
    """Double SHA-512/256 as used by Radiant for block hashing."""
    return sha512_256(sha512_256(data))

def sha256d(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

class RadiantMiner:
    def __init__(self):
        self.running = True

    def run(self):
        print("Radiant CPU Miner (SHA-512/256d) Started")
        while self.running:
            template = self._get_block_template()
            if not template:
                print("Failed to get block template, retrying in 5s...")
                time.sleep(5)
                continue
            self._mine_block(template)

    def _get_block_template(self):
        try:
            result = subprocess.run([
                f"{PROJECT_DIR}/build/src/radiant-cli", f'-{NETWORK}',
                f'-rpcuser={RPC_USER}', f'-rpcpassword={RPC_PASS}',
                f'-rpcport={RPC_PORT}', 'getblocktemplate',
                '{"rules": ["segwit"]}'
            ], capture_output=True, text=True, cwd=PROJECT_DIR, check=True)
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"Error getting block template: {e}")
            return None

    def _mine_block(self, template):
        print(f"\nMining block at height {template['height']}")
        
        # 1. Create Coinbase Transaction
        coinbase_tx_data, address = self._create_coinbase_tx(template)
        if not coinbase_tx_data:
            print("Failed to create coinbase transaction.")
            return

        # 2. Calculate Merkle Root
        coinbase_txid = sha256d(coinbase_tx_data)
        transactions_txids = [coinbase_txid] + [bytes.fromhex(tx['txid'])[::-1] for tx in template['transactions']]
        merkle_root = self._calculate_merkle_root(transactions_txids)
        print(f"Merkle Root: {merkle_root[::-1].hex()}")

        # 3. Mine the block
        self._mine(template, merkle_root, [coinbase_tx_data] + [bytes.fromhex(tx['data']) for tx in template['transactions']])

    def _mine(self, template, merkle_root, transactions_data):
        target = int(template['target'], 16)
        print(f"Target: {template['target']}")

        # Bits field is already in compact form, needs little-endian byte order
        bits_bytes = bytes.fromhex(template['bits'])
        bits_le = bits_bytes[::-1]  # Reverse to little-endian
        
        header = struct.pack('<i', template['version']) \
               + bytes.fromhex(template['previousblockhash'])[::-1] \
               + merkle_root \
               + struct.pack('<I', template['curtime']) \
               + bits_le \
               + b'\x00\x00\x00\x00' # Placeholder for nonce

        start_time = time.time()
        best_hash = b'\xff' * 32
        for nonce in range(2**32):
            header_with_nonce = header[:-4] + struct.pack('<I', nonce)
            block_hash = sha512_256d(header_with_nonce)
            
            if block_hash[::-1] < best_hash:
                best_hash = block_hash[::-1]

            if int.from_bytes(block_hash, 'little') < target:
                elapsed = time.time() - start_time
                hash_rate = nonce / elapsed if elapsed > 0 else 0
                print(f"\n*** FOUND VALID HASH! Nonce: {nonce} ***")
                print(f"Hash: {block_hash[::-1].hex()}")
                print(f"Hash Rate: {hash_rate:,.0f} H/s")

                self._submit_block(header_with_nonce, transactions_data)
                return

            if nonce % 1000000 == 0 and nonce != 0:
                elapsed = time.time() - start_time
                hash_rate = nonce / elapsed if elapsed > 0 else 0
                print(f"Checked {nonce:,} nonces @ {hash_rate:,.0f} H/s | Best: {best_hash.hex()[:16]}...")

        print("Failed to find a nonce in the given range.")

    def _get_new_address(self):
        try:
            result = subprocess.run([
                f"{PROJECT_DIR}/build/src/radiant-cli", f'-{NETWORK}',
                '-rpcwallet=miner',
                f'-rpcuser={RPC_USER}', f'-rpcpassword={RPC_PASS}',
                f'-rpcport={RPC_PORT}', 'getnewaddress'
            ], capture_output=True, text=True, cwd=PROJECT_DIR, check=True)
            return result.stdout.strip()
        except Exception as e:
            print(f"Error getting new address: {e}")
            return None

    def _base58_decode(self, s):
        b58_digits = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
        n = 0
        for char in s:
            n = n * 58 + b58_digits.index(char)
        return n.to_bytes((n.bit_length() + 7) // 8, 'big')

    def _create_coinbase_tx(self, template):
        address = self._get_new_address()
        if not address:
            return None, None
        
        decoded_address = self._base58_decode(address)
        pubkeyhash = decoded_address[1:-4]

        # BIP34 height encoding
        height = template['height']
        if height == 0:
            coinbase_script_sig = b'\x00'  # OP_0
        elif height <= 16:
            coinbase_script_sig = bytes([0x50 + height])  # OP_1 through OP_16
        elif height <= 0x7f:
            coinbase_script_sig = bytes([0x01, height])  # 1-byte push
        elif height <= 0x7fff:
            coinbase_script_sig = b'\x02' + struct.pack('<H', height)  # 2-byte push
        elif height <= 0x7fffff:
            coinbase_script_sig = b'\x03' + struct.pack('<I', height)[:3]  # 3-byte push
        else:
            coinbase_script_sig = b'\x04' + struct.pack('<I', height)  # 4-byte push
        coinbase_output_script = b'\x76\xa9\x14' + pubkeyhash + b'\x88\xac'

        # --- Simplified Transaction Serialization ---
        # This is still not fully correct, but is a step closer.
        # A full implementation requires serializing each part of the tx correctly.
        
        # tx version
        tx_data = struct.pack('<i', 1)
        # vin
        tx_data += struct.pack('<B', 1) # 1 input
        tx_data += b'\x00' * 32 # prevout hash
        tx_data += struct.pack('<I', 0xffffffff) # prevout index
        tx_data += struct.pack('<B', len(coinbase_script_sig)) + coinbase_script_sig
        tx_data += struct.pack('<I', 0xffffffff) # sequence
        # vout
        tx_data += struct.pack('<B', 1) # 1 output
        tx_data += struct.pack('<q', template['coinbasevalue'])
        tx_data += struct.pack('<B', len(coinbase_output_script)) + coinbase_output_script
        # locktime
        tx_data += struct.pack('<I', 0)

        return tx_data, address

    def _calculate_merkle_root(self, txids):
        # This function now expects a list of txids as bytes
        if not txids:
            return b'\x00' * 32

        while len(txids) > 1:
            if len(txids) % 2 != 0:
                txids.append(txids[-1])
            next_level = []
            for i in range(0, len(txids), 2):
                # Note: txids are already bytes, no need for bytes.fromhex
                combined = txids[i] + txids[i+1]
                next_level.append(sha256d(combined))
            txids = next_level
        return txids[0]

    def _serialize_tx(self, tx):
        # Simplified serialization for coinbase
        data = struct.pack('<i', tx['version'])
        data += self._serialize_varint(len(tx['vin']))
        for vin in tx['vin']:
            data += b'\x00' * 32 # prevout hash
            data += struct.pack('<I', 0xffffffff) # prevout index
            data += self._serialize_varint(len(vin['coinbase'])) + vin['coinbase']
            data += struct.pack('<I', vin['sequence'])
        data += self._serialize_varint(len(tx['vout']))
        for vout in tx['vout']:
            data += struct.pack('<q', vout['value'])
            data += self._serialize_varint(len(vout['scriptPubKey'])) + vout['scriptPubKey']
        data += struct.pack('<I', tx['locktime'])
        return data

    def _serialize_varint(self, n):
        if n < 0xfd:
            return struct.pack('<B', n)
        elif n <= 0xffff:
            return b'\xfd' + struct.pack('<H', n)
        elif n <= 0xffffffff:
            return b'\xfe' + struct.pack('<I', n)
        else:
            return b'\xff' + struct.pack('<Q', n)

    def _submit_block(self, header, transactions):
        block_hex = header.hex()
        block_hex += self._serialize_varint(len(transactions)).hex()
        for tx_data in transactions:
            block_hex += tx_data.hex()
        
        try:
            result = subprocess.run([
                f"{PROJECT_DIR}/build/src/radiant-cli", f'-{NETWORK}',
                f'-rpcuser={RPC_USER}', f'-rpcpassword={RPC_PASS}',
                f'-rpcport={RPC_PORT}', 'submitblock', block_hex
            ], capture_output=True, text=True, cwd=PROJECT_DIR, check=True)
            print(f"Block submitted successfully: {result.stdout}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to submit block: {e.stderr}")

if __name__ == "__main__":
    miner = RadiantMiner()
    miner.run()
