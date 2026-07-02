# P4a Staging Qualification Record Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the P4a explicit staging writer that persists qualification records to a caller-provided staging directory without updating candidate table or opening downstream gates.

**Architecture:** Add one explicit entry in `src/data_sources/tdx_local/first_batch.py` after the candidate table update audit layer. The writer validates a passed candidate table update audit report, writes record JSON files first using temporary file replacement, then writes `manifest.json` last so no complete manifest exists before records land. It returns a pass or blocked report with all candidate table, trading layer, signal, and backtest gates closed.

**Tech Stack:** Python standard library, `pathlib`, `json`, `tempfile`, `unittest`.

---

## File Structure

- Modify `tests/test_tdx_local_first_batch.py`
  - Import `write_qualification_records_to_staging_when_explicitly_requested`.
  - Add pass, blocked, and forbidden-field tests beside the candidate table update audit tests.
- Modify `src/data_sources/tdx_local/first_batch.py`
  - Add the public writer entry.
  - Add small helpers for staging path layout, safe file names, JSON atomic writes, record payload creation, and blocked reports.
- Modify `src/data_sources/tdx_local/__init__.py`
  - Export the new public entry.
- Modify `docs/04_施工计划_当前进度版.md`
  - Record P4a only after tests pass.
- Modify `docs/06_Roadmap_TodoList_后续路线图与待办.md`
  - Mark staging IO validation complete only after tests pass.

## Task 1: RED Test For Successful Staging Persistence

**Files:**
- Modify: `tests/test_tdx_local_first_batch.py`

- [ ] **Step 1: Add the import**

```python
from data_sources.tdx_local import (
    ...
    write_qualification_records_to_staging_when_explicitly_requested,
)
```

- [ ] **Step 2: Add a pass-case test**

```python
def test_write_qualification_records_to_staging_when_explicitly_requested_writes_records_then_manifest(self) -> None:
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
    with tempfile.TemporaryDirectory() as tmp:
        staging_root = Path(tmp) / "staging"
        report = write_qualification_records_to_staging_when_explicitly_requested(
            audit_report,
            staging_root=staging_root,
            generated_at="2026-06-30T21:00:00+08:00",
        )
        manifest_path = staging_root / "qualification-records-v0.1" / "manifest.json"
        record_path = (
            staging_root
            / "qualification-records-v0.1"
            / "records"
            / "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        record = json.loads(record_path.read_text(encoding="utf-8"))

    self.assertEqual(report["result"], "pass")
    self.assertTrue(report["qualification_record_persistence_performed"])
    self.assertEqual(report["qualification_record_persistence_target"], "staging")
    self.assertFalse(report["candidate_table_update_performed"])
    self.assertFalse(report["candidate_table_update_allowed"])
    self.assertFalse(report["trading_layer_read_allowed"])
    self.assertFalse(report["signal_generation_allowed"])
    self.assertFalse(report["backtest_execution_allowed"])
    self.assertEqual(manifest["qualification_record_count"], 1)
    self.assertEqual(manifest["record_files"], ["records/ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1.json"])
    self.assertTrue(manifest["qualification_record_persistence_performed"])
    self.assertEqual(record["qualification_record_status"], "formal_record_persisted_to_staging")
    self.assertEqual(record["qualification_record_id"], "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1")
```

- [ ] **Step 3: Run RED**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_tdx_local_first_batch.TdxLocalFirstBatchTest.test_write_qualification_records_to_staging_when_explicitly_requested_writes_records_then_manifest -v
```

Expected: fail with an import error because the function is not defined yet.

## Task 2: RED Tests For Blocked And Forbidden Inputs

**Files:**
- Modify: `tests/test_tdx_local_first_batch.py`

- [ ] **Step 1: Add blocked input test**

```python
def test_write_qualification_records_to_staging_when_explicitly_requested_blocks_bad_audit_report(self) -> None:
    audit_report = {
        "result": "blocked",
        "audit_id": "candidate_table_update_audit_package_v0.1",
        "candidate_table_update_audit_result": "blocked",
        "candidate_table_update_package_prepared": False,
        "candidate_table_update_performed": False,
        "candidate_table_update_audit_packages": [],
    }
    with tempfile.TemporaryDirectory() as tmp:
        staging_root = Path(tmp) / "staging"
        report = write_qualification_records_to_staging_when_explicitly_requested(
            audit_report,
            staging_root=staging_root,
            generated_at="2026-06-30T21:05:00+08:00",
        )
        self.assertFalse(staging_root.exists())

    self.assertEqual(report["result"], "blocked")
    self.assertFalse(report["qualification_record_persistence_performed"])
    self.assertIn("candidate_table_update_audit_not_pass", report["issues"])
    self.assertFalse(report["candidate_table_update_allowed"])
    self.assertFalse(report["trading_layer_read_allowed"])
    self.assertFalse(report["signal_generation_allowed"])
    self.assertFalse(report["backtest_execution_allowed"])
