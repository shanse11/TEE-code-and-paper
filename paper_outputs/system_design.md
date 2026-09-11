# 系统设计说明

## 架构图

```mermaid
flowchart LR
  User["高频 DApp 用户请求"] --> Exec["Execution Layer: simulated TEE"]
  Exec --> Att["Attestation: H(input), H(output), nonce, MRENCLAVE"]
  Att --> Commit["Compact Commit: state_root, output_hash, proof_hash, da_pointer, da_merkle_root"]
  Exec --> DA["DA Store: payload, payload_hash, leaf_hashes, merkle_proofs"]
  Commit --> Chain["JSON Ledger / Simulated Chain"]
  Chain --> Challenge["Recoverable Challenge"]
  DA --> Challenge
  Challenge --> Replay["Bisection + Single-step Replay"]
  Replay --> Resolve["Resolve / Slash / Finalize"]
```

## 数据结构

### Commit

```json
{
  "state_root": "...",
  "output_hash": "...",
  "proof_hash": "...",
  "da_pointer": "...",
  "da_merkle_root": "..."
}
```

### DA Entry

```json
{
  "da_pointer": "...",
  "payload": {"prompt": "...", "response": "...", "attestation": "..."},
  "payload_hash": "...",
  "leaf_hashes": {"prompt": "...", "response": "..."},
  "merkle_root": "...",
  "merkle_proofs": {"response": [{"position": "left", "hash": "..."}]}
}
```

### Challenge Evidence

```json
{
  "da_status": {"available": true, "valid": true, "reason": "da_proof_valid"},
  "mismatch_types": ["response_mismatch"],
  "target_step": 2,
  "expected_hash": "...",
  "claimed_hash": "..."
}
```

## 协议流程

```mermaid
sequenceDiagram
  participant U as User / Challenger
  participant C as Chain
  participant D as DA Store
  participant W as Watchdog
  U->>C: challenge-open(tx)
  C->>D: load payload + proof
  U->>C: challenge-respond(tx)
  loop bisection
    U->>C: challenge-step(tx)
  end
  alt timeout
    W->>C: challenge-recover(tx)
  end
  U->>C: challenge-replay(tx)
  C->>C: resolve and slash if invalid
```

## 状态机

```mermaid
stateDiagram-v2
  [*] --> PENDING
  PENDING --> OPEN: challenge-open
  OPEN --> RESPONDED: challenge-respond
  RESPONDED --> NARROWING: challenge-step
  NARROWING --> READY_FOR_REPLAY: dispute narrowed
  NARROWING --> RECOVERED: timeout + recover
  RECOVERED --> NARROWING: continue step
  READY_FOR_REPLAY --> REPLAYED: challenge-replay
  REPLAYED --> RESOLVED: challenge-resolve
  RESOLVED --> SLASHED: invalid
  PENDING --> FINALIZED: dispute window expired
```
