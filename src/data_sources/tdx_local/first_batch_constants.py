from __future__ import annotations

import csv
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any

import duckdb

from ashare_intake_validator import (
    audit_first_batch_front_filter_run,
    audit_first_batch_readiness,
    audit_first_batch_record_drafts,
    audit_first_batch_sample_table_trial,
)
from .readers import (
    _normalize_duckdb_symbol,
    _resolve_duckdb_table_ref,
    read_daily_bars,
    read_intraday_range,
    read_symbol_master,
)
from .price_limit_sample_pool import screen_pullback_add_price_limit_candidates



FORBIDDEN_OUTPUT_FIELDS = {
    "buy_signal",
    "sell_signal",
    "trade_accept",
    "trade_reject",
    "trade_defer",
    "signal_decision",
    "target_position",
    "position_size",
    "ashare_t1_action",
    "limit_up_strategy",
    "limit_down_strategy",
    "industry_hot_score",
    "liquidity_rank_as_applicability",
    "rhythm_meaning_override",
    "tachibana_applicability_override",
}


CANDIDATE_HEADER = [
    "ts_code",
    "symbol_name",
    "board_type",
    "list_date",
    "is_st",
    "is_new_stock_window",
    "data_quality_status",
    "source_ref",
]

SW_HEADER = [
    "ts_code",
    "sw_l1_name",
    "sw_l2_name",
    "valid_from",
    "valid_to",
    "source_ref",
]

DAILY_HEADER = [
    "ts_code",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "adj_ref",
    "suspension_flag",
    "corporate_action_flag",
    "missing_bar_flag",
]

DEFAULT_FIRST_BATCH_SAMPLE_ENTRIES = [
    {
        "ts_code": "000001.SZ",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "expected_structure_target": "meaningful",
        "selection_reason": "Bank sample with a relatively clean upward push for first-batch meaningful coverage.",
        "evidence_ref": "docs/a-share/first-batch-real-samples.md#000001sz",
    },
    {
        "ts_code": "300750.SZ",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "expected_structure_target": "limited",
        "selection_reason": "High-volatility pullback sample for PM-dependent limited coverage.",
        "snapshot_preset": "pullback_pressure",
        "evidence_ref": "docs/a-share/first-batch-real-samples.md#300750sz",
    },
    {
        "ts_code": "600000.SH",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "expected_structure_target": "limited",
        "selection_reason": "Range-wait banking sample to preserve a second limited case.",
        "snapshot_preset": "range_wait",
        "evidence_ref": "docs/a-share/first-batch-real-samples.md#600000sh",
    },
    {
        "ts_code": "601127.SH",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "expected_structure_target": "unknown",
        "selection_reason": "Structure still left in research-pending state, used to keep unknown coverage honest.",
        "evidence_ref": "docs/a-share/first-batch-real-samples.md#601127sh",
    },
    {
        "ts_code": "002714.SZ",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "expected_structure_target": "not_meaningful",
        "selection_reason": "Noise-dominated sample used for explicit not-meaningful coverage.",
        "evidence_ref": "docs/a-share/first-batch-real-samples.md#002714sz",
    },
]


DEFAULT_ADD_ON_PRICE_LIMIT_SHORTLIST_SAMPLE_ENTRIES = [
    {
        "ts_code": "603538.SH",
        "trade_date": "2026-04-01",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "research_priority_group": "core",
        "formal_review_bucket": "pressure_adjust_reopen",
        "core_snapshot_focus": "pressure_adjust_reopen_core",
        "selection_reason": "Core reopened-touch candidate with down-limit-side pressure-adjust value.",
        "evidence_ref": "docs/tachibana/index/Tachibana-A股-add_on-price_limit-shortlist-intraday-review-v0.1.md#formal-review-shortlist",
    },
    {
        "ts_code": "603008.SH",
        "trade_date": "2026-03-30",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "research_priority_group": "core",
        "formal_review_bucket": "pressure_adjust_reopen",
        "core_snapshot_focus": "pressure_adjust_reopen_core",
        "selection_reason": "Core reopened-touch candidate with cleaner down-limit-side pressure-adjust shape.",
        "evidence_ref": "docs/tachibana/index/Tachibana-A股-add_on-price_limit-shortlist-intraday-review-v0.1.md#formal-review-shortlist",
    },
    {
        "ts_code": "600310.SH",
        "trade_date": "2026-03-30",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "research_priority_group": "core",
        "formal_review_bucket": "pressure_adjust_reopen",
        "core_snapshot_focus": "pressure_adjust_reopen_core",
        "selection_reason": "Core reopened-touch candidate preserving scarce up-limit-side comparison value.",
        "evidence_ref": "docs/tachibana/index/Tachibana-A股-add_on-price_limit-shortlist-intraday-review-v0.1.md#formal-review-shortlist",
    },
    {
        "ts_code": "603687.SH",
        "trade_date": "2026-03-27",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "research_priority_group": "core",
        "formal_review_bucket": "pressure_adjust_reopen",
        "core_snapshot_focus": "pressure_adjust_reopen_core",
        "selection_reason": "Core reopened-touch candidate extending the pressure-adjust comparison set to a fourth sample.",
        "evidence_ref": "docs/tachibana/index/Tachibana-A股-add_on-price_limit-shortlist-intraday-review-v0.1.md#formal-review-shortlist",
    },
    {
        "ts_code": "002663.SZ",
        "trade_date": "2026-04-03",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "research_priority_group": "backup",
        "formal_review_bucket": "near_limit_compare",
        "core_snapshot_focus": "near_limit_compare_backup",
        "selection_reason": "Backup near-limit comparison sample kept for extreme down-limit-side proximity without touch.",
        "evidence_ref": "docs/tachibana/index/Tachibana-A股-add_on-price_limit-shortlist-intraday-review-v0.1.md#formal-review-shortlist",
    },
    {
        "ts_code": "000899.SZ",
        "trade_date": "2026-03-30",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "research_priority_group": "backup",
        "formal_review_bucket": "near_limit_compare",
        "core_snapshot_focus": "near_limit_compare_backup",
        "selection_reason": "Backup near-limit comparison sample kept as a steadier down-limit-side proximity control.",
        "evidence_ref": "docs/tachibana/index/Tachibana-A股-add_on-price_limit-shortlist-intraday-review-v0.1.md#formal-review-shortlist",
    },
]

SNAPSHOT_PRESETS = {
    "meaningful": {
        "malf_background": "alive_wave",
        "wave_range_break_fields": {
            "wave_core_state": "alive",
            "progress_state": "research_selected_clean_window",
        },
    },
    "limited": {
        "malf_background": "pullback",
        "wave_range_break_fields": {
            "pressure_adjustment": True,
        },
    },
    "unknown": {
        "malf_background": "unknown",
        "wave_range_break_fields": {},
    },
    "not_meaningful": {
        "malf_background": "no_structure",
        "wave_range_break_fields": {
            "negative_type": "NM-NO-STRUCTURE",
        },
    },
    "pullback_pressure": {
        "malf_background": "pullback",
        "wave_range_break_fields": {
            "pressure_adjustment": True,
        },
    },
    "range_wait": {
        "malf_background": "range",
        "wave_range_break_fields": {
            "range_state": "alive",
            "no_trade_wait": True,
        },
    },
}
