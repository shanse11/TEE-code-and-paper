#ifndef HYBRID_KECCAK_H
#define HYBRID_KECCAK_H

#include <stddef.h>
#include <stdint.h>

void keccak256(const uint8_t *in, size_t len, uint8_t out[32]);

#endif
