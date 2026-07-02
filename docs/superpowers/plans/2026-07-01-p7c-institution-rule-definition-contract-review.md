# P7c Institution Rule Definition Contract Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and superpowers:executing-plans. Do not write production code until the RED tests in Task 1 have been added and observed failing.

**Goal:** Build the P7c read-only institution rule definition contract review. It checks whether P7b-reviewed T+1, price-limit, and suspension/resume drafts satisfy the future formal institution rule definition entry contract, while keeping institution rule definition, trading layer read, signal generation, and backtest execution closed.

**Spec:** `docs/superpowers/specs/2026-07-01-p7c-institution-rule-definition-contract-review-design.md`

**Architecture:** Add one explicit audit entry after `audit_institution_rule_definition_draft_review_gate_when_explicitly_requested` in `src/data_sources/tdx_local/first_batch.py`. The function must consume only in-memory payloads, must not read raw market data, must not write files, must not open institution rule definition, must not open trading layer read, must not generate signals, and must return pass / blocked reports only. Export it from `src/data_sources/tdx_local/__init__.py`.

**Proposed entry:**

`audit_institution_rule_definition_contract_review_when_explicitly_requested`

**Tech Stack:** Python standard library, `unittest`, `json`, temp directories.

---

### Task 1: Add P7c RED Tests

**Files:**

- Modify: `tests/test_tdx_local_first_batch.py`

- [x] **Step 1: Import the new entry**

Add `audit_institution_rule_definition_contract_review_when_explicitly_requested` to the existing `data_sources.tdx_local` import block.

- [x] **Step 2: Add helper payloads**

Add `_p7c_contract_review_inputs()` in the test class.

It should reuse `_p7b_draft_review_inputs()` and `audit_institution_rule_definition_draft_review_gate_when_explicitly_requested()` to create the P7b report, then add three reviewed draft contract input payloads:

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
- `contract_review_status == "ready"`
- non-empty `definition_contract_fields`
- `consumer_entrypoint == "institution_rule_definition"`
- all downstream gates false

- [x] **Step 3: Add pass test**

Create `test_audit_institution_rule_definition_contract_review_when_explicitly_requested_passes_contract_ready_drafts`.

Assertions:

- `result == "pass"`
- `audit_id == "institution_rule_definition_contract_review_audit_v0.1"`
- `institution_rule_definition_contract_review_result == "pass"`
- `institution_rule_definition_contract_review_status == "ready_for_explicit_institution_rule_definition_open_gate_review"`
- contract reviewed draft inputs are exactly `t1`, `price_limit`, `suspension_resume`
- `institution_rule_definition_allowed is False`
- `trading_layer_read_allowed is False`
- `signal_generation_allowed is False`
- `backtest_execution_allowed is False`
- `next_action == "action:review_explicit_institution_rule_definition_open_gate"`
- no forbidden field appears in the report payload

- [x] **Step 4: Add blocked tests**

Create `test_audit_institution_rule_definition_contract_review_when_explicitly_requested_blocks_missing_or_failed_inputs`.

Cover:

- missing P7b draft review gate report
- failed P7b draft review gate report
- missing T+1 draft input
- missing price-limit draft input
- missing suspension/resume draft input
- draft input without `draft_input_only=True`

Each blocked report must keep all hard gates false.

- [x] **Step 5: Add contract quality blocked test**

Create `test_audit_institution_rule_definition_contract_review_when_explicitly_requested_blocks_incomplete_contract`.

Cover:

- `contract_review_status != "ready"`
- empty `definition_contract_fields`
- `consumer_entrypoint != "institution_rule_definition"`
- `field_contract_status != "complete"`

- [x] **Step 6: Add forbidden field test**

Create `test_audit_institution_rule_definition_contract_review_when_explicitly_requested_blocks_forbidden_field_without_echo`.

Inject one forbidden field such as `target_position` or `signal_decision`.

Assertions:

- `result == "blocked"`
- issue code includes `institution_rule_definition_contract_review_forbidden_output_field_present`
- report payload does not echo the forbidden field name
- all hard gates remain false

