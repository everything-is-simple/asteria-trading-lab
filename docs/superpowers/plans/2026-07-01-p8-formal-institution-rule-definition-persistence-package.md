# P8 Formal Institution Rule Definition Persistence Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the P8 formal institution rule definition persistence package preparation gate without writing files or opening trading layer read, signal generation, or backtest execution.

**Architecture:** Add one explicit package preparation entry after `audit_formal_institution_rule_definition_when_explicitly_requested` in `src/data_sources/tdx_local/first_batch.py`. The function consumes only in-memory payloads: one P7e pass report and one formal institution rule definition payload. It returns pass or blocked audit reports only, strips forbidden fields, keeps downstream gates closed, and prepares a future write-audit gate rather than any real persistence.

**Tech Stack:** Python standard library, `unittest`, existing `data_sources.tdx_local.first_batch` helpers.

---

### Task 1: Add P8 RED Tests

**Files:**
- Modify: `tests/test_tdx_local_first_batch.py`

- [ ] **Step 1: Import the new entry**

Add `prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested` to the existing `data_sources.tdx_local` import block.

- [ ] **Step 2: Add helper payloads**

Add `_p8_formal_rule_definition_persistence_package_inputs()` in `TdxLocalFirstBatchTest`:

```python
def _p8_formal_rule_definition_persistence_package_inputs(self, root: Path) -> dict[str, dict]:
    p7e_inputs = self._p7e_formal_rule_definition_inputs(root)
    p7e_report = audit_formal_institution_rule_definition_when_explicitly_requested(
        **p7e_inputs,
        generated_at="2026-07-01T16:00:00+08:00",
    )
    self.assertEqual(p7e_report["result"], "pass")
    return {
        "p7e_formal_rule_definition_report": p7e_report,
        "formal_institution_rule_definition_payload": p7e_inputs["formal_institution_rule_definition_input"],
    }
```

- [ ] **Step 3: Add pass test**

Create `test_prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested_passes_package_ready_payload`.

Expected assertions:

```python
self.assertEqual(report["result"], "pass")
self.assertEqual(report["audit_id"], "formal_institution_rule_definition_persistence_package_v0.1")
self.assertEqual(report["formal_institution_rule_definition_persistence_package_result"], "pass")
self.assertEqual(
    report["formal_institution_rule_definition_persistence_package_status"],
    "formal_institution_rule_definition_persistence_package_prepared",
)
self.assertTrue(report["formal_institution_rule_definition_persistence_package_prepared"])
self.assertFalse(report["formal_institution_rule_definition_persistence_performed"])
self.assertEqual(report["source_formal_institution_rule_definition_result"], "pass")
self.assertEqual(report["packaged_rule_definition_inputs"], ["t1", "price_limit", "suspension_resume"])
self.assertEqual(report["package_field_contract_status"], "complete")
self.assertEqual(report["package_boundary_status"], "clean")
self.assertEqual(report["package_evidence_status"], "ready")
self.assertTrue(report["institution_rule_definition_allowed"])
self.assertFalse(report["trading_layer_read_allowed"])
self.assertFalse(report["signal_generation_allowed"])
self.assertFalse(report["backtest_execution_allowed"])
self.assertEqual(
    report["next_action"],
    "action:audit_formal_institution_rule_definition_write_when_explicitly_requested",
)
payload = json.dumps(report, ensure_ascii=False)
self.assertFalse(any(field in payload for field in P7_FORBIDDEN_FIELDS))
```

- [ ] **Step 4: Add blocked tests**

Create `test_prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested_blocks_missing_or_failed_inputs`.

Cover these cases:

```python
cases = [
    (
        "p7e_formal_rule_definition_report",
        None,
        "formal_institution_rule_definition_persistence_package_requires_p7e_pass",
    ),
    (
        "p7e_formal_rule_definition_report",
        {"formal_institution_rule_definition_result": "blocked"},
        "formal_institution_rule_definition_persistence_package_requires_p7e_pass",
    ),
    (
        "formal_institution_rule_definition_payload",
        None,
        "formal_institution_rule_definition_persistence_package_requires_definition_payload",
    ),
    (
        "formal_institution_rule_definition_payload",
        {"consumed_reviewed_draft_inputs": ["t1", "price_limit"]},
        "formal_institution_rule_definition_persistence_package_requires_full_reviewed_draft_coverage",
    ),
    (
        "formal_institution_rule_definition_payload",
        {"field_contract_status": "incomplete"},
        "formal_institution_rule_definition_persistence_package_requires_complete_field_contract",
    ),
]
```

Each report must be blocked and keep all hard gates closed.

- [ ] **Step 5: Add forbidden-field test**

Create `test_prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested_blocks_forbidden_field_without_echo`.

Inject `position_size = 1.0` into `formal_institution_rule_definition_payload`.

Assert issue:

```python
"formal_institution_rule_definition_persistence_package_forbidden_output_field_present"
```

Assert the forbidden field is not present in serialized output.

- [ ] **Step 6: Add hard-gate test**

Create `test_prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested_keeps_downstream_hard_gates_false`.

Pass-valid inputs must return `institution_rule_definition_allowed is True` and all downstream hard gates false.

