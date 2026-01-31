#!/usr/bin/env python3
"""
Shared utilities for Radiant mining scripts
Provides common functions for hashing, encoding, and transaction building
"""

import hashlib
import struct
from typing import List, Tuple


# Constants
HASH_SIZE = 32
HEADER_SIZE = 80
MAX_UINT32 = 0xffffffff
COINBASE_PREVOUT_HASH = b'\x00' * 32
COINBASE_PREVOUT_INDEX = 0xffffffff
COINBASE_SEQUENCE = 0xffffffff


def sha512_256(data: bytes) -> bytes:
    """
    Proper SHA-512/256 using correct initialization vectors.
    
    Args:
        data: Input bytes to hash
        
    Returns:
        32-byte hash digest
    """
    return hashlib.new('sha512_256', data).digest()


def sha512_256d(data: bytes) -> bytes:
    """
    Double SHA-512/256 as used by Radiant for block hashing.
    
    Args:
        data: Input bytes to hash
        
    Returns:
        32-byte double hash digest
    """
    return sha512_256(sha512_256(data))


def sha256d(data: bytes) -> bytes:
    """
    Double SHA-256 (used for transaction hashing).
    
    Args:
        data: Input bytes to hash
        
    Returns:
        32-byte double hash digest
    """
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def base58_decode(s: str) -> bytes:
    """
    Decode Base58 string to bytes with proper leading zero handling.
    
    Args:
        s: Base58 encoded string
        
    Returns:
        Decoded bytes
        
    Raises:
        ValueError: If input contains invalid Base58 characters
    """
    b58_digits = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    
    try:
        n = 0
        for char in s:
            n = n * 58 + b58_digits.index(char)
    except ValueError as e:
        raise ValueError(f"Invalid Base58 character in address: {e}")
    
    # Count leading '1's which represent leading zero bytes
    leading_zeros = len(s) - len(s.lstrip('1'))
    
    # Convert to bytes, handling the case where n is 0
    if n == 0:
        result = b''
    else:
        result = n.to_bytes((n.bit_length() + 7) // 8, 'big')
    
    # Prepend leading zero bytes
    return b'\x00' * leading_zeros + result


def base58check_decode(s: str) -> bytes:
    """
    Decode Base58Check encoded string and verify checksum.
    
    Args:
        s: Base58Check encoded string
        
    Returns:
        Decoded payload (without checksum)
        
    Raises:
        ValueError: If checksum is invalid or data is too short
    """
    raw = base58_decode(s)
    if len(raw) < 5:
        raise ValueError("Invalid Base58Check length")
    
    payload, checksum = raw[:-4], raw[-4:]
    computed_checksum = sha256d(payload)[:4]
    
    if computed_checksum != checksum:
        raise ValueError("Invalid Base58Check checksum")
    
    return payload


def encode_bip34_height(height: int) -> bytes:
    """
    Encode block height for coinbase script signature per BIP34.
    
    Args:
        height: Block height
        
    Returns:
        Encoded height bytes for script
    """
    if height == 0:
        return b'\x00'  # OP_0
    elif height <= 16:
        return bytes([0x50 + height])  # OP_1 through OP_16
    elif height <= 0x7f:
        return bytes([0x01, height])  # 1-byte push
    elif height <= 0x7fff:
        return b'\x02' + struct.pack('<H', height)  # 2-byte push
    elif height <= 0x7fffff:
        return b'\x03' + struct.pack('<I', height)[:3]  # 3-byte push
    else:
        return b'\x04' + struct.pack('<I', height)[:4]  # 4-byte push (fixed)


def create_coinbase_transaction(
    height: int,
    coinbase_value: int,
    address: str,
    extranonce1: bytes = b'',
    extranonce2: bytes = b''
) -> bytes:
    """
    Create a coinbase transaction.
    
    Args:
        height: Block height for BIP34
        coinbase_value: Coinbase reward in satoshis
        address: Mining reward address (Base58Check encoded)
        extranonce1: Extra nonce 1 (for stratum)
        extranonce2: Extra nonce 2 (for stratum)
        
    Returns:
        Serialized coinbase transaction
        
    Raises:
        ValueError: If address is invalid
    """
    # Decode address to get pubkeyhash
    try:
        payload = base58check_decode(address)
        if len(payload) != 21:
            raise ValueError(f"Invalid address payload length: {len(payload)} bytes (expected 21)")
        pubkeyhash = payload[1:]  # Skip version byte
        if len(pubkeyhash) != 20:
            raise ValueError(f"Invalid pubkeyhash length: {len(pubkeyhash)} bytes (expected 20)")
    except Exception as e:
        raise ValueError(f"Failed to decode address: {e}")
    
    # Create coinbase script signature (BIP34 height + extranonces)
    height_script = encode_bip34_height(height)
    coinbase_script_sig = height_script + extranonce1 + extranonce2
    
    # Create output script (P2PKH)
    coinbase_output_script = b'\x76\xa9\x14' + pubkeyhash + b'\x88\xac'
    
    # Build transaction
    tx_data = struct.pack('<i', 1)  # Version
    tx_data += struct.pack('<B', 1)  # Input count
    tx_data += COINBASE_PREVOUT_HASH  # Prevout hash
    tx_data += struct.pack('<I', COINBASE_PREVOUT_INDEX)  # Prevout index
    tx_data += struct.pack('<B', len(coinbase_script_sig)) + coinbase_script_sig  # Script
    tx_data += struct.pack('<I', COINBASE_SEQUENCE)  # Sequence
    tx_data += struct.pack('<B', 1)  # Output count
    tx_data += struct.pack('<q', coinbase_value)  # Value
    tx_data += struct.pack('<B', len(coinbase_output_script)) + coinbase_output_script  # Script
    tx_data += struct.pack('<I', 0)  # Locktime
    
    return tx_data


def create_coinbase_parts(
    height: int,
    coinbase_value: int,
    address: str,
    extranonce1_size: int = 4,
    extranonce2_size: int = 4
) -> Tuple[bytes, bytes]:
    """
    Create coinbase transaction split into two parts for Stratum.
    Extranonces will be inserted between coinbase1 and coinbase2.
    
    Args:
        height: Block height
        coinbase_value: Reward in satoshis
        address: Mining address
        extranonce1_size: Size of extranonce1 in bytes
        extranonce2_size: Size of extranonce2 in bytes
        
    Returns:
        Tuple of (coinbase1, coinbase2)
    """
    # Decode address
    payload = base58check_decode(address)
    if len(payload) != 21:
        raise ValueError(f"Invalid address payload length: {len(payload)} bytes")
    pubkeyhash = payload[1:]
    
    # BIP34 height encoding
    height_script = encode_bip34_height(height)
    
    # Calculate total script length including extranonces
    total_script_len = len(height_script) + extranonce1_size + extranonce2_size
    
    # Coinbase 1: Version -> Script Length -> Height Script
    coinbase1 = struct.pack('<i', 1)  # Version
    coinbase1 += struct.pack('<B', 1)  # 1 input
    coinbase1 += COINBASE_PREVOUT_HASH
    coinbase1 += struct.pack('<I', COINBASE_PREVOUT_INDEX)
    coinbase1 += struct.pack('<B', total_script_len) + height_script
    
    # Coinbase output script
    coinbase_output_script = b'\x76\xa9\x14' + pubkeyhash + b'\x88\xac'
    
    # Coinbase 2: Sequence -> Outputs -> Locktime
    coinbase2 = struct.pack('<I', COINBASE_SEQUENCE)  # sequence
    coinbase2 += struct.pack('<B', 1)  # 1 output
    coinbase2 += struct.pack('<q', coinbase_value)  # value
    coinbase2 += struct.pack('<B', len(coinbase_output_script)) + coinbase_output_script
    coinbase2 += struct.pack('<I', 0)  # locktime
    
    return coinbase1, coinbase2


def calculate_merkle_root(txids: List[bytes]) -> bytes:
    """
    Calculate merkle root from list of transaction IDs.
    
    Args:
        txids: List of transaction IDs (as bytes, already in correct endianness)
        
    Returns:
        32-byte merkle root
    """
    if not txids:
        return b'\x00' * HASH_SIZE
    
    current_level = list(txids)  # Copy to avoid modifying input
    
    while len(current_level) > 1:
        # Duplicate last element if odd number
        if len(current_level) % 2 != 0:
            current_level.append(current_level[-1])
        
        next_level = []
        for i in range(0, len(current_level), 2):
            combined = current_level[i] + current_level[i + 1]
            next_level.append(sha256d(combined))
        
        current_level = next_level
    
    return current_level[0]


def serialize_varint(n: int) -> bytes:
    """
    Serialize an integer as a Bitcoin variable-length integer.
    
    Args:
        n: Integer to serialize
        
    Returns:
        Varint encoded bytes
    """
    if n < 0xfd:
        return struct.pack('<B', n)
    elif n <= 0xffff:
        return b'\xfd' + struct.pack('<H', n)
    elif n <= 0xffffffff:
        return b'\xfe' + struct.pack('<I', n)
    else:
        return b'\xff' + struct.pack('<Q', n)


def validate_hex_string(s: str, expected_length: int = None) -> bool:
    """
    Validate that a string is valid hexadecimal.
    
    Args:
        s: String to validate
        expected_length: Expected length in characters (optional)
        
    Returns:
        True if valid hex, False otherwise
    """
    if expected_length is not None and len(s) != expected_length:
        return False
    
    try:
        int(s, 16)
        return True
    except ValueError:
        return False
