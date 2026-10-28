#include "task.h"
#include "keccak.h"
#include <stdio.h>
#include <string.h>

static void print_hex(const uint8_t *p, size_t n) {
    for (size_t i = 0; i < n; i++) printf("%02x", p[i]);
}

int main(void) {
    uint8_t empty[32];
    keccak256((const uint8_t *)"", 0, empty);
    printf("empty ");
    print_hex(empty, 32);
    printf("\n");
    uint8_t initial[32];
    memset(initial, 0x11, 32);
    uint8_t output[32], root[32], report[64], nonce[32];
    memset(nonce, 0x22, 32);
    if (task_compute(initial, 4, output, root) != 0) return 1;
    task_report_digest(output, root, nonce, report);
    printf("output ");
    print_hex(output, 32);
    printf("\nroot ");
    print_hex(root, 32);
    printf("\nreport ");
    print_hex(report, 32);
    printf("\n");
    return 0;
}
