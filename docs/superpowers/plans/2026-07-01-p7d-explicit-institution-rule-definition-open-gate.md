# P7d Explicit Institution Rule Definition Open Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and superpowers:executing-plans. Do not write production code until the RED tests in Task 1 have been added and observed failing.

**Goal:** Build the P7d explicit open gate for institution rule definition. It consumes P7c contract review evidence and a deliberate open-gate approval, opens only `institution_rule_definition_allowed`, and keeps trading layer read, signal generation, and backtest execution closed.

**Spec:** `docs/superpowers/specs/2026-07-01-p7d-explicit-institution-rule-definition-open-gate-design.md`

**Architecture:** Add one explicit audit entry after `audit_institution_rule_definition_contract_review_when_explicitly_requested` in `src/data_sources/tdx_local/first_batch.py`. The function must consume only in-memory payloads, must not read raw market data, must not write files, must not generate institution rules, must not open trading layer read, must not generate signals, and must return pass / blocked reports only. Export it from `src/data_sources/tdx_local/__init__.py`.

**Proposed entry:**

`audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested`

**Tech Stack:** Python standard library, `unittest`, `json`, temp directories.

---

### Task 1: Add P7d RED Tests

**Files:**

- Modify: `tests/test_tdx_local_first_batch.py`

- [x] **Step 1: Import the new entry**

Add `audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested` to the existing `data_sources.tdx_local` import block.

- [x] **Step 2: Add helper payloads**

Add `_p7d_open_gate_inputs()` in the test class.

It should reuse `_p7c_contract_review_inputs()` and `audit_institution_rule_definition_contract_review_when_explicitly_requested()` to create the P7c report, then return:

- `p7c_contract_review_report`
- three contract-ready draft inputs
- `explicit_open_gate_decision`

The open-gate decision must include:

- `gate_decision == "approve_institution_rule_definition_only"`
- `gate_scope == "institution_rule_definition_only"`
- non-empty `approved_by`
- non-empty `approval_evidence_refs`
- `acknowledged_no_trading_layer_read is True`
- `acknowledged_no_signal_generation is True`
- `acknowledged_no_backtest_execution is True`

- [x] **Step 3: Add pass test**

Create `test_audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested_passes_explicit_rule_definition_only_gate`.

Assertions:

- `result == "pass"`
- `audit_id == "explicit_institution_rule_definition_open_gate_audit_v0.1"`
- `explicit_institution_rule_definition_open_gate_result == "pass"`
- `explicit_institution_rule_definition_open_gate_status == "institution_rule_definition_opened_for_rule_definition_only"`
- `institution_rule_definition_allowed is True`
- `trading_layer_read_allowed is False`
- `signal_generation_allowed is False`
- `backtest_execution_allowed is False`
- `next_action == "action:define_formal_institution_rules_only"`
- no forbidden field appears in the report payload

- [x] **Step 4: Add blocked tests**

Create `test_audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested_blocks_missing_or_failed_inputs`.

Cover:

- missing P7c contract review report
- failed P7c contract review report
- missing T+1 draft input
- missing price-limit draft input
- missing suspension/resume draft input
- draft input without `draft_input_only=True`

- [x] **Step 5: Add explicit decision blocked test**

Create `test_audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested_blocks_bad_open_gate_decision`.

Cover:

- missing explicit decision
- wrong `gate_decision`
- wrong `gate_scope`
- missing `approved_by`
- empty `approval_evidence_refs`
- missing no-trading/no-signal/no-backtest acknowledgement

- [x] **Step 6: Add forbidden field test**

Create `test_audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested_blocks_forbidden_field_without_echo`.

Inject one forbidden field such as `signal_decision`.

- [x] **Step 7: Add hard-gate test**

Create `test_audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested_opens_only_rule_definition_gate`.

Pass-valid inputs must return:

- `institution_rule_definition_allowed is True`
- `trading_layer_read_allowed is False`
- `signal_generation_allowed is False`
- `backtest_execution_allowed is False`

- [x] **Step 8: Run RED verification**

Run:

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_tdx_local_first_batch.TdxLocalFirstBatchTest.test_audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested_passes_explicit_rule_definition_only_gate -v
```

Expected: fail because the entry is not implemented or exported yet.

---

### Task 2: Implement P7d Audit

**Files:**

- Modify: `src/data_sources/tdx_local/first_batch.py`

- [x] **Step 1: Add public function**

Add:

```python
def audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested(
    p7c_contract_review_report: dict[str, Any] | None,
    t1_rule_draft_input: dict[str, Any] | None,
    price_limit_rule_draft_input: dict[str, Any] | None,
    suspension_resume_rule_draft_input: dict[str, Any] | None,
    explicit_open_gate_decision: dict[str, Any] | None,
    generated_at: str | None = None,
) -> dict[str, Any]:
```

- [x] **Step 2: Validate P7c contract review**

Require:

- `audit_id == "institution_rule_definition_contract_review_audit_v0.1"`
- `institution_rule_definition_contract_review_result == "pass"`
- `institution_rule_definition_contract_review_status == "ready_for_explicit_institution_rule_definition_open_gate_review"`
- trading / signal / backtest gates closed

Issue code:

`explicit_institution_rule_definition_open_gate_requires_p7c_contract_review_pass`

- [x] **Step 3: Validate contract-ready draft inputs**

For each required input:

- payload is dict
- `rule_draft_input_type` matches expected type
- `draft_input_only is True`
- `contract_review_status == "ready"`
- `definition_contract_fields` is a non-empty list
- `consumer_entrypoint == "institution_rule_definition"`
- trading / signal / backtest gates closed

- [x] **Step 4: Validate explicit open-gate decision**

Require:

- `gate_decision == "approve_institution_rule_definition_only"`
- `gate_scope == "institution_rule_definition_only"`
- non-empty `approved_by`
- non-empty `approval_evidence_refs`
- all no-trading/no-signal/no-backtest acknowledgements true

- [x] **Step 5: Validate forbidden fields**

Use the existing `_first_forbidden_output_field_present()` and `_strip_forbidden_fields()` helpers.

- [x] **Step 6: Return pass / blocked reports**

Pass report must open only:

- `institution_rule_definition_allowed=True`

Pass and blocked reports must keep:

- `trading_layer_read_allowed=False`
- `signal_generation_allowed=False`
- `backtest_execution_allowed=False`

---

### Task 3: Export Public Entry

**Files:**

- Modify: `src/data_sources/tdx_local/__init__.py`

- [x] Add `audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested` to the import list.
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

- P7d explicit open gate implemented.
- P7d pass means `institution_rule_definition_opened_for_rule_definition_only`.
- Formal institution rule definition may begin only as rule-definition-only work.
- Trading layer read, signal generation, and backtest execution remain closed.

---

### Completion Evidence

- RED verification failed first because the new P7d entry was not exported.
- Focused verification passed:

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_tdx_local_first_batch -v
```

Result: `80 tests OK`

- Full verification passed:

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest discover -s tests -v
```

Result: `271 tests OK`
