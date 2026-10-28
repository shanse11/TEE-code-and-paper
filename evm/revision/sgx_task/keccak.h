#ifndef HYBRID_KECCAK_H
#define HYBRID_KECCAK_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
void keccak256(const uint8_t *in, size_t inlen, uint8_t out[32]);
#ifdef __cplusplus
}
#endif
#endif
