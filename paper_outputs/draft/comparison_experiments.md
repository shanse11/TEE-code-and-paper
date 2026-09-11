# Comparison-Oriented Evaluation Addendum

Generated document: `revised_evaluation.docx`

Source paper preserved: `revised_paper.docx`

All added comparisons use the existing prototype outputs under `project_code/paper_outputs/` and the existing experiment script `project_code/scripts/run_paper_experiments.py`. No real SGX, Celestia, EigenDA, blob-market, Sepolia throughput, or production benchmark is introduced.

## Baselines Added

1. **No-recover challenge baseline**
   - Source scenario: `challenge_timeout_no_recover` in `failure_scenarios.csv`.
   - Why reasonable: it disables the paper's main recovery mechanism while keeping the same synthetic timeout workload and challenge state machine. This isolates the liveness contribution of `recover`.

2. **Recoverable challenge treatment**
   - Source scenario: `challenge_timeout_recover` in `failure_scenarios.csv`.
   - Why reasonable: it uses the same timeout injection, but allows watchdog recovery and subsequent replay/resolve.

3. **Full payload submission baseline**
   - Source metrics: `full_bytes` and `full_onchain_calldata_*` in `cost_grid.csv`.
   - Why reasonable: it represents the direct design point where prompt/response/attestation payload is placed on chain, against which compact commit can be compared.

4. **Compact commit treatment**
   - Source metrics: `compact_bytes` and compact DA route estimates in `cost_grid.csv`.
   - Why reasonable: it is the proposed evidence-carrying structure that stores fixed-size commitment fields on chain while retrieving detailed evidence through DA.

5. **DA route baselines**
   - Routes: `full_onchain_calldata`, `compact_external_da`, `compact_eip4844_like`, `compact_modular_da_sampling`.
   - Why reasonable: these are already encoded as configuration profiles in the experiment script, so the comparison is a controlled estimate over payload size and batch size rather than a claim about live networks.

6. **Fault-specific handling baselines**
   - Faults: response tampering, DA unavailable, DA proof invalid, timeout with/without recovery, trace mismatch, attestation invalid.
   - Why reasonable: each fault is already injected by the prototype. The comparison asks which faults are merely detectable and which reach recovery, replay, and slashing.

## New Experiments Added

### 1. Recover vs No-Recover Comparison

Category: **liveness comparison**

Metrics added:

- `detection_rate`
- `replay_success_rate` / replay completion rate
- `resolve_success_rate`
- `slashed_rate`
- `finalized_rate` / terminal outcome rate
- `avg_recovery_delay`

| Scenario | Detection | Replay | Resolve | Slashing | Terminal Outcome | Avg Recovery Delay |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| no-recover | 100% | 0% | 0% | 0% | 0% | N/A |
| recoverable challenge | 100% | 100% | 100% | 100% | 100% | 1.0s configured after timeout threshold |

Notes:

- `avg_recovery_delay` is a synthetic scheduler-derived value. In the failure scenario script, the last challenge step occurs at `t+2s`, timeout threshold is `t+4s`, and recovery is invoked at `t+5s`; the paper reports this as one configured second after timeout threshold.
- The comparison shows that detection is not equivalent to challenge completion.
- Recovery changes liveness, not correctness facts.

Figures added:

- `comparison_figures/recover_vs_no_recover_bar.png`
- `comparison_figures/timeout_stalled_vs_recovered.png`
- `comparison_figures/replay_recovery_timeline.png`

### 2. Compact Commit vs Full Payload Comparison

Category: **cost comparison** and **evidence-linkage comparison**

Metrics added:

- `onchain bytes`
- `replay readiness`
- `DA fetch dependency`
- `proof granularity`
- `verification overhead`

| Scheme | Onchain Bytes | Replay Ready | Evidence Retrieval | Verification Cost |
| --- | ---: | --- | --- | --- |
| full payload | avg 50,068.84 bytes at payload=8192, prompt=64 | Yes, payload is directly present | No DA fetch needed | High on-chain byte footprint |
| compact commit | avg 406.00 bytes | Yes, if DA entry and Merkle proof are available | Requires DA pointer and field proof | DA fetch + Merkle verification |

Figure added:

- `comparison_figures/compact_vs_full_payload_bytes.png`

### 3. Fault-Oriented Comparison

Category: **fault-oriented comparison**

| Fault Type | Detectable | Recoverable | Replayable | Slashable |
| --- | --- | --- | --- | --- |
| response tampering | yes | no | yes | yes |
| DA unavailable | yes | no | no | no |
| DA proof invalid | yes | no | no | no |
| timeout / no recover | yes | no | no | no |
| timeout / recover | yes | yes | yes | yes |
| trace mismatch | yes | no | yes | yes |
| attestation invalid | yes | no | no | no |

Figure/table added:

- `comparison_figures/fault_oriented_heatmap.png`

### 4. DA Route Tradeoff Comparison

Category: **cost comparison** and **scalability comparison**

Metrics added:

- `amortized cost`
- `replay readiness`
- `payload scaling`
- `batch sensitivity`
- `estimated DA dependency`

Routes compared:

- `full_onchain_calldata`
- `compact_external_da`
- `compact_eip4844_like`
- `compact_modular_da_sampling`

Figure added:

- `comparison_figures/da_route_tradeoff_comparison.png`

### 5. Concurrent Challenge Scalability

Category: **scalability comparison**

Status: **not added as a measured paper result**.

Reason: the existing output set does not contain multiple concurrent challenge sessions, replay queue delay, recovery queue overhead, or queue growth measurements. The paper therefore does not claim concurrent scalability. It only notes that such measurement is future work.

## New Figures Added

1. `recover_vs_no_recover_bar.png` - recover vs no-recover bar chart.
2. `timeout_stalled_vs_recovered.png` - stalled sessions vs recovered sessions.
3. `compact_vs_full_payload_bytes.png` - compact commit vs full payload bytes.
4. `da_route_tradeoff_comparison.png` - DA route tradeoff figure.
5. `fault_oriented_heatmap.png` - fault-oriented comparison heatmap/table.
6. `replay_recovery_timeline.png` - replay/recovery timeline figure.

## Prototype and Estimation Boundaries

- Workload is synthetic: prompt length, payload size, trace steps, timeout, and batch size are configured by script.
- TEE is simulated. No SGX/TDX remote attestation benchmark is claimed.
- DA is mock/verifiable or profile-based. No Celestia/EigenDA availability or economics are measured.
- Cost is configuration-based estimation using gas-per-byte profiles, not mainnet gas, blob fee, or production DA pricing.
- Sepolia evidence remains deployability evidence only.
- Concurrent challenge scalability is not claimed because the current experiment output does not measure it.