- [ ] **Step 7: Run RED verification**

Run:

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; python -B -m unittest tests.test_tdx_local_first_batch.TdxLocalFirstBatchTest.test_prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested_passes_package_ready_payload -v
```

Expected: FAIL with import error or missing function before implementation.

### Task 2: Implement P8 Package Preparation

**Files:**
- Modify: `src/data_sources/tdx_local/first_batch.py`

- [ ] **Step 1: Add public function**

Add:

```python
def prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested(
    p7e_formal_rule_definition_report: dict[str, Any] | None,
    formal_institution_rule_definition_payload: dict[str, Any] | None,
    generated_at: str | None = None,
) -> dict[str, Any]:
```

- [ ] **Step 2: Validate P7e pass report**

Require:

```python
audit_id == "formal_institution_rule_definition_audit_v0.1"
formal_institution_rule_definition_result == "pass"
formal_institution_rule_definition_status == "formal_institution_rule_definition_audited_for_rule_definition_only"
institution_rule_definition_allowed is True
trading_layer_read_allowed is False
signal_generation_allowed is False
backtest_execution_allowed is False
```

Issue code:

```python
"formal_institution_rule_definition_persistence_package_requires_p7e_pass"
```

- [ ] **Step 3: Validate formal definition payload**

Require:

```python
artifact_id == "formal_institution_rule_definition_input_v0.1"
definition_scope == "institution_rule_definition_only"
definition_input_status == "ready_for_audit"
consumed_reviewed_draft_inputs == ["t1", "price_limit", "suspension_resume"]
field_contract_status == "complete"
boundary_review_status == "clean"
evidence_refs is a non-empty list
formal_definition_fields is a non-empty list
institution_rule_definition_allowed is True
trading_layer_read_allowed is False
signal_generation_allowed is False
backtest_execution_allowed is False
```

- [ ] **Step 4: Validate forbidden fields**

Use `_first_forbidden_output_field_present` on both inputs.

Issue code:

```python
"formal_institution_rule_definition_persistence_package_forbidden_output_field_present"
```

- [ ] **Step 5: Return pass / blocked reports**

Pass report must include:

```python
{
    "result": "pass",
    "generated_at": generated_at_value,
    "research_only": True,
    "audit_id": "formal_institution_rule_definition_persistence_package_v0.1",
    "formal_institution_rule_definition_persistence_package_result": "pass",
    "formal_institution_rule_definition_persistence_package_status": (
        "formal_institution_rule_definition_persistence_package_prepared"
    ),
    "formal_institution_rule_definition_persistence_package_prepared": True,
    "formal_institution_rule_definition_persistence_performed": False,
    "source_formal_institution_rule_definition_result": "pass",
    "packaged_rule_definition_inputs": ["t1", "price_limit", "suspension_resume"],
    "package_field_contract_status": "complete",
    "package_boundary_status": "clean",
    "package_evidence_status": "ready",
    "institution_rule_definition_allowed": True,
    "trading_layer_read_allowed": False,
    "signal_generation_allowed": False,
    "backtest_execution_allowed": False,
    "next_action": "action:audit_formal_institution_rule_definition_write_when_explicitly_requested",
}
```

Blocked report must include:

```python
{
    "result": "blocked",
    "generated_at": generated_at,
    "research_only": True,
    "audit_id": "formal_institution_rule_definition_persistence_package_v0.1",
    "formal_institution_rule_definition_persistence_package_result": "blocked",
    "formal_institution_rule_definition_persistence_package_status": (
        "blocked_before_formal_institution_rule_definition_persistence_package_prepared"
    ),
    "formal_institution_rule_definition_persistence_package_prepared": False,
    "formal_institution_rule_definition_persistence_performed": False,
    "issues": sorted(set(issues)),
    "packaged_rule_definition_inputs": ["t1", "price_limit", "suspension_resume"],
    "institution_rule_definition_allowed": False,
    "trading_layer_read_allowed": False,
    "signal_generation_allowed": False,
    "backtest_execution_allowed": False,
    "next_action": "action:repair_formal_institution_rule_definition_persistence_package_inputs",
}
```

Wrap both reports with `_strip_forbidden_fields`.

### Task 3: Export Public Entry

**Files:**
- Modify: `src/data_sources/tdx_local/__init__.py`

- [ ] Add `prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested` to the import list.
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
- Modify: `docs/04_施工计划_当前进度版.md`
- Modify: `docs/06_Roadmap_TodoList_后续路线图与待办.md`
- Modify: `docs/daily-status/2026-07-01-下一步工作计划.md`

Update only after implementation and tests pass:

- P8 formal institution rule definition persistence package implemented.
- P8 pass means `formal_institution_rule_definition_persistence_package_prepared`.
- `formal_institution_rule_definition_persistence_performed=False`.
- Trading layer read, signal generation, and backtest execution remain closed.
- Future work may continue only through a separate formal write audit gate.

### Self-Review

- Spec coverage: The plan covers spec, tests, implementation, export, verification, and docs.
- Placeholder scan: No TBD/TODO placeholders are present.
- Type consistency: Function names, report keys, status values, and issue codes match the P8 spec.
