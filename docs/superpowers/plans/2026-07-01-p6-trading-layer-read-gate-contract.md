# P6 Trading Layer Read Gate Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and superpowers:executing-plans. Do not write production code until the RED tests in Task 1 have been added and observed failing.

**Goal:** Build the P6 read-only trading layer read gate / consumer contract audit that consumes P5 readiness proof plus Method/PM, Backtest Input, and execution constraint audit-only inputs, then reports readiness for contract review while keeping all downstream gates closed.

**Spec:** `docs/superpowers/specs/2026-07-01-p6-trading-layer-read-gate-contract-design.md`

**Architecture:** Add one explicit audit entry beside `audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested` in `src/data_sources/tdx_local/first_batch.py`. The function must not read raw market data, must not write files, must not open trading layer read, and must return pass / blocked reports only. Export the function from `src/data_sources/tdx_local/__init__.py`.

**Proposed entry:**

`audit_trading_layer_read_gate_contract_when_explicitly_requested`

**Tech Stack:** Python standard library, `unittest`, `json`, `pathlib`, temp directories.

---

### Task 1: Add P6 RED Tests

**Files:**

- Modify: `tests/test_tdx_local_first_batch.py`

- [ ] **Step 1: Import the new entry**

Add `audit_trading_layer_read_gate_contract_when_explicitly_requested` to the existing `data_sources.tdx_local` import block.

- [ ] **Step 2: Reuse existing formal candidate table helper**

Use `_write_single_formal_candidate_table()` to create the formal candidate table manifest, then call `audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested()` to create the P5 readiness report used by P6.

- [ ] **Step 3: Add small fixture helpers for P6 inputs**

Add helper payloads in the test class:

- `method_pm_bridge_gate` with `result == "pass"`.
- `backtest_input_gate` with `result == "pass"`.
- `execution_constraint_snapshot` or equivalent audit-only artifact with `audit_only == True`.

These helpers must not include signal, order, position, or backtest result fields.

- [ ] **Step 4: Add pass test**

Create `test_audit_trading_layer_read_gate_contract_when_explicitly_requested_passes_contract_inputs`.

Assertions:

- `result == "pass"`
- `audit_id == "trading_layer_read_gate_contract_audit_v0.1"`
- `trading_layer_read_gate_contract_audit_result == "pass"`
- `trading_layer_read_gate_contract_status == "ready_for_trading_layer_read_contract_review"`
- `candidate_table_trading_layer_readiness_audit_result == "pass"`
- `method_pm_gate_result == "pass"`
- `backtest_input_gate_result == "pass"`
- `execution_constraint_audit_only is True`
- `institution_rule_definition_allowed is False`
- `trading_layer_read_allowed is False`
- `signal_generation_allowed is False`
- `backtest_execution_allowed is False`
- `next_action == "action:review_trading_layer_read_gate_contract"`
- no forbidden field appears in the report payload.

- [ ] **Step 5: Add blocked tests**

Add focused blocked tests for:

- missing P5 readiness report;
- P5 readiness report not pass;
- missing Method/PM gate;
- Method/PM gate not pass;
- missing Backtest Input gate;
- Backtest Input gate not pass;
- missing execution constraint artifact;
- execution constraint artifact not audit-only.

Each blocked report must keep all downstream gates false.

- [ ] **Step 6: Add forbidden field test**

Create a test where one P6 input includes a forbidden field such as `buy_signal`, `trade_accept`, `target_position`, or `position_size`.

Assertions:

- `result == "blocked"`
- issue code includes `trading_layer_read_gate_forbidden_output_field_present`
- report payload does not echo the forbidden field name
- all downstream gates remain false.

- [ ] **Step 7: Add no-trading-layer-opened test**

Even with all valid inputs, assert:

- `institution_rule_definition_allowed is False`
- `trading_layer_read_allowed is False`
- `signal_generation_allowed is False`
- `backtest_execution_allowed is False`

- [ ] **Step 8: Run RED verification**

