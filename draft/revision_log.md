# Revision Log: Structural Academic Revision

Source file preserved: `Hybrid_TEE_Rollup_修改版本.docx`

Generated files:

- `revised_paper.docx`
- `revision_log.md`

## Original Chapter Structure

1. Introduction
2. Background
3. Motivation
4. Problem Statement and Threat Model
5. System Design
6. Recoverable Challenge Protocol
7. DA Cost Model
8. Evaluation
9. Threats to Validity
10. Related Work
11. Conclusion

Reference material was kept after the body.

## New Chapter Structure

1. Introduction
2. Background and Threat Model
3. System Overview
4. Recoverable Challenge Protocol
5. Evidence-Carrying Compact Commit and DA Binding
6. DA-aware Cost Model
7. Evaluation
8. Discussion and Limitations

References are retained as non-numbered back matter rather than a counted first-level paper section.

## Sections Merged

- Original Motivation was merged into Introduction.
  - Reason: Motivation repeated the same high-frequency DApp tradeoff already introduced in Section 1. The revised Introduction now introduces the core tension once, through a running timeout/failure scenario.
- Original Background and Problem Statement and Threat Model were merged into Background and Threat Model.
  - Reason: The original Background explained Rollup/TEE/DA concepts, while the original Problem Statement restated the same design tension. The revised section separates conceptual background from problem scope and adversarial assumptions.
- Original System Design was reframed as System Overview.
  - Reason: The section now emphasizes end-to-end workflow, normal path vs exceptional path, DA interaction, and recovery trigger instead of reading like a component list.
- Original Formal Definitions were moved into Recoverable Challenge Protocol.
  - Reason: The definitions exist to constrain recover semantics, so keeping them inside the protocol section improves state transition continuity.
- Original Threats to Validity, Related Work, and Conclusion were merged under Discussion and Limitations.
  - Reason: The paper target is an 8-section systems/security structure. Limitations, deployment boundary, relationship to prior work, and future direction are now presented as discussion subsections rather than three separate top-level fragments.

## Deleted or Reduced Repetition

- Reduced repeated disclaimers that the prototype is not production-ready. The disclaimer is kept in the abstract, threat model boundary, evaluation methodology, and discussion, but removed from repeated local paragraphs where it interrupted the narrative.
- Removed the standalone Motivation section because its pure on-chain / pure off-chain / pure TEE / pure optimistic comparison repeated Introduction and Background content.
- Reduced repeated explanations of compact commit as merely saving bytes. The revised paper consistently describes it as an evidence entry for DA-backed replay and challenge.
- Reduced repeated statements that Sepolia does not prove production readiness; this is now concentrated in Evaluation and Discussion.
- Avoided repeating that recovery is not a correctness proof in every paragraph; the point is stated once in protocol intuition, once in properties, and once in evaluation interpretation.

## New Narrative Transitions

- Added a running failure scenario in the Introduction: a high-frequency AI inference DApp where a TEE-generated response is committed compactly, the full payload lives in DA, and a challenge stalls after timeout.
- Added the paper-wide narrative line: failure -> recovery -> replay -> resolution.
- Added a transition from compact commit to DA evidence: compact commit is not a plain hash, but the minimum entry point into payload, field proof, attestation, and replay evidence.
- Added a transition from System Overview to Protocol: normal execution is cheap, but exceptional execution must preserve the same evidence context.
- Added a transition from Cost Model to Evaluation: payload size, batch size, and DA route are evaluated as a systems tradeoff rather than isolated variables.
- Added a transition from Evaluation to Discussion: prototype evidence is useful because it validates mechanism interfaces, while deployment-grade claims remain future work.

## Paragraphs Rewritten

- Abstract: reframed around the failure/recovery/replay/resolution problem instead of only listing mechanisms and results.
- Introduction paragraphs: rewritten to introduce the running failure scenario, the challenge liveness gap, and why compact commit is an evidence entry.
- Contribution paragraphs: rewritten to emphasize mechanism semantics rather than feature enumeration.
- Background paragraphs: lightly rewritten to avoid overlap with Motivation and to foreground TEE/DA/challenge assumptions.
- Threat model paragraphs: rewritten as adversarial assumptions and attack surface rather than general limitations.
- System Design opening: rewritten as System Overview with end-to-end workflow and normal/exceptional paths.
- Data layer paragraphs: condensed in System Overview and expanded later in the new evidence-carrying commit section.
- Formal Definitions discussion: rewritten as protocol property explaining why recover preserves correctness facts.
- Recoverable Challenge Protocol paragraphs: rewritten for timeout -> recover -> replay -> resolve continuity.
- DA Cost Model paragraphs: rewritten in systems-oriented tradeoff terms, with batch size and DA route influence made explicit.
- Evaluation opening: rewritten to state evaluation goals, prototype limitations, methodology separation, and adversarial focus.
- RQ interpretation paragraphs: rewritten to explain why results matter, not only what numbers changed.
- Discussion opening and conclusion: rewritten to state research value despite simulated TEE/mock DA limitations.

