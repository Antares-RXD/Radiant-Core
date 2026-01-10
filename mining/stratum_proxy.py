#!/usr/bin/env python3
"""
Radiant Stratum Proxy
Bridges SHA-256 ASIC miners to Radiant node via getblocktemplate
"""

import asyncio
import json
import struct
import hashlib
import time
import logging
import subprocess
import socket
from typing import Dict, Optional, Tuple
import os

# Configuration
RPC_USER = os.getenv("RPC_USER", "testnet")
RPC_PASS = os.getenv("RPC_PASS", "testnetpass123")
RPC_PORT = os.getenv("RPC_PORT", "17332")
PROJECT_DIR = os.getenv("PROJECT_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NETWORK = os.getenv("NETWORK", "testnet")

STRATUM_PORT = 3333  # Standard stratum port
DIFFICULTY = 1.0  # Start difficulty

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RadiantStratumProxy:
    def __init__(self):
        self.clients = {}
        self.current_job = None
        self.submissions = {}
        self.rpc_url = f"http://{RPC_USER}:{RPC_PASS}@127.0.0.1:{RPC_PORT}"
        
    async def get_block_template(self) -> Optional[dict]:
        """Get block template from Radiant node"""
        try:
            cmd = [
                f"{PROJECT_DIR}/build/src/radiant-cli", f"-{NETWORK}",
                f"-rpcuser={RPC_USER}", f"-rpcpassword={RPC_PASS}",
                f"-rpcport={RPC_PORT}", "getblocktemplate",
                '{"rules": ["segwit"]}'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except Exception as e:
            logger.error(f"Failed to get block template: {e}")
            return None
    
    def calculate_merkle_root(self, txids: list) -> bytes:
        """Calculate merkle root from transaction IDs"""
        if not txids:
            return b'\x00' * 32
        
        tree = [bytes.fromhex(txid)[::-1] for txid in txids]
        
        while len(tree) > 1:
            if len(tree) % 2 == 1:
                tree.append(tree[-1])
            
            new_tree = []
            for i in range(0, len(tree), 2):
                combined = tree[i] + tree[i+1]
                hash_result = hashlib.sha256(hashlib.sha256(combined).digest()).digest()
                new_tree.append(hash_result)
            
            tree = new_tree
        
        return tree[0][::-1]  # Reverse to little-endian
    
    def create_coinbase_tx(self, template: dict) -> Tuple[bytes, str]:
        """Create coinbase transaction (simplified)"""
        # Get new address for rewards
        try:
            cmd = [
                f"{PROJECT_DIR}/build/src/radiant-cli", f"-{NETWORK}",
                "-rpcwallet=miner", f"-rpcuser={RPC_USER}",
                f"-rpcpassword={RPC_PASS}", f"-rpcport={RPC_PORT}",
                "getnewaddress"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            address = result.stdout.strip()
        except:
            address = "rXhTestAddress123456789"  # Fallback
        
        # BIP34 height encoding
        height = template['height']
        if height <= 16:
            coinbase_script_sig = bytes([0x50 + height])  # OP_1 through OP_16
        else:
            coinbase_script_sig = b'\x03' + struct.pack('<I', height)[:3]
        
        # Simple coinbase transaction (simplified)
        coinbase_output_script = b'\x76\xa9\x14' + b'\x00' * 20 + b'\x88\xac'  # Placeholder script
        
        tx_data = struct.pack('<i', 1)  # Version
        tx_data += struct.pack('<B', 1)  # 1 input
        tx_data += b'\x00' * 32  # prevout hash
        tx_data += struct.pack('<I', 0xffffffff)  # prevout index
        tx_data += struct.pack('<B', len(coinbase_script_sig)) + coinbase_script_sig
        tx_data += struct.pack('<I', 0xffffffff)  # sequence
        tx_data += struct.pack('<B', 1)  # 1 output
        tx_data += struct.pack('<q', template['coinbasevalue'])  # value
        tx_data += struct.pack('<B', len(coinbase_output_script)) + coinbase_output_script
        tx_data += struct.pack('<I', 0)  # locktime
        
        return tx_data, address
    
    def create_block_header(self, template: dict, coinbase_tx: bytes) -> bytes:
        """Create block header for mining"""
        # Calculate merkle root
        txids = [coinbase_tx.hex()] + template['transactions']
        merkle_root = self.calculate_merkle_root(txids)
        
        # Create header
        bits_bytes = bytes.fromhex(template['bits'])[::-1]  # Little-endian
        
        header = struct.pack('<i', template['version']) \
               + bytes.fromhex(template['previousblockhash'])[::-1] \
               + merkle_root \
               + struct.pack('<I', template['curtime']) \
               + bits_bytes \
               + b'\x00\x00\x00\x00'  # Nonce placeholder
        
        return header
    
    def create_stratum_job(self, template: dict) -> dict:
        """Create stratum job from block template"""
        coinbase_tx, address = self.create_coinbase_tx(template)
        header = self.create_block_header(template, coinbase_tx)
        
        # Convert to mining job format
        job_id = str(int(time.time()))
        
        # For SHA-256, we need to convert SHA-512/256d target to SHA-256 target
        target = int(template['target'], 16)
        # Simplified target conversion (may need adjustment)
        sha256_target = target >> 256  # Rough approximation
        
        return {
            'job_id': job_id,
            'prevhash': template['previousblockhash'],
            'coinbase1': coinbase_tx[:42].hex(),  # First part
            'coinbase2': coinbase_tx[42:].hex(),   # Second part
            'merkle_branch': [],  # Simplified
            'version': template['version'],
            'nbits': template['bits'],
            'ntime': template['curtime'],
            'target': hex(sha256_target)[2:].zfill(64),
            'difficulty': DIFFICULTY
        }
    
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle stratum client connection"""
        client_id = f"{writer.get_extra_info('peername')}"
        logger.info(f"New client connected: {client_id}")
        
        try:
            # Send mining.notify subscription
            await self.send_stratum_message(writer, {
                "id": 1,
                "method": "mining.notify",
                "params": [
                    "job1",  # job_id
                    "00000000",  # prevhash
                    "",  # coinbase1
                    "",  # coinbase2
                    [],  # merkle_branch
                    "20000000",  # version
                    "1d00ffff",  # nbits
                    "604e99c9",  # ntime
                    False  # clean_jobs
                ]
            })
            
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
            logger.info(f"Client disconnected: {client_id}")
    
    async def handle_stratum_message(self, writer: asyncio.StreamWriter, message: dict, client_id: str):
        """Handle stratum protocol messages"""
        method = message.get('method')
        params = message.get('params', [])
        msg_id = message.get('id')
        
        if method == 'mining.subscribe':
            # Handle subscription
            await self.send_stratum_message(writer, {
                "id": msg_id,
                "result": [
                    [
                        ["mining.notify", "ae681f6b"],
                        ["mining.set_difficulty", "b4b66939"]
                    ],
                    "ae681f6b",
                    8
                ],
                "error": None
            })
            
        elif method == 'mining.authorize':
            # Handle worker authorization
            worker_name = params[0] if params else "unknown"
            self.clients[client_id] = {'worker': worker_name, 'authorized': True}
            logger.info(f"Authorized worker: {worker_name}")
            
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
        
        # Extract submission data
        worker_name = params[0]
        job_id = params[1]
        extra_nonce2 = params[2]
        ntime = params[3]
        nonce = params[4]
        
        # For now, accept all shares (simplified)
        # In production, need to validate the share
        
        logger.info(f"Share from {worker_name}: nonce={nonce}")
        
        # Accept share
        await self.send_stratum_message(writer, {
            "id": msg_id,
            "result": True,
            "error": None
        })
        
        # TODO: Check if this is a valid block and submit to node
    
    async def send_stratum_message(self, writer: asyncio.StreamWriter, message: dict):
        """Send stratum message to client"""
        try:
            line = json.dumps(message) + "\n"
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
        logger.info(f"Connect ASICs to: stratum+tcp://<YOUR_IP>:{STRATUM_PORT}")
        
        async with server:
            await server.serve_forever()

async def main():
    proxy = RadiantStratumProxy()
    
    # Test node connection
    logger.info("Testing node connection...")
    template = await proxy.get_block_template()
    if not template:
        logger.error("Cannot connect to Radiant node")
        return
    
    logger.info(f"Connected to node (height: {template.get('height', 'unknown')})")
    
    # Start stratum server
    await proxy.start_server()

if __name__ == "__main__":
    asyncio.run(main())
