# P7b Institution Rule Draft Review Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and superpowers:executing-plans. Do not write production code until the RED tests in Task 1 have been added and observed failing.

**Goal:** Build the P7b read-only institution rule draft review gate. It checks whether T+1, price-limit, and suspension/resume draft inputs have enough review quality to enter P7c contract review, while keeping formal institution rule definition, trading layer read, signal generation, and backtest execution closed.

**Spec:** `docs/superpowers/specs/2026-07-01-p7b-institution-rule-draft-review-gate-design.md`

**Architecture:** Add one explicit audit entry after `audit_institution_rule_definition_readiness_when_explicitly_requested` in `src/data_sources/tdx_local/first_batch.py`. The function must consume only in-memory payloads, must not read raw market data, must not write files, must not open trading layer read, must not define institution rules, and must return pass / blocked reports only. Export it from `src/data_sources/tdx_local/__init__.py`.

**Proposed entry:**

`audit_institution_rule_definition_draft_review_gate_when_explicitly_requested`

**Tech Stack:** Python standard library, `unittest`, `json`, temp directories.

---

### Task 1: Add P7b RED Tests

**Files:**

- Modify: `tests/test_tdx_local_first_batch.py`

- [x] **Step 1: Import the new entry**

Add `audit_institution_rule_definition_draft_review_gate_when_explicitly_requested` to the existing `data_sources.tdx_local` import block.

- [x] **Step 2: Add helper payloads**

Add `_p7b_draft_review_inputs()` in the test class.

It should reuse `_p7_readiness_inputs()` and `audit_institution_rule_definition_readiness_when_explicitly_requested()` to create the P7a readiness report, then add three reviewed draft input payloads:

- `t1_rule_draft_input`
- `price_limit_rule_draft_input`
- `suspension_resume_rule_draft_input`

Each input must include:

- `result == "pass"`
- matching `rule_draft_input_type`
- `draft_input_only is True`
- `draft_quality_status == "ready_for_review"`
- `field_contract_status == "complete"`
- non-empty `evidence_refs`
- `boundary_review_status == "clean"`
- all downstream gates false

- [x] **Step 3: Add pass test**

Create `test_audit_institution_rule_definition_draft_review_gate_when_explicitly_requested_passes_review_ready_drafts`.

Assertions:

- `result == "pass"`
- `audit_id == "institution_rule_definition_draft_review_gate_audit_v0.1"`
- `institution_rule_definition_draft_review_gate_result == "pass"`
- `institution_rule_definition_draft_review_status == "ready_for_institution_rule_definition_contract_review"`
- reviewed draft inputs are exactly `t1`, `price_limit`, `suspension_resume`
- `institution_rule_definition_allowed is False`
- `trading_layer_read_allowed is False`
- `signal_generation_allowed is False`
- `backtest_execution_allowed is False`
- `next_action == "action:write_p7c_institution_rule_definition_contract_review_spec"`
- no forbidden field appears in the report payload

- [x] **Step 4: Add blocked tests**

Create `test_audit_institution_rule_definition_draft_review_gate_when_explicitly_requested_blocks_missing_or_failed_inputs`.

Cover:

- missing P7a readiness report
- failed P7a readiness report
- missing T+1 draft input
- missing price-limit draft input
- missing suspension/resume draft input
- draft input without `draft_input_only=True`

Each blocked report must keep all hard gates false.

- [x] **Step 5: Add draft quality blocked test**

Create `test_audit_institution_rule_definition_draft_review_gate_when_explicitly_requested_blocks_incomplete_draft_quality`.

Cover:

- `draft_quality_status != "ready_for_review"`
- `field_contract_status != "complete"`
- empty `evidence_refs`
- `boundary_review_status != "clean"`

- [x] **Step 6: Add forbidden field test**

Create `test_audit_institution_rule_definition_draft_review_gate_when_explicitly_requested_blocks_forbidden_field_without_echo`.

Inject one forbidden field such as `signal_decision` or `tachibana_applicability_override`.

Assertions:

- `result == "blocked"`
- issue code includes `institution_rule_definition_draft_review_forbidden_output_field_present`
- report payload does not echo the forbidden field name
- all hard gates remain false

- [x] **Step 7: Add hard-gate test**

