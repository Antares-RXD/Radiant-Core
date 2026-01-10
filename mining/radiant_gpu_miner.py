#!/usr/bin/env python3
"""
Radiant GPU Miner using PyOpenCL
SHA-512/256d proof-of-work mining on GPU
"""

import hashlib
import json
import struct
import subprocess
import time
import numpy as np

try:
    import pyopencl as cl
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    print("PyOpenCL not available, falling back to CPU")

# --- Configuration ---
import os

RPC_USER = os.getenv("RPC_USER", "testnet")
RPC_PASS = os.getenv("RPC_PASS", "testnetpass123")
RPC_PORT = os.getenv("RPC_PORT", "17332")
PROJECT_DIR = os.getenv("PROJECT_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NETWORK = os.getenv("NETWORK", "testnet")

# OpenCL kernel for SHA-512/256d
# SHA-512/256 uses SHA-512 rounds but with different IVs and truncated output
OPENCL_KERNEL = """
// SHA-512/256 Initial Hash Values (different from SHA-512)
__constant ulong H_INIT[8] = {
    0x22312194FC2BF72CUL, 0x9F555FA3C84C64C2UL,
    0x2393B86B6F53B151UL, 0x963877195940EABDUL,
    0x96283EE2A88EFFE3UL, 0xBE5E1E2553863992UL,
    0x2B0199FC2C85B8AAUL, 0x0EB72DDC81C52CA2UL
};

// SHA-512 Round Constants
__constant ulong K[80] = {
    0x428a2f98d728ae22UL, 0x7137449123ef65cdUL, 0xb5c0fbcfec4d3b2fUL, 0xe9b5dba58189dbbcUL,
    0x3956c25bf348b538UL, 0x59f111f1b605d019UL, 0x923f82a4af194f9bUL, 0xab1c5ed5da6d8118UL,
    0xd807aa98a3030242UL, 0x12835b0145706fbeUL, 0x243185be4ee4b28cUL, 0x550c7dc3d5ffb4e2UL,
    0x72be5d74f27b896fUL, 0x80deb1fe3b1696b1UL, 0x9bdc06a725c71235UL, 0xc19bf174cf692694UL,
    0xe49b69c19ef14ad2UL, 0xefbe4786384f25e3UL, 0x0fc19dc68b8cd5b5UL, 0x240ca1cc77ac9c65UL,
    0x2de92c6f592b0275UL, 0x4a7484aa6ea6e483UL, 0x5cb0a9dcbd41fbd4UL, 0x76f988da831153b5UL,
    0x983e5152ee66dfabUL, 0xa831c66d2db43210UL, 0xb00327c898fb213fUL, 0xbf597fc7beef0ee4UL,
    0xc6e00bf33da88fc2UL, 0xd5a79147930aa725UL, 0x06ca6351e003826fUL, 0x142929670a0e6e70UL,
    0x27b70a8546d22ffcUL, 0x2e1b21385c26c926UL, 0x4d2c6dfc5ac42aedUL, 0x53380d139d95b3dfUL,
    0x650a73548baf63deUL, 0x766a0abb3c77b2a8UL, 0x81c2c92e47edaee6UL, 0x92722c851482353bUL,
    0xa2bfe8a14cf10364UL, 0xa81a664bbc423001UL, 0xc24b8b70d0f89791UL, 0xc76c51a30654be30UL,
    0xd192e819d6ef5218UL, 0xd69906245565a910UL, 0xf40e35855771202aUL, 0x106aa07032bbd1b8UL,
    0x19a4c116b8d2d0c8UL, 0x1e376c085141ab53UL, 0x2748774cdf8eeb99UL, 0x34b0bcb5e19b48a8UL,
    0x391c0cb3c5c95a63UL, 0x4ed8aa4ae3418acbUL, 0x5b9cca4f7763e373UL, 0x682e6ff3d6b2b8a3UL,
    0x748f82ee5defb2fcUL, 0x78a5636f43172f60UL, 0x84c87814a1f0ab72UL, 0x8cc702081a6439ecUL,
    0x90befffa23631e28UL, 0xa4506cebde82bde9UL, 0xbef9a3f7b2c67915UL, 0xc67178f2e372532bUL,
    0xca273eceea26619cUL, 0xd186b8c721c0c207UL, 0xeada7dd6cde0eb1eUL, 0xf57d4f7fee6ed178UL,
    0x06f067aa72176fbaUL, 0x0a637dc5a2c898a6UL, 0x113f9804bef90daeUL, 0x1b710b35131c471bUL,
    0x28db77f523047d84UL, 0x32caab7b40c72493UL, 0x3c9ebe0a15c9bebcUL, 0x431d67c49c100d4cUL,
    0x4cc5d4becb3e42b6UL, 0x597f299cfc657e2aUL, 0x5fcb6fab3ad6faecUL, 0x6c44198c4a475817UL
};

#define ROTR64(x, n) (((x) >> (n)) | ((x) << (64 - (n))))
#define CH(x, y, z) (((x) & (y)) ^ (~(x) & (z)))
#define MAJ(x, y, z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))
#define SIGMA0(x) (ROTR64(x, 28) ^ ROTR64(x, 34) ^ ROTR64(x, 39))
#define SIGMA1(x) (ROTR64(x, 14) ^ ROTR64(x, 18) ^ ROTR64(x, 41))
#define sigma0(x) (ROTR64(x, 1) ^ ROTR64(x, 8) ^ ((x) >> 7))
#define sigma1(x) (ROTR64(x, 19) ^ ROTR64(x, 61) ^ ((x) >> 6))

inline ulong swap64(ulong val) {
    return ((val & 0xFF00000000000000UL) >> 56) |
           ((val & 0x00FF000000000000UL) >> 40) |
           ((val & 0x0000FF0000000000UL) >> 24) |
           ((val & 0x000000FF00000000UL) >> 8) |
           ((val & 0x00000000FF000000UL) << 8) |
           ((val & 0x0000000000FF0000UL) << 24) |
           ((val & 0x000000000000FF00UL) << 40) |
           ((val & 0x00000000000000FFUL) << 56);
}

void sha512_256_transform(__private ulong *state, __private const ulong *block) {
    ulong W[80];
    ulong a, b, c, d, e, f, g, h;
    ulong T1, T2;
    
    // Load block (big-endian)
    for (int i = 0; i < 16; i++) {
        W[i] = swap64(block[i]);
    }
    
    // Extend
    for (int i = 16; i < 80; i++) {
        W[i] = sigma1(W[i-2]) + W[i-7] + sigma0(W[i-15]) + W[i-16];
    }
    
    a = state[0]; b = state[1]; c = state[2]; d = state[3];
    e = state[4]; f = state[5]; g = state[6]; h = state[7];
    
    // 80 rounds
    for (int i = 0; i < 80; i++) {
        T1 = h + SIGMA1(e) + CH(e, f, g) + K[i] + W[i];
        T2 = SIGMA0(a) + MAJ(a, b, c);
        h = g; g = f; f = e; e = d + T1;
        d = c; c = b; b = a; a = T1 + T2;
    }
    
    state[0] += a; state[1] += b; state[2] += c; state[3] += d;
    state[4] += e; state[5] += f; state[6] += g; state[7] += h;
}

void sha512_256(__private const uchar *data, uint len, __private uchar *hash) {
    ulong state[8];
    ulong block[16];
    
    // Initialize with SHA-512/256 IVs
    for (int i = 0; i < 8; i++) state[i] = H_INIT[i];
    
    // Process complete blocks
    uint blocks = len / 128;
    for (uint b = 0; b < blocks; b++) {
        for (int i = 0; i < 16; i++) {
            block[i] = ((__private const ulong*)(data + b * 128))[i];
        }
        sha512_256_transform(state, block);
    }
    
    // Final block with padding
    uchar final_block[128];
    uint remaining = len % 128;
    for (uint i = 0; i < remaining; i++) {
        final_block[i] = data[blocks * 128 + i];
    }
    final_block[remaining] = 0x80;
    for (uint i = remaining + 1; i < 128; i++) {
        final_block[i] = 0;
    }
    
    // If not enough room for length, process and start new block
    if (remaining >= 112) {
        for (int i = 0; i < 16; i++) {
            block[i] = ((__private ulong*)final_block)[i];
        }
        sha512_256_transform(state, block);
        for (int i = 0; i < 16; i++) final_block[i * 8] = 0;
        for (int i = 0; i < 112; i++) final_block[i] = 0;
    }
    
    // Append length in bits (big-endian)
    ulong bit_len = (ulong)len * 8;
    ((__private ulong*)final_block)[15] = swap64(bit_len);
    ((__private ulong*)final_block)[14] = 0;
    
    for (int i = 0; i < 16; i++) {
        block[i] = ((__private ulong*)final_block)[i];
    }
    sha512_256_transform(state, block);
    
    // Output first 32 bytes (256 bits) in big-endian
    for (int i = 0; i < 4; i++) {
        ((__private ulong*)hash)[i] = swap64(state[i]);
    }
}

void sha512_256d(__private const uchar *data, uint len, __private uchar *hash) {
    uchar intermediate[32];
    sha512_256(data, len, intermediate);
    sha512_256(intermediate, 32, hash);
}

__kernel void mine_sha512_256d(
    __global const uchar *header_base,  // 76 bytes (header without nonce)
    __global uchar *result_hash,        // Output: best hash found
    __global uint *result_nonce,        // Output: nonce that produced best hash
    __global uint *found,               // Output: 1 if valid hash found
    __global const uchar *target,       // Target hash (32 bytes)
    const uint nonce_start,             // Starting nonce for this batch
    const uint batch_size               // Number of nonces to try
) {
    uint gid = get_global_id(0);
    if (gid >= batch_size) return;
    
    uint nonce = nonce_start + gid;
    
    // Build full 80-byte header
    uchar header[80];
    for (int i = 0; i < 76; i++) {
        header[i] = header_base[i];
    }
    // Append nonce (little-endian)
    header[76] = (nonce) & 0xFF;
    header[77] = (nonce >> 8) & 0xFF;
    header[78] = (nonce >> 16) & 0xFF;
    header[79] = (nonce >> 24) & 0xFF;
    
    // Compute double SHA-512/256
    uchar hash[32];
    sha512_256d(header, 80, hash);
    
    // Compare with target (little-endian comparison)
    // Hash needs to be less than target
    bool valid = false;
    bool less = false;
    for (int i = 31; i >= 0; i--) {
        if (hash[i] < target[i]) {
            less = true;
            break;
        } else if (hash[i] > target[i]) {
            break;
        }
    }
    valid = less || (hash[31] == target[31]);  // Equal at all bytes checked
    
    // Re-check properly: hash < target means valid
    valid = false;
    for (int i = 31; i >= 0; i--) {
        if (hash[i] < target[i]) {
            valid = true;
            break;
        } else if (hash[i] > target[i]) {
            valid = false;
            break;
        }
    }
    
    if (valid) {
        // Atomic check to only store first valid result
        if (atomic_cmpxchg(found, 0, 1) == 0) {
            *result_nonce = nonce;
            for (int i = 0; i < 32; i++) {
                result_hash[i] = hash[i];
            }
        }
    }
}
"""

# --- CPU Hashing (fallback) --- #
def sha512_256(data):
    return hashlib.new('sha512_256', data).digest()

def sha512_256d(data):
    return sha512_256(sha512_256(data))

def sha256d(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


class GPUMiner:
    def __init__(self):
        self.running = True
        self.ctx = None
        self.queue = None
        self.program = None
        self.batch_size = 2**22  # ~4M nonces per batch
        
        if GPU_AVAILABLE:
            self._init_opencl()
    
    def _init_opencl(self):
        try:
            platforms = cl.get_platforms()
            print(f"Found {len(platforms)} OpenCL platform(s)")
            
            for platform in platforms:
                print(f"  Platform: {platform.name}")
                devices = platform.get_devices()
                for dev in devices:
                    print(f"    Device: {dev.name} ({dev.type})")
            
            # Try to get GPU device first, fall back to CPU
            self.ctx = None
            for platform in platforms:
                try:
                    devices = platform.get_devices(device_type=cl.device_type.GPU)
                    if devices:
                        self.ctx = cl.Context(devices=[devices[0]])
                        print(f"\nUsing GPU: {devices[0].name}")
                        break
                except:
                    continue
            
            if self.ctx is None:
                # Fall back to any device
                self.ctx = cl.create_some_context(interactive=False)
                print("Using default OpenCL device")
            
            self.queue = cl.CommandQueue(self.ctx)
            self.program = cl.Program(self.ctx, OPENCL_KERNEL).build()
            print("OpenCL kernel compiled successfully")
            
        except Exception as e:
            print(f"OpenCL initialization failed: {e}")
            self.ctx = None
    
    def run(self):
        print("Radiant GPU Miner (SHA-512/256d) Started")
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
        transactions_data = [coinbase_tx_data] + [bytes.fromhex(tx['data']) for tx in template['transactions']]
        
        if self.ctx is not None:
            self._mine_gpu(template, merkle_root, transactions_data)
        else:
            self._mine_cpu(template, merkle_root, transactions_data)

    def _mine_gpu(self, template, merkle_root, transactions_data):
        target_hex = template['target']
        target_bytes = bytes.fromhex(target_hex)[::-1]  # Little-endian for comparison
        print(f"Target: {target_hex}")
        
        bits_bytes = bytes.fromhex(template['bits'])
        bits_le = bits_bytes[::-1]
        
        # Build header base (76 bytes, without nonce)
        header_base = struct.pack('<i', template['version']) \
                    + bytes.fromhex(template['previousblockhash'])[::-1] \
                    + merkle_root \
                    + struct.pack('<I', template['curtime']) \
                    + bits_le
        
        assert len(header_base) == 76, f"Header base should be 76 bytes, got {len(header_base)}"
        
        # Create OpenCL buffers
        mf = cl.mem_flags
        header_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=np.frombuffer(header_base, dtype=np.uint8))
        target_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=np.frombuffer(target_bytes, dtype=np.uint8))
        result_hash_buf = cl.Buffer(self.ctx, mf.WRITE_ONLY, 32)
        result_nonce_buf = cl.Buffer(self.ctx, mf.WRITE_ONLY, 4)
        found_buf = cl.Buffer(self.ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=np.array([0], dtype=np.uint32))
        
        start_time = time.time()
        nonce = 0
        total_hashes = 0
        
        print(f"GPU mining with batch size: {self.batch_size:,}")
        
        while nonce < 2**32:
            # Reset found flag
            cl.enqueue_copy(self.queue, found_buf, np.array([0], dtype=np.uint32))
            
            # Run kernel
            self.program.mine_sha512_256d(
                self.queue,
                (self.batch_size,),
                None,
                header_buf,
                result_hash_buf,
                result_nonce_buf,
                found_buf,
                target_buf,
                np.uint32(nonce),
                np.uint32(self.batch_size)
            )
            
            # Check if found
            found = np.zeros(1, dtype=np.uint32)
            cl.enqueue_copy(self.queue, found, found_buf).wait()
            
            if found[0] == 1:
                result_nonce = np.zeros(1, dtype=np.uint32)
                result_hash = np.zeros(32, dtype=np.uint8)
                cl.enqueue_copy(self.queue, result_nonce, result_nonce_buf)
                cl.enqueue_copy(self.queue, result_hash, result_hash_buf).wait()
                
                elapsed = time.time() - start_time
                hash_rate = total_hashes / elapsed if elapsed > 0 else 0
                
                print(f"\n*** FOUND VALID HASH! Nonce: {result_nonce[0]} ***")
                print(f"Hash: {bytes(result_hash)[::-1].hex()}")
                print(f"Hash Rate: {hash_rate:,.0f} H/s")
                
                # Rebuild full header and submit
                full_header = header_base + struct.pack('<I', result_nonce[0])
                self._submit_block(full_header, transactions_data)
                return
            
            nonce += self.batch_size
            total_hashes += self.batch_size
            
            if (nonce // self.batch_size) % 10 == 0:
                elapsed = time.time() - start_time
                hash_rate = total_hashes / elapsed if elapsed > 0 else 0
                print(f"Checked {total_hashes:,} nonces @ {hash_rate:,.0f} H/s")
        
        print("Failed to find a nonce in the given range.")

    def _mine_cpu(self, template, merkle_root, transactions_data):
        """Fallback CPU mining"""
        target = int(template['target'], 16)
        print(f"Target: {template['target']}")
        print("WARNING: Using CPU fallback (slow)")

        bits_bytes = bytes.fromhex(template['bits'])
        bits_le = bits_bytes[::-1]
        
        header = struct.pack('<i', template['version']) \
               + bytes.fromhex(template['previousblockhash'])[::-1] \
               + merkle_root \
               + struct.pack('<I', template['curtime']) \
               + bits_le \
               + b'\x00\x00\x00\x00'

        start_time = time.time()
        for nonce in range(2**32):
            header_with_nonce = header[:-4] + struct.pack('<I', nonce)
            block_hash = sha512_256d(header_with_nonce)

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
                print(f"Checked {nonce:,} nonces @ {hash_rate:,.0f} H/s")

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

        tx_data = struct.pack('<i', 1)
        tx_data += struct.pack('<B', 1)
        tx_data += b'\x00' * 32
        tx_data += struct.pack('<I', 0xffffffff)
        tx_data += struct.pack('<B', len(coinbase_script_sig)) + coinbase_script_sig
        tx_data += struct.pack('<I', 0xffffffff)
        tx_data += struct.pack('<B', 1)
        tx_data += struct.pack('<q', template['coinbasevalue'])
        tx_data += struct.pack('<B', len(coinbase_output_script)) + coinbase_output_script
        tx_data += struct.pack('<I', 0)

        return tx_data, address

    def _calculate_merkle_root(self, txids):
        if not txids:
            return b'\x00' * 32

        while len(txids) > 1:
            if len(txids) % 2 != 0:
                txids.append(txids[-1])
            next_level = []
            for i in range(0, len(txids), 2):
                combined = txids[i] + txids[i+1]
                next_level.append(sha256d(combined))
            txids = next_level
        return txids[0]

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
            print(f"Block submitted: {result.stdout}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to submit block: {e.stderr}")


if __name__ == "__main__":
    miner = GPUMiner()
    miner.run()
