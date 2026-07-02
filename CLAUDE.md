# CLAUDE.md

This file provides working guidance for repository contributors and Claude/Codex-style coding agents.

## Core Commands

Run all tests:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
```

Show the A-share pipeline CLI surface:

```powershell
$env:PYTHONPATH='src'
python -m ashare_intake_validator --help
```

Run the front-filter system audit:

```powershell
$env:PYTHONPATH='src'
python -m tachibana_front_filter --audit-front-filter-system
```

Generate the minimal institution fact package:

```powershell
$env:PYTHONPATH='src'
python -m data_sources.tdx_local.institution_facts --duckdb-root Z:\malf-data --data-root Z:\asteria-trading-labs-data --ts-code 000001.SZ --ts-code 300750.SZ --ts-code 600000.SH --window-start 2026-03-24 --window-end 2026-04-03
```

Run the current active downstream gate:

```powershell
$env:PYTHONPATH='src'
python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-execution-policy-research-prep Z:\asteria-trading-lab\docs\tachibana\execution-policy-reviews\first-batch-v0.1 --method-pm-plan-dir Z:\asteria-trading-lab\docs\tachibana\method-pm-plans\first-batch-v0.1 --institution-fact-root Z:\asteria-trading-labs-data
```

## Current Architecture Truth

The repo currently has three real code trunks:

- `src/original_tachibana/`: historical Pioneer replay and reports
- `src/tachibana_front_filter.py`: MALF-Tachibana front cognitive gate
- `src/ashare_intake_validator.py` plus `src/data_sources/tdx_local/`: A-share read-only intake and institution audit chain

The live chain has already reached:

`execution_policy_research_prep -> action:prepare_execution_policy_research`

This means the project has passed structure qualification, Method/PM merge, institution fact intake, execution feasibility review, policy candidate review, archive, and research prep for the first batch.

## Hard Boundaries

These must stay false unless the project explicitly opens a later phase:

- `institution_rule_definition_allowed`
- `signal_generation_allowed`
- `backtest_execution_allowed`

The system must not emit:

- `buy_signal`
- `sell_signal`
- `trade_accept`
- `target_position`
- `position_size`
- `ashare_t1_action`
- `limit_up_strategy`
- `limit_down_strategy`

## Data Roots

Real data is outside the repo:

- `Z:\asteria-trading-labs-data`
- `Z:\malf-data`
- `Z:\new_tdx64`
- `Z:\tdx_offline_Data`

Tests use only `tests/fixtures/`.
