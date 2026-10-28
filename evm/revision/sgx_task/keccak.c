#include "keccak.h"
#include <string.h>

static const uint64_t RC[24] = {
    0x0000000000000001ULL, 0x0000000000008082ULL, 0x800000000000808aULL,
    0x8000000080008000ULL, 0x000000000000808bULL, 0x0000000080000001ULL,
    0x8000000080008081ULL, 0x8000000000008009ULL, 0x000000000000008aULL,
    0x0000000000000088ULL, 0x0000000080008009ULL, 0x000000008000000aULL,
    0x000000008000808bULL, 0x800000000000008bULL, 0x8000000000008089ULL,
    0x8000000000008003ULL, 0x8000000000008002ULL, 0x8000000000000080ULL,
    0x000000000000800aULL, 0x800000008000000aULL, 0x8000000080008081ULL,
    0x8000000000008080ULL, 0x0000000080000001ULL, 0x8000000080008008ULL
};

static const int ROT[24] = {
    1, 3, 6, 10, 15, 21, 28, 36, 45, 55, 2, 14,
    27, 41, 56, 8, 25, 43, 62, 18, 39, 61, 20, 44
};

static const int PIL[24] = {
    10, 7, 11, 17, 18, 3, 5, 16, 8, 21, 24, 4,
    15, 23, 19, 13, 12, 2, 20, 14, 22, 9, 6, 1
};

static uint64_t rotl(uint64_t x, int n) {
    return (x << n) | (x >> (64 - n));
}

static void keccakf(uint64_t st[25]) {
    for (int round = 0; round < 24; round++) {
        uint64_t bc[5];
        for (int i = 0; i < 5; i++) bc[i] = st[i] ^ st[i + 5] ^ st[i + 10] ^ st[i + 15] ^ st[i + 20];
        for (int i = 0; i < 5; i++) {
            uint64_t t = bc[(i + 4) % 5] ^ rotl(bc[(i + 1) % 5], 1);
            for (int j = 0; j < 25; j += 5) st[j + i] ^= t;
        }
        uint64_t t = st[1];
        for (int i = 0; i < 24; i++) {
            int j = PIL[i];
            bc[0] = st[j];
            st[j] = rotl(t, ROT[i]);
            t = bc[0];
        }
        for (int j = 0; j < 25; j += 5) {
            uint64_t tmp[5];
            for (int i = 0; i < 5; i++) tmp[i] = st[j + i];
            for (int i = 0; i < 5; i++) st[j + i] = tmp[i] ^ ((~tmp[(i + 1) % 5]) & tmp[(i + 2) % 5]);
        }
        st[0] ^= RC[round];
    }
}

void keccak256(const uint8_t *in, size_t inlen, uint8_t out[32]) {
    uint64_t st[25];
    uint8_t temp[136];
    const size_t rsiz = 136;
    memset(st, 0, sizeof st);
    while (inlen >= rsiz) {
        for (size_t i = 0; i < rsiz / 8; i++) {
            uint64_t lane;
            memcpy(&lane, in + 8 * i, 8);
            st[i] ^= lane;
        }
        keccakf(st);
        in += rsiz;
        inlen -= rsiz;
    }
    memset(temp, 0, rsiz);
    memcpy(temp, in, inlen);
    temp[inlen] ^= 0x01;
    temp[rsiz - 1] ^= 0x80;
    for (size_t i = 0; i < rsiz / 8; i++) {
        uint64_t lane;
        memcpy(&lane, temp + 8 * i, 8);
        st[i] ^= lane;
    }
    keccakf(st);
    memcpy(out, st, 32);
}
