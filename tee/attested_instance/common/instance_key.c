#include "instance_key.h"

#include <string.h>

#include "keccak.h"
#include "secp256k1.h"
#include "secp256k1_recovery.h"
#include "task.h"

static secp256k1_context *ctx(void) {
    static secp256k1_context *c = NULL;
    if (c == NULL) c = secp256k1_context_create(SECP256K1_CONTEXT_NONE);
    return c;
}

int hybrid_instance_from_seed(const uint8_t seed[32], hybrid_instance_key_t *key) {
    secp256k1_pubkey pub;
    uint8_t ser[65];
    size_t ser_len = sizeof(ser);
    uint8_t h[32];
    if (!secp256k1_ec_seckey_verify(ctx(), seed)) return -1;
    if (!secp256k1_ec_pubkey_create(ctx(), &pub, seed)) return -1;
    secp256k1_ec_pubkey_serialize(ctx(), ser, &ser_len, &pub, SECP256K1_EC_UNCOMPRESSED);
    keccak256(ser + 1, 64, h);
    memcpy(key->seckey, seed, 32);
    memcpy(key->address, h + 12, 20);
    return 0;
}

int hybrid_instance_sign(const hybrid_instance_key_t *key, const uint8_t digest[32], uint8_t sig[65]) {
    uint8_t msg[32];
    secp256k1_ecdsa_recoverable_signature rsig;
    int recid = 0;
    hybrid_eth_signed_hash(digest, msg);
    if (!secp256k1_ecdsa_sign_recoverable(ctx(), &rsig, msg, key->seckey, NULL, NULL)) return -1;
    secp256k1_ecdsa_recoverable_signature_serialize_compact(ctx(), sig, &recid, &rsig);
    sig[64] = (uint8_t)(27 + recid);
    return 0;
}
