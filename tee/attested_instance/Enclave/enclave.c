#include <stdlib.h>
#include <string.h>

#include "Enclave_t.h"
#include "instance_key.h"
#include "sgx_trts.h"
#include "sgx_utils.h"
#include "task.h"

static hybrid_instance_key_t g_key;
static int g_ready = 0;

// libsecp256k1 is built with USE_EXTERNAL_DEFAULT_CALLBACKS because the enclave has no stdio.
void secp256k1_default_illegal_callback_fn(const char *str, void *data) {
    (void)str; (void)data;
    abort();
}
void secp256k1_default_error_callback_fn(const char *str, void *data) {
    (void)str; (void)data;
    abort();
}

static void fill_task(hybrid_task_t *t, const uint8_t *task_id, const uint8_t *initial, uint16_t steps,
                      const uint8_t *data_hash) {
    memset(t, 0, sizeof(*t));
    memcpy(t->task_id, task_id, 32);
    memcpy(t->initial, initial, 32);
    memcpy(t->data_hash, data_hash, 32);
    t->steps = steps;
    t->version = 1;
}

sgx_status_t ecall_init_instance(const sgx_target_info_t *qe_target, sgx_report_t *report, uint8_t *address) {
    uint8_t seed[32];
    for (int tries = 0; tries < 8; ++tries) {
        if (sgx_read_rand(seed, sizeof(seed)) != SGX_SUCCESS) return SGX_ERROR_UNEXPECTED;
        if (hybrid_instance_from_seed(seed, &g_key) == 0) {
            g_ready = 1;
            break;
        }
    }
    memset(seed, 0, sizeof(seed));
    if (!g_ready) return SGX_ERROR_UNEXPECTED;
    sgx_report_data_t rd;
    memset(&rd, 0, sizeof(rd));
    memcpy(rd.d, g_key.address, 20);
    memcpy(address, g_key.address, 20);
    return sgx_create_report(qe_target, &rd, report);
}

sgx_status_t ecall_run_task(const uint8_t *task_id, const uint8_t *initial, uint16_t steps, const uint8_t *data_hash,
                            const uint8_t *domain, uint64_t chain_id, const uint8_t *contract,
                            uint8_t *output, uint8_t *trace_root, uint8_t *signature) {
    if (!g_ready) return SGX_ERROR_INVALID_STATE;
    hybrid_task_t t;
    fill_task(&t, task_id, initial, steps, data_hash);
    if (hybrid_compute(t.initial, t.steps, t.output, t.trace_root) != 0) return SGX_ERROR_INVALID_PARAMETER;
    uint8_t digest[32];
    hybrid_task_digest(domain, chain_id, contract, &t, digest);
    if (hybrid_instance_sign(&g_key, digest, signature) != 0) return SGX_ERROR_UNEXPECTED;
    memcpy(output, t.output, 32);
    memcpy(trace_root, t.trace_root, 32);
    return SGX_SUCCESS;
}

sgx_status_t ecall_sign_forged(const uint8_t *task_id, const uint8_t *initial, uint16_t steps, const uint8_t *data_hash,
                               const uint8_t *domain, uint64_t chain_id, const uint8_t *contract,
                               const uint8_t *forged_output, uint8_t *trace_root, uint8_t *signature) {
#ifdef HYBRID_FAULT_INJECTION
    if (!g_ready) return SGX_ERROR_INVALID_STATE;
    hybrid_task_t t;
    fill_task(&t, task_id, initial, steps, data_hash);
    uint8_t honest_output[32];
    if (hybrid_compute(t.initial, t.steps, honest_output, t.trace_root) != 0) return SGX_ERROR_INVALID_PARAMETER;
    memcpy(t.output, forged_output, 32);
    uint8_t digest[32];
    hybrid_task_digest(domain, chain_id, contract, &t, digest);
    if (hybrid_instance_sign(&g_key, digest, signature) != 0) return SGX_ERROR_UNEXPECTED;
    memcpy(trace_root, t.trace_root, 32);
    return SGX_SUCCESS;
#else
    (void)task_id; (void)initial; (void)steps; (void)data_hash; (void)domain; (void)chain_id;
    (void)contract; (void)forged_output; (void)trace_root; (void)signature;
    return SGX_ERROR_FEATURE_NOT_SUPPORTED;
#endif
}
