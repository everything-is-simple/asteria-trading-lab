# P4c Formal Candidate Table Write Design

**Date:** 2026-06-30
**Status:** Draft for review
**Scope:** Formal `data_root` candidate table write from staging, with human gate, full rollback, and trading layer still closed

## 1. Current Position

The current system position is:

`candidate_table_staging_update_performed`

P4b has already proved candidate table merge semantics in a caller-provided staging directory. It writes:

```text
<staging_root>/
  candidate-table-v0.1/
    manifest.json
    candidate-table-draft.jsonl
```

P4b does not write formal `data_root`, does not open trading layer read, does not generate signals, and does not run backtests.

P4c starts from this state.

## 2. P4c Goal

P4c defines a formal `data_root` candidate table write entry. It consumes the P4b staging candidate table artifact and writes to:

```text
Z:\asteria-trading-labs-data\ashare\candidate-table-v0.1\
  manifest.json
  candidate-table.jsonl
```

It requires an explicit human gate flag. It performs a full atomic replacement with backup. It does not open trading layer read.

## 3. Design Decisions

All four design questions are resolved:

| Question | Decision |
|---|---|
| Formal path | `Z:\asteria-trading-labs-data\ashare\candidate-table-v0.1\candidate-table.jsonl` + `manifest.json` |
| Format | JSONL, same as P4b staging format |
| Human gate | `confirm_formal_write=True` required; blocked without it |
| Rollback | Full rollback, no residual artifacts; existing formal directory backed up before write |
| Trading layer | Remains closed after P4c; opened only via separate P5 audit |

## 4. P4c Entry

Proposed function:

`write_candidate_table_to_formal_data_root_when_explicitly_confirmed`

The name encodes three boundaries:

- it writes to formal `data_root`, not staging;
- it writes the candidate table, not qualification records;
- it only runs when the caller explicitly confirms the write.

## 5. Inputs

The function accepts:

- `candidate_table_staging_manifest_path` — path to the P4b staging manifest
- `formal_data_root` — the data root to write into; the function will resolve the full target path internally as `<formal_data_root>/ashare/candidate-table-v0.1/`
- `confirm_formal_write` — must be `True`; if `False` or absent the function blocks immediately
- optional `generated_at`

## 6. Input Validation

The P4b staging manifest must prove:

- `manifest_id == "candidate_table_staging_manifest_v0.1"`
- `candidate_table_update_performed == True`
- `candidate_table_update_target == "staging"`
- `candidate_table_update_allowed == False`
- `trading_layer_read_allowed == False`
- `signal_generation_allowed == False`
- `backtest_execution_allowed == False`
- `candidate_table_draft_file` is present and resolves to a readable file
- `qualification_record_staging_manifest_id` is present (provenance link)

The function must also verify that `candidate-table-draft.jsonl` is non-empty and contains no forbidden trading or backtest fields in any row.

If `confirm_formal_write` is not explicitly `True`, the function returns a blocked report immediately without reading any staging files:

```
result = "blocked"
block_reason = "confirm_formal_write not set; formal data_root write requires explicit human confirmation"
candidate_table_update_performed = False
```

## 7. Backup Strategy

Before any write to the formal target directory, P4c must:

1. Check whether `<formal_data_root>/ashare/candidate-table-v0.1/` already exists.
2. If it exists, copy it to a timestamped backup path:
   ```
   <formal_data_root>/ashare/candidate-table-v0.1.backup.<ISO8601>/
     manifest.json
     candidate-table.jsonl
   ```
3. Record the backup path in the write report.
4. If the backup copy fails, abort without modifying the live directory.

The backup is kept on disk after a successful formal write. It is not removed automatically. Rollback restores from this backup if needed.

## 8. Atomic Write Sequence

Write order after backup succeeds:

1. Create temp directory: `<formal_data_root>/ashare/candidate-table-v0.1.__tmp__/`
2. Write `candidate-table.jsonl` into temp directory.
3. Write `manifest.json` into temp directory.
4. Atomically replace `candidate-table-v0.1/` with `candidate-table-v0.1.__tmp__/`:
   - On Windows: rename the existing live directory to a side path, rename temp to live, then remove the side path.
5. Remove the temp directory if it survived.

If any step from 2 onward fails:

- Remove the temp directory.
- Leave the live directory untouched (still the original or the backup-restored version).
- Return `result="blocked"` with `block_reason` describing the failure step.
- Never return partial success.

