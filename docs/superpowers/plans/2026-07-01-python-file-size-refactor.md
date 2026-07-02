# Python File Size Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split every Python source or test file over 1000 lines in `src/`, `scripts/`, and `tests/`, then enforce the limit with a regression test.

**Architecture:** Keep the three current public entry modules as compatibility facades and move implementation into responsibility-focused modules. Split the matching test mirrors by the same domain boundaries so `unittest discover` remains the canonical runner.

**Tech Stack:** Python standard library, `unittest`, existing Asteria audit modules.

---

## Current Over-Limit Files

- `src/data_sources/tdx_local/first_batch.py`
- `tests/test_tdx_local_first_batch.py`
- `tests/test_ashare_intake_validator.py`
- `src/ashare_intake_validator.py`
- `src/tachibana_front_filter.py`
- `tests/test_tachibana_front_filter.py`

## Hard Boundaries

- Preserve existing public imports from `tachibana_front_filter`, `ashare_intake_validator`, and `data_sources.tdx_local.first_batch`.
- Preserve CLI behavior for `python -m tachibana_front_filter` and `python -m ashare_intake_validator`.
- Do not add trading signal, position, or backtest execution semantics.
- Keep downstream hard gates closed unless existing tests explicitly prove otherwise:
  - `trading_layer_read_allowed`
  - `signal_generation_allowed`
  - `backtest_execution_allowed`
- Do not read or write external market data roots during refactor verification.

## Tasks

### Task 1: Add File Size Guard

**Files:**
- Create: `tests/test_source_file_size_contract.py`

- [ ] Add a `unittest` test that scans `src/`, `scripts/`, and `tests/` for `.py` files.
- [ ] Exclude `__pycache__` directories.
- [ ] Fail when any file is over 1000 lines.
- [ ] Run `python -B -m unittest tests.test_source_file_size_contract -v`.
- [ ] Confirm RED with the six known over-limit files.

### Task 2: Split Tachibana Front Filter

**Files:**
- Modify: `src/tachibana_front_filter.py`
- Create: `src/tachibana_front_filter_catalogs.py`
- Create: `src/tachibana_front_filter_audits.py`
- Create: `src/tachibana_front_filter_runtime.py`
- Create: `src/tachibana_front_filter_cli.py`
- Split: `tests/test_tachibana_front_filter.py`

- [ ] Move catalogs and getter functions into `tachibana_front_filter_catalogs.py`.
- [ ] Move audit gate functions into `tachibana_front_filter_audits.py`.
- [ ] Move runtime snapshot and qualification draft functions into `tachibana_front_filter_runtime.py`.
- [ ] Move CLI parsing into `tachibana_front_filter_cli.py`.
- [ ] Leave `tachibana_front_filter.py` as a facade that re-exports existing public names and delegates `main()`.
- [ ] Split tests into catalog, runtime, gate, and CLI test files.
- [ ] Run `python -B -m unittest tests.test_tachibana_catalogs tests.test_tachibana_runtime tests.test_tachibana_gates tests.test_tachibana_cli -v`.
- [ ] Run `python -m tachibana_front_filter --audit-front-filter-system`.

### Task 3: Split A-Share Intake Validator

**Files:**
- Modify: `src/ashare_intake_validator.py`
- Create: `src/ashare_intake_contracts.py`
- Create: `src/ashare_first_batch_pipeline.py`
- Create: `src/ashare_execution_constraint_pipeline.py`
- Create: `src/ashare_execution_policy_pipeline.py`
- Create: `src/ashare_intake_cli.py`
- Create: `src/ashare_intake_utils.py`
- Split: `tests/test_ashare_intake_validator.py`

- [ ] Move common CSV/JSON/package validators into `ashare_intake_utils.py`.
- [ ] Move package and contract audits into `ashare_intake_contracts.py`.
- [ ] Move first-batch MALF and front-filter audits into `ashare_first_batch_pipeline.py`.
- [ ] Move institution and execution feasibility audits into `ashare_execution_constraint_pipeline.py`.
- [ ] Move execution-policy audits into `ashare_execution_policy_pipeline.py`.
- [ ] Move CLI dispatch into `ashare_intake_cli.py`.
- [ ] Leave `ashare_intake_validator.py` as a facade that re-exports existing public names and delegates `main()`.
- [ ] Split tests into support, contract, first-batch, execution-constraint, execution-policy, and CLI test files.
- [ ] Run the split A-share test modules directly.
- [ ] Run `python -m ashare_intake_validator --help`.

### Task 4: Split TDX First Batch

**Files:**
- Modify: `src/data_sources/tdx_local/first_batch.py`
- Create: `src/data_sources/tdx_local/first_batch_constants.py`
- Create: `src/data_sources/tdx_local/first_batch_common.py`
- Create: `src/data_sources/tdx_local/first_batch_sample_packages.py`
- Create: `src/data_sources/tdx_local/first_batch_shortlist.py`
- Create: `src/data_sources/tdx_local/first_batch_reviews.py`
- Create: `src/data_sources/tdx_local/qualification_record_gates.py`
- Create: `src/data_sources/tdx_local/candidate_table_gates.py`
- Create: `src/data_sources/tdx_local/trading_readiness_gates.py`
- Create: `src/data_sources/tdx_local/rule_definition_gates.py`
- Split: `tests/test_tdx_local_first_batch.py`

- [ ] Move constants into `first_batch_constants.py`.
- [ ] Move shared JSON/CSV/path/date/forbidden-field helpers into `first_batch_common.py`.
- [ ] Move first-batch sample package builders into `first_batch_sample_packages.py`.
- [ ] Move add-on price-limit shortlist and materialization helpers into `first_batch_shortlist.py`.
- [ ] Move MALF snapshot, front-filter, and qualification draft reviews into `first_batch_reviews.py`.
- [ ] Move qualification record persistence gates into `qualification_record_gates.py`.
- [ ] Move candidate table gates into `candidate_table_gates.py`.
- [ ] Move trading readiness gates into `trading_readiness_gates.py`.
- [ ] Move P7/P8 rule-definition gates into `rule_definition_gates.py`.
- [ ] Leave `first_batch.py` as a facade that re-exports existing public names.
- [ ] Split tests into support, sample, shortlist, review, qualification, candidate, trading-readiness, and rule-definition files.
- [ ] Run the split TDX test modules directly.

### Task 5: Final Verification

- [ ] Run `python -B -m unittest tests.test_source_file_size_contract -v`.
- [ ] Run `python -B -m unittest discover -s tests -v`.
- [ ] Run `python -m tachibana_front_filter --audit-front-filter-system`.
- [ ] Run `python -m ashare_intake_validator --help`.
- [ ] Run `git diff --check`.
- [ ] Confirm no `.py` file under `src/`, `scripts/`, or `tests/` exceeds 1000 lines.
