from __future__ import annotations

import re

REQUIRED_CANDIDATE_FIELDS = [
    "ts_code",
    "symbol_name",
    "board_type",
    "list_date",
    "is_st",
    "is_new_stock_window",
    "data_quality_status",
    "source_ref",
]

REQUIRED_SW_FIELDS = [
    "ts_code",
    "sw_l1_name",
    "sw_l2_name",
    "valid_from",
    "valid_to",
    "source_ref",
]

REQUIRED_DAILY_FIELDS = [
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

REQUIRED_SNAPSHOT_FIELDS = [
    "malf_snapshot_ref",
    "ts_code",
    "window_start",
    "window_end",
    "source_daily_file",
    "generated_at",
    "malf_version",
    "malf_background",
    "wave_range_break_fields",
    "evidence_ref",
    "snapshot_quality_status",
]

REQUIRED_INSTITUTION_FACT_FIELDS = [
    "ts_code",
    "trade_date",
    "is_trading_day",
    "is_suspended",
    "limit_up_price",
    "limit_down_price",
    "close_limit_status",
    "touched_limit_status",
    "board_lot_size",
    "source_ref",
]

FORBIDDEN_FIELDS = {
    "buy_signal",
    "sell_signal",
    "trade_accept",
    "target_position",
    "ashare_t1_action",
    "limit_up_strategy",
    "limit_down_strategy",
    "industry_hot_score",
    "liquidity_rank_as_applicability",
}

BOARD_TYPES = {"main", "gem", "star", "bse", "unknown"}
QUALITY_STATUSES = {"ready", "incomplete", "source_missing", "disputed"}
BOOLEAN_VALUES = {"true", "false"}
LIMIT_CLOSE_STATUSES = {"none", "limit_up", "limit_down", "near_limit_up", "near_limit_down", "unknown"}
TOUCHED_LIMIT_STATUSES = {"none", "touched_up", "touched_down", "both", "unknown"}
PRICE_LIMIT_EVENT_RELATION_STATUSES = {
    "relation_clear",
    "relation_constrained",
    "relation_blocked",
    "relation_unknown",
}
PRICE_LIMIT_EVENT_FILL_BLOCKING_STATUSES = {
    "no_explicit_fill_blocking_fact",
    "explicit_fill_blocking_fact",
    "fill_blocking_unknown",
    "not_applicable",
}
PRICE_LIMIT_EVENT_LIMIT_PROXIMITY_STATUSES = {
    "not_near_limit",
    "near_limit",
    "at_limit",
    "proximity_unknown",
    "not_applicable",
}
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
METHOD_PM_PLAN_DRAFT_FIELDS = [
    "ashare_sample_id",
    "ts_code",
    "method_action",
    "method_status",
    "method_reason",
    "pm_required",
    "pm_action",
    "execution_intent",
    "execution_event_type",
    "method_evidence_ref",
]

INSTITUTION_GATE_FORBIDDEN_FIELDS = {
    "ashare_t1_action",
    "limit_up_strategy",
    "limit_down_strategy",
    "trade_accept",
    "trade_reject",
    "trade_defer",
    "signal_decision",
    "target_position",
    "structure_suitable",
    "rhythm_meaning_override",
    "tachibana_applicability_override",
}

EXECUTION_FEASIBILITY_VERDICT_STATUSES = [
    "not_evaluated",
    "evidence_ready",
    "executable",
    "constrained",
    "blocked",
    "carry_forward_required",
    "blocked_by_fact_review",
]
MANUAL_EXECUTION_FEASIBILITY_VERDICT_STATUSES = [
    "not_evaluated",
    "executable",
    "constrained",
    "blocked",
    "carry_forward_required",
]
MANUAL_EXECUTION_FEASIBILITY_VERDICT_FIELDS = [
    "ashare_sample_id",
    "ts_code",
    "feasibility_status",
    "verdict_reason",
    "blocked_reason",
    "carry_forward_required",
    "evidence_ref",
]
EXECUTION_POLICY_CANDIDATE_TYPES = [
    "t1",
    "price_limit",
    "suspension_resume",
]
MANUAL_EXECUTION_POLICY_REVIEW_STATUSES = [
    "review_required",
    "evidence_incomplete",
    "carry_forward_required",
    "blocked",
]
MANUAL_EXECUTION_POLICY_REVIEW_FIELDS = [
    "ashare_sample_id",
    "ts_code",
    "candidate_reviews",
]
MANUAL_EXECUTION_POLICY_REVIEW_CANDIDATE_FIELDS = [
    "candidate_constraint_type",
    "review_status",
    "review_reason",
    "blocked_reason",
    "evidence_ref",
]