Create `test_audit_institution_rule_definition_draft_review_gate_when_explicitly_requested_keeps_hard_gates_false`.

Pass-valid inputs must still return:

- `institution_rule_definition_allowed is False`
- `trading_layer_read_allowed is False`
- `signal_generation_allowed is False`
- `backtest_execution_allowed is False`

- [x] **Step 8: Run RED verification**

Run:

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_tdx_local_first_batch.TdxLocalFirstBatchTest.test_audit_institution_rule_definition_draft_review_gate_when_explicitly_requested_passes_review_ready_drafts -v
```

Expected: fail because the entry is not implemented or exported yet.

---

### Task 2: Implement P7b Audit

**Files:**

- Modify: `src/data_sources/tdx_local/first_batch.py`

- [x] **Step 1: Add public function**

Add:

```python
def audit_institution_rule_definition_draft_review_gate_when_explicitly_requested(
    p7a_readiness_report: dict[str, Any] | None,
    t1_rule_draft_input: dict[str, Any] | None,
    price_limit_rule_draft_input: dict[str, Any] | None,
    suspension_resume_rule_draft_input: dict[str, Any] | None,
    generated_at: str | None = None,
) -> dict[str, Any]:
```

- [x] **Step 2: Validate P7a readiness**

Require:

- `audit_id == "institution_rule_definition_readiness_audit_v0.1"`
- `institution_rule_definition_readiness_audit_result == "pass"`
- `institution_rule_definition_readiness_status == "ready_for_institution_rule_definition_draft_review"`
- hard gates closed

Issue code:

`institution_rule_definition_draft_review_requires_p7a_readiness_pass`

- [x] **Step 3: Validate reviewed draft inputs**

For each required input:

- payload is dict
- `rule_draft_input_type` matches expected type
- `draft_input_only is True`
- `draft_quality_status == "ready_for_review"`
- `field_contract_status == "complete"`
- `evidence_refs` is a non-empty list
- `boundary_review_status == "clean"`
- hard gates closed

Issue codes:

- `institution_rule_definition_draft_review_requires_t1_review_ready_draft`
- `institution_rule_definition_draft_review_requires_price_limit_review_ready_draft`
- `institution_rule_definition_draft_review_requires_suspension_resume_review_ready_draft`
- `institution_rule_definition_draft_review_requires_draft_input_only`
- `institution_rule_definition_draft_review_requires_ready_quality`
- `institution_rule_definition_draft_review_requires_complete_field_contract`
- `institution_rule_definition_draft_review_requires_evidence_refs`
- `institution_rule_definition_draft_review_requires_clean_boundary`
- `institution_rule_definition_draft_review_downstream_gate_open`

- [x] **Step 4: Validate forbidden fields**

Use the existing `_first_forbidden_output_field_present()` and `_strip_forbidden_fields()` helpers.

Issue code:

`institution_rule_definition_draft_review_forbidden_output_field_present`

- [x] **Step 5: Return pass / blocked reports**

Pass report must set:

- `institution_rule_definition_allowed=False`
- `trading_layer_read_allowed=False`
- `signal_generation_allowed=False`
- `backtest_execution_allowed=False`

Blocked report must also keep the same gates false and sort/deduplicate issues.

---

### Task 3: Export Public Entry

**Files:**

- Modify: `src/data_sources/tdx_local/__init__.py`

- [x] Add `audit_institution_rule_definition_draft_review_gate_when_explicitly_requested` to the import list.
- [x] Add it to `__all__`.

---

### Task 4: Verify

Run focused tests:

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_tdx_local_first_batch -v
```

Run full tests:

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest discover -s tests -v
```

Run whitespace check:

```powershell
git diff --check
```

---

### Task 5: Documentation Closeout

**Files:**

- Modify: `docs/06_Roadmap_TodoList_后续路线图与待办.md`
- Modify: `docs/daily-status/2026-07-01-下一步工作计划.md`
- Modify: `docs/04_施工计划_当前进度版.md`

Update only after implementation and tests pass:

- P7b draft review gate implemented.
- P7b pass means `ready_for_institution_rule_definition_contract_review`.
- Complete P7 still requires P7c.
- Formal institution rule definition remains closed.
- Trading layer read, signal generation, and backtest execution remain closed.
