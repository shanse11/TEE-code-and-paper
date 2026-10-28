#ifndef HYBRID_TASK_H
#define HYBRID_TASK_H

#include <stdint.h>

#define HYBRID_MAX_STEPS 128

// Mirrors AttestedTaskRollup.TaskInput; every field is ABI-encoded as one 32-byte word.
typedef struct {
    uint8_t task_id[32];
    uint8_t initial[32];
    uint16_t steps;
    uint32_t version;
    uint8_t output[32];
    uint8_t trace_root[32];
    uint8_t data_hash[32];
} hybrid_task_t;

// Same hash chain as AttestedTaskRollup.compute: x_{i+1} = keccak256(abi.encode(i, x_i)),
// root = keccak256(abi.encode(bytes32[] x_0..x_n)). Returns 0 on success.
int hybrid_compute(const uint8_t initial[32], uint16_t steps, uint8_t output[32], uint8_t root[32]);

// keccak256(abi.encode(DOMAIN, chainid, contract, task)).
void hybrid_task_digest(const uint8_t domain[32], uint64_t chain_id, const uint8_t contract[20],
                        const hybrid_task_t *task, uint8_t digest[32]);

// keccak256("\x19Ethereum Signed Message:\n32" || digest), as checked by the contract.
void hybrid_eth_signed_hash(const uint8_t digest[32], uint8_t out[32]);

#endif