## Figure and Table Position Adjustments

- Figure 1 remains near System Overview, but its surrounding text now frames it as an end-to-end workflow with normal path, exceptional path, DA interaction, and recovery trigger.
- Figure 2 remains in Recoverable Challenge Protocol, but it is now introduced after protocol definitions so the state machine has a formal context.
- Figures 3-7 remain in Evaluation and are aligned with their corresponding RQs; their interpretation text now connects the figures to systems questions rather than listing result values.
- Table 1 remains in Introduction as the contribution table.
- Table 2 was revised from a capability checklist into a mechanism-oriented comparison table. It now describes challenge role, recovery semantics, DA evidence binding, and cost model role.
- Table 3 remains under RQ4 and is interpreted as a fault-boundary table rather than a universal slashing claim.
- Table 4 remains under RQ5 as local EVM gas evidence.
- Table 5 remains under RQ5 as Sepolia deployability evidence.
- Table 6 remains under Discussion / Relationship to Prior Work rather than a separate top-level Related Work chapter.

## Evaluation Improvements

- Added explicit evaluation goals at the beginning of Evaluation.
- Added methodology boundaries: Python prototype, local EVM gasUsed, and Sepolia deployability evidence answer different questions.
- Reframed RQ1 as submission-size decoupling plus evidence entry, not only byte reduction.
- Reframed RQ2 as a tradeoff among payload size, batch size, and DA route.
- Reframed RQ3 around adversarial timeout liveness: detection alone is insufficient if the challenge cannot finish.
- Reframed RQ4 as threat-specific reasoning: some failures are detectable/rejectable, while only some have current challenge + slashing closure.
- Reframed RQ5 as a limited on-chain counterpart claim rather than a production-readiness claim.
- Added interpretation of recovery overhead as an exceptional-path cost rather than normal-path overhead.

## Systems/Security Style Enhancements

- Strengthened adversarial assumptions and attack surface language.
- Used mechanism-driven phrasing such as recovery semantics, evidence entry, state transition continuity, and liveness-preserving transition.
- Reduced defensive writing by concentrating limitations in the appropriate sections.
- Avoided presenting the work as a complete Rollup replacement; positioned it as a mechanism enhancement to Hybrid TEE-Rollup exceptional paths.
- Made the research narrative closer to systems/security conference style: problem framing, protocol mechanism, evidence binding, cost tradeoff, adversarial evaluation, and bounded discussion.

## Deleted Repetitive Expressions

- Repeated variants of “当前原型不代表生产级系统” were consolidated into the threat model boundary, evaluation methodology, and final discussion.
- Repeated variants of “compact commit 降低链上字节数” were replaced with the evidence-entry framing.
- Repeated variants of “recover 不改变正确性” were consolidated into the protocol property and RQ3 interpretation.
- Repeated route explanations in the cost model and evaluation were shortened so the evaluation can focus on observed trends and tradeoffs.

## Running Scenario Added

The revised paper uses a high-frequency AI inference DApp as the running scenario:

- A user submits frequent prompt requests.
- A simulated TEE executor returns a response and attestation.
- The chain receives only a compact commit.
- Full prompt, response, attestation, payload hash, Merkle root, and field proofs are stored in DA.
- A malicious or faulty executor may submit a response inconsistent with DA evidence or stall during challenge.
- Recovery reactivates the timed-out challenge session.
- Replay checks the mismatch evidence.
- Resolve/slashing completes the arbitration where the current fault taxonomy supports it.

## Protocol Narrative Adjustments

- Formal definitions are now inside the protocol chapter.
- Recovery is described as a liveness-preserving transition, not a correctness decision.
- Challenge Facts are explicitly preserved across recover.
- The protocol path now distinguishes normal finalization, executable dispute resolution, and timeout recovery.
- The replay step is linked back to evidence-carrying compact commit and DA proof availability.
- Correctness discussion now separates DA binding, recovery liveness, and bisection localization.
