// Host for the attested instance enclave.
//
//   ./build/app <out_dir> <chain_id> <contract_hex> [--forge]
//
// Writes <out_dir>/instance_quote.dat, <out_dir>/instance.json and <out_dir>/tasks.json.
// The instance key exists only inside this enclave process, so the quote and all task
// signatures must come from the same run.
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>

#include "Enclave_u.h"
#include "keccak.h"
#include "sgx_dcap_ql_wrapper.h"
#include "sgx_urts.h"

#define ENCLAVE_FILE "build/enclave.signed.so"

static double now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1e3 + ts.tv_nsec / 1e6;
}

static void to_hex(const uint8_t *b, size_t n, char *out) {
    static const char *h = "0123456789abcdef";
    out[0] = '0';
    out[1] = 'x';
    for (size_t i = 0; i < n; ++i) {
        out[2 + 2 * i] = h[b[i] >> 4];
        out[3 + 2 * i] = h[b[i] & 15];
    }
    out[2 + 2 * n] = 0;
}

static int from_hex(const char *s, uint8_t *out, size_t n) {
    if (s[0] == '0' && (s[1] == 'x' || s[1] == 'X')) s += 2;
    if (strlen(s) != 2 * n) return -1;
    for (size_t i = 0; i < n; ++i) {
        unsigned v;
        if (sscanf(s + 2 * i, "%2x", &v) != 1) return -1;
        out[i] = (uint8_t)v;
    }
    return 0;
}

// AttestedTaskRollup.DOMAIN = keccak256("HYBRID_ATTESTED_TASK_V1").
static void domain_bytes(uint8_t domain[32]) {
    static const char tag[] = "HYBRID_ATTESTED_TASK_V1";
    keccak256((const uint8_t *)tag, sizeof(tag) - 1, domain);
}

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: %s <out_dir> <chain_id> <contract_hex> [--forge] [--domain 0x..]\n", argv[0]);
        return 2;
    }
    const char *out_dir = argv[1];
    uint64_t chain_id = strtoull(argv[2], NULL, 10);
    uint8_t contract[20], domain[32];
    if (from_hex(argv[3], contract, 20) != 0) return 2;
    int forge = 0;
    domain_bytes(domain);
    for (int i = 4; i < argc; ++i) {
        if (strcmp(argv[i], "--forge") == 0) forge = 1;
        if (strcmp(argv[i], "--domain") == 0 && i + 1 < argc && from_hex(argv[++i], domain, 32) != 0) return 2;
    }
    mkdir(out_dir, 0755);

    sgx_enclave_id_t eid;
    double t0 = now_ms();
    sgx_status_t st = sgx_create_enclave(ENCLAVE_FILE, 0, NULL, NULL, &eid, NULL);
    double t_create = now_ms() - t0;
    if (st != SGX_SUCCESS) {
        fprintf(stderr, "sgx_create_enclave failed: 0x%x\n", st);
        return 1;
    }

    sgx_target_info_t qe_target;
    quote3_error_t qe = sgx_qe_get_target_info(&qe_target);
    if (qe != SGX_QL_SUCCESS) {
        fprintf(stderr, "sgx_qe_get_target_info failed: 0x%x\n", qe);
        return 1;
    }
    sgx_report_t report;
    uint8_t address[20];
    sgx_status_t ret;
    t0 = now_ms();
    st = ecall_init_instance(eid, &ret, &qe_target, &report, address);
    double t_init = now_ms() - t0;
    if (st != SGX_SUCCESS || ret != SGX_SUCCESS) {
        fprintf(stderr, "ecall_init_instance failed: 0x%x 0x%x\n", st, ret);
        return 1;
    }
    uint32_t quote_size = 0;
    t0 = now_ms();
    if ((qe = sgx_qe_get_quote_size(&quote_size)) != SGX_QL_SUCCESS) return 1;
    uint8_t *quote = malloc(quote_size);
    if ((qe = sgx_qe_get_quote(&report, quote_size, quote)) != SGX_QL_SUCCESS) {
        fprintf(stderr, "sgx_qe_get_quote failed: 0x%x\n", qe);
        return 1;
    }
    double t_quote = now_ms() - t0;

    char path[1024];
    snprintf(path, sizeof(path), "%s/instance_quote.dat", out_dir);
    FILE *f = fopen(path, "wb");
    fwrite(quote, 1, quote_size, f);
    fclose(f);

    char addr_hex[64], mr_hex[80];
    to_hex(address, 20, addr_hex);
    to_hex(report.body.mr_enclave.m, 32, mr_hex);
    snprintf(path, sizeof(path), "%s/instance.json", out_dir);
    f = fopen(path, "w");
    fprintf(f, "{\"instance\":\"%s\",\"mrEnclave\":\"%s\",\"quoteBytes\":%u,\"forgeBuild\":%s,"
               "\"createEnclaveMs\":%.3f,\"initInstanceMs\":%.3f,\"quoteMs\":%.3f}\n",
            addr_hex, mr_hex, quote_size, forge ? "true" : "false", t_create, t_init, t_quote);
    fclose(f);

    const uint16_t steps_list[] = {4, 16, 64, 128};
    snprintf(path, sizeof(path), "%s/tasks.json", out_dir);
    f = fopen(path, "w");
    fprintf(f, "[");
    for (int c = 0; c < 4; ++c) {
        uint8_t task_id[32], initial[32], data_hash[32], output[32], root[32], sig[65];
        memset(task_id, 0x20 + c, 32);
        memset(initial, 0x11, 32);
        memset(data_hash, 0x33, 32);
        t0 = now_ms();
        if (forge) {
            memset(output, 0xee, 32);
            st = ecall_sign_forged(eid, &ret, task_id, initial, steps_list[c], data_hash, domain, chain_id, contract,
                                   output, root, sig);
        } else {
            st = ecall_run_task(eid, &ret, task_id, initial, steps_list[c], data_hash, domain, chain_id, contract,
                                output, root, sig);
        }
        double t_task = now_ms() - t0;
        if (st != SGX_SUCCESS || ret != SGX_SUCCESS) {
            fprintf(stderr, "task ecall failed: 0x%x 0x%x\n", st, ret);
            return 1;
        }
        char h1[80], h2[80], h3[80], h4[80], h5[140];
        to_hex(task_id, 32, h1);
        to_hex(output, 32, h2);
        to_hex(root, 32, h3);
        to_hex(data_hash, 32, h4);
        to_hex(sig, 65, h5);
        fprintf(f, "%s{\"steps\":%u,\"taskId\":\"%s\",\"output\":\"%s\",\"traceRoot\":\"%s\",\"dataHash\":\"%s\","
                   "\"signature\":\"%s\",\"ecallMs\":%.4f}",
                c ? "," : "", steps_list[c], h1, h2, h3, h4, h5, t_task);
    }
    fprintf(f, "]\n");
    fclose(f);
    sgx_destroy_enclave(eid);
    printf("instance %s, quote %u bytes, written to %s\n", addr_hex, quote_size, out_dir);
    return 0;
}