Manifest must be the last file written inside the temp directory before the final rename.

## 9. Output Path

The function writes only to:

```text
<formal_data_root>/ashare/candidate-table-v0.1/
  manifest.json
  candidate-table.jsonl
```

It must not write:

- staging directories;
- trading layer files;
- signal files;
- backtest files;
- any path outside `<formal_data_root>/ashare/candidate-table-v0.1/` (except the backup path under the same `ashare/` subtree).

## 10. Return Contract

On pass:

- `result = "pass"`
- `candidate_table_update_performed = True`
- `candidate_table_update_target = "formal_data_root"`
- `candidate_table_update_allowed = False`
- `formal_candidate_table_path = "<resolved absolute path to candidate-table.jsonl>"`
- `formal_candidate_table_manifest_path = "<resolved absolute path to manifest.json>"`
- `backup_path = "<resolved absolute path to backup directory>"`
- `trading_layer_read_allowed = False`
- `signal_generation_allowed = False`
- `backtest_execution_allowed = False`
- `next_action = "action:review_formal_candidate_table_before_trading_layer_audit"`

On block:

- `result = "blocked"`
- `block_reason = "<specific reason>"`
- `candidate_table_update_performed = False`
- all downstream gates remain false;
- no files written or modified.

## 11. Formal Candidate Table Manifest

The manifest written inside the formal directory should include:

- `manifest_id = "candidate_table_formal_manifest_v0.1"`
- `generated_at`
- `source_staging_manifest_id`
- `source_qualification_record_staging_manifest_id`
- `candidate_table_row_count`
- `candidate_table_file`
- `backup_path`
- `candidate_table_update_performed = true`
- `candidate_table_update_target = "formal_data_root"`
- `candidate_table_update_allowed = false`
- `trading_layer_read_allowed = false`
- `signal_generation_allowed = false`
- `backtest_execution_allowed = false`

## 12. Trading Layer Gate

`trading_layer_read_allowed` remains `False` after P4c.

Opening the trading layer requires a separate P5 audit that:

- reviews the formal candidate table content;
- confirms institution rule definition is ready;
- explicitly sets `trading_layer_read_allowed = True` via a separate audit entry.

P4c must not contain any logic that sets `trading_layer_read_allowed = True` under any condition.

## 13. Test Design

P4c implementation should add tests for:

1. Pass case:
   - valid P4b staging manifest;
   - `confirm_formal_write=True`;
   - backup directory created;
   - `candidate-table.jsonl` written to temp then renamed to live;
   - `manifest.json` written last;
   - returns `candidate_table_update_performed=True` and `candidate_table_update_target="formal_data_root"`;
   - keeps `trading_layer_read_allowed=False` and downstream gates false.

2. Blocked — missing confirm flag:
   - `confirm_formal_write` absent or `False`;
   - no files read, no backup created, no files written;
   - blocked report explains missing confirmation.

3. Blocked — invalid staging manifest:
   - bad staging manifest or missing `candidate-table-draft.jsonl`;
   - no backup, no output files;
   - blocked report states manifest validation failure.

4. Blocked — forbidden field in staging rows:
   - any staging row contains a trading or backtest field;
   - no backup, no output files;
   - blocked report names the forbidden field.

5. Rollback simulation:
   - simulate a write failure after backup succeeds;
   - confirm live directory is untouched;
   - confirm backup path still exists and is readable;
   - confirm temp directory is cleaned up.

All tests must use `tests/fixtures/` only. No test should touch the real `Z:\asteria-trading-labs-data` path.

Focused verification:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_tdx_local_first_batch -v
```

Full verification:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
```

## 14. Documentation After P4c Implementation

After implementation and tests pass:

- `04_施工计划_当前进度版.md` should record formal candidate table write completed, backup path confirmed, trading layer still closed.
- `06_Roadmap_TodoList_后续路线图与待办.md` should mark all four P4 items complete, and mark `trading_layer_read_allowed` as still pending P5.

## 15. Review Decision

If this design is approved, the next step is an implementation plan for P4c only:

1. add failing tests for formal candidate table write (pass, blocked-no-confirm, blocked-bad-manifest, forbidden-field, rollback);
2. implement the explicit P4c writer with backup and atomic rename;
3. export the entry from `data_sources.tdx_local`;
4. update `04` and `06` after green tests;
5. run focused and full verification.
