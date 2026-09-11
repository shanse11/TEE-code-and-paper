# Narrative Revision Log

Source file preserved: `revised_evaluation.docx`

Generated files:

- `conference_refined_paper.docx`
- `narrative_revision_log.md`

## Paragraphs Rewritten

- Paragraph 4: `高频 DApp，如元宇宙状态同步...`
  - Why: Abstract rewritten to foreground the systems/security tradeoff, contribution significance, and scope-aware empirical claim.
- Paragraph 8: `高频 DApp 把区块链扩容问题推到一个不容易回避的位置...`
  - Why: Introduction opening sharpened around cost/latency/verifiability/liveness tension and running failure scenario.
- Paragraph 9: `现有 Rollup 路线为这一张力提供了不同折中...`
  - Why: Introduction baseline comparison rewritten to clarify why fully onchain/offchain/pure TEE are insufficient.
- Paragraph 10: `这类断点在 timeout 场景中尤其明显...`
  - Why: Problem statement strengthened to frame timeout as liveness/arbitration continuity rather than engineering inconvenience.
- Paragraph 11: `轻量提交也存在类似边界...`
  - Why: Compact commit framing and early scope awareness strengthened without defensive repetition.
- Paragraph 13: `本文的第一项贡献是将 Hybrid TEE-Rollup 中的 challenge...`
  - Why: Contribution 1 rewritten to emphasize detection vs resolution and liveness-preserving semantics.
- Paragraph 14: `第二项贡献是 evidence-carrying compact commit...`
  - Why: Contribution 2 rewritten to distinguish evidence-carrying commit from compression.
- Paragraph 15: `第三项贡献是 DA-aware cost model...`
  - Why: Contribution 3 rewritten to emphasize design insight and amortization boundary rather than headline cost reduction.
- Paragraph 19: `表 2 的作用是界定机制位置...`
  - Why: Contribution table narration rewritten for reviewer readability and significance.
- Paragraph 28: `本文关注的问题可以概括为...`
  - Why: Problem scope rewritten as a sharper conference-style problem statement.
- Paragraph 30: `本文不覆盖真实硬件 TEE 的侧信道攻击...`
  - Why: Threat model boundary rewritten as scope-aware framing rather than late disclaimer.
- Paragraph 32: `系统由执行层、数据层和验证层组成...`
  - Why: System overview opening rewritten to state what the section answers and connect mechanisms.
- Paragraph 40: `数据层保存完整 payload 及其可验证结构...`
  - Why: DA interface paragraph rewritten to reinforce compact commit as evidence preservation.
- Paragraph 48: `本节先给出 challenge session...`
  - Why: Protocol section opening rewritten to clarify why formal definitions matter.
- Paragraph 66: `recover 是本文强调的关键机制...`
  - Why: Protocol intuition rewritten to emphasize liveness/correctness separation.
- Paragraph 73: `Compact commit 的研究价值不在于...`
  - Why: Evidence-carrying section opening rewritten for impact and reviewer clarity.
- Paragraph 75: `从对抗性角度看...`
  - Why: Adversarial discussion rewritten to keep humility while clarifying significance.
- Paragraph 78: `本文比较四类 DA route...`
  - Why: Cost model paragraph rewritten to unify gas/profile boundary and tradeoff language.
- Paragraph 82: `Evaluation 围绕三个目标展开...`
  - Why: Evaluation opening rewritten to state section purpose, implications, and empirical scope.
- Paragraph 86: `其中，C_commit 表示链上提交 compact commit...`
  - Why: Cost formula explanation rewritten to stabilize boundary language.
- Paragraph 88: `RQ1 的实验从提交结构本身入手...`
  - Why: RQ1 opening rewritten to emphasize isolation of payload growth and replay path.
- Paragraph 90: `实验现象比较直接...`
  - Why: RQ1 result interpretation rewritten to explain system implication beyond smaller bytes.
- Paragraph 91: `RQ1 的结论是有限但关键的...`
  - Why: RQ1 takeaway rewritten to contrast compact commit with plain hash/compression.
