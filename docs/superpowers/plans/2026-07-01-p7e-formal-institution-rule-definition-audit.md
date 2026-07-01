# P7e Formal Institution Rule Definition Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the P7e formal institution rule definition audit so the system can review a formal rule definition input under the already-opened `rule-definition-only` gate without opening trading layer read, signal generation, or backtest execution.

**Architecture:** Add one explicit audit entry after `audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested` in `src/data_sources/tdx_local/first_batch.py`. The function will consume only in-memory payloads: one `P7d` pass report, three contract-ready reviewed draft inputs, and one formal institution rule definition input. It must return pass or blocked audit reports only, keep all downstream gates closed, and prepare the path for a future persistence-package layer rather than any trading behavior.

**Tech Stack:** Python standard library, `unittest`, `json`, temp directories.

---

### Task 1: Add P7e RED Tests

**Files:**
- Modify: `tests/test_tdx_local_first_batch.py`

- [ ] **Step 1: Import the new entry**

Add `audit_formal_institution_rule_definition_when_explicitly_requested` to the existing `data_sources.tdx_local` import block.

- [ ] **Step 2: Add helper payloads**

Add `_p7e_formal_rule_definition_inputs()` in the test class.

It should reuse `_p7d_open_gate_inputs()` and `audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested()` to create the `P7d` report, then return:

- `p7d_open_gate_report`
- three contract-ready reviewed draft inputs
- `formal_institution_rule_definition_input`

The formal definition input should include:

- `artifact_id == "formal_institution_rule_definition_input_v0.1"`
- `definition_scope == "institution_rule_definition_only"`
- `definition_input_status == "ready_for_audit"`
- `consumed_reviewed_draft_inputs == ["t1", "price_limit", "suspension_resume"]`
- `field_contract_status == "complete"`
- `boundary_review_status == "clean"`
- non-empty `evidence_refs`
- non-empty `formal_definition_fields`

- [ ] **Step 3: Add pass test**

Create `test_audit_formal_institution_rule_definition_when_explicitly_requested_passes_rule_definition_only_input`.

Assert:

- `result == "pass"`
- `audit_id == "formal_institution_rule_definition_audit_v0.1"`
- `formal_institution_rule_definition_result == "pass"`
- `formal_institution_rule_definition_status == "formal_institution_rule_definition_audited_for_rule_definition_only"`
- `p7d_open_gate_result == "pass"`
- `consumed_reviewed_draft_inputs == ["t1", "price_limit", "suspension_resume"]`
- `formal_institution_rule_definition_field_contract_status == "complete"`
- `formal_institution_rule_definition_boundary_status == "clean"`
- `formal_institution_rule_definition_evidence_status == "ready"`
- `institution_rule_definition_allowed is True`
- `trading_layer_read_allowed is False`
- `signal_generation_allowed is False`
- `backtest_execution_allowed is False`
- `next_action == "action:prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested"`

- [ ] **Step 4: Add blocked tests**

Create `test_audit_formal_institution_rule_definition_when_explicitly_requested_blocks_missing_or_failed_inputs`.

Cover:

- missing `P7d` open gate report
- failed `P7d` open gate report
- missing `t1` reviewed draft
- missing `price_limit` reviewed draft
- missing `suspension_resume` reviewed draft
- missing formal institution rule definition input
- definition input without full `consumed_reviewed_draft_inputs`
- definition input with `field_contract_status != "complete"`

- [ ] **Step 5: Add forbidden-field test**

Create `test_audit_formal_institution_rule_definition_when_explicitly_requested_blocks_forbidden_field_without_echo`.

Inject one forbidden field such as `signal_decision`.

- [ ] **Step 6: Add hard-gate test**

Create `test_audit_formal_institution_rule_definition_when_explicitly_requested_keeps_downstream_hard_gates_false`.

Pass-valid inputs must return:

- `institution_rule_definition_allowed is True`
- `trading_layer_read_allowed is False`
- `signal_generation_allowed is False`
- `backtest_execution_allowed is False`

- [ ] **Step 7: Run RED verification**

Run:

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_tdx_local_first_batch.TdxLocalFirstBatchTest.test_audit_formal_institution_rule_definition_when_explicitly_requested_passes_rule_definition_only_input -v
```

Expected: fail because the new entry is not implemented or exported yet.

### Task 2: Implement P7e Audit

**Files:**
- Modify: `src/data_sources/tdx_local/first_batch.py`

- [ ] **Step 1: Add public function**

Add:

```python
def audit_formal_institution_rule_definition_when_explicitly_requested(
    p7d_open_gate_report: dict[str, Any] | None,
    t1_rule_draft_input: dict[str, Any] | None,
    price_limit_rule_draft_input: dict[str, Any] | None,
    suspension_resume_rule_draft_input: dict[str, Any] | None,
    formal_institution_rule_definition_input: dict[str, Any] | None,
    generated_at: str | None = None,
) -> dict[str, Any]:
```

- [ ] **Step 2: Validate `P7d` open gate**

Require:

- `audit_id == "explicit_institution_rule_definition_open_gate_audit_v0.1"`
- `explicit_institution_rule_definition_open_gate_result == "pass"`
- `explicit_institution_rule_definition_open_gate_status == "institution_rule_definition_opened_for_rule_definition_only"`
- downstream gates remain closed

Issue code:

`formal_institution_rule_definition_requires_p7d_open_gate_pass`

- [ ] **Step 3: Validate reviewed draft inputs**

For each required input:

- payload is dict
- `rule_draft_input_type` matches expected type
- `draft_input_only is True`
- `contract_review_status == "ready"`
- `definition_contract_fields` is a non-empty list
- `consumer_entrypoint == "institution_rule_definition"`
- downstream gates remain closed

- [ ] **Step 4: Validate formal definition input**

Require:

- `artifact_id == "formal_institution_rule_definition_input_v0.1"`
- `definition_scope == "institution_rule_definition_only"`
- `definition_input_status == "ready_for_audit"`
- `consumed_reviewed_draft_inputs == ["t1", "price_limit", "suspension_resume"]`
- `field_contract_status == "complete"`
- `boundary_review_status == "clean"`
- `evidence_refs` is a non-empty list
- `formal_definition_fields` is a non-empty list
- downstream gates remain closed

- [ ] **Step 5: Validate forbidden fields**

Use the existing forbidden-field helpers already used by P7 phases.

- [ ] **Step 6: Return pass / blocked reports**

Pass report must keep:

- `institution_rule_definition_allowed=True`
- `trading_layer_read_allowed=False`
- `signal_generation_allowed=False`
- `backtest_execution_allowed=False`

Blocked report must keep:

- `institution_rule_definition_allowed=False`
- `trading_layer_read_allowed=False`
- `signal_generation_allowed=False`
- `backtest_execution_allowed=False`

### Task 3: Export Public Entry

**Files:**
- Modify: `src/data_sources/tdx_local/__init__.py`

- [ ] Add `audit_formal_institution_rule_definition_when_explicitly_requested` to the import list.
- [ ] Add it to `__all__`.

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

### Task 5: Documentation Closeout

**Files:**
- Modify: `docs/06_Roadmap_TodoList_后续路线图与待办.md`
- Modify: `docs/daily-status/2026-07-01-下一步工作计划.md`
- Modify: `docs/04_施工计划_当前进度版.md`

Update only after implementation and tests pass:

- P7e formal institution rule definition audit implemented.
- P7e pass means `formal_institution_rule_definition_audited_for_rule_definition_only`.
- Trading layer read, signal generation, and backtest execution remain closed.
- Future work may continue only through a separate persistence/package gate or another explicit downstream gate.
