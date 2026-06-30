# P4c Formal Candidate Table Write Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the P4c explicit formal data root candidate table writer that consumes a P4b staging candidate table manifest and writes a formal JSONL candidate table with human confirmation, backup, rollback, and all downstream gates closed.

**Architecture:** Add one explicit entry in `src/data_sources/tdx_local/first_batch.py` after the P4b staging writer. The function validates the P4b manifest and draft rows, requires `confirm_formal_write=True`, backs up any existing formal table directory, writes a temp directory, then renames it into `<formal_data_root>/ashare/candidate-table-v0.1`. Tests use temporary directories only and do not touch real `Z:\asteria-trading-labs-data`.

**Tech Stack:** Python standard library, `pathlib`, `json`, `shutil`, `unittest`.

---

### Task 1: Add P4c RED Tests

**Files:**
- Modify: `tests/test_tdx_local_first_batch.py`

- [ ] **Step 1: Import the new entry**

Add `write_candidate_table_to_formal_data_root_when_explicitly_confirmed` beside the P4b import:

```python
from data_sources.tdx_local import (
    ...
    update_candidate_table_from_staged_qualification_records_when_explicitly_requested,
    write_candidate_table_to_formal_data_root_when_explicitly_confirmed,
    write_qualification_records_to_staging_when_explicitly_requested,
)
```

- [ ] **Step 2: Add a helper that produces a valid P4b staging manifest**

Add this helper beside `_write_single_staged_qualification_record`:

```python
    def _write_single_staged_candidate_table(self, root: Path) -> Path:
        qualification_manifest = self._write_single_staged_qualification_record(root / "qualification-staging")
        report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
            qualification_record_staging_manifest_path=qualification_manifest,
            candidate_table_staging_root=root / "candidate-staging",
            generated_at="2026-06-30T23:00:00+08:00",
        )
        self.assertEqual(report["result"], "pass")
        return root / "candidate-staging" / "candidate-table-v0.1" / "manifest.json"
```

- [ ] **Step 3: Add pass test**

```python
    def test_write_candidate_table_to_formal_data_root_when_explicitly_confirmed_writes_formal_jsonl_with_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging_manifest = self._write_single_staged_candidate_table(root / "staging")
            formal_data_root = root / "formal-data"
            live_root = formal_data_root / "ashare" / "candidate-table-v0.1"
            live_root.mkdir(parents=True)
            (live_root / "candidate-table.jsonl").write_text('{"old": true}\n', encoding="utf-8")
            (live_root / "manifest.json").write_text('{"manifest_id": "old"}\n', encoding="utf-8")

            report = write_candidate_table_to_formal_data_root_when_explicitly_confirmed(
                candidate_table_staging_manifest_path=staging_manifest,
                formal_data_root=formal_data_root,
                confirm_formal_write=True,
                generated_at="2026-06-30T23:10:00+08:00",
            )
            manifest = json.loads((live_root / "manifest.json").read_text(encoding="utf-8"))
            rows = [
                json.loads(line)
                for line in (live_root / "candidate-table.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            backups = list((formal_data_root / "ashare").glob("candidate-table-v0.1.backup.*"))
            tmp_exists = (formal_data_root / "ashare" / "candidate-table-v0.1.__tmp__").exists()

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["candidate_table_update_performed"])
        self.assertEqual(report["candidate_table_update_target"], "formal_data_root")
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["next_action"], "action:review_formal_candidate_table_before_trading_layer_audit")
        self.assertEqual(manifest["manifest_id"], "candidate_table_formal_manifest_v0.1")
        self.assertEqual(manifest["candidate_table_row_count"], 1)
        self.assertEqual(manifest["candidate_table_file"], "candidate-table.jsonl")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["candidate_table_update_target"], "formal_data_root")
        self.assertTrue(rows[0]["candidate_table_update_performed"])
        self.assertFalse(rows[0]["trading_layer_read_allowed"])
        self.assertEqual(len(backups), 1)
        self.assertTrue((backups[0] / "candidate-table.jsonl").exists())
        self.assertFalse(tmp_exists)
        payload = json.dumps({"report": report, "manifest": manifest, "rows": rows}, ensure_ascii=False)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))
```

- [ ] **Step 4: Add missing confirmation test**

