// Native (non-SGX) check of the enclave's pure logic. Prints JSON vectors that
// test/check_vectors.js compares against ethers.
#include <stdio.h>
#include <string.h>

#include "../common/instance_key.h"
#include "../common/keccak.h"
#include "../common/task.h"

static void hex(const char *name, const uint8_t *b, size_t n, int comma) {
    printf("\"%s\":\"0x", name);
    for (size_t i = 0; i < n; ++i) printf("%02x", b[i]);
    printf("\"%s", comma ? "," : "");
}

int main(void) {
    uint8_t seed[32], domain[32], contract[20];
    memset(seed, 0x42, 32);
    memset(contract, 0xcc, 20);
    keccak256((const uint8_t *)"HYBRID_ATTESTED_TASK_V1", 23, domain);
    hybrid_instance_key_t key;
    if (hybrid_instance_from_seed(seed, &key) != 0) return 1;

    printf("{");
    hex("seed", seed, 32, 1);
    hex("address", key.address, 20, 1);
    hex("domain", domain, 32, 1);
    printf("\"cases\":[");
    const uint16_t steps_list[] = {1, 4, 64, 128};
    for (int c = 0; c < 4; ++c) {
        hybrid_task_t t;
        memset(&t, 0, sizeof(t));
        memset(t.task_id, 0x10 + c, 32);
        memset(t.initial, 0x11, 32);
        memset(t.data_hash, 0x33, 32);
        t.steps = steps_list[c];
        t.version = 1;
        if (hybrid_compute(t.initial, t.steps, t.output, t.trace_root) != 0) return 2;
        uint8_t digest[32], sig[65];
        hybrid_task_digest(domain, 31337, contract, &t, digest);
        if (hybrid_instance_sign(&key, digest, sig) != 0) return 3;
        printf("{\"steps\":%u,", t.steps);
        hex("taskId", t.task_id, 32, 1);
        hex("initial", t.initial, 32, 1);
        hex("dataHash", t.data_hash, 32, 1);
        hex("output", t.output, 32, 1);
        hex("traceRoot", t.trace_root, 32, 1);
        hex("digest", digest, 32, 1);
        hex("signature", sig, 65, 0);
        printf("}%s", c < 3 ? "," : "");
    }
    printf("]}\n");
    return 0;
}
