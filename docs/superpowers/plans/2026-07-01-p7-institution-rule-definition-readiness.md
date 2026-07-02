# P7a Institution Rule Definition Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and superpowers:executing-plans. Do not write production code until the RED tests in Task 1 have been added and observed failing.

**Goal:** Build the P7a read-only institution rule definition readiness audit. It checks whether T+1, price-limit, and suspension/resume materials are ready as rule draft inputs only, while keeping formal institution rule definition, trading layer read, signal generation, and backtest execution closed.

**Spec:** `docs/superpowers/specs/2026-07-01-p7-institution-rule-definition-readiness-design.md`

**Architecture:** Add one explicit audit entry after `audit_trading_layer_read_gate_contract_when_explicitly_requested` in `src/data_sources/tdx_local/first_batch.py`. The function must consume only in-memory payloads, must not read raw market data, must not write files, must not open trading layer read, must not define institution rules, and must return pass / blocked reports only. Export it from `src/data_sources/tdx_local/__init__.py`.

**Proposed entry:**

`audit_institution_rule_definition_readiness_when_explicitly_requested`

**Tech Stack:** Python standard library, `unittest`, `json`, temp directories.

---

### Task 1: Add P7a RED Tests

**Files:**

- Modify: `tests/test_tdx_local_first_batch.py`

- [x] **Step 1: Import the new entry**

Add `audit_institution_rule_definition_readiness_when_explicitly_requested` to the existing `data_sources.tdx_local` import block.

- [x] **Step 2: Add helper payloads**

Add `_p7_readiness_inputs()` in the test class.

It should reuse `_p6_contract_inputs()` and `audit_trading_layer_read_gate_contract_when_explicitly_requested()` to create the P6 report, then add three draft input payloads:

- `t1_rule_draft_input`
- `price_limit_rule_draft_input`
- `suspension_resume_rule_draft_input`

Each input must include:

- `result == "pass"`
- matching `rule_draft_input_type`
- `draft_input_only is True`
- all downstream gates false

- [x] **Step 3: Add pass test**

Create `test_audit_institution_rule_definition_readiness_when_explicitly_requested_passes_draft_inputs`.

Assertions:

- `result == "pass"`
- `audit_id == "institution_rule_definition_readiness_audit_v0.1"`
- `institution_rule_definition_readiness_audit_result == "pass"`
- `institution_rule_definition_readiness_status == "ready_for_institution_rule_definition_draft_review"`
- required draft inputs are exactly `t1`, `price_limit`, `suspension_resume`
- `institution_rule_definition_allowed is False`
- `trading_layer_read_allowed is False`
- `signal_generation_allowed is False`
- `backtest_execution_allowed is False`
- `next_action == "action:review_institution_rule_definition_drafts"`
- no forbidden field appears in the report payload

- [x] **Step 4: Add blocked tests**

Create `test_audit_institution_rule_definition_readiness_when_explicitly_requested_blocks_missing_or_failed_inputs`.

Cover:

- missing P6 contract report
- failed P6 contract report
- missing T+1 draft input
- missing price-limit draft input
- missing suspension/resume draft input
- draft input without `draft_input_only=True`

Each blocked report must keep all hard gates false.

- [x] **Step 5: Add forbidden field test**

Create `test_audit_institution_rule_definition_readiness_when_explicitly_requested_blocks_forbidden_field_without_echo`.

Inject one forbidden field such as `limit_up_strategy` or `rhythm_meaning_override`.

Assertions:

- `result == "blocked"`
- issue code includes `institution_rule_definition_readiness_forbidden_output_field_present`
- report payload does not echo the forbidden field name
- all hard gates remain false

- [x] **Step 6: Add hard-gate test**

Create `test_audit_institution_rule_definition_readiness_when_explicitly_requested_keeps_hard_gates_false`.

Pass-valid inputs must still return:

- `institution_rule_definition_allowed is False`
- `trading_layer_read_allowed is False`
- `signal_generation_allowed is False`
- `backtest_execution_allowed is False`

- [x] **Step 7: Run RED verification**

Run:

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_tdx_local_first_batch.TdxLocalFirstBatchTest.test_audit_institution_rule_definition_readiness_when_explicitly_requested_passes_draft_inputs -v
```

Expected: fail because the entry is not implemented or exported yet.

---

### Task 2: Implement P7a Audit

**Files:**

- Modify: `src/data_sources/tdx_local/first_batch.py`

- [x] **Step 1: Add public function**

Add:

```python
def audit_institution_rule_definition_readiness_when_explicitly_requested(
    p6_contract_report: dict[str, Any] | None,
    t1_rule_draft_input: dict[str, Any] | None,
    price_limit_rule_draft_input: dict[str, Any] | None,
    suspension_resume_rule_draft_input: dict[str, Any] | None,
    generated_at: str | None = None,
) -> dict[str, Any]:
```

- [x] **Step 2: Validate P6 contract**

Require:

- `audit_id == "trading_layer_read_gate_contract_audit_v0.1"`
- `trading_layer_read_gate_contract_audit_result == "pass"`
- `trading_layer_read_gate_contract_status == "ready_for_trading_layer_read_contract_review"`
- hard gates closed

Issue code:

`institution_rule_definition_readiness_requires_p6_contract_pass`

- [x] **Step 3: Validate draft inputs**

For each required input:

- payload is dict
- `rule_draft_input_type` matches expected type
- `draft_input_only is True`
- `result == "pass"` or `readiness == "pass"`
- hard gates closed

Issue codes:

- `institution_rule_definition_readiness_requires_t1_draft_input`
- `institution_rule_definition_readiness_requires_price_limit_draft_input`
- `institution_rule_definition_readiness_requires_suspension_resume_draft_input`
- `institution_rule_definition_readiness_requires_draft_input_only`
- `institution_rule_definition_readiness_downstream_gate_open`

- [x] **Step 4: Validate forbidden fields**

Use the existing `_first_forbidden_output_field_present()` and `_strip_forbidden_fields()` helpers.

Issue code:

`institution_rule_definition_readiness_forbidden_output_field_present`

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

- [x] Add `audit_institution_rule_definition_readiness_when_explicitly_requested` to the import list.
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

Update only after implementation and tests pass:

- P7a readiness audit implemented.
- P7a pass means `ready_for_institution_rule_definition_draft_review`.
- Formal institution rule definition remains closed.
- Trading layer read, signal generation, and backtest execution remain closed.

---

### Follow-up: P7 Is Not Complete Yet

P7a completes the readiness audit only. Complete P7 still requires:

- P7b rule draft review gate.
- P7c institution rule definition contract review.
