# CLAUDE-en.md

This is the English companion note for the repository.

## Repository Purpose

`asteria-trading-lab` is a research-first project that:

1. reconstructs Tachibana Yoshimasa's 1975-1976 trading records,
2. re-expresses them through MALF structural language,
3. audits whether selected A-share samples are suitable for later execution-policy research.

It is **not** a production trading system.

## What Is Already Implemented

- historical Pioneer replay and reporting in `src/original_tachibana/`
- MALF-Tachibana front cognitive filter in `src/tachibana_front_filter.py`
- local Tongdaxin / DuckDB read-only intake in `src/data_sources/tdx_local/`
- A-share institution audit pipeline in `src/ashare_intake_validator.py`

The current verified downstream state is:

`execution_policy_research_prep -> action:prepare_execution_policy_research`

## Main Commands

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
python -m ashare_intake_validator --help
python -m tachibana_front_filter --audit-front-filter-system
```

Current active gate:

```powershell
$env:PYTHONPATH='src'
python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-execution-policy-research-prep Z:\asteria-trading-lab\docs\tachibana\execution-policy-reviews\first-batch-v0.1 --method-pm-plan-dir Z:\asteria-trading-lab\docs\tachibana\method-pm-plans\first-batch-v0.1 --institution-fact-root Z:\asteria-trading-labs-data
```

## Non-Negotiable Boundaries

The project must not emit:

- `buy_signal`
- `sell_signal`
- `trade_accept`
- `target_position`
- `position_size`
- `ashare_t1_action`
- `limit_up_strategy`
- `limit_down_strategy`

And these gates must remain `false` at the current phase:

- `institution_rule_definition_allowed`
- `signal_generation_allowed`
- `backtest_execution_allowed`
