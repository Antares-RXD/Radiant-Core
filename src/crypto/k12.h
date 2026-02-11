// Copyright (c) 2026 The Radiant developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

// KangarooTwelve (K12) hash function implementation for OP_K12 opcode.
// Based on the K12 specification: https://keccak.team/kangarootwelve.html
// K12 uses Keccak-p[1600,12] (reduced-round Keccak with 12 rounds).
// This implementation supports single-block mode only (inputs < 8192 bytes),
// which is sufficient for all script/PoW use cases in Radiant.
// Leverages the existing KeccakF permutation from sha3.cpp.

#ifndef BITCOIN_CRYPTO_K12_H
#define BITCOIN_CRYPTO_K12_H

#include <cstdint>
#include <cstdlib>

class CK12 {
public:
    static const size_t OUTPUT_SIZE = 32;
    static const size_t RATE = 168; // bytes (1344 bits, capacity = 256 bits)

    CK12();
    CK12 &Write(const uint8_t *data, size_t len);
    void Finalize(uint8_t *output);
    CK12 &Reset();

private:
    uint64_t m_state[25];
    uint8_t m_buffer[RATE];
    size_t m_buf_pos;

    // Keccak-p[1600,12]: reduced-round permutation (last 12 of 24 rounds)
    static void KeccakP12(uint64_t (&st)[25]);
};

#endif // BITCOIN_CRYPTO_K12_H