- [x] **Step 7: Add hard-gate test**

Create `test_audit_institution_rule_definition_contract_review_when_explicitly_requested_keeps_hard_gates_false`.

Pass-valid inputs must still return:

- `institution_rule_definition_allowed is False`
- `trading_layer_read_allowed is False`
- `signal_generation_allowed is False`
- `backtest_execution_allowed is False`

- [x] **Step 8: Run RED verification**

Run:

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_tdx_local_first_batch.TdxLocalFirstBatchTest.test_audit_institution_rule_definition_contract_review_when_explicitly_requested_passes_contract_ready_drafts -v
```

Expected: fail because the entry is not implemented or exported yet.

---

### Task 2: Implement P7c Audit

**Files:**

- Modify: `src/data_sources/tdx_local/first_batch.py`

- [x] **Step 1: Add public function**

Add:

```python
def audit_institution_rule_definition_contract_review_when_explicitly_requested(
    p7b_draft_review_gate_report: dict[str, Any] | None,
    t1_rule_draft_input: dict[str, Any] | None,
    price_limit_rule_draft_input: dict[str, Any] | None,
    suspension_resume_rule_draft_input: dict[str, Any] | None,
    generated_at: str | None = None,
) -> dict[str, Any]:
```

- [x] **Step 2: Validate P7b draft review gate**

Require:

- `audit_id == "institution_rule_definition_draft_review_gate_audit_v0.1"`
- `institution_rule_definition_draft_review_gate_result == "pass"`
- `institution_rule_definition_draft_review_status == "ready_for_institution_rule_definition_contract_review"`
- hard gates closed

Issue code:

`institution_rule_definition_contract_review_requires_p7b_draft_review_gate_pass`

- [x] **Step 3: Validate contract-ready draft inputs**

For each required input:

- payload is dict
- `rule_draft_input_type` matches expected type
- `draft_input_only is True`
- `draft_quality_status == "ready_for_review"`
- `field_contract_status == "complete"`
- `evidence_refs` is a non-empty list
- `boundary_review_status == "clean"`
- `contract_review_status == "ready"`
- `definition_contract_fields` is a non-empty list
- `consumer_entrypoint == "institution_rule_definition"`
- hard gates closed

Issue codes:

- `institution_rule_definition_contract_review_requires_t1_contract_ready_draft`
- `institution_rule_definition_contract_review_requires_price_limit_contract_ready_draft`
- `institution_rule_definition_contract_review_requires_suspension_resume_contract_ready_draft`
- `institution_rule_definition_contract_review_requires_draft_input_only`
- `institution_rule_definition_contract_review_requires_ready_quality`
- `institution_rule_definition_contract_review_requires_complete_field_contract`
- `institution_rule_definition_contract_review_requires_evidence_refs`
- `institution_rule_definition_contract_review_requires_clean_boundary`
- `institution_rule_definition_contract_review_requires_ready_contract_review`
- `institution_rule_definition_contract_review_requires_definition_contract_fields`
- `institution_rule_definition_contract_review_requires_definition_consumer_entrypoint`
- `institution_rule_definition_contract_review_downstream_gate_open`

- [x] **Step 4: Validate forbidden fields**

Use the existing `_first_forbidden_output_field_present()` and `_strip_forbidden_fields()` helpers.

Issue code:

`institution_rule_definition_contract_review_forbidden_output_field_present`

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

- [x] Add `audit_institution_rule_definition_contract_review_when_explicitly_requested` to the import list.
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

- P7c contract review implemented.
- P7c pass means `ready_for_explicit_institution_rule_definition_open_gate_review`.
- Complete P7 is finished only as a preparation milestone.
- Formal institution rule definition still requires a separate explicit open gate.
- Trading layer read, signal generation, and backtest execution remain closed.

---

### Completion Evidence

- RED verification failed first because the new P7c entry was not exported.
- Focused verification passed:

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_tdx_local_first_batch -v
```

Result: `75 tests OK`

- Full verification passed:

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest discover -s tests -v
```

Result: `266 tests OK`