```

- [ ] **Step 2: Add forbidden field test**

```python
def test_write_qualification_records_to_staging_when_explicitly_requested_blocks_forbidden_fields_without_files(self) -> None:
    audit_report = {
        "result": "pass",
        "audit_id": "candidate_table_update_audit_package_v0.1",
        "candidate_table_update_audit_result": "pass",
        "candidate_table_update_package_prepared": True,
        "candidate_table_update_performed": False,
        "candidate_table_update_allowed": False,
        "candidate_table_update_audit_packages": [
            {
                "candidate_table_update_audit_result": "pass",
                "qualification_record_status": "formal_record_ready_for_persistence",
                "qualification_record_id": "ASHARE-QUAL-000899.SZ-2026-04-23-2026-06-29-v0.1",
                "ts_code": "000899.SZ",
                "qualification_rule_id": "Q-PRESSURE-ADJUST",
                "candidate_table_update_package_prepared": True,
                "candidate_table_update_performed": False,
                "trade_accept": True,
            }
        ],
    }
    with tempfile.TemporaryDirectory() as tmp:
        staging_root = Path(tmp) / "staging"
        report = write_qualification_records_to_staging_when_explicitly_requested(
            audit_report,
            staging_root=staging_root,
            generated_at="2026-06-30T21:10:00+08:00",
        )
        self.assertFalse(staging_root.exists())

    self.assertEqual(report["result"], "blocked")
    self.assertFalse(report["qualification_record_persistence_performed"])
    self.assertEqual(report["held_qualification_record_staging_count"], 1)
    self.assertEqual(
        report["held_qualification_record_staging_items"][0]["qualification_record_persistence_reason"],
        "qualification_record_staging_forbidden_output_field_present",
    )
    self.assertFalse(report["candidate_table_update_allowed"])
    self.assertFalse(report["trading_layer_read_allowed"])
    self.assertFalse(report["signal_generation_allowed"])
    self.assertFalse(report["backtest_execution_allowed"])
```

- [ ] **Step 3: Run RED**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_tdx_local_first_batch -v
```

Expected: fail because the new function is not exported.

## Task 3: Implement P4a Staging Writer

**Files:**
- Modify: `src/data_sources/tdx_local/first_batch.py`
- Modify: `src/data_sources/tdx_local/__init__.py`

- [ ] **Step 1: Add the public function**

```python
def write_qualification_records_to_staging_when_explicitly_requested(
    candidate_table_update_audit_report: dict[str, Any],
    staging_root: str | Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    ...
```

- [ ] **Step 2: Validate input gates**

The function blocks if:

- audit result is not `pass`;
- package prepared is not true;
- candidate table update performed is not false;
- candidate table update allowed is not false;
- no candidate audit package exists;
- any candidate package has forbidden output fields;
- any candidate package is not a passed candidate table update audit package.

- [ ] **Step 3: Write records before manifest**

Implementation order:

1. create `<staging_root>/qualification-records-v0.1/records`;
2. for each record, write `<id>.json.tmp`;
3. replace `<id>.json`;
4. after all records succeed, write `manifest.json.tmp`;
5. replace `manifest.json`.

- [ ] **Step 4: Export the function**

Add it to the import list and `__all__` in `src/data_sources/tdx_local/__init__.py`.

- [ ] **Step 5: Run GREEN**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_tdx_local_first_batch -v
```

Expected: all first batch tests pass.

## Task 4: Update Progress Docs

**Files:**
- Modify: `docs/04_施工计划_当前进度版.md`
- Modify: `docs/06_Roadmap_TodoList_后续路线图与待办.md`

- [ ] **Step 1: Update current progress**

Record that P4a staging persistence has occurred, and only staging persistence has occurred.

- [ ] **Step 2: Update roadmap checkboxes**

Mark:

```markdown
- [x] 设计真实持久化写入入口。
- [x] 先在临时目录验证真实文件 IO。
```

Keep candidate table update and formal `data_root` discussion pending.

- [ ] **Step 3: Run full verification**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
git diff --check
```

Expected: all tests pass and no diff check errors.

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
git add -- src/data_sources/tdx_local/first_batch.py src/data_sources/tdx_local/__init__.py tests/test_tdx_local_first_batch.py docs/04_施工计划_当前进度版.md docs/06_Roadmap_TodoList_后续路线图与待办.md docs/superpowers/plans/2026-06-30-p4a-staging-qualification-record-persistence.md
git commit -m "Add staging qualification record persistence writer"
```

- [ ] **Step 3: Push**

Run:

```powershell
git push
```
