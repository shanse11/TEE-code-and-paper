#ifndef HYBRID_INSTANCE_KEY_H
#define HYBRID_INSTANCE_KEY_H

#include <stdint.h>

// secp256k1 instance key held inside the enclave. The Ethereum address of the public key is
// placed in report_data[0:20] so the contract can bind later task signatures to the quote.
typedef struct {
    uint8_t seckey[32];
    uint8_t address[20];
} hybrid_instance_key_t;

// Derives the key from 32 random bytes. Returns 0 on success, -1 if the seed is not a valid key.
int hybrid_instance_from_seed(const uint8_t seed[32], hybrid_instance_key_t *key);

// 65-byte r || s || v signature (v = 27 or 28) over hybrid_eth_signed_hash(digest).
int hybrid_instance_sign(const hybrid_instance_key_t *key, const uint8_t digest[32], uint8_t sig[65]);

#endif
