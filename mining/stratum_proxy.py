#!/usr/bin/env python3
"""
Radiant Stratum Proxy
Bridges ASIC/GPU miners to Radiant node via getblocktemplate
Supports: Iceriver RXD ASICs, lolminer, srbminer, teamredminer, and other SHA-512/256d miners
"""

import asyncio
import json
import struct
import hashlib
import time
import logging
import subprocess
import socket
from typing import Dict, Optional, Tuple, Set
import os

# Configuration
RPC_USER = os.getenv("RPC_USER", "2d6b47f6ffd190cab44bfcd1ced86c4a")
RPC_PASS = os.getenv("RPC_PASS", "69xs4Vp5P12jVKbx/FJ3G4CFCDIqCaCvOgo/qIHh8gY=")
RPC_PORT = os.getenv("RPC_PORT", "17332")
PROJECT_DIR = os.getenv("PROJECT_DIR", "/Users/main/Downloads/Radiant-Core-main")
CLI_PATH = os.getenv("CLI_PATH", os.path.join(PROJECT_DIR, "build/src/radiant-cli"))
NETWORK = os.getenv("NETWORK", "testnet")

STRATUM_PORT = int(os.getenv("STRATUM_PORT", "3333"))
DIFFICULTY = float(os.getenv("DIFFICULTY", "8.0"))
DEBUG = os.getenv("DEBUG", "").lower() in ("1", "true", "yes")

