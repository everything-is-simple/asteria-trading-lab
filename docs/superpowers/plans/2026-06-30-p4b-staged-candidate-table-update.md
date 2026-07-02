# P4b Staged Candidate Table Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the P4b explicit staged candidate table writer that reads P4a staged qualification records and writes a staged JSONL candidate table draft without touching formal `data_root`.

**Architecture:** Add one explicit entry in `src/data_sources/tdx_local/first_batch.py` after the P4a staging writer. The function reads a P4a `qualification-records-v0.1/manifest.json`, validates every referenced record, converts records into JSONL candidate table rows, writes into `candidate-table-v0.1.__tmp__`, then replaces `candidate-table-v0.1` only after all files are complete. It preserves hard gates: `candidate_table_update_allowed=False`, `trading_layer_read_allowed=False`, `signal_generation_allowed=False`, and `backtest_execution_allowed=False`.

**Tech Stack:** Python standard library, `pathlib`, `json`, `shutil`, `unittest`.

---

## File Structure

- Modify `tests/test_tdx_local_first_batch.py`
  - Import `update_candidate_table_from_staged_qualification_records_when_explicitly_requested`.
  - Add pass, bad manifest, forbidden field, duplicate key, and idempotent rewrite tests.
- Modify `src/data_sources/tdx_local/first_batch.py`
  - Add public P4b entry.
  - Add helpers for manifest loading, record validation, JSONL writing, duplicate checks, temp directory replacement, and blocked reports.
- Modify `src/data_sources/tdx_local/__init__.py`
  - Export the new public entry.
- Modify `docs/04_施工计划_当前进度版.md`
  - Record P4b only after tests pass.
- Modify `docs/06_Roadmap_TodoList_后续路线图与待办.md`
  - Add P4b implementation status after tests pass.

## Task 1: RED Tests For Staged Candidate Table Pass Case

**Files:**
- Modify: `tests/test_tdx_local_first_batch.py`

- [ ] **Step 1: Add the import**

```python
from data_sources.tdx_local import (
    ...
    update_candidate_table_from_staged_qualification_records_when_explicitly_requested,
)
```

- [ ] **Step 2: Add a small helper in the test class**

```python
def _write_single_staged_qualification_record(self, staging_root: Path) -> Path:
    audit_report = {
        "result": "pass",
        "research_only": True,
        "audit_id": "candidate_table_update_audit_package_v0.1",
        "candidate_table_update_audit_result": "pass",
        "candidate_table_update_package_prepared": True,
        "candidate_table_update_performed": False,
        "candidate_table_update_allowed": False,
        "trading_layer_read_allowed": False,
        "candidate_table_update_audit_packages": [
            {
                "candidate_table_update_audit_result": "pass",
                "qualification_record_status": "formal_record_ready_for_persistence",
                "qualification_record_id": "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1",
                "ashare_sample_id": "ASHARE-ADDON-600310-20260605",
                "ts_code": "600310.SH",
                "symbol_name": "桂东电力",
                "sample_window_start": "2026-04-23",
                "sample_window_end": "2026-06-29",
                "qualification_rule_id": "Q-PRESSURE-ADJUST",
                "rhythm_meaning": "limited",
                "tachibana_applicability": "conditional",
                "source_qualification_record_persistence_performed": False,
                "candidate_table_update_package_prepared": True,
                "candidate_table_update_performed": False,
                "candidate_table_update_allowed": False,
                "trading_layer_read_allowed": False,
            }
        ],
    }
    write_qualification_records_to_staging_when_explicitly_requested(
        audit_report,
        staging_root=staging_root,
        generated_at="2026-06-30T21:00:00+08:00",
    )
    return staging_root / "qualification-records-v0.1" / "manifest.json"
```

- [ ] **Step 3: Add pass-case test**

```python
def test_update_candidate_table_from_staged_qualification_records_when_explicitly_requested_writes_jsonl_and_manifest(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        manifest_path = self._write_single_staged_qualification_record(root / "qualification-staging")
        candidate_staging_root = root / "candidate-staging"
        report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
            qualification_record_staging_manifest_path=manifest_path,
            candidate_table_staging_root=candidate_staging_root,
            generated_at="2026-06-30T22:00:00+08:00",
        )
        table_root = candidate_staging_root / "candidate-table-v0.1"
        manifest = json.loads((table_root / "manifest.json").read_text(encoding="utf-8"))
        rows = [
            json.loads(line)
            for line in (table_root / "candidate-table-draft.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        tmp_dirs = list(candidate_staging_root.glob("*. __tmp__"))

    self.assertEqual(report["result"], "pass")
    self.assertTrue(report["candidate_table_update_performed"])
    self.assertEqual(report["candidate_table_update_target"], "staging")
    self.assertFalse(report["candidate_table_update_allowed"])
    self.assertFalse(report["trading_layer_read_allowed"])
    self.assertFalse(report["signal_generation_allowed"])
    self.assertFalse(report["backtest_execution_allowed"])
    self.assertEqual(manifest["manifest_id"], "candidate_table_staging_manifest_v0.1")
    self.assertEqual(manifest["candidate_table_row_count"], 1)
    self.assertEqual(rows[0]["candidate_table_row_id"], "CANDIDATE-TABLE-ROW::ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1")
    self.assertEqual(rows[0]["candidate_table_update_target"], "staging")
    self.assertFalse(rows[0]["candidate_table_update_allowed"])
    self.assertFalse(tmp_dirs)
```

