#!/usr/bin/env python3
"""
Radiant Stratum Proxy
"""

import asyncio
import json
import struct
import hashlib
import time
import logging
import signal
import base64
import secrets
from typing import Dict, Optional, Tuple, Set
import os

# Try to import aiohttp for async HTTP, fallback to urllib
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    import urllib.request
    import urllib.error
    AIOHTTP_AVAILABLE = False
    logging.warning("aiohttp not available, using synchronous urllib (slower performance)")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration - Required credentials (no defaults for security)
RPC_USER = os.getenv("RPC_USER")
RPC_PASS = os.getenv("RPC_PASS")
RPC_PORT = os.getenv("RPC_PORT", "27332")
RPC_HOST = os.getenv("RPC_HOST", "127.0.0.1")
RPC_WALLET = os.getenv("RPC_WALLET", "miner")
PROJECT_DIR = os.getenv("PROJECT_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NETWORK = os.getenv("NETWORK", "testnet")

# Stratum configuration
STRATUM_PORT = int(os.getenv("STRATUM_PORT", "3333"))
STRATUM_DIFFICULTY = float(os.getenv("STRATUM_DIFFICULTY", "0.001"))
MAX_JOBS = int(os.getenv("MAX_JOBS", "20"))
JOB_POLL_INTERVAL = int(os.getenv("JOB_POLL_INTERVAL", "5"))
MAX_NTIME_DRIFT = int(os.getenv("MAX_NTIME_DRIFT", "7200"))  # 2 hours

# Authentication - comma-separated list of allowed workers
# SECURITY: Empty list now requires explicit configuration
ALLOWED_WORKERS_STR = os.getenv("ALLOWED_WORKERS", "")
ALLOWED_WORKERS = ALLOWED_WORKERS_STR.split(",") if ALLOWED_WORKERS_STR else []
if not ALLOWED_WORKERS:
    logger.warning("WARNING: No ALLOWED_WORKERS configured - any worker can connect!")
    logger.warning("Set ALLOWED_WORKERS environment variable for production use")

# Rate limiting
MAX_SHARES_PER_MINUTE = int(os.getenv("MAX_SHARES_PER_MINUTE", "600"))
MAX_AUTH_FAILURES = int(os.getenv("MAX_AUTH_FAILURES", "5"))
AUTH_FAILURE_BAN_TIME = int(os.getenv("AUTH_FAILURE_BAN_TIME", "300"))  # 5 minutes


def validate_config():
    """Validate required configuration on startup"""
    errors = []
    
    if not RPC_USER:
        errors.append("RPC_USER environment variable is required")
    if not RPC_PASS:
        errors.append("RPC_PASS environment variable is required")
    
    # Validate port is numeric
    try:
        int(RPC_PORT)
    except ValueError:
        errors.append(f"RPC_PORT must be numeric, got: {RPC_PORT}")
    
    # Validate network
    if NETWORK not in ["testnet", "mainnet", "regtest"]:
        errors.append(f"Invalid NETWORK '{NETWORK}'. Must be: testnet, mainnet, or regtest")
    
    if errors:
        for err in errors:
            logger.error(f"Configuration error: {err}")
        logger.error("Set required environment variables before running:")
        logger.error("  export RPC_USER=your_rpc_username")
        logger.error("  export RPC_PASS=your_rpc_password")
        raise ValueError("Missing required configuration. See errors above.")


class RadiantStratumProxy:
    def __init__(self):
        self.clients: Dict[str, dict] = {}
        self.jobs: Dict[str, dict] = {}
        self.current_job_id: Optional[str] = None
        # Use random seed for extranonce1 to avoid collisions on restart
        self.extranonce1_base = secrets.token_hex(8)  # Generate a unique base per proxy instance
        self.extranonce1_counter = 0
        self.rpc_host = RPC_HOST
        self.rpc_port = RPC_PORT
        self.rpc_user = RPC_USER
        self.rpc_pass = RPC_PASS
        self.rpc_wallet = RPC_WALLET
        self.block_template: Optional[dict] = None
        self.aiohttp_session: Optional[aiohttp.ClientSession] = None if AIOHTTP_AVAILABLE else None
        self._shutdown_event = asyncio.Event()
        # Share deduplication: {job_id: set of (extranonce2, nonce) tuples}
        self.submitted_shares: Dict[str, Set[Tuple[str, str]]] = {}
        # Rate limiting: {client_id: list of timestamps}
        self.share_timestamps: Dict[str, list] = {}
        # Auth failure tracking: {client_id: (failure_count, ban_until_timestamp)}
        self.auth_failures: Dict[str, Tuple[int, float]] = {}
        # Job cache lock for thread safety
        self.job_lock = asyncio.Lock()

    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if AIOHTTP_AVAILABLE and self.aiohttp_session is None:
            self.aiohttp_session = aiohttp.ClientSession()

    async def _close_session(self):
        """Close aiohttp session"""
        if self.aiohttp_session:
            await self.aiohttp_session.close()
            self.aiohttp_session = None

    async def _rpc_call_async(self, method: str, params: list, wallet: Optional[str] = None, timeout: int = 5):
        """Async RPC call using aiohttp"""
        await self._ensure_session()
        
        base_url = f"http://{self.rpc_host}:{self.rpc_port}"
        url = f"{base_url}/wallet/{wallet}" if wallet else f"{base_url}/"

        payload = {
            "jsonrpc": "1.0",
            "id": "radiant-stratum-proxy",
            "method": method,
            "params": params,
        }

        auth = base64.b64encode(f"{self.rpc_user}:{self.rpc_pass}".encode()).decode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth}",
        }

        try:
            async with self.aiohttp_session.post(
                url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(f"RPC HTTP {resp.status}: {body[:200]}")
                data = await resp.json()
        except aiohttp.ClientError as e:
            raise RuntimeError(f"RPC connection error: {type(e).__name__}")

        if data.get("error"):
            err = data["error"]
            raise RuntimeError(f"RPC error {err.get('code')}: {err.get('message')}")
        return data.get("result")

    def _rpc_call_sync(self, method: str, params: list, wallet: Optional[str] = None, timeout: int = 5):
        """Synchronous RPC call fallback using urllib"""
        base_url = f"http://{self.rpc_host}:{self.rpc_port}"
        url = f"{base_url}/wallet/{wallet}" if wallet else f"{base_url}/"

        payload = {
            "jsonrpc": "1.0",
            "id": "radiant-stratum-proxy",
            "method": method,
            "params": params,
        }

        auth = base64.b64encode(f"{self.rpc_user}:{self.rpc_pass}".encode()).decode()
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Basic {auth}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="ignore")
            raise RuntimeError(f"RPC HTTP {e.code}: {body[:200]}")

        if data.get("error"):
            err = data["error"]
            raise RuntimeError(f"RPC error {err.get('code')}: {err.get('message')}")
        return data.get("result")

    async def _rpc_call(self, method: str, params: list, wallet: Optional[str] = None, timeout: int = 5):
        """RPC call - uses async if aiohttp available, otherwise runs sync in executor"""
        if AIOHTTP_AVAILABLE:
            return await self._rpc_call_async(method, params, wallet, timeout)
        else:
            logger.warning('Falling back to synchronous RPC call; consider installing aiohttp for better performance')
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._rpc_call_sync, method, params, wallet, timeout)
        
    async def get_block_template(self) -> Optional[dict]:
        """Get block template from Radiant node"""
        try:
            # Radiant doesn't use segwit - use empty object
            result = await self._rpc_call("getblocktemplate", [{}])
            if not isinstance(result, dict):
                raise RuntimeError("getblocktemplate returned non-object result")
            return result
        except Exception as e:
            logger.error(f"Failed to get block template: {e}")
            return None
    
    async def submit_block(self, block_hex: str) -> bool:
        """Submit valid block to node"""
        try:
            result = await self._rpc_call("submitblock", [block_hex])
            if result is None:
                logger.info("Block accepted by node!")
                return True
            logger.warning(f"Block submission result: {result}")
            return False
        except Exception as e:
            logger.error(f"Failed to submit block: {e}")
            return False

    # --- Hashing Helpers ---
    def _base58_decode(self, s: str) -> bytes:
        """Decode Base58 string to bytes with leading-zero preservation"""
        b58_digits = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
        
        n = 0
        for char in s:
            n = n * 58 + b58_digits.index(char)
        
        result = n.to_bytes((n.bit_length() + 7) // 8, 'big') if n > 0 else b''
        
        leading_zeros = len(s) - len(s.lstrip('1'))
        return b'\x00' * leading_zeros + result

    def _hash256(self, data: bytes) -> bytes:
        return hashlib.sha256(hashlib.sha256(data).digest()).digest()

    def _base58check_decode(self, s: str) -> bytes:
        raw = self._base58_decode(s)
        if len(raw) < 5:
            raise ValueError("Invalid Base58Check length")
        payload, checksum = raw[:-4], raw[-4:]
        if self._hash256(payload)[:4] != checksum:
            raise ValueError("Invalid Base58Check checksum")
        return payload

    def sha512_256(self, data: bytes) -> bytes:
        """SHA-512/256 hash"""
        return hashlib.new('sha512_256', data).digest()

    def sha512_256d(self, data: bytes) -> bytes:
        """Double SHA-512/256 (Radiant PoW)"""
        return self.sha512_256(self.sha512_256(data))

    def get_target_from_difficulty(self, difficulty: float) -> int:
        """Calculate target from stratum difficulty"""
        # Diff 1 is 0x00000000ffff0000... 
        diff1 = 0x00000000FFFF0000000000000000000000000000000000000000000000000000
        if difficulty == 0:
            return int(diff1)
        return int(diff1 / difficulty)

    async def create_coinbase_parts(self, template: dict, extranonce1_size: int = 4, extranonce2_size: int = 4) -> Tuple[bytes, bytes]:
        """Create coinbase transaction parts (coinbase1, coinbase2)
        
        Raises:
            RuntimeError: If unable to get a valid payout address
        """
        # Get new address for rewards - MUST succeed, no silent fallbacks
        address = None
        try:
            wallet = self.rpc_wallet
            addr = await self._rpc_call("getnewaddress", [], wallet=wallet, timeout=5)
            if addr:
                address = str(addr).strip()
        except Exception as e:
            logger.error(f"Failed to get new address from wallet: {e}")
            raise RuntimeError(f"Cannot create coinbase: failed to get mining address from wallet '{wallet}'. Ensure wallet exists and is loaded.")
        
        if not address:
            raise RuntimeError("No payout address available - cannot create coinbase")
        
        # Create output script from address - MUST succeed
        try:
            payload = self._base58check_decode(address)
            if len(payload) != 21:
                raise ValueError(f"Invalid address payload length: {len(payload)} bytes (expected 21)")
            pubkeyhash = payload[1:]
            if len(pubkeyhash) != 20:
                raise ValueError(f"Invalid pubkeyhash length: {len(pubkeyhash)} bytes (expected 20)")
            coinbase_output_script = b'\x76\xa9\x14' + pubkeyhash + b'\x88\xac'
        except Exception as e:
            logger.error(f"Failed to decode address {address}: {e}")
            raise RuntimeError(f"Cannot create coinbase output script: {e}")

        # BIP34 height encoding
        height = template['height']
        if height == 0:
            coinbase_script_sig = b'\x00'  # OP_0 for height 0
        elif height <= 16:
            coinbase_script_sig = bytes([0x50 + height])  # OP_1 through OP_16
        else:
            coinbase_script_sig = b'\x03' + struct.pack('<I', height)[:3]
            
        # Calculate total script length including extranonces
        # script = height_script + extranonce1 + extranonce2
        total_script_len = len(coinbase_script_sig) + extranonce1_size + extranonce2_size
        
        # Coinbase 1: Version -> Script Length -> Height Script
        coinbase1 = struct.pack('<i', 1)  # Version
        coinbase1 += struct.pack('<B', 1)  # 1 input
        coinbase1 += b'\x00' * 32  # prevout hash
        coinbase1 += struct.pack('<I', 0xffffffff)  # prevout index
        coinbase1 += struct.pack('<B', total_script_len) + coinbase_script_sig
        
        # Coinbase 2: Sequence -> Outputs -> Locktime
        coinbase2 = struct.pack('<I', 0xffffffff)  # sequence
        coinbase2 += struct.pack('<B', 1)  # 1 output
        coinbase2 += struct.pack('<q', template['coinbasevalue'])  # value
        coinbase2 += struct.pack('<B', len(coinbase_output_script)) + coinbase_output_script
        coinbase2 += struct.pack('<I', 0)  # locktime
        
        return coinbase1, coinbase2

    def create_block_header_from_parts(self, version, prevhash, merkle_root, time_val, bits) -> bytes:
        """Create block header from components"""
        # prevhash is usually hex string, need bytes little endian
        if isinstance(prevhash, str):
            prevhash_bytes = bytes.fromhex(prevhash)[::-1]
        else:
            prevhash_bytes = prevhash
            
        if isinstance(bits, str):
            bits_bytes = bytes.fromhex(bits)[::-1]
        else:
            bits_bytes = bits
            
        header = struct.pack('<i', version) \
               + prevhash_bytes \
               + merkle_root[::-1] \
               + struct.pack('<I', time_val) \
               + bits_bytes \
               + b'\x00\x00\x00\x00'  # Nonce placeholder (0)
        return header

    def get_merkle_branch(self, template_txs: list) -> list:
        """Calculate merkle branch for the coinbase (index 0)
        
        Properly tracks the coinbase position through each level to find correct siblings.
        This is critical for ASIC compatibility - incorrect merkle branches will cause all shares to be rejected.
        """
        if not template_txs:
            return []

        tx_hashes = []
        for tx in template_txs:
            if isinstance(tx, dict):
                h = tx.get('hash') or tx.get('txid')
                if not h:
                    raise ValueError("Transaction missing hash/txid field")
                tx_hashes.append(bytes.fromhex(h)[::-1])
            elif isinstance(tx, str):
                tx_hashes.append(bytes.fromhex(tx)[::-1])

        branch = []
        current_level = [b'\x00' * 32] + tx_hashes
        current_index = 0

        while len(current_level) > 1:
            if len(current_level) % 2 == 1:
                current_level.append(current_level[-1])

            sibling_index = current_index ^ 1
            branch.append(current_level[sibling_index][::-1].hex())

            next_level = []
            for i in range(0, len(current_level), 2):
                combined = current_level[i] + current_level[i + 1]
                next_level.append(self._hash256(combined))

            current_index //= 2
            current_level = next_level

        return branch

    async def create_stratum_job(self, template: dict) -> dict:
        """Create stratum job from block template"""
        coinbase1, coinbase2 = await self.create_coinbase_parts(template)
        
        # Calculate merkle branch
        merkle_branch = self.get_merkle_branch(template['transactions'])
        
        # Convert to mining job format
        job_id = hex(int(time.time() * 1000))[2:] # Unique hex ID
        
        # Save job details for validation
        self.jobs[job_id] = {
            'template': template,
            'coinbase1': coinbase1,
            'coinbase2': coinbase2,
            'merkle_branch': merkle_branch,
            'target': template['target']
        }
        
        # Initialize share tracking for this job
        self.submitted_shares[job_id] = set()
        
        # Prune old jobs to keep only MAX_JOBS most recent (with lock for thread safety)
        async with self.job_lock:
            if len(self.jobs) > MAX_JOBS:
                sorted_jobs = sorted(self.jobs.keys(), key=lambda k: self.jobs[k]['template']['curtime'])
                while len(sorted_jobs) > MAX_JOBS:
                    oldest_key = sorted_jobs.pop(0)
                    del self.jobs[oldest_key]
                    # Fix memory leak: clean up share tracking for old jobs
                    self.submitted_shares.pop(oldest_key, None)
            
        return {
            'job_id': job_id,
            'prevhash': template['previousblockhash'],
            'coinbase1': coinbase1.hex(),
            'coinbase2': coinbase2.hex(),
            'merkle_branch': merkle_branch,
            'version': hex(template['version'])[2:],
            'nbits': template['bits'],
            'ntime': hex(template['curtime'])[2:],
            'clean_jobs': True
        }
    
    # Helper to calculate full merkle root from stratum style branch
    def calculate_merkle_root_from_branch(self, coinbase_hash_bin: bytes, branch: list) -> bytes:
        current = coinbase_hash_bin
        for branch_hash_hex in branch:
            branch_hash = bytes.fromhex(branch_hash_hex)[::-1] # Little endian
            # Stratum merkle branch handling (double sha256 of concat)
            # Typically coinbase is left, branch is right
            combined = current + branch_hash
            current = hashlib.sha256(hashlib.sha256(combined).digest()).digest()
        return current

    def _check_rate_limit(self, client_id: str) -> bool:
        """Check if client is within rate limit. Returns True if allowed."""
        now = time.time()
        if client_id not in self.share_timestamps:
            self.share_timestamps[client_id] = []
        
        # Remove timestamps older than 1 minute
        self.share_timestamps[client_id] = [
            ts for ts in self.share_timestamps[client_id] if now - ts < 60
        ]
        
        if len(self.share_timestamps[client_id]) >= MAX_SHARES_PER_MINUTE:
            return False
        
        self.share_timestamps[client_id].append(now)
        return True

    def _is_duplicate_share(self, job_id: str, extranonce2: str, nonce: str) -> bool:
        """Check if share has already been submitted. Returns True if duplicate."""
        if job_id not in self.submitted_shares:
            return False
        
        share_key = (extranonce2, nonce)
        if share_key in self.submitted_shares[job_id]:
            return True
        
        self.submitted_shares[job_id].add(share_key)
        return False
    
    def _check_auth_ban(self, client_id: str) -> bool:
        """Check if client is banned due to auth failures. Returns True if banned."""
        if client_id in self.auth_failures:
            failures, ban_until = self.auth_failures[client_id]
            if time.time() < ban_until:
                return True
            # Ban expired, reset
            del self.auth_failures[client_id]
        return False
    
    def _record_auth_failure(self, client_id: str):
        """Record authentication failure and apply ban if threshold exceeded."""
        now = time.time()
        if client_id in self.auth_failures:
            failures, _ = self.auth_failures[client_id]
            failures += 1
        else:
            failures = 1
        
        if failures >= MAX_AUTH_FAILURES:
            ban_until = now + AUTH_FAILURE_BAN_TIME
            self.auth_failures[client_id] = (failures, ban_until)
            logger.warning(f"Client {client_id} banned for {AUTH_FAILURE_BAN_TIME}s due to {failures} auth failures")
        else:
            self.auth_failures[client_id] = (failures, now)
    
    def _validate_hex_param(self, param: str, expected_length: int, param_name: str) -> bool:
        """Validate hex parameter format and length."""
        if len(param) != expected_length:
            return False
        try:
            int(param, 16)
            return True
        except ValueError:
            return False

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle stratum client connection"""
        client_id = f"{writer.get_extra_info('peername')}"
        logger.info(f"New client connected: {client_id}")
        
        # Generate unique extranonce1 per client using base and counter
        extranonce1 = (self.extranonce1_base + hex(self.extranonce1_counter)[2:].zfill(8)).zfill(8)
        self.extranonce1_counter += 1
        
        self.clients[client_id] = {
            'authorized': False,
            'extranonce1': extranonce1,
            'worker': 'unknown',
            'writer': writer
        }
        
        try:
            # Send mining.notify subscription
            # Note: Typically we wait for subscribe, but some miners expect immediate notify
            # We'll wait for them to subscribe first properly
            
            # Handle client messages
            while True:
                line = await reader.readline()
                if not line:
                    break
                
                try:
                    message = json.loads(line.strip().decode())
                    await self.handle_stratum_message(writer, message, client_id)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from {client_id}: {line}")
                except Exception as e:
                    logger.error(f"Error handling message from {client_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Client error {client_id}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            if client_id in self.clients:
                del self.clients[client_id]
            # Clean up all client data structures
            self.share_timestamps.pop(client_id, None)
            self.auth_failures.pop(client_id, None)
            logger.info(f"Client disconnected: {client_id}")
    
    async def handle_stratum_message(self, writer: asyncio.StreamWriter, message: dict, client_id: str):
        """Handle stratum protocol messages"""
        method = message.get('method')
        params = message.get('params', [])
        msg_id = message.get('id')
        
        if method == 'mining.subscribe':
            # Handle subscription
            extranonce1 = self.clients[client_id]['extranonce1']
            
            await self.send_stratum_message(writer, {
                "id": msg_id,
                "result": [
                    [
                        ["mining.notify", "ae681f6b"],
                        ["mining.set_difficulty", "b4b66939"]
                    ],
                    extranonce1,
                    4 # extranonce2_size
                ],
                "error": None
            })

            # Send difficulty immediately
            await self.send_stratum_message(writer, {
                "id": None,
                "method": "mining.set_difficulty",
                "params": [STRATUM_DIFFICULTY]
            })
            
            # Send first job immediately after subscribe
            if self.jobs:
                # Send latest job
                latest_job_id = list(self.jobs.keys())[-1]
                job = self.jobs[latest_job_id]
                # Re-construct params for notify
                params = [
                    latest_job_id,
                    job['template']['previousblockhash'],
                    job['coinbase1'].hex(),
                    job['coinbase2'].hex(),
                    job['merkle_branch'],
                    hex(job['template']['version'])[2:],
                    job['template']['bits'],
                    hex(job['template']['curtime'])[2:],
                    True
                ]
                await self.send_stratum_message(writer, {
                    "id": None,
                    "method": "mining.notify",
                    "params": params
                })
            
        elif method == 'mining.authorize':
            # Handle worker authorization
            worker_name = params[0] if params else "unknown"
            
            # Check if client is banned
            if self._check_auth_ban(client_id):
                logger.warning(f"Rejected banned client: {client_id}")
                await self.send_stratum_message(writer, {
                    "id": msg_id,
                    "result": False,
                    "error": [24, "Temporarily banned due to auth failures", None]
                })
                return
            
            # Check if worker is in allowed list (if configured)
            if ALLOWED_WORKERS:
                # Extract base worker name (before any dot)
                base_worker = worker_name.split('.')[0] if '.' in worker_name else worker_name
                if base_worker not in ALLOWED_WORKERS and worker_name not in ALLOWED_WORKERS:
                    logger.warning(f"Rejected unauthorized worker: {worker_name} ({client_id})")
                    self._record_auth_failure(client_id)
                    await self.send_stratum_message(writer, {
                        "id": msg_id,
                        "result": False,
                        "error": [24, "Unauthorized worker", None]
                    })
                    return
            
            self.clients[client_id]['worker'] = worker_name
            self.clients[client_id]['authorized'] = True
            logger.info(f"Authorized worker: {worker_name} ({client_id})")
            
            # Clear any auth failures on successful auth
            if client_id in self.auth_failures:
                del self.auth_failures[client_id]
            
            await self.send_stratum_message(writer, {
                "id": msg_id,
                "result": True,
                "error": None
            })
            
        elif method == 'mining.submit':
            # Handle share submission
            await self.handle_share_submission(writer, message, client_id)
            
        else:
            logger.warning(f"Unknown method: {method}")
    
    async def handle_share_submission(self, writer: asyncio.StreamWriter, message: dict, client_id: str):
        """Handle submitted share"""
        params = message.get('params', [])
        msg_id = message.get('id')
        
        if len(params) < 5:
            await self.send_stratum_message(writer, {
                "id": msg_id,
                "result": False,
                "error": [20, "Invalid parameters", None]
            })
            return
        
        # Rate limiting check
        if not self._check_rate_limit(client_id):
            logger.warning(f"Rate limit exceeded for {client_id}")
            await self.send_stratum_message(writer, {
                "id": msg_id,
                "result": False,
                "error": [25, "Rate limit exceeded", None]
            })
            return
        
        # Extract submission data
        worker_name = params[0]
        job_id = params[1]
        extra_nonce2 = params[2]
        ntime = params[3]
        nonce = params[4]
        
        # Validate hex parameters format and length
        if not self._validate_hex_param(extra_nonce2, 8, "extranonce2"):
            await self.send_stratum_message(writer, {
                "id": msg_id,
                "result": False,
                "error": [22, "Invalid extranonce2 format or size (expected 8 hex chars)", None]
            })
            return
        
        if not self._validate_hex_param(nonce, 8, "nonce"):
            await self.send_stratum_message(writer, {
                "id": msg_id,
                "result": False,
                "error": [22, "Invalid nonce format (expected 8 hex chars)", None]
            })
            return
        
        if not self._validate_hex_param(ntime, 8, "ntime"):
            await self.send_stratum_message(writer, {
                "id": msg_id,
                "result": False,
                "error": [22, "Invalid ntime format (expected 8 hex chars)", None]
            })
            return
        
        if job_id not in self.jobs:
            await self.send_stratum_message(writer, {
                "id": msg_id,
                "result": False,
                "error": [21, "Job not found", None]
            })
            return
        
        # Check for duplicate share
        if self._is_duplicate_share(job_id, extra_nonce2, nonce):
            logger.warning(f"Duplicate share from {worker_name}: job={job_id}")
            await self.send_stratum_message(writer, {
                "id": msg_id,
                "result": False,
                "error": [22, "Duplicate share", None]
            })
            return
            
        job = self.jobs[job_id]
        
        # Validate share
        try:
            # 1. Reconstruct Coinbase
            extranonce1 = self.clients[client_id]['extranonce1']
            coinbase_tx = job['coinbase1'] + bytes.fromhex(extranonce1) + bytes.fromhex(extra_nonce2) + job['coinbase2']
            coinbase_hash_bin = hashlib.sha256(hashlib.sha256(coinbase_tx).digest()).digest()
            
            # 2. Calculate Merkle Root
            merkle_root = self.calculate_merkle_root_from_branch(coinbase_hash_bin, job['merkle_branch'])
            
            # 3. Construct Header
            # ntime is hex string, convert to int
            ntime_val = int(ntime, 16)
            nonce_val = int(nonce, 16)
            
            # Validate ntime is within acceptable range
            template_time = job['template']['curtime']
            min_time = job['template'].get('mintime', template_time - MAX_NTIME_DRIFT)
            max_time = template_time + MAX_NTIME_DRIFT
            if ntime_val < min_time or ntime_val > max_time:
                logger.warning(f"Invalid ntime from {worker_name}: {ntime_val} not in [{min_time}, {max_time}]")
                await self.send_stratum_message(writer, {
                    "id": msg_id,
                    "result": False,
                    "error": [20, "Invalid ntime", None]
                })
                return
            # nonce bytes (4 bytes)
            nonce_bytes = struct.pack('<I', nonce_val)
            
            header = self.create_block_header_from_parts(
                job['template']['version'],
                job['template']['previousblockhash'],
                merkle_root,
                ntime_val,
                job['template']['bits']
            )
            # Update nonce in header (last 4 bytes)
            header = header[:-4] + nonce_bytes
            
            # 4. Hash Header (SHA512/256d for Radiant)
            block_hash_bin = self.sha512_256d(header)
            block_hash_hex = block_hash_bin[::-1].hex()
            block_hash_int = int(block_hash_hex, 16)
            
            # 5. Check Difficulty
            # Job target is the network target
            job_target = int(job['target'], 16)
            
            # Share target is based on current stratum difficulty
            share_target = self.get_target_from_difficulty(STRATUM_DIFFICULTY)
            
            if block_hash_int <= job_target:
                logger.info(f"BLOCK FOUND! Hash: {block_hash_hex}")
                # Submit block
                block_hex = (header + bytes([0]) + coinbase_tx).hex() # Simplified block hex
                # Wait, block hex is Header + txn_count + coinbasetx + other_txs
                
                # We need to reconstruct full block hex
                # Header (80 bytes)
                # Tx Count (VarInt)
                # Coinbase
                # Other Txs
                
                # VarInt for tx count
                num_txs = 1 + len(job['template']['transactions'])
                if num_txs < 0xfd:
                    tx_count = bytes([num_txs])
                elif num_txs <= 0xffff:
                    tx_count = b'\xfd' + struct.pack('<H', num_txs)
                else:
                    tx_count = b'\xfe' + struct.pack('<I', num_txs)
                    
                full_block = header + tx_count + coinbase_tx
                
                for tx in job['template']['transactions']:
                    if isinstance(tx, dict):
                        if 'data' not in tx:
                            logger.error(f"Transaction missing 'data' field: {tx.get('txid', 'unknown')}")
                            logger.error("Block submission aborted: getblocktemplate must include transaction data")
                            await self.send_stratum_message(writer, {
                                "id": msg_id,
                                "result": False,
                                "error": [20, "Template missing tx data", None]
                            })
                            return
                        full_block += bytes.fromhex(tx['data'])
                    else:
                        logger.error(f"Invalid transaction format: expected dict with 'data', got {type(tx)}")
                        logger.error("Block submission aborted: malformed template")
                        await self.send_stratum_message(writer, {
                            "id": msg_id,
                            "result": False,
                            "error": [20, "Malformed template", None]
                        })
                        return
                
                if await self.submit_block(full_block.hex()):
                    logger.info(f"Block submitted successfully: {block_hash_hex}")
                else:
                    logger.error(f"Block submission failed: {block_hash_hex}")
                     
            elif block_hash_int <= share_target:
                logger.debug(f"Valid share accepted: {block_hash_hex}")
            else:
                logger.warning(f"Invalid share from {worker_name}: {block_hash_hex} > {hex(share_target)}")
                await self.send_stratum_message(writer, {
                    "id": msg_id,
                    "result": False,
                    "error": [23, "Low difficulty share", None]
                })
                return

            # Accept share
            await self.send_stratum_message(writer, {
                "id": msg_id,
                "result": True,
                "error": None
            })
            
        except Exception as e:
            import traceback
            logger.error(f"Share validation failed: {e}")
            logger.debug(traceback.format_exc())
            await self.send_stratum_message(writer, {
                "id": msg_id,
                "result": False,
                "error": [20, f"Validation failed: {str(e)}", None]
            })
    
    async def send_stratum_message(self, writer: asyncio.StreamWriter, message: dict):
        """Send stratum message to client"""
        try:
            line = json.dumps(message) + "\n"
            writer.write(line.encode())
            await writer.drain()
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    
    async def broadcast_new_job(self, job: dict):
        """Broadcast new job to all clients"""
        params = [
            job['job_id'],
            job['prevhash'],
            job['coinbase1'],
            job['coinbase2'],
            job['merkle_branch'],
            job['version'],
            job['nbits'],
            job['ntime'],
            True
        ]
        
        message = {
            "id": None,
            "method": "mining.notify",
            "params": params
        }
        
        # Iterate over copy of keys to avoid modification issues
        for client_id in list(self.clients.keys()):
            try:
                client = self.clients.get(client_id)
                if client and 'writer' in client:
                    await self.send_stratum_message(client['writer'], message)
            except Exception as e:
                logger.error(f"Failed to broadcast to {client_id}: {e}")

    async def update_job_loop(self):
        """Periodically update block template"""
        logger.info("Starting job update loop...")
        while not self._shutdown_event.is_set():
            try:
                template = await self.get_block_template()
                if template:
                    # Check if new work
                    current_prevhash = None
                    if self.jobs:
                        latest_id = list(self.jobs.keys())[-1]
                        current_prevhash = self.jobs[latest_id]['template']['previousblockhash']
                    
                    if current_prevhash != template['previousblockhash']:
                        logger.info(f"New block detected: {template['height']}")
                        job = await self.create_stratum_job(template)
                        await self.broadcast_new_job(job)
            except Exception as e:
                logger.error(f"Error updating job: {e}")
            
            # Use configurable poll interval
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=JOB_POLL_INTERVAL
                )
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue polling

    async def start_server(self):
        """Start stratum server"""
        server = await asyncio.start_server(
            self.handle_client,
            '0.0.0.0',
            STRATUM_PORT
        )
        
        logger.info(f"Stratum proxy listening on port {STRATUM_PORT}")
        logger.info(f"Connect ASICs to: stratum+tcp://<YOUR_IP>:{STRATUM_PORT}")
        
        async with server:
            await self._shutdown_event.wait()
            logger.info("Shutdown signal received, stopping server...")
        
        # Close all client connections
        for client_id, client in list(self.clients.items()):
            try:
                if 'writer' in client:
                    client['writer'].close()
                    await client['writer'].wait_closed()
            except Exception:
                pass
        
        # Close HTTP session
        await self._close_session()
        logger.info("Stratum server stopped")

    def shutdown(self):
        """Signal the proxy to shut down gracefully"""
        self._shutdown_event.set()

async def main():
    # Validate configuration before starting
    validate_config()
    
    proxy = RadiantStratumProxy()
    
    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, proxy.shutdown)
    
    # Test node connection
    logger.info("Testing node connection...")
    template = await proxy.get_block_template()
    if not template:
        logger.error("Cannot connect to Radiant node")
        return
    
    logger.info(f"Connected to node (height: {template.get('height', 'unknown')})")
    
    # Create initial job
    try:
        initial_job = await proxy.create_stratum_job(template)
        logger.info(f"Initial job created: {initial_job['job_id']}")
    except Exception as e:
        logger.error(f"Failed to create initial job: {e}")
        return
    
    # Start job update loop
    update_task = asyncio.create_task(proxy.update_job_loop())
    
    # Start stratum server
    try:
        await proxy.start_server()
    finally:
        update_task.cancel()
        try:
            await update_task
        except asyncio.CancelledError:
            pass
        logger.info("Stratum proxy shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
