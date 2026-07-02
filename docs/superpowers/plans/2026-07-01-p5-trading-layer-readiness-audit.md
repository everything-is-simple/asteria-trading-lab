# P5 Trading Layer Readiness Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the P5 read-only trading layer readiness audit that consumes the formal candidate table manifest/JSONL and confirms readiness for a future trading-layer read gate while keeping all downstream gates closed.

**Architecture:** Add one explicit audit entry near the P4c formal candidate table writer in `src/data_sources/tdx_local/first_batch.py`. The function reads only `manifest.json` and `candidate-table.jsonl`, validates formal-table shape, forbidden fields, row counts, duplicate row ids, and closed hard gates, then returns a pass or blocked report without writing files. Export the function from `src/data_sources/tdx_local/__init__.py`.

**Tech Stack:** Python standard library, `pathlib`, `json`, `unittest`.

---

### Task 1: Add P5 RED Tests

**Files:**
- Modify: `tests/test_tdx_local_first_batch.py`

- [ ] **Step 1: Import the new entry**

Add `audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested` beside the P4c import:

```python
from data_sources.tdx_local import (
    ...
    audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested,
    ...
    write_candidate_table_to_formal_data_root_when_explicitly_confirmed,
)
```

- [ ] **Step 2: Add a helper that produces a valid P4c formal manifest**

Add this helper beside `_write_single_staged_candidate_table`:

```python
    def _write_single_formal_candidate_table(self, root: Path) -> Path:
        staging_manifest = self._write_single_staged_candidate_table(root / "staging")
        formal_data_root = root / "formal-data"
        report = write_candidate_table_to_formal_data_root_when_explicitly_confirmed(
            candidate_table_staging_manifest_path=staging_manifest,
            formal_data_root=formal_data_root,
            confirm_formal_write=True,
            generated_at="2026-07-01T09:00:00+08:00",
        )
        self.assertEqual(report["result"], "pass")
        return formal_data_root / "ashare" / "candidate-table-v0.1" / "manifest.json"
```

- [ ] **Step 3: Add pass test**

```python
    def test_audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested_passes_formal_candidate_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_single_formal_candidate_table(root)

            report = audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested(
                formal_candidate_table_manifest_path=manifest_path,
                generated_at="2026-07-01T09:10:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["audit_id"], "candidate_table_trading_layer_readiness_audit_v0.1")
        self.assertEqual(report["candidate_table_trading_layer_readiness_audit_result"], "pass")
        self.assertTrue(report["candidate_table_trading_layer_readiness_checked"])
        self.assertEqual(
            report["candidate_table_trading_layer_readiness_status"],
            "ready_for_trading_layer_read_gate_review",
        )
        self.assertEqual(report["candidate_table_row_count"], 1)
        self.assertTrue(report["candidate_table_update_performed"])
        self.assertEqual(report["candidate_table_update_target"], "formal_data_root")
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(
            report["next_action"],
            "action:write_p5_implementation_plan_for_trading_layer_readiness_audit",
        )
        payload = json.dumps(report, ensure_ascii=False)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))
```

- [ ] **Step 4: Add blocked missing manifest test**

```python
    def test_audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested_blocks_missing_manifest_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_manifest = root / "formal-data" / "ashare" / "candidate-table-v0.1" / "manifest.json"

            report = audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested(
                formal_candidate_table_manifest_path=missing_manifest,
                generated_at="2026-07-01T09:20:00+08:00",
            )

            self.assertFalse((root / "formal-data").exists())

        self.assertEqual(report["result"], "blocked")
        self.assertIn("candidate_table_formal_manifest_missing", report["issues"])
        self.assertFalse(report["candidate_table_trading_layer_readiness_checked"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
```

- [ ] **Step 5: Add forbidden field test**

```python
    def test_audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested_blocks_forbidden_jsonl_field_without_echo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_single_formal_candidate_table(root)
            table_path = manifest_path.parent / "candidate-table.jsonl"
            rows = [
                json.loads(line)
                for line in table_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            rows[0]["buy_signal"] = True
            table_path.write_text(
                "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
                encoding="utf-8",
            )

            report = audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested(
                formal_candidate_table_manifest_path=manifest_path,
                generated_at="2026-07-01T09:30:00+08:00",
            )

        self.assertEqual(report["result"], "blocked")
        self.assertIn("candidate_table_trading_readiness_forbidden_output_field_present", report["issues"])
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("buy_signal", payload)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
```