log_level = logging.DEBUG if DEBUG else logging.INFO
logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RadiantStratumProxy:
    def __init__(self):
        self.clients = {}
        self.current_job = None
        self.valid_jobs = {}  # Track all valid jobs
        self.job_counter = 0
        self.submissions = {}  # Track submissions per job to prevent duplicates
        self.rpc_url = f"http://{RPC_USER}:{RPC_PASS}@127.0.0.1:{RPC_PORT}"
        
    def sha512_256(self, data: bytes) -> bytes:
        """SHA-512/256 hash using proper initialization vectors"""
        return hashlib.new('sha512_256', data).digest()
    
    def sha512_256d(self, data: bytes) -> bytes:
        """SHA-512/256d hash (double SHA-512/256) - Radiant's algorithm"""
        return self.sha512_256(self.sha512_256(data))
    
    def swap_endian_words(self, hex_str: str) -> str:
        """Swap endianness of each 4-byte word in hex string for ASIC prevhash format.
        
        ASICs expect prevhash with each 4-byte chunk byte-swapped.
        Example: 'aabbccdd11223344' -> 'ddccbbaa44332211'
        """
        result = ''
        for i in range(0, len(hex_str), 8):
            word = hex_str[i:i+8]
            # Reverse bytes within each 4-byte word
            result += ''.join([word[j:j+2] for j in range(6, -1, -2)])
        return result
    
    def bits_to_target(self, bits: str) -> int:
        """Convert compact bits representation to target integer"""
        bits_bytes = bytes.fromhex(bits)
        exponent = bits_bytes[3]
        coefficient = int.from_bytes(bits_bytes[:3], 'little')
        target = coefficient * (256 ** (exponent - 3))
        return target
    
    async def get_block_template(self) -> Optional[dict]:
        """Get block template from Radiant node"""
        try:
            cmd = [
                CLI_PATH,
                f"-rpcuser={RPC_USER}", f"-rpcpassword={RPC_PASS}",
                f"-rpcport={RPC_PORT}", "getblocktemplate",
                '{"rules": ["segwit"]}'
            ]
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            template = json.loads(result.stdout)
            logger.info(f"Raw prevhash from node: {template.get('previousblockhash')}")
            return template
        except Exception as e:
            logger.error(f"Failed to get block template: {e}")
            return None
    
    def calculate_merkle_root(self, coinbase_hash: bytes, tx_hashes: list) -> bytes:
        """Calculate merkle root from coinbase and transaction hashes"""
        # Start with coinbase hash
        tree = [coinbase_hash]
        
        # Add transaction hashes (reversed to little-endian)
        for tx in tx_hashes:
            if 'txid' in tx:
                tree.append(bytes.fromhex(tx['txid'])[::-1])
            elif 'hash' in tx:
                tree.append(bytes.fromhex(tx['hash'])[::-1])
        
        # Build merkle tree
        while len(tree) > 1:
            if len(tree) % 2 == 1:
                tree.append(tree[-1])
            
            new_tree = []
            for i in range(0, len(tree), 2):
                combined = tree[i] + tree[i+1]
                # Use double SHA-256 for merkle tree (standard Bitcoin merkle)
                hash_result = hashlib.sha256(hashlib.sha256(combined).digest()).digest()
                new_tree.append(hash_result)
            
            tree = new_tree
        
        return tree[0]  # Already in correct format
    
    def base58_decode(self, s: str) -> bytes:
        """Decode Base58 string to bytes"""
        b58_digits = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
        n = 0
        for char in s:
            n = n * 58 + b58_digits.index(char)
        leading_zeros = len(s) - len(s.lstrip('1'))
        if n == 0:
            result = b''
        else:
            result = n.to_bytes((n.bit_length() + 7) // 8, 'big')
        return b'\x00' * leading_zeros + result
    
    def address_to_pubkeyhash(self, address: str) -> bytes:
        """Extract pubkeyhash from Base58Check address"""
        raw = self.base58_decode(address)
        # Remove version byte (1) and checksum (4)
        return raw[1:-4]
    
    def create_coinbase_tx(self, template: dict, extranonce1: str) -> Tuple[bytes, bytes, bytes, str]:
        """Create coinbase transaction for Radiant mining.
        
        Standard stratum format:
        - coinbase1: version + input + scriptsig_len + height + timestamp + push_8_opcode
        - miner adds: extranonce1 (4 bytes) + extranonce2 (4 bytes)
        - coinbase2: pool_message + sequence + outputs + locktime
        
        Key: coinbase1 does NOT include extranonce1!
        """
        # Try to get a mining address
        try:
            cmd = [
                CLI_PATH,
                "-rpcwallet=miner", f"-rpcuser={RPC_USER}",
                f"-rpcpassword={RPC_PASS}", f"-rpcport={RPC_PORT}",
                "getnewaddress", "", "legacy"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            address = result.stdout.strip()
        except Exception as e:
            logger.warning(f"Could not get address: {e}, using default")
            address = None
        
        # BIP34 height encoding (push opcode + height bytes)
        height = template['height']
        if height <= 0x7f:
            height_script = bytes([0x01, height])
        elif height <= 0x7fff:
            height_script = b'\x02' + struct.pack('<H', height)
        elif height <= 0x7fffff:
            height_script = b'\x03' + struct.pack('<I', height)[:3]
        else:
            height_script = b'\x04' + struct.pack('<I', height)
        
        # Timestamp (4 bytes, push opcode + value)
        timestamp_script = b'\x04' + bytes.fromhex('ab117c65')
        
        # Pool message for coinbase2
        pool_message = b"radiant1.0.0.0-prxy"
        pool_message_script = bytes([len(pool_message)]) + pool_message
        
        # Calculate total script sig length
        # height_script + timestamp_script + push_8 + extranonce1(4) + extranonce2(4) + pool_message_script
        script_sig_len = len(height_script) + len(timestamp_script) + 1 + 8 + len(pool_message_script)
        
        # Output script (P2PKH)
        if address:
            try:
                pubkeyhash = self.address_to_pubkeyhash(address)
                if len(pubkeyhash) == 20:
                    coinbase_output_script = b'\x76\xa9\x14' + pubkeyhash + b'\x88\xac'
                else:
                    coinbase_output_script = b'\x51'  # OP_TRUE
            except:
                coinbase_output_script = b'\x51'  # OP_TRUE
        else:
            coinbase_output_script = b'\x51'  # OP_TRUE for testing
        
        # === COINBASE1: Everything up to (but NOT including) extranonce1 ===
        coinbase1 = struct.pack('<I', 1)  # Version
        coinbase1 += b'\x01'  # 1 input
        coinbase1 += b'\x00' * 32  # prevout hash (null for coinbase)
        coinbase1 += struct.pack('<I', 0xffffffff)  # prevout index
        coinbase1 += bytes([script_sig_len])  # Script sig length
        coinbase1 += height_script  # Height
        coinbase1 += timestamp_script  # Timestamp
        coinbase1 += b'\x08'  # Push 8 bytes opcode (for extranonce1 + extranonce2)
        # NOTE: extranonce1 is NOT included here - miner adds it!
        
        # === COINBASE2: After extranonces -> end ===
        coinbase2 = pool_message_script  # Pool message (part of script sig)
        coinbase2 += struct.pack('<I', 0)  # sequence = 0
        coinbase2 += b'\x01'  # 1 output
        coinbase2 += struct.pack('<Q', template['coinbasevalue'])  # value
        coinbase2 += bytes([len(coinbase_output_script)]) + coinbase_output_script
        coinbase2 += struct.pack('<I', 0)  # locktime
        
        logger.info(f"Coinbase1 len={len(coinbase1)} (excludes extranonce1), Coinbase2 len={len(coinbase2)}")
        logger.info(f"Height={height}, extranonce1={extranonce1}")
        
        return coinbase1, coinbase2, height_script, address or ""
    
    def create_block_header(self, template: dict, merkle_root: bytes, ntime: int, nonce: bytes) -> bytes:
        """Create block header for mining"""
        # Radiant block header format (80 bytes)
        header = struct.pack('<I', template['version'])
        header += bytes.fromhex(template['previousblockhash'])[::-1]
        header += merkle_root
        header += struct.pack('<I', ntime)
        header += bytes.fromhex(template['bits'])[::-1]
        header += nonce
        
        return header
    
    def create_stratum_job(self, template: dict, extranonce1: str) -> dict:
        """Create stratum job from block template for Iceriver RXD miners"""
        self.job_counter += 1
        job_id = format(self.job_counter, '04x')  # 4-char hex job ID
        
        # Create coinbase transaction parts
        coinbase1, coinbase2, coinbase_script, address = self.create_coinbase_tx(template, extranonce1)
        
        # Calculate merkle branch (steps to reach root)
        merkle_branch = []
        if 'transactions' in template and len(template['transactions']) > 0:
            # Build merkle steps from transactions
            tx_hashes = []
            for tx in template['transactions']:
                if 'txid' in tx:
                    tx_hashes.append(bytes.fromhex(tx['txid'])[::-1])
                elif 'hash' in tx:
                    tx_hashes.append(bytes.fromhex(tx['hash'])[::-1])
            
            # Calculate merkle branch steps
            if tx_hashes:
                    merkle_branch = self.get_merkle_steps(tx_hashes)
        
        # Swap bytes within each 4-byte word of prevhash (required for stratum/ASIC compatibility)
        prevhash_bytes = bytes.fromhex(template['previousblockhash'])
        prevhash_swapped = b''.join(
            prevhash_bytes[i:i+4][::-1] for i in range(0, 32, 4)
        )
        prevhash_stratum = prevhash_swapped.hex()
        logger.info(f"Prevhash: template={template['previousblockhash'][:16]}... -> stratum={prevhash_stratum[:16]}...")
        
        job_data = {
            'job_id': job_id,
            'prevhash': prevhash_stratum,
            'coinbase1': coinbase1.hex(),
            'coinbase2': coinbase2.hex(),
            'merkle_branch': merkle_branch,
            'version': struct.pack('>I', template['version']).hex(),  # Big-endian for stratum
            'nbits': template['bits'],
            'ntime': struct.pack('>I', template['curtime']).hex(),  # Big-endian for stratum
            'clean_jobs': True,
            'template': template,
            'target': self.bits_to_target(template['bits']),
            'extranonce1': extranonce1  # Store for validation
        }
        
        # Store job for validation
        self.valid_jobs[job_id] = job_data
        self.submissions[job_id] = set()
        
        return job_data
    
    def get_merkle_steps(self, tx_hashes: list) -> list:
        """Calculate merkle branch steps (coinbase path)"""
        branches = []
        if not tx_hashes:
            return branches

        layer = tx_hashes[:]
        index = 0  # Coinbase tx index

        while len(layer) > 1:
            if len(layer) % 2 == 1:
                layer.append(layer[-1])

            sibling_index = index ^ 1
            branches.append(layer[sibling_index].hex())

            next_layer = []
            for i in range(0, len(layer), 2):
                combined = layer[i] + layer[i + 1]
                hashed = hashlib.sha256(hashlib.sha256(combined).digest()).digest()
                next_layer.append(hashed)

            layer = next_layer
            index //= 2

        return branches
    
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle stratum client connection"""
        client_id = f"{writer.get_extra_info('peername')}"
        logger.info(f"New miner connected: {client_id}")
        
        # Generate unique extranonce1 for this client (4 bytes = 8 hex chars)
        extranonce1 = format(hash(client_id) & 0xffffffff, '08x')
        
        # Store client connection
        self.clients[client_id] = {
            'writer': writer,
            'extranonce1': extranonce1,
            'authorized': False,
            'worker': None
        }
        
        try:
            # Handle client messages
            while True:
                line = await reader.readline()
                if not line:
                    break
                
                try:
                    message = json.loads(line.strip().decode())
                    logger.info(f"<<< RECV from {client_id}: {message}")
                    await self.handle_stratum_message(writer, message, client_id, extranonce1)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from {client_id}: {line}")
                except Exception as e:
                    logger.error(f"Error handling message from {client_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Client error {client_id}: {e}")
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
            writer.close()
            await writer.wait_closed()
            logger.info(f"Client disconnected: {client_id}")
    
    async def handle_stratum_message(self, writer: asyncio.StreamWriter, message: dict, client_id: str, extranonce1: str):
        """Handle stratum protocol messages"""
        method = message.get('method')
        params = message.get('params', [])
        msg_id = message.get('id')
        
        if method == 'mining.subscribe':
            # Handle subscription - send extranonce info
            subscription_id = format(int(time.time()) & 0xffffffff, '08x')
            
            await self.send_stratum_message(writer, {
                "id": msg_id,
                "result": [
                    [
                        ["mining.set_difficulty", subscription_id],
                        ["mining.notify", subscription_id]
                    ],
                    extranonce1,  # extranonce1 (4 bytes)
                    4  # extranonce2 size (4 bytes)
                ],
                "error": None
            })
            logger.info(f"Miner subscribed with extranonce1: {extranonce1}")
            
        elif method == 'mining.authorize':
            # Handle worker authorization
            worker_name = params[0] if params else "unknown"
            worker_pass = params[1] if len(params) > 1 else ""
            
            self.clients[client_id]['worker'] = worker_name
            self.clients[client_id]['authorized'] = True
            logger.info(f"Authorized worker: {worker_name}")
            
            await self.send_stratum_message(writer, {
                "id": msg_id,
                "result": True,
                "error": None
            })
            
            # Send initial difficulty
            await self.send_stratum_message(writer, {
                "id": None,
                "method": "mining.set_difficulty",
                "params": [DIFFICULTY]
            })
            
            # Send initial job - always create fresh job with current template
            template = await self.get_block_template()
            if template:
                job = self.create_stratum_job(template, extranonce1)
                self.current_job = job
                self.valid_jobs[job['job_id']] = job
                await self.send_job_to_client(writer, job, True)
                logger.info(f"Created and sent initial job {job['job_id']} to {worker_name}")
            
        elif method == 'mining.configure':
            # Handle version rolling configuration
            logger.info(f"ASIC requesting configure: {params}")
            # Support version rolling with mask 1fffe000
            await self.send_stratum_message(writer, {
                "id": msg_id,
                "result": {
                    "version-rolling": True,
                    "version-rolling.mask": "1fffe000"
                },
                "error": None
            })
            
        elif method == 'mining.submit':
            # Handle share submission
            await self.handle_share_submission(writer, message, client_id)
        
        elif method == 'mining.extranonce.subscribe':
            # Some miners request extranonce subscription
            await self.send_stratum_message(writer, {
                "id": msg_id,
                "result": True,
                "error": None
            })
        
        elif method == 'mining.configure':
            # Handle version rolling and other extensions
            extensions = params[0] if params else []
            extension_params = params[1] if len(params) > 1 else {}
            
            result = {}
            # Support version-rolling if requested
            if 'version-rolling' in extensions:
                # Allow version rolling with mask 0x1fffe000 (standard BIP320)
                result['version-rolling'] = True
                result['version-rolling.mask'] = '1fffe000'
                logger.info(f"Enabled version-rolling with mask 1fffe000")
            
            await self.send_stratum_message(writer, {
                "id": msg_id,
                "result": result,
                "error": None
            })
            logger.info(f"Handled mining.configure: extensions={extensions}, result={result}")
            
        else:
            logger.warning(f"Unknown method: {method}")
    
    async def send_job_to_client(self, writer: asyncio.StreamWriter, job: dict, clean_jobs: bool):
        """Send mining job to client"""
        logger.info(f"=== Sending Job {job['job_id']} ===")
        logger.info(f"  prevhash:    {job['prevhash']} (len={len(job['prevhash'])})")
        logger.info(f"  coinbase1:   {job['coinbase1']} (len={len(job['coinbase1'])})")
        logger.info(f"  coinbase2:   {job['coinbase2']} (len={len(job['coinbase2'])})")
        logger.info(f"  merkle_branch: {job['merkle_branch']}")
        logger.info(f"  version:     {job['version']} (len={len(job['version'])})")
        logger.info(f"  nbits:       {job['nbits']} (len={len(job['nbits'])})")
        logger.info(f"  ntime:       {job['ntime']} (len={len(job['ntime'])})")
        logger.info(f"  extranonce1: {job['extranonce1']} (len={len(job['extranonce1'])})")
        
        await self.send_stratum_message(writer, {
            "id": None,
            "method": "mining.notify",
            "params": [
                job['job_id'],
                job['prevhash'],
                job['coinbase1'],
                job['coinbase2'],
                job['merkle_branch'],
                job['version'],
                job['nbits'],
                job['ntime'],
                clean_jobs
            ]
        })
    
    async def handle_share_submission(self, writer: asyncio.StreamWriter, message: dict, client_id: str):
        """Handle submitted share with full validation"""
        params = message.get('params', [])
        msg_id = message.get('id')
        
        logger.info(f"=== Share Submission from {client_id} ===")
        logger.info(f"  Raw params: {params}")
        
        if len(params) < 5:
            logger.warning(f"Invalid params length: {len(params)}")
            await self.send_stratum_message(writer, {
                "id": msg_id,
                "result": False,
                "error": [20, "Invalid parameters", None]
            })
            return
        
        # Extract submission data
        worker_name = params[0]
        job_id = params[1]
        extranonce2 = params[2]
        ntime = params[3]
        nonce = params[4]
        
        logger.info(f"  worker: {worker_name}")
        logger.info(f"  job_id: {job_id}")
        logger.info(f"  extranonce2: {extranonce2}")
        logger.info(f"  ntime: {ntime}")
        logger.info(f"  nonce: {nonce}")
        
        # Validate submission
        error = self.validate_share(job_id, extranonce2, ntime, nonce, worker_name)
        
        if error:
            logger.warning(f"Share rejected from {worker_name}: {error[1]}")
            await self.send_stratum_message(writer, {
                "id": msg_id,
                "result": False,
                "error": error
            })
            return
        
        logger.info(f"Valid share from {worker_name}: job={job_id}, nonce={nonce}")
        
        # Accept share
        await self.send_stratum_message(writer, {
            "id": msg_id,
            "result": True,
            "error": None
        })
        
        # Check if this is a valid block and submit to node
        await self.check_block_solution(job_id, extranonce2, ntime, nonce)
    
    def validate_share(self, job_id: str, extranonce2: str, ntime: str, nonce: str, worker: str) -> Optional[list]:
        """Validate submitted share"""
        # Check job exists
        if job_id not in self.valid_jobs:
            return [21, "job not found", None]
        
        job = self.valid_jobs[job_id]
        template = job['template']
        
        # Validate extranonce2 length (should be 4 bytes = 8 hex chars)
        if len(extranonce2) != 8:
            return [20, "incorrect size of extranonce2", None]
        
        # Validate ntime length
        if len(ntime) != 8:
            return [20, "incorrect size of ntime", None]
        
        # Validate nonce length
        if len(nonce) != 8:
            return [20, "incorrect size of nonce", None]
        
        # Check for duplicate submission
        submission_key = f"{extranonce2}:{ntime}:{nonce}:{worker}"
        if submission_key in self.submissions[job_id]:
            return [22, "duplicate share", None]
        
        # Validate ntime range
        ntime_int = int(ntime, 16)
        current_time = int(time.time())
        if ntime_int < template['curtime'] or ntime_int > current_time + 7200:
            return [20, "ntime out of range", None]
        
        # Build complete coinbase: coinbase1 + extranonce1 + extranonce2 + coinbase2
        # Note: coinbase1 does NOT include extranonce1 - miner adds both extranonces
        coinbase1 = bytes.fromhex(job['coinbase1'])
        coinbase2 = bytes.fromhex(job['coinbase2'])
        extranonce1_bytes = bytes.fromhex(job['extranonce1'])
        extranonce2_bytes = bytes.fromhex(extranonce2)
        coinbase = coinbase1 + extranonce1_bytes + extranonce2_bytes + coinbase2
        
        logger.debug(f"Coinbase length: {len(coinbase)} bytes")
        logger.debug(f"Coinbase hex: {coinbase.hex()[:100]}...")
        
        # Calculate coinbase hash (double SHA-256 for txid)
        coinbase_hash = hashlib.sha256(hashlib.sha256(coinbase).digest()).digest()
        logger.debug(f"Coinbase hash: {coinbase_hash[::-1].hex()}")  # Display as txid (reversed)
        
        # Calculate merkle root
        merkle_root = coinbase_hash
        for branch in job['merkle_branch']:
            merkle_root = hashlib.sha256(hashlib.sha256(
                merkle_root + bytes.fromhex(branch)
            ).digest()).digest()
        
        logger.debug(f"Merkle root: {merkle_root.hex()}")
        
        # Nonce from ASIC - try both byte orders to find valid one
        nonce_bytes = bytes.fromhex(nonce)
        nonce_le = nonce_bytes[::-1]  # Reverse for little-endian
        nonce_be = nonce_bytes  # Keep as big-endian
        
        # Build block header with little-endian nonce first (standard)
        header = self.create_block_header(
            template,
            merkle_root,
            ntime_int,
            nonce_le
        )
        
        logger.debug(f"Header length: {len(header)} bytes")
        logger.debug(f"Header hex: {header.hex()}")
        
        # Hash block header with SHA-512/256d
        block_hash = self.sha512_256d(header)
        hash_int = int.from_bytes(block_hash, 'little')
        
        logger.debug(f"Block hash (LE nonce): {block_hash[::-1].hex()}")
        
        # Also try big-endian nonce in case ASIC sends it differently
        header_be = self.create_block_header(template, merkle_root, ntime_int, nonce_be)
        block_hash_be = self.sha512_256d(header_be)
        hash_int_be = int.from_bytes(block_hash_be, 'little')
        
        logger.debug(f"Block hash (BE nonce): {block_hash_be[::-1].hex()}")
        
        # Calculate share difficulty for both
        max_target = 0x00000000FFFF0000000000000000000000000000000000000000000000000000
        share_diff_le = max_target / hash_int if hash_int > 0 else 0
        share_diff_be = max_target / hash_int_be if hash_int_be > 0 else 0
        
        logger.info(f"Share diff (LE nonce): {share_diff_le:.6f}, (BE nonce): {share_diff_be:.6f}")
        
        # Use whichever nonce interpretation gives better difficulty
        if share_diff_be > share_diff_le:
            share_diff = share_diff_be
            block_hash = block_hash_be
            hash_int = hash_int_be
            logger.info("Using big-endian nonce interpretation")
        else:
            share_diff = share_diff_le
            logger.info("Using little-endian nonce interpretation")
        
        logger.debug(f"  block hash: {block_hash[::-1].hex()}")  # Display in big-endian
        logger.debug(f"  share difficulty: {share_diff:.4f}, required: {DIFFICULTY}")
        
        # Check if share meets minimum difficulty
        if share_diff < DIFFICULTY * 0.99:  # 0.99 for rounding tolerance
            logger.warning(f"Share difficulty {share_diff:.6f} below required {DIFFICULTY}")
            return [23, f"low difficulty share of {share_diff:.6f}", None]
        
        # Mark submission as seen
        self.submissions[job_id].add(submission_key)
        
        # Check if this is a valid block (meets network target)
        if hash_int <= job['target']:
            logger.info(f"*** BLOCK FOUND *** Hash: {block_hash.hex()}")
        
        return None
    
    async def check_block_solution(self, job_id: str, extranonce2: str, ntime: str, nonce: str):
        """Check if share is a valid block and submit to node"""
        if job_id not in self.valid_jobs:
            return
        
        job = self.valid_jobs[job_id]
        template = job['template']
        
        # Rebuild full block: coinbase1 + extranonce1 + extranonce2 + coinbase2
        coinbase1 = bytes.fromhex(job['coinbase1'])
        coinbase2 = bytes.fromhex(job['coinbase2'])
        extranonce1_bytes = bytes.fromhex(job['extranonce1'])
        extranonce2_bytes = bytes.fromhex(extranonce2)
        coinbase = coinbase1 + extranonce1_bytes + extranonce2_bytes + coinbase2
        
        # Calculate merkle root
        coinbase_hash = hashlib.sha256(hashlib.sha256(coinbase).digest()).digest()
        merkle_root = coinbase_hash
        for branch in job['merkle_branch']:
            merkle_root = hashlib.sha256(hashlib.sha256(
                merkle_root + bytes.fromhex(branch)
            ).digest()).digest()
        
        # Build header - try both nonce interpretations
        ntime_int = int(ntime, 16)
        nonce_bytes = bytes.fromhex(nonce)
        
        # Try little-endian nonce
        header_le = self.create_block_header(template, merkle_root, ntime_int, nonce_bytes[::-1])
        block_hash_le = self.sha512_256d(header_le)
        hash_int_le = int.from_bytes(block_hash_le, 'little')
        
        # Try big-endian nonce
        header_be = self.create_block_header(template, merkle_root, ntime_int, nonce_bytes)
        block_hash_be = self.sha512_256d(header_be)
        hash_int_be = int.from_bytes(block_hash_be, 'little')
        
        # Use whichever meets target (or has lower hash)
        if hash_int_be < hash_int_le:
            header = header_be
            block_hash = block_hash_be
            hash_int = hash_int_be
        else:
            header = header_le
            block_hash = block_hash_le
            hash_int = hash_int_le
        
        if hash_int <= job['target']:
            # Build full block for submission
            block_hex = self.build_block_submission(header, coinbase, template)
            await self.submit_block(block_hex)
    
    def build_block_submission(self, header: bytes, coinbase: bytes, template: dict) -> str:
        """Build complete block for submission"""
        # Block = header + transaction count + coinbase + transactions
        tx_count = 1 + len(template.get('transactions', []))
        
        block = header
        block += self.var_int(tx_count)
        block += coinbase
        
        # Add all transactions
        for tx in template.get('transactions', []):
            block += bytes.fromhex(tx['data'])
        
        return block.hex()
    
    def var_int(self, n: int) -> bytes:
        """Encode variable length integer"""
        if n < 0xfd:
            return bytes([n])
        elif n <= 0xffff:
            return b'\xfd' + struct.pack('<H', n)
        elif n <= 0xffffffff:
            return b'\xfe' + struct.pack('<I', n)
        else:
            return b'\xff' + struct.pack('<Q', n)
    
    async def submit_block(self, block_hex: str):
        """Submit block to Radiant node"""
        try:
            cmd = [
                CLI_PATH,
                f"-rpcuser={RPC_USER}", f"-rpcpassword={RPC_PASS}",
                f"-rpcport={RPC_PORT}", "submitblock", block_hex
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and not result.stdout.strip():
                logger.info("*** BLOCK ACCEPTED BY NODE ***")
            else:
                logger.error(f"Block submission failed: {result.stdout.strip()}")
        except Exception as e:
            logger.error(f"Failed to submit block: {e}")
    
    async def send_stratum_message(self, writer: asyncio.StreamWriter, message: dict):
        """Send stratum message to client"""
        try:
            line = json.dumps(message) + "\n"
            if message.get('method') == 'mining.notify':
                logger.info(f">>> SENDING TO ASIC: {line.strip()}")
            writer.write(line.encode())
            await writer.drain()
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    
    async def start_server(self):
        """Start stratum server"""
        server = await asyncio.start_server(
            self.handle_client,
            '0.0.0.0',
            STRATUM_PORT
        )
        
        logger.info(f"Stratum proxy listening on port {STRATUM_PORT}")
        logger.info(f"Connect miners (ASIC/GPU) to: stratum+tcp://<YOUR_IP>:{STRATUM_PORT}")
        
        async with server:
            await server.serve_forever()
    
    async def poll_block_template(self):
        """Poll for new block templates and broadcast to miners"""
        logger.info("Starting block template polling task...")
        poll_count = 0
        while True:
            try:
                poll_count += 1
                template = await self.get_block_template()
                if template:
                    logger.debug(f"Poll #{poll_count}: height={template['height']}, prevhash={template['previousblockhash'][:16]}...")
                    
                    # Check if new block (only on previousblockhash change, NOT curtime)
                    is_new = False
                    if not self.current_job:
                        is_new = True
                        logger.info(f"No current job, creating initial job for height {template['height']}")
                    elif template.get('previousblockhash') != self.current_job.get('template', {}).get('previousblockhash'):
                        is_new = True
                        logger.info(f"New block detected at height {template['height']}")
                    
                    if is_new:
                        # Broadcast to all connected miners
                        await self.broadcast_new_job(template)
                else:
                    logger.warning(f"Poll #{poll_count}: Failed to get template from node")
                
                # Poll every 5 seconds for new blocks
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error polling block template: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(5)
    
    async def broadcast_new_job(self, template: dict):
        """Create and broadcast new job to all connected miners"""
        # Create jobs for each connected client (each gets unique extranonce1)
        disconnected = []
        
        for client_id, client_info in self.clients.items():
            if not client_info.get('authorized'):
                continue
            
            try:
                extranonce1 = client_info['extranonce1']
                job = self.create_stratum_job(template, extranonce1)
                
                # Update current job for this extranonce1
                if not self.current_job:
                    self.current_job = job
                else:
                    # Keep reference to latest job
                    self.current_job = job
                
                writer = client_info['writer']
                await self.send_job_to_client(writer, job, True)
                
                logger.info(f"Sent job {job['job_id']} to {client_info['worker']}")
            except Exception as e:
                logger.error(f"Failed to send job to {client_id}: {e}")
                disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            if client_id in self.clients:
                del self.clients[client_id]

async def main():
    proxy = RadiantStratumProxy()
    
    # Test node connection
    logger.info("Testing node connection...")
    template = await proxy.get_block_template()
    if not template:
        logger.error("Cannot connect to Radiant node")
        return
    
    logger.info(f"Connected to node (height: {template.get('height', 'unknown')})")
    
    # Start polling task before server
    polling_task = asyncio.create_task(proxy.poll_block_template())
    logger.info("Polling task started successfully")
    
    # Start stratum server
    await proxy.start_server()

if __name__ == "__main__":
    asyncio.run(main())