- Paragraph 96: `RQ2 关注批处理后的成本摊销...`
  - Why: RQ2 opening rewritten to frame feasibility and estimation boundary.
- Paragraph 98: `随着 batch size 增大...`
  - Why: RQ2 result paragraph rewritten to emphasize high-frequency implication and boundary.
- Paragraph 99: `从预期关系看...`
  - Why: RQ2 tradeoff paragraph rewritten to avoid simplistic cost winner framing.
- Paragraph 104: `RQ3 将注意力转到异常路径...`
  - Why: RQ3 opening rewritten to make liveness claim direct.
- Paragraph 106: `在 trace steps 为 4...`
  - Why: RQ3 result paragraph rewritten to foreground detection vs completion.
- Paragraph 107: `这一现象说明 recover 的价值主要是活性...`
  - Why: RQ3 takeaway rewritten to explain high-frequency impact.
- Paragraph 111: `Recover 的单次链上开销确实高于...`
  - Why: Recovery overhead paragraph rewritten to clarify implication and gasUsed boundary.
- Paragraph 118: `RQ4 进一步拆开 fault taxonomy...`
  - Why: RQ4 opening rewritten for security-paper fault taxonomy framing.
- Paragraph 120: `Normal path 中...`
  - Why: RQ4 result paragraph rewritten to strengthen fault-oriented reasoning.
- Paragraph 128: `RQ5 回到链上对应物...`
  - Why: RQ5 opening rewritten to clarify chain correspondence and non-production scope.
- Paragraph 131: `因此，RQ5 支撑的是一个阶段性主张...`
  - Why: RQ5 takeaway rewritten to highlight significance without overclaiming.
- Paragraph 142: `The preceding RQs validate...`
  - Why: Comparison-oriented evaluation opening rewritten for reviewer readability.
- Paragraph 152: `Observation. Both paths detect timeout...`
  - Why: Recover comparison observation sharpened.
- Paragraph 158: `Observation. The result reflects more than compression...`
  - Why: Compact-vs-full observation rewritten for evidence-entry significance.
- Paragraph 170: `Observation. Full calldata deteriorates...`
  - Why: DA route observation rewritten to strengthen tradeoff reasoning and scope.
- Paragraph 174: `本节合并原 limitations...`
  - Why: Discussion opening rewritten to integrate limitations with impact rather than isolate them.
- Paragraph 188: `综合这些边界...`
  - Why: Limitations/future work paragraph rewritten to connect scope to research value.
- Paragraph 202: `实验给出的回答是谨慎肯定的...`
  - Why: Takeaway paragraph rewritten for conference-style final implication.

## Contribution Significance Strengthened

- Recoverable Challenge is reframed as a liveness-preserving transition rather than an engineering patch.
- Evidence-Carrying Compact Commit is reframed as a minimal verifiable evidence entry rather than compression.
- DA-aware Cost Model is reframed as a route-selection and amortization-boundary tool rather than a price estimator.

## Impact Improvements

- Introduction now foregrounds the four-way tension among low interaction cost, low latency, public verifiability, and challenge liveness.
- Timeout is framed as protocol liveness and arbitration continuity, not merely an implementation failure.
- High-frequency DApp motivation is tied to many small interactions that require continuous settlement.
- Evaluation takeaways now state why each result changes system understanding.

## Reviewer Readability Improvements

- Section openings now state what problem the section answers.
- Evaluation RQs now include direct implication sentences.
- Figure and table captions now interpret observations instead of only describing contents.
- Scope boundaries are introduced early and repeated only where they prevent metric misinterpretation.

## Systems/Security Narrative Enhancements

- The paper uses failure -> recovery -> replay -> resolution as the main protocol narrative.
- Fault-oriented evaluation separates detection, recovery, replay, and slashing.
- GasUsed, amortized gas, and DA-profile costs are consistently labeled as local EVM baselines or configuration-based estimates.
- Sepolia evidence is consistently described as deployability / protocol-to-contract mapping, not production readiness.

## Production-Readiness Boundary

- No real SGX/TDX security, real DA network availability, mainnet fee, production benchmark, or audit-readiness claim was added.
- The revised narrative keeps academic humility while making contribution significance easier to identify.