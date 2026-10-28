#ifndef HYBRID_TASK_H
#define HYBRID_TASK_H
#include <stdint.h>
#define TASK_MAX_STEPS 128
#ifdef __cplusplus
extern "C" {
#endif
int task_compute(const uint8_t initial[32], uint16_t steps, uint8_t output[32], uint8_t root[32]);
void task_report_digest(const uint8_t output[32], const uint8_t root[32], const uint8_t nonce[32], uint8_t report_data[64]);
#ifdef __cplusplus
}
#endif
#endif
