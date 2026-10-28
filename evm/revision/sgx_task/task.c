#include "task.h"
#include "keccak.h"
#include <stddef.h>
#include <string.h>

static void write_u256(uint8_t out[32], uint64_t v) {
    memset(out, 0, 32);
    for (int i = 0; i < 8; i++) out[31 - i] = (uint8_t)((v >> (8 * i)) & 0xff);
}

int task_compute(const uint8_t initial[32], uint16_t steps, uint8_t output[32], uint8_t root[32]) {
    if (initial == 0 || output == 0 || root == 0) return 1;
    if (steps < 1 || steps > TASK_MAX_STEPS) return 2;
    uint8_t trace[TASK_MAX_STEPS + 1][32];
    memcpy(trace[0], initial, 32);
    for (uint16_t i = 0; i < steps; i++) {
        uint8_t buf[64];
        write_u256(buf, i);
        memcpy(buf + 32, trace[i], 32);
        keccak256(buf, 64, trace[i + 1]);
    }
    memcpy(output, trace[steps], 32);
    uint8_t encoded[32 + 32 + (TASK_MAX_STEPS + 1) * 32];
    write_u256(encoded, 32);
    write_u256(encoded + 32, (uint64_t)steps + 1);
    memcpy(encoded + 64, trace, ((size_t)steps + 1) * 32);
    keccak256(encoded, 64 + ((size_t)steps + 1) * 32, root);
    return 0;
}

void task_report_digest(const uint8_t output[32], const uint8_t root[32], const uint8_t nonce[32], uint8_t report_data[64]) {
    uint8_t buf[96];
    memcpy(buf, output, 32);
    memcpy(buf + 32, root, 32);
    memcpy(buf + 64, nonce, 32);
    memset(report_data, 0, 64);
    keccak256(buf, 96, report_data);
}
