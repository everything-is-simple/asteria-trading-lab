# P4b Candidate Table Update Design

**Date:** 2026-06-30
**Status:** Draft for review
**Scope:** Candidate table staging update boundary after P4a qualification record persistence

## 1. Current Position

The current system position is:

`qualification_record_staging_persistence_performed`

P4a has already proved true file IO in a caller-provided staging directory. It writes:

```text
<staging_root>/
  qualification-records-v0.1/
    manifest.json
    records/
      <qualification_record_id>.json
```

P4a does not update candidate table, does not write formal `data_root`, does not open trading layer read, does not generate signals, and does not run backtests.

P4b starts from this state.

## 2. P4b Goal

P4b designs the candidate table update entry that consumes staged qualification records and produces a staged candidate table update artifact.

The next implementation milestone should not write the formal `data_root` candidate table. It should prove candidate table merge semantics in staging first.

## 3. Design Questions

P4b must answer four questions before implementation:

1. candidate table file format;
2. staging table path versus formal `data_root` path;
3. merge key and duplicate handling strategy;
4. rollback behavior when writing fails.

## 4. Recommended Approach

### Approach A: staged JSONL candidate table with manifest

This is the recommended approach.

P4b reads the P4a staging manifest, loads the staged qualification record JSON files, builds candidate table rows, writes them as JSON Lines, and writes a candidate table update manifest last.

File shape:

```text
<staging_root>/
  candidate-table-v0.1/
    manifest.json
    candidate-table-draft.jsonl
```

Why JSONL:

- standard library only;
- preserves nested audit values better than CSV;
- easy to append or rebuild deterministically;
- one row per line makes review and diff inspection practical;
- avoids adding a Parquet dependency before table semantics are stable.

### Approach B: staged CSV candidate table

This is simple and familiar, and the repository already uses CSV for first-batch data intake.

Trade-off: CSV flattens audit fields too aggressively. The candidate table now needs provenance, qualification status, and merge metadata. CSV would force either lossy flattening or stringified JSON columns too early.

### Approach C: staged Parquet candidate table

This is closer to analytical table storage.

Trade-off: it requires a dependency and a stronger schema commitment before P4b has proven merge semantics. It is deferred.

## 5. Chosen Format

Use Approach A:

`candidate-table-draft.jsonl` plus `manifest.json`

This format is still a staging artifact. It is not the formal production candidate table format.

## 6. P4b Entry

Proposed function:

`update_candidate_table_from_staged_qualification_records_when_explicitly_requested`

Inputs:

- `qualification_record_staging_manifest_path`
- `candidate_table_staging_root`
- optional `generated_at`

The function must be explicit and verbose because it is the first candidate table mutation boundary.

## 7. Input Requirements

The P4a manifest must prove:

- `manifest_id == "qualification_record_staging_manifest_v0.1"`
- `qualification_record_persistence_performed == True`
- `qualification_record_persistence_target == "staging"`
- `candidate_table_update_performed == False`
- `candidate_table_update_allowed == False`
- `trading_layer_read_allowed == False`
- `signal_generation_allowed == False`
- `backtest_execution_allowed == False`
- `record_files` is non-empty

Each referenced record must prove:

- `qualification_record_status == "formal_record_persisted_to_staging"`
- `qualification_record_persistence_performed == True`
- `qualification_record_persistence_target == "staging"`
- `candidate_table_update_performed == False`
- forbidden trading and backtest fields are absent

If any required condition fails, P4b blocks and writes nothing.

## 8. Output Path

P4b writes only under the caller-provided candidate table staging root:

```text
<candidate_table_staging_root>/
  candidate-table-v0.1/
    manifest.json
    candidate-table-draft.jsonl
```

It must not write:

- formal `data_root`;
- existing `ashare/candidate-universe-v0.1.csv`;
- trading layer files;
- signal files;
- backtest files.

## 9. Candidate Table Row Contract

Each JSONL row should include only qualification and audit routing fields:

- `candidate_table_row_id`
- `candidate_table_row_status`
- `qualification_record_id`
- `ashare_sample_id`
- `ts_code`
- `symbol_name`
- `sample_window_start`
- `sample_window_end`
- `qualification_rule_id`
- `rhythm_meaning`
- `tachibana_applicability`
- `source_qualification_record_manifest_id`
- `source_qualification_record_file`
- `candidate_table_updated_at`
- `candidate_table_update_performed`
- `candidate_table_update_target`
- `candidate_table_update_allowed`
- `trading_layer_read_allowed`
- `signal_generation_allowed`
- `backtest_execution_allowed`
- `boundary_warning`
- `next_action`