```python
    def test_write_candidate_table_to_formal_data_root_when_explicitly_confirmed_blocks_without_confirm_before_reading_staging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_manifest = root / "missing" / "manifest.json"
            formal_data_root = root / "formal-data"

            report = write_candidate_table_to_formal_data_root_when_explicitly_confirmed(
                candidate_table_staging_manifest_path=missing_manifest,
                formal_data_root=formal_data_root,
                confirm_formal_write=False,
                generated_at="2026-06-30T23:15:00+08:00",
            )

            self.assertFalse((formal_data_root / "ashare").exists())

        self.assertEqual(report["result"], "blocked")
        self.assertIn("confirm_formal_write_required", report["issues"])
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertFalse(report["trading_layer_read_allowed"])
```

- [ ] **Step 5: Add invalid manifest test**

```python
    def test_write_candidate_table_to_formal_data_root_when_explicitly_confirmed_blocks_bad_manifest_without_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging_manifest = root / "candidate-staging" / "candidate-table-v0.1" / "manifest.json"
            staging_manifest.parent.mkdir(parents=True)
            staging_manifest.write_text(json.dumps({"manifest_id": "bad"}, ensure_ascii=False), encoding="utf-8")
            formal_data_root = root / "formal-data"

            report = write_candidate_table_to_formal_data_root_when_explicitly_confirmed(
                candidate_table_staging_manifest_path=staging_manifest,
                formal_data_root=formal_data_root,
                confirm_formal_write=True,
                generated_at="2026-06-30T23:20:00+08:00",
            )

            self.assertFalse((formal_data_root / "ashare").exists())

        self.assertEqual(report["result"], "blocked")
        self.assertIn("candidate_table_staging_manifest_invalid", report["issues"])
        self.assertFalse(report["candidate_table_update_performed"])
```

- [ ] **Step 6: Add forbidden field test**

```python
    def test_write_candidate_table_to_formal_data_root_when_explicitly_confirmed_blocks_forbidden_staging_row_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging_manifest = self._write_single_staged_candidate_table(root / "staging")
            table_root = staging_manifest.parent
            rows = [
                json.loads(line)
                for line in (table_root / "candidate-table-draft.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            rows[0]["buy_signal"] = True
            (table_root / "candidate-table-draft.jsonl").write_text(
                "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
                encoding="utf-8",
            )
            formal_data_root = root / "formal-data"

            report = write_candidate_table_to_formal_data_root_when_explicitly_confirmed(
                candidate_table_staging_manifest_path=staging_manifest,
                formal_data_root=formal_data_root,
                confirm_formal_write=True,
                generated_at="2026-06-30T23:25:00+08:00",
            )

            self.assertFalse((formal_data_root / "ashare").exists())

        self.assertEqual(report["result"], "blocked")
        self.assertIn("candidate_table_formal_forbidden_output_field_present", report["issues"])
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("buy_signal", payload)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))
```

- [ ] **Step 7: Add rollback test**

```python
    def test_write_candidate_table_to_formal_data_root_when_explicitly_confirmed_rolls_back_when_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging_manifest = self._write_single_staged_candidate_table(root / "staging")
            formal_data_root = root / "formal-data"
            live_root = formal_data_root / "ashare" / "candidate-table-v0.1"
            live_root.mkdir(parents=True)
            (live_root / "candidate-table.jsonl").write_text('{"old": true}\n', encoding="utf-8")
            (live_root / "manifest.json").write_text('{"manifest_id": "old"}\n', encoding="utf-8")

            report = write_candidate_table_to_formal_data_root_when_explicitly_confirmed(
                candidate_table_staging_manifest_path=staging_manifest,
                formal_data_root=formal_data_root,
                confirm_formal_write=True,
                generated_at="2026-06-30T23:30:00+08:00",
                simulate_failure_step="after_backup",
            )
            old_payload = (live_root / "candidate-table.jsonl").read_text(encoding="utf-8")
            backups = list((formal_data_root / "ashare").glob("candidate-table-v0.1.backup.*"))
            tmp_exists = (formal_data_root / "ashare" / "candidate-table-v0.1.__tmp__").exists()

        self.assertEqual(report["result"], "blocked")
        self.assertIn("candidate_table_formal_write_failed_after_backup", report["issues"])
        self.assertEqual(old_payload, '{"old": true}\n')
        self.assertEqual(len(backups), 1)
        self.assertTrue((backups[0] / "candidate-table.jsonl").exists())
        self.assertFalse(tmp_exists)
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertFalse(report["trading_layer_read_allowed"])
```

