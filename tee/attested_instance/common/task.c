#include "task.h"

#include <string.h>

#include "keccak.h"

static void put_u64_word(uint8_t word[32], uint64_t v) {
    memset(word, 0, 32);
    for (int i = 0; i < 8; ++i) word[31 - i] = (uint8_t)(v >> (8 * i));
}

int hybrid_compute(const uint8_t initial[32], uint16_t steps, uint8_t output[32], uint8_t root[32]) {
    // abi.encode(bytes32[]) = offset word | length word | n+1 elements.
    static uint8_t enc[64 + 32 * (HYBRID_MAX_STEPS + 1)];
    if (steps < 1 || steps > HYBRID_MAX_STEPS) return -1;
    uint8_t *trace = enc + 64;
    put_u64_word(enc, 32);
    put_u64_word(enc + 32, (uint64_t)steps + 1);
    memcpy(trace, initial, 32);
    uint8_t pair[64];
    for (uint16_t i = 0; i < steps; ++i) {
        put_u64_word(pair, i);
        memcpy(pair + 32, trace + 32 * i, 32);
        keccak256(pair, sizeof(pair), trace + 32 * (i + 1));
    }
    memcpy(output, trace + 32 * steps, 32);
    keccak256(enc, 64 + 32 * ((size_t)steps + 1), root);
    return 0;
}

void hybrid_task_digest(const uint8_t domain[32], uint64_t chain_id, const uint8_t contract[20],
                        const hybrid_task_t *task, uint8_t digest[32]) {
    uint8_t enc[32 * 10];
    memcpy(enc, domain, 32);
    put_u64_word(enc + 32, chain_id);
    memset(enc + 64, 0, 12);
    memcpy(enc + 76, contract, 20);
    memcpy(enc + 96, task->task_id, 32);
    memcpy(enc + 128, task->initial, 32);
    put_u64_word(enc + 160, task->steps);
    put_u64_word(enc + 192, task->version);
    memcpy(enc + 224, task->output, 32);
    memcpy(enc + 256, task->trace_root, 32);
    memcpy(enc + 288, task->data_hash, 32);
    keccak256(enc, sizeof(enc), digest);
}

void hybrid_eth_signed_hash(const uint8_t digest[32], uint8_t out[32]) {
    static const char prefix[] = "\x19" "Ethereum Signed Message:\n32";
    uint8_t buf[sizeof(prefix) - 1 + 32];
    memcpy(buf, prefix, sizeof(prefix) - 1);
    memcpy(buf + sizeof(prefix) - 1, digest, 32);
    keccak256(buf, sizeof(buf), out);
}
