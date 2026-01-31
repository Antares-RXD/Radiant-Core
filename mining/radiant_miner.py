#!/usr/bin/env python3

import hashlib
import json
import struct
import subprocess
import time
import signal
import sys
from pathlib import Path

# --- Configuration ---
import os

# Add mining directory to path for shared utilities
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mining_utils import (
    sha512_256, sha512_256d, sha256d,
    base58_decode, encode_bip34_height,
    create_coinbase_transaction, calculate_merkle_root,
    serialize_varint, HASH_SIZE, HEADER_SIZE, MAX_UINT32
)

# Try to load from config file if env vars not set
CONFIG_DIR = Path.home() / ".radiant_mining"
CONFIG_FILE = CONFIG_DIR / "config.json"

def load_config():
    """Load configuration from file or environment"""
    config = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                config = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
    
    # Environment variables override config file
    rpc_user = os.getenv("RPC_USER") or config.get("rpc", {}).get("user")
    rpc_pass = os.getenv("RPC_PASS") or config.get("rpc", {}).get("pass")
    rpc_port = os.getenv("RPC_PORT") or str(config.get("rpc", {}).get("port", "27332"))
    network = os.getenv("NETWORK") or config.get("network", "testnet")
    
    return rpc_user, rpc_pass, rpc_port, network

RPC_USER, RPC_PASS, RPC_PORT, NETWORK = load_config()
PROJECT_DIR = os.getenv("PROJECT_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Validate required configuration
if not RPC_USER or not RPC_PASS:
    print("ERROR: RPC_USER and RPC_PASS are required")
    print("Set them in one of these ways:")
    print("  1. Environment variables:")
    print("     export RPC_USER=your_rpc_username")
    print("     export RPC_PASS=your_rpc_password")
    print(f"  2. Config file: {CONFIG_FILE}")
    exit(1)

# Validate port is numeric
try:
    RPC_PORT = str(int(RPC_PORT))
except ValueError:
    print(f"ERROR: RPC_PORT must be numeric, got: {RPC_PORT}")
    exit(1)

# Validate network
if NETWORK not in ["testnet", "mainnet", "regtest"]:
    print(f"ERROR: Invalid NETWORK '{NETWORK}'. Must be: testnet, mainnet, or regtest")
    exit(1)

class RadiantMiner:
    def __init__(self):
        self.running = True
        self.shutdown_requested = False
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self.shutdown_requested = True
        self.running = False

    def run(self):
        print("Radiant CPU Miner (SHA-512/256d) Started")
        print("Press Ctrl+C to stop mining gracefully")
        try:
            while self.running and not self.shutdown_requested:
                template = self._get_block_template()
                if not template:
                    if not self.shutdown_requested:
                        print("Failed to get block template, retrying in 5s...")
                        for _ in range(50):  # Check shutdown every 0.1s
                            if self.shutdown_requested:
                                break
                            time.sleep(0.1)
                    continue
                self._mine_block(template)
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received")
        finally:
            print("Mining stopped.")

    def _get_block_template(self):
        """Get block template from node via radiant-cli (credentials passed via stdin)"""
        try:
            # Create config string to pass via stdin (more secure than command line)
            config_str = f"-rpcuser={RPC_USER}\n-rpcpassword={RPC_PASS}\n"
            
            # Note: Radiant does not use segwit, so no rules parameter needed
            result = subprocess.run([
                f"{PROJECT_DIR}/build/src/radiant-cli",
                f'-{NETWORK}',
                f'-rpcport={RPC_PORT}',
                '-stdin',
                'getblocktemplate'
            ], input=config_str, capture_output=True, text=True, cwd=PROJECT_DIR, timeout=30)
            
            if result.returncode != 0:
                if not self.shutdown_requested:
                    print(f"Error getting block template: {result.stderr}")
                return None
            
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            print("Timeout getting block template")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing block template JSON: {e}")
            if result.stdout:
                print(f"  stdout: {result.stdout[:200]}")
            return None
        except Exception as e:
            if not self.shutdown_requested:
                print(f"Unexpected error getting block template: {e}")
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
        best_hash = b'\xff' * HASH_SIZE
        for nonce in range(2**32):
            # Check for shutdown request periodically
            if self.shutdown_requested:
                print("\nMining interrupted by shutdown request")
                return
            
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

        if not self.shutdown_requested:
            print("Failed to find a nonce in the given range.")

    def _get_new_address(self):
        """Get new mining address from wallet (credentials via stdin)"""
        try:
            config_str = f"-rpcuser={RPC_USER}\n-rpcpassword={RPC_PASS}\n"
            
            result = subprocess.run([
                f"{PROJECT_DIR}/build/src/radiant-cli",
                f'-{NETWORK}',
                '-rpcwallet=miner',
                f'-rpcport={RPC_PORT}',
                '-stdin',
                'getnewaddress'
            ], input=config_str, capture_output=True, text=True, cwd=PROJECT_DIR, timeout=10)
            
            if result.returncode != 0:
                print(f"Error getting new address: {result.stderr}")
                return None
            
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            print("Timeout getting new address")
            return None
        except Exception as e:
            print(f"Error getting new address: {e}")
            return None

    def _base58_decode(self, s):
        """Decode Base58 string - using shared utility"""
        return base58_decode(s)

    def _create_coinbase_tx(self, template):
        """Create coinbase transaction using shared utility"""
        address = self._get_new_address()
        if not address:
            return None, None
        
        try:
            tx_data = create_coinbase_transaction(
                height=template['height'],
                coinbase_value=template['coinbasevalue'],
                address=address
            )
            return tx_data, address
        except Exception as e:
            print(f"Error creating coinbase transaction: {e}")
            return None, None

    def _calculate_merkle_root(self, txids):
        """Calculate merkle root using shared utility"""
        return calculate_merkle_root(txids)

    def _serialize_varint(self, n):
        """Serialize varint using shared utility"""
        return serialize_varint(n)

    def _submit_block(self, header, transactions):
        """Submit block to node (credentials via stdin)"""
        block_hex = header.hex()
        block_hex += self._serialize_varint(len(transactions)).hex()
        for tx_data in transactions:
            block_hex += tx_data.hex()
        
        try:
            config_str = f"-rpcuser={RPC_USER}\n-rpcpassword={RPC_PASS}\n"
            
            result = subprocess.run([
                f"{PROJECT_DIR}/build/src/radiant-cli",
                f'-{NETWORK}',
                f'-rpcport={RPC_PORT}',
                '-stdin',
                'submitblock', block_hex
            ], input=config_str, capture_output=True, text=True, cwd=PROJECT_DIR, timeout=30)
            
            if result.returncode == 0:
                print(f"Block submitted successfully: {result.stdout}")
            else:
                print(f"Failed to submit block: {result.stderr}")
        except subprocess.TimeoutExpired:
            print("Timeout submitting block")
        except Exception as e:
            print(f"Unexpected error submitting block: {e}")

if __name__ == "__main__":
    miner = RadiantMiner()
    miner.run()