Run:

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_tdx_local_first_batch.TdxLocalFirstBatchTest.test_audit_trading_layer_read_gate_contract_when_explicitly_requested_passes_contract_inputs -v
```

Expected: fail because `audit_trading_layer_read_gate_contract_when_explicitly_requested` is not implemented or exported yet.

### Task 2: Implement P6 Audit

**Files:**

- Modify: `src/data_sources/tdx_local/first_batch.py`

- [ ] **Step 1: Add public function**

Add near the P5 readiness audit:

```python
def audit_trading_layer_read_gate_contract_when_explicitly_requested(
    p5_readiness_report: dict[str, Any] | None,
    formal_candidate_table_manifest: dict[str, Any] | None,
    method_pm_gate: dict[str, Any] | None,
    backtest_input_gate: dict[str, Any] | None,
    execution_constraint_artifact: dict[str, Any] | None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    ...
```

Implementation may adjust parameter names if existing local conventions point to a cleaner shape, but it must preserve the spec contract and the tests.

- [ ] **Step 2: Validate P5 readiness**

Require:

- `audit_id == "candidate_table_trading_layer_readiness_audit_v0.1"`
- `candidate_table_trading_layer_readiness_audit_result == "pass"`
- `candidate_table_trading_layer_readiness_status == "ready_for_trading_layer_read_gate_review"`
- all downstream gates are false.

Blocked issue code:

`trading_layer_read_gate_requires_p5_readiness_pass`

- [ ] **Step 3: Validate formal candidate table manifest**

Require formal candidate table proof remains formal target and closed gate:

- `candidate_table_update_target == "formal_data_root"`
- `trading_layer_read_allowed is False`

Blocked issue code:

`trading_layer_read_gate_requires_formal_candidate_table`

- [ ] **Step 4: Validate Method/PM and Backtest Input gates**

Require `result == "pass"` or the agreed equivalent readiness fields from the spec.

Blocked issue codes:

- `trading_layer_read_gate_requires_method_pm_gate_pass`
- `trading_layer_read_gate_requires_backtest_input_gate_pass`

- [ ] **Step 5: Validate execution constraint artifact**

Require audit-only semantics and block anything that acts like institution rules, signal, order, position, execution strategy, or backtest result.

Blocked issue code:

`trading_layer_read_gate_requires_execution_constraint_audit_only`

- [ ] **Step 6: Reject forbidden fields without echo**

Scan all input payloads for forbidden fields. If found, return only sanitized issue codes and do not echo the field names in `issues` or any report payload.

Blocked issue code:

`trading_layer_read_gate_forbidden_output_field_present`

- [ ] **Step 7: Return pass / blocked reports**

Pass report fields must match the P6 spec and keep:

- `institution_rule_definition_allowed=False`
- `trading_layer_read_allowed=False`
- `signal_generation_allowed=False`
- `backtest_execution_allowed=False`

Blocked reports must keep the same hard gates false.

### Task 3: Export P6 Entry

**Files:**

- Modify: `src/data_sources/tdx_local/__init__.py`

- [ ] Add `audit_trading_layer_read_gate_contract_when_explicitly_requested` to the import list.
- [ ] Add `"audit_trading_layer_read_gate_contract_when_explicitly_requested"` to `__all__`.

### Task 4: Focused Verification

Run:

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_tdx_local_first_batch -v
```

Expected: all first-batch tests pass.

If `src/ashare_intake_validator.py` is touched, also run:

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_ashare_intake_validator -v
```

### Task 5: Full Verification

Run:

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest discover -s tests -v
git diff --check
```

Expected:

- unittest reports all tests OK;
- `git diff --check` reports no whitespace errors.

### Task 6: Documentation Follow-Up

After implementation and verification only:

- update `docs/04_施工计划_当前进度版.md` with the new current system position;
- update `docs/06_Roadmap_TodoList_后续路线图与待办.md` to mark P6 implementation complete;
- update this daily status file with test output.

Do not do this documentation follow-up before the P6 implementation is actually complete.