- [ ] **Step 6: Add does-not-open-trading-layer test**

```python
    def test_audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested_never_opens_downstream_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_single_formal_candidate_table(root)

            report = audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested(
                formal_candidate_table_manifest_path=manifest_path,
                generated_at="2026-07-01T09:40:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
```

- [ ] **Step 7: Run RED verification**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_tdx_local_first_batch.TdxLocalFirstBatchTest.test_audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested_passes_formal_candidate_table -v
```

Expected: fail with `ImportError` because the function is not exported yet.

### Task 2: Implement P5 Readiness Audit

**Files:**
- Modify: `src/data_sources/tdx_local/first_batch.py`

- [ ] **Step 1: Add public function**

Add after `write_candidate_table_to_formal_data_root_when_explicitly_confirmed`:

```python
def audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested(
    formal_candidate_table_manifest_path: str | Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    ...
```

- [ ] **Step 2: Add validation behavior**

The function must:

- read only the passed manifest and the manifest-referenced `candidate-table.jsonl`;
- block missing or invalid manifest with `candidate_table_formal_manifest_missing` or `candidate_table_formal_manifest_invalid`;
- reject manifest `candidate_table_file` values that are absolute paths, contain `..`, or point outside the manifest directory;
- require formal manifest fields listed in the spec;
- require non-empty JSONL rows and matching row count;
- require unique `candidate_table_row_id`;
- require `candidate_table_row_id`, `qualification_record_id`, and `ts_code`;
- require row target `formal_data_root`;
- require all hard gates false;
- block forbidden fields without echoing the field names in the report.

- [ ] **Step 3: Add helpers**

Add helpers near the P4c helpers:

```python
def _candidate_table_trading_readiness_blocked_report(
    generated_at: str,
    issues: list[str],
) -> dict[str, Any]:
    ...

def _validate_candidate_table_formal_manifest_for_trading_readiness(
    manifest: dict[str, Any],
    issues: list[str],
) -> None:
    ...

def _candidate_table_jsonl_path_from_manifest(manifest_path: Path, manifest: dict[str, Any], issues: list[str]) -> Path:
    ...

def _validate_candidate_table_formal_rows_for_trading_readiness(
    rows: list[dict[str, Any]],
    expected_count: int,
    issues: list[str],
) -> None:
    ...
```

- [ ] **Step 4: Run GREEN focused tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_tdx_local_first_batch -v
```

Expected: all first-batch tests pass.

### Task 3: Export P5 Entry

**Files:**
- Modify: `src/data_sources/tdx_local/__init__.py`

- [ ] **Step 1: Add import**

Add `audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested` to the `from .first_batch import (...)` list.

- [ ] **Step 2: Add `__all__` entry**

Add `"audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested"` to `__all__`.

### Task 4: Final Verification And Commit

**Files:**
- `docs/superpowers/specs/2026-07-01-p5-trading-layer-readiness-audit-design.md`
- `docs/superpowers/plans/2026-07-01-p5-trading-layer-readiness-audit.md`
- `tests/test_tdx_local_first_batch.py`
- `src/data_sources/tdx_local/first_batch.py`
- `src/data_sources/tdx_local/__init__.py`

- [ ] **Step 1: Run full verification**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests
git diff --check
```

Expected:

- unittest reports all tests OK;
- `git diff --check` reports no whitespace errors.

- [ ] **Step 2: Commit**

Run:

```powershell
git add -- docs/superpowers/specs/2026-07-01-p5-trading-layer-readiness-audit-design.md docs/superpowers/plans/2026-07-01-p5-trading-layer-readiness-audit.md tests/test_tdx_local_first_batch.py src/data_sources/tdx_local/first_batch.py src/data_sources/tdx_local/__init__.py
git commit -m "Add trading layer readiness audit"
```

- [ ] **Step 3: Push**

Run:

```powershell
git push
```

If push fails with the existing GitHub TLS handshake problem, keep the local commits intact and report the exact push error.
