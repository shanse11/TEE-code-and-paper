# Attested instance enclave for AttestedTaskRollup.
#
#   make native-check   build the pure logic natively and compare with ethers (no SGX needed)
#   make sgx            build App + signed Enclave on an SGX DCAP host (SGX_SDK must be set)
#   make clean sgx FAULT_INJECTION=1
#                       fault-injection build; ecall_sign_forged is enabled and MRENCLAVE differs
#
# The SGX targets follow the layout of the SDK's QuoteGenerationSample.

SECP := third_party/secp256k1
SECP_FLAGS := -DENABLE_MODULE_RECOVERY=1 -DENABLE_MODULE_ECDH=0 -I$(SECP)/include -I$(SECP)/src -I$(SECP)
SECP_SRC := $(SECP)/src/secp256k1.c $(SECP)/src/precomputed_ecmult.c $(SECP)/src/precomputed_ecmult_gen.c
COMMON_SRC := common/keccak.c common/task.c common/instance_key.c

native-check: build/native_vectors
	./build/native_vectors > build/vectors.json
	NODE_PATH=../../evm/node_modules node test/check_vectors.js build/vectors.json

build/native_vectors: test/native_vectors.c $(COMMON_SRC) | $(SECP)
	mkdir -p build
	$(CC) -O2 -Wall -Wno-unused-function $(SECP_FLAGS) -Icommon -o $@ test/native_vectors.c $(COMMON_SRC) $(SECP_SRC)

$(SECP):
	./fetch_secp256k1.sh

# ---------------------------------------------------------------- SGX (Linux, SGX SDK 2.19+, DCAP)
SGX_SDK ?= /opt/alibaba/teesdk/intel/sgxsdk
SGX_EDGER8R := $(SGX_SDK)/bin/x64/sgx_edger8r
SGX_SIGN := $(SGX_SDK)/bin/x64/sgx_sign
SGX_LIB := $(SGX_SDK)/lib64

ENCLAVE_CFLAGS := -m64 -O2 -nostdinc -fvisibility=hidden -fpie -fstack-protector -ffunction-sections -fdata-sections \
	-I$(SGX_SDK)/include -I$(SGX_SDK)/include/tlibc -Icommon -IEnclave $(SECP_FLAGS) \
	-DUSE_EXTERNAL_DEFAULT_CALLBACKS=1 $(if $(FAULT_INJECTION),-DHYBRID_FAULT_INJECTION=1)
ENCLAVE_LDFLAGS := -Wl,--no-undefined -nostdlib -nodefaultlibs -nostartfiles -L$(SGX_LIB) \
	-Wl,--whole-archive -lsgx_trts -Wl,--no-whole-archive \
	-Wl,--start-group -lsgx_tstdc -lsgx_tcrypto -lsgx_tservice -Wl,--end-group \
	-Wl,-Bstatic -Wl,-Bsymbolic -Wl,--no-undefined -Wl,-pie,-eenclave_entry -Wl,--export-dynamic \
	-Wl,--defsym,__ImageBase=0 -Wl,--gc-sections -Wl,--version-script=Enclave/Enclave.lds

APP_CFLAGS := -m64 -O2 -fPIC -I$(SGX_SDK)/include -IApp -Icommon
APP_LDFLAGS := -L$(SGX_LIB) -lsgx_urts -lsgx_dcap_ql -lpthread

sgx: build/app build/enclave.signed.so

Enclave/Enclave_t.c: Enclave/Enclave.edl
	cd Enclave && $(SGX_EDGER8R) --trusted Enclave.edl --search-path $(SGX_SDK)/include

App/Enclave_u.c: Enclave/Enclave.edl
	cd App && $(SGX_EDGER8R) --untrusted ../Enclave/Enclave.edl --search-path $(SGX_SDK)/include

build/enclave.so: Enclave/Enclave_t.c Enclave/enclave.c $(COMMON_SRC) | $(SECP)
	mkdir -p build
	$(CC) $(ENCLAVE_CFLAGS) -o $@ Enclave/Enclave_t.c Enclave/enclave.c $(COMMON_SRC) $(SECP_SRC) $(ENCLAVE_LDFLAGS)

build/enclave.signed.so: build/enclave.so Enclave/Enclave.config.xml Enclave/Enclave_private.pem
	$(SGX_SIGN) sign -key Enclave/Enclave_private.pem -enclave build/enclave.so -out $@ -config Enclave/Enclave.config.xml

Enclave/Enclave_private.pem:
	openssl genrsa -out $@ -3 3072

build/app: App/Enclave_u.c App/app.c common/keccak.c
	mkdir -p build
	$(CC) $(APP_CFLAGS) -o $@ App/app.c App/Enclave_u.c common/keccak.c $(APP_LDFLAGS)

clean:
	rm -rf build Enclave/Enclave_t.* App/Enclave_u.*

.PHONY: native-check sgx clean
