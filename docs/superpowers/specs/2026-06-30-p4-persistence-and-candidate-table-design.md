# P4 Persistence and Candidate Table Design

**Date:** 2026-06-30
**Status:** Draft for review
**Scope:** P4 true persistence and candidate table write boundary

## 1. Background

The current system is positioned at:

`candidate_table_update_audit_package_prepared`

That means the chain has already produced a formal qualification record persistence package and has also prepared a candidate table update audit package. It does not mean any true file persistence, candidate table update, trading layer read, signal generation, or backtest execution has occurred.

P4 is the first phase that may touch real file IO. Because of that, the phase needs a smaller first milestone before any formal `data_root` write is discussed.

## 2. P4 Goal

P4 has four roadmap items:

1. Design the true persistence write entry.
2. Design the candidate table update entry.
3. Validate true file IO in a temporary or staging directory first.
4. Discuss formal `data_root` writing only after the staging path is stable.

This design keeps those four items separate. The first implementation milestone is P4a, not full P4.

## 3. Recommended Approach

### Approach A: staging-first persistence, candidate table still closed

This is the recommended approach.

P4a writes formal qualification records into a caller-provided staging directory. It proves that the system can perform real file IO, write records and a manifest, preserve atomic replacement semantics, and keep all downstream gates closed.

Trade-off: it does not yet update the candidate table. That is intentional because the first IO milestone should prove persistence mechanics before table mutation semantics.

### Approach B: staging persistence plus candidate table staging draft

This would write qualification records and also generate a candidate table draft in staging.

Trade-off: it moves faster on visible table output, but it mixes two risk types: file persistence and table mutation semantics. It is more likely to blur the difference between "records persisted" and "candidate table updated."

### Approach C: direct formal `data_root` writer

This would write directly to the formal data root.

Trade-off: it is rejected for the current phase. The project has not yet proven the write shape, rollback behavior, manifest contract, or candidate table boundary in a staging path.

## 4. Chosen Design

Use Approach A for the next implementation milestone:

`P4a staging qualification record persistence`

The candidate table update entry is designed in this document as P4b, but is not implemented in P4a.

## 5. P4a Entry

Proposed function:

`write_qualification_records_to_staging_when_explicitly_requested`

The name should remain intentionally verbose because it encodes the safety boundary:

- it writes qualification records, not candidate table rows;
- it writes to staging, not formal `data_root`;
- it only runs when explicitly called.

## 6. P4a Inputs

The entry accepts:

- `candidate_table_update_audit_report`
- `staging_root`
- optional `generated_at`

The audit report must prove:

- `candidate_table_update_audit_result == "pass"`
- `candidate_table_update_package_prepared == True`
- `candidate_table_update_performed == False`
- `candidate_table_update_allowed == False`
- at least one candidate table update audit package exists

The function must reject reports that skip the previous audit layer or already claim a candidate table update was performed.

## 7. P4a Output Files

The function writes only under the caller-provided staging root:

```text
<staging_root>/
  qualification-records-v0.1/
    manifest.json
    records/
      <qualification_record_id>.json
```

The implementation should use atomic file replacement for individual files. It should not write outside `staging_root`.

The manifest should include:

- `manifest_id`
- `generated_at`
- `source_audit_id`
- `qualification_record_count`
- `record_files`
- `qualification_record_persistence_performed = true`
- `qualification_record_persistence_target = "staging"`
- `candidate_table_update_performed = false`
- `candidate_table_update_allowed = false`
- `trading_layer_read_allowed = false`
- `signal_generation_allowed = false`
- `backtest_execution_allowed = false`

## 8. P4a Return Contract

On pass, the returned report should state:

- `result = "pass"`
- `qualification_record_persistence_performed = True`
- `qualification_record_persistence_target = "staging"`
- `candidate_table_update_performed = False`
- `candidate_table_update_allowed = False`
- `trading_layer_read_allowed = False`
- `signal_generation_allowed = False`
- `backtest_execution_allowed = False`

On block, the returned report should state:

- `result = "blocked"`
- `qualification_record_persistence_performed = False`
- downstream gates remain false
- no partial success wording

## 9. P4b Candidate Table Update Boundary

P4b should be a separate explicit entry after P4a is tested:

`update_candidate_table_from_staged_qualification_records_when_explicitly_requested`

P4b may read from a staged qualification record manifest and prepare or perform a candidate table update according to a separate audit rule. It must not be implemented as part of P4a.

P4b requires a future decision on:

- candidate table file format;
- staging table versus formal table path;
- merge key and duplicate handling;
- rollback behavior;
- whether formal `data_root` writes are allowed.

Until those decisions are made, candidate table update remains closed.

## 10. Forbidden Fields and Gates

P4a must not introduce:

- buy signal fields;
- sell signal fields;
- position sizing fields;
- trading decision fields;
- backtest result fields;
- trading layer read permission.

These gates remain false:

- `candidate_table_update_allowed`
- `trading_layer_read_allowed`
- `signal_generation_allowed`
- `backtest_execution_allowed`

If any input package contains forbidden trading or backtest semantics, P4a should block instead of writing.

## 11. Test Design

P4a implementation should add at least three test groups:

1. Pass case:
   - valid audit report;
   - writes `manifest.json`;
   - writes one or more record files;
   - returns persistence performed true;
   - keeps candidate table and downstream gates false.

2. Blocked case:
   - missing or failed audit result;
   - no files written;
   - downstream gates false.

3. Forbidden field case:
   - input includes signal, position, trading decision, or backtest fields;
   - no files written;
   - blocked report explains the forbidden field.

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

## 12. Documentation Updates After P4a

After P4a is implemented and tested:

- `04_施工计划_当前进度版.md` should record only the completed P4a fact.
- `06_Roadmap_TodoList_后续路线图与待办.md` should mark only the staging IO item complete.
- P4b candidate table update should remain pending until separately implemented.

## 13. Out of Scope

P4a does not:

- write formal `data_root`;
- update candidate table;
- open trading layer read;
- define institution rules;
- generate signals;
- execute backtests.

## 14. Review Decision

If this design is approved, the next step is an implementation plan for P4a only:

1. add failing tests for staging persistence;
2. implement the explicit staging writer;
3. export the entry from `data_sources.tdx_local`;
4. update `04` and `06` after green tests;
5. run focused and full verification.
