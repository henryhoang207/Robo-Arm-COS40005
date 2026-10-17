# STM32H5F5 Simulator Test - Handover Checklist

## 1. Planning Documents

- [x] Draft test specification created with eight proposed test cases.
- [x] Sample logical input created for TC-01.
- [x] Expected-output draft created for TC-01.
- [x] Decision log created to track proposals and unresolved decisions.
- [x] README created to explain document purpose, scope, and limitations.
- [x] Test-to-evidence mapping created.
- [x] Interface specification draft created.
- [ ] Review all planning files for consistency before handoff.
- [ ] Confirm that sample input, expected output, and test specification
      use consistent field names and assumptions.

## 2. Existing Simulation Evidence

- [x] Existing SO101-49 results README reviewed.
- [x] MuJoCo results distinguished from physical hardware validation.
- [x] Position-error thresholds identified as requiring team approval.
- [x] Previously reported SO101-49 simulation results recorded as existing
      evidence, subject to verification of the relevant artifacts.
- [ ] Confirm evidence paths and outputs for each SO101-40 test case
      claimed to have simulation coverage.
- [ ] Verify the exact test scripts and result artifacts where the
      handoff requires test-level evidence.
- [ ] Re-run relevant tests from a repository checkout only if
      reproducibility is required or existing evidence is insufficient.
- [ ] Record actual execution results and any remaining evidence gaps.

## 3. Decisions Requiring Confirmation

- [ ] Recover the additional deliverable omitted from the truncated
      meeting note, or document the unresolved question and follow-up owner.
- [ ] Confirm the AI-to-MCU command interface and MCU-to-simulator
      response interface.
- [ ] Confirm joint names, joint mapping, units, sequence handling,
      and command-duration semantics.
- [ ] Agree on position-error tolerance and measurement method.
- [ ] Agree on timeout, replay, reset, and fault-response policies.
- [ ] Confirm final result artifact format and storage location.
- [ ] Identify which checks require MuJoCo, STM32H5F5 execution,
      or physical-arm validation.
- [ ] Record the decision authority and rationale for each confirmed
      interface or acceptance decision.

## 4. Handover Record

- Planning handoff deadline: 19 October 2026.
- Run-output milestone: 30 November 2026.
- Primary assignee: Nguyen.
- IoT lead: Chung.
- Current status: Draft - pending review and unresolved decisions.

## 5. Handover Outcome

- [ ] Reviewed by the responsible team member.
- [ ] Confirmed decisions, rationale, and decision owners recorded.
- [ ] Unresolved questions, dependencies, and blockers documented.
- [ ] Related implementation/research records updated with agreed scope
      and schedule effects.
- [ ] Jira task updated with links to the planning documents.
- [ ] Handover outcome and any remaining actions recorded.

## 6. Limitations

This checklist tracks planning and handoff readiness. It does not claim
that the STM32H5F5 implementation, target-environment test, or physical
SO-101 validation has been completed.

A checked planning item indicates that the corresponding planning activity
was completed; it does not establish that the underlying technical test
passed or that an unapproved requirement has been accepted.