The row must not contain buy, sell, position, trading decision, or backtest result fields.

## 10. Merge Key

Use this deterministic merge key:

```text
qualification_record_id
```

Reason:

- the upstream qualification record already encodes the formal reviewed unit;
- it prevents two writes for the same formal qualification record from becoming two candidate rows;
- it does not require choosing a broader market identity like `ts_code + window`, which might collapse legitimately distinct future qualification rules.

`candidate_table_row_id` should be:

```text
CANDIDATE-TABLE-ROW::<qualification_record_id>
```

## 11. Duplicate Handling

Within a single P4b input manifest:

- duplicate `qualification_record_id` values block the whole update;
- no candidate table draft is written.

Across an existing staging candidate table draft:

- if the existing row has the same `qualification_record_id` and identical source values, keep one row and report `deduplicated_existing_row_count`;
- if the existing row has the same `qualification_record_id` but different source values, block with `candidate_table_merge_conflict`;
- do not overwrite silently.

The first implementation may support the no-existing-table case first, but the design requires explicit behavior for the existing-table case before formal `data_root` writing is considered.

## 12. Atomic Write And Rollback

P4b should use a build directory under the candidate table staging root:

```text
<candidate_table_staging_root>/
  candidate-table-v0.1.__tmp__/
    candidate-table-draft.jsonl
    manifest.json
```

Write order:

1. validate all inputs before writing;
2. create the temp directory;
3. write `candidate-table-draft.jsonl`;
4. write temp `manifest.json`;
5. atomically replace or move the completed files into `candidate-table-v0.1`;
6. remove the temp directory.

If any write fails before the final replace:

- leave no new `manifest.json`;
- leave the previous completed staging candidate table untouched if it exists;
- return `result="blocked"` or raise an IO error according to implementation style;
- never return partial success.

Manifest must be the last visible completed artifact.

## 13. Return Contract

On pass:

- `result = "pass"`
- `candidate_table_update_performed = True`
- `candidate_table_update_target = "staging"`
- `candidate_table_update_allowed = False`
- `trading_layer_read_allowed = False`
- `signal_generation_allowed = False`
- `backtest_execution_allowed = False`
- `next_action = "action:review_staged_candidate_table_before_formal_data_root_write"`

On block:

- `result = "blocked"`
- `candidate_table_update_performed = False`
- `candidate_table_update_target = "staging"`
- all downstream gates remain false;
- no files are written.

## 14. Formal Data Root Boundary

Formal `data_root` candidate table writing remains out of scope for P4b.

P4b may produce a staged candidate table draft and manifest. A future P4c or later phase must separately decide:

- exact formal candidate table path;
- whether formal format remains JSONL or becomes another table format;
- formal backup and rollback policy;
- operator approval requirements;
- trading layer read gate.

## 15. Test Design

P4b implementation should add tests for:

1. Pass case:
   - reads a valid P4a manifest;
   - writes `candidate-table-draft.jsonl`;
   - writes `manifest.json` last;
   - returns `candidate_table_update_performed=True`;
   - keeps `candidate_table_update_allowed=False` and downstream gates false.

2. Blocked manifest case:
   - bad manifest or missing record files;
   - no output directory or manifest appears.

3. Forbidden field case:
   - staged record contains trading or backtest field;
   - no output files appear.

4. Duplicate key case:
   - duplicate `qualification_record_id` in one manifest;
   - blocks the whole update.

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

## 16. Documentation After P4b Implementation

After implementation and tests pass:

- `04_施工计划_当前进度版.md` should record only staged candidate table update, not formal `data_root` writing.
- `06_Roadmap_TodoList_后续路线图与待办.md` should mark candidate table update design and staging candidate table update complete.
- formal `data_root` discussion should remain pending until separately reviewed.

## 17. Review Decision

If this design is approved, the next step is an implementation plan for P4b only:

1. add failing tests for staged candidate table update;
2. implement the explicit P4b writer;
3. export the entry from `data_sources.tdx_local`;
4. update `04` and `06` after green tests;
5. run focused and full verification.