- [ ] **Step 8: Run RED verification**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_tdx_local_first_batch.TdxLocalFirstBatchTest.test_write_candidate_table_to_formal_data_root_when_explicitly_confirmed_writes_formal_jsonl_with_backup -v
```

Expected: fail with `ImportError` or missing function name before implementation.

### Task 2: Implement P4c Writer

**Files:**
- Modify: `src/data_sources/tdx_local/first_batch.py`

- [ ] **Step 1: Add public function**

Add `write_candidate_table_to_formal_data_root_when_explicitly_confirmed(...)` after the P4b function. Signature:

```python
def write_candidate_table_to_formal_data_root_when_explicitly_confirmed(
    candidate_table_staging_manifest_path: str | Path,
    formal_data_root: str | Path,
    confirm_formal_write: bool = False,
    generated_at: str | None = None,
    simulate_failure_step: str | None = None,
) -> dict[str, Any]:
```

Behavior:
- If `confirm_formal_write is not True`, return blocked without reading staging.
- Validate staging manifest.
- Read non-empty `candidate-table-draft.jsonl`.
- Strip/validate forbidden fields.
- Convert row target fields from `staging` to `formal_data_root`.
- Backup existing live directory before temp write.
- Write temp `candidate-table.jsonl`, then temp `manifest.json`.
- Replace live directory.
- Return pass with all downstream gates false.

- [ ] **Step 2: Add helpers**

Add helpers near P4b helper functions:

```python
def _validate_candidate_table_staging_manifest(manifest: dict[str, Any], issues: list[str]) -> None:
    ...

def _candidate_table_formal_row(row: dict[str, Any]) -> dict[str, Any]:
    ...

def _candidate_table_formal_manifest(staging_manifest: dict[str, Any], rows: list[dict[str, Any]], generated_at: str, backup_path: str | None) -> dict[str, Any]:
    ...

def _candidate_table_formal_blocked_report(generated_at: str, issues: list[str], backup_path: str | None = None) -> dict[str, Any]:
    ...

def _backup_existing_candidate_table_dir(table_root: Path, generated_at: str) -> Path | None:
    ...

def _replace_candidate_table_dir(tmp_root: Path, table_root: Path) -> None:
    ...
```

- [ ] **Step 3: Run focused tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_tdx_local_first_batch -v
```

Expected: all first-batch tests pass.

### Task 3: Export Entry and Update Docs

**Files:**
- Modify: `src/data_sources/tdx_local/__init__.py`
- Modify: `docs/04_施工计划_当前进度版.md`
- Modify: `docs/06_Roadmap_TodoList_后续路线图与待办.md`

- [ ] **Step 1: Export function**

Add `write_candidate_table_to_formal_data_root_when_explicitly_confirmed` to the import list and `__all__`.

- [ ] **Step 2: Update construction plan**

Record:
- current position becomes `formal_candidate_table_update_performed`;
- P4c writes formal candidate table JSONL under data root when explicitly confirmed;
- backup is created for existing formal table directory;
- trading layer, signal, and backtest gates remain closed.

- [ ] **Step 3: Update Roadmap**

Mark P4c implementation complete, keep P5 trading layer readiness audit pending.

### Task 4: Final Verification and Commit

**Files:**
- All modified P4c files.

- [ ] **Step 1: Run full verification**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests
git diff --check
```

Expected:
- unittest reports all tests OK;
- `git diff --check` has no whitespace errors.

- [ ] **Step 2: Commit and push**

Run:

```powershell
git add src/data_sources/tdx_local/first_batch.py src/data_sources/tdx_local/__init__.py tests/test_tdx_local_first_batch.py docs/04_施工计划_当前进度版.md docs/06_Roadmap_TodoList_后续路线图与待办.md docs/superpowers/plans/2026-06-30-p4c-formal-candidate-table-write.md
git commit -m "Add formal candidate table data root writer"
git push
```