- [ ] **Step 4: Run RED**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_tdx_local_first_batch.TdxLocalFirstBatchTest.test_update_candidate_table_from_staged_qualification_records_when_explicitly_requested_writes_jsonl_and_manifest -v
```

Expected: fail with import error because P4b is not exported yet.

## Task 2: RED Tests For Blocked Inputs And Duplicate Keys

**Files:**
- Modify: `tests/test_tdx_local_first_batch.py`

- [ ] **Step 1: Add bad manifest test**

Use a manifest with `manifest_id="bad"` and assert:

- report is blocked;
- `candidate_table_update_performed=False`;
- output root does not exist.

- [ ] **Step 2: Add forbidden field test**

Create a valid P4a staging directory, inject `trade_accept=True` into the staged record, run P4b, and assert:

- report is blocked;
- no candidate-table output directory exists;
- forbidden field is not echoed in output.

- [ ] **Step 3: Add duplicate key test**

Create a valid P4a staging directory, copy the same record to a second file, append the second file to `record_files`, run P4b, and assert:

- report is blocked;
- issues include `candidate_table_duplicate_qualification_record_id`;
- no candidate-table output directory exists.

- [ ] **Step 4: Add idempotent rewrite test**

Run P4b twice against the same input and same candidate staging root, then assert:

- second run returns pass;
- `candidate-table-v0.1.__tmp__` does not remain;
- manifest still has one row;
- candidate-table directory exists.

- [ ] **Step 5: Run RED**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_tdx_local_first_batch -v
```

Expected: fail because P4b is not implemented.

## Task 3: Implement P4b Writer

**Files:**
- Modify: `src/data_sources/tdx_local/first_batch.py`
- Modify: `src/data_sources/tdx_local/__init__.py`

- [ ] **Step 1: Add public function**

```python
def update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
    qualification_record_staging_manifest_path: str | Path,
    candidate_table_staging_root: str | Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    ...
```

- [ ] **Step 2: Add validation**

Block if:

- manifest cannot be read as JSON;
- manifest id is not `qualification_record_staging_manifest_v0.1`;
- persistence target is not staging;
- `candidate_table_update_performed` is not false;
- `candidate_table_update_allowed` is not false;
- downstream gates are not false;
- `record_files` is empty;
- any record is missing or invalid;
- any record has forbidden output fields;
- duplicate `qualification_record_id` appears.

- [ ] **Step 3: Add row builder**

Each row includes:

- `candidate_table_row_id = "CANDIDATE-TABLE-ROW::<qualification_record_id>"`
- `candidate_table_row_status = "staged_candidate_table_row"`
- qualification fields from the record;
- source manifest and file;
- `candidate_table_update_performed=True`;
- `candidate_table_update_target="staging"`;
- all downstream gates false.

- [ ] **Step 4: Add temp directory replacement**

Use:

```python
tmp_root = table_root.with_name(f"{table_root.name}.__tmp__")
if tmp_root.exists():
    shutil.rmtree(tmp_root)
tmp_root.mkdir(parents=True)
```

Write `candidate-table-draft.jsonl` and `manifest.json` into `tmp_root`.

On Windows, do not rely on `Path.replace()` for non-empty directories. After tmp files are complete:

```python
if table_root.exists():
    shutil.rmtree(table_root)
tmp_root.rename(table_root)
```

If any exception happens before final rename, remove `tmp_root` and leave existing `table_root` untouched.

- [ ] **Step 5: Export the function**

Add to `src/data_sources/tdx_local/__init__.py` import list and `__all__`.

- [ ] **Step 6: Run GREEN**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_tdx_local_first_batch -v
```

Expected: all first-batch tests pass.

## Task 4: Update Documents And Verify

**Files:**
- Modify: `docs/04_施工计划_当前进度版.md`
- Modify: `docs/06_Roadmap_TodoList_后续路线图与待办.md`

- [ ] **Step 1: Update `04`**

Record:

- current position becomes `candidate_table_staging_update_performed`;
- P4b staged candidate table update has occurred;
- formal `data_root`, trading layer, signal, and backtest remain closed.

- [ ] **Step 2: Update `06`**

Record P4b implementation under P4 while keeping formal `data_root` discussion pending.

- [ ] **Step 3: Full verification**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
git diff --check
```

Expected: full tests pass and no diff check errors.

## Task 5: Commit And Push

**Files:**
- Stage all touched files.

- [ ] **Step 1: Inspect status**

Run:

```powershell
git status --short
git diff --stat
```

- [ ] **Step 2: Commit**

Run:

```powershell
git add -- src/data_sources/tdx_local/first_batch.py src/data_sources/tdx_local/__init__.py tests/test_tdx_local_first_batch.py docs/04_施工计划_当前进度版.md docs/06_Roadmap_TodoList_后续路线图与待办.md docs/superpowers/plans/2026-06-30-p4b-staged-candidate-table-update.md
git commit -m "Add staged candidate table update writer"
```

- [ ] **Step 3: Push**

Run:

```powershell
git push
```
