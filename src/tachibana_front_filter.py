from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FORBIDDEN_OUTPUT_FIELDS = {
    "buy_signal",
    "sell_signal",
    "trade_accept",
    "target_position",
    "ashare_t1_action",
    "position_size",
    "center_position",
}

CANDIDATE_TABLE_GATE_FIELDS = [
    "record_consistency",
    "rhythm_meaning",
    "tachibana_applicability",
    "qualification_rule_id",
    "boundary_warning",
    "evidence_level",
]

BACKTEST_INPUT_FORBIDDEN_FIELDS = {
    "signal_decision",
    "trade_accept",
    "trade_reject",
    "trade_defer",
    "signal_decision_from_rhythm",
    "trade_accept_from_meaningful",
    "trade_reject_from_not_meaningful",
    "backtest_gate_by_rhythm_only",
    "prediction_direction",
    "target_position_from_malf",
    "center_position_from_malf",
    "lock_confirmed_by_malf",
    "structure_strength_by_size",
}

METHOD_ACTIONS = {
    "trend_probe_entry",
    "trend_confirmation_add",
    "pullback_entry",
    "pullback_add",
    "distribution_reduce",
    "exit_on_rhythm_failure",
    "reversal_flip",
    "inventory_rebalance",
    "wait_no_action",
}

METHOD_STATUSES = {"observed", "inferred", "hypothesis"}

PM_ACTIONS = {
    "open_center",
    "add_on",
    "reduce_add_on",
    "reduce_center",
    "inventory_seed",
    "lock_candidate",
    "unlock",
    "rebalance",
    "clear",
    "hold",
}

METHOD_ACTION_CATALOG = {
    "trend_probe_entry": {
        "layer": "method",
        "pm_required_default": False,
        "execution_replay_allowed": True,
        "malf_can_generate": False,
        "boundary_warning": ["method_action_requires_method_evidence_not_malf_only"],
    },
    "trend_confirmation_add": {
        "layer": "method",
        "pm_required_default": True,
        "execution_replay_allowed": True,
        "malf_can_generate": False,
        "boundary_warning": ["do_not_treat_addon_as_malf_structure_strength"],
    },
    "pullback_entry": {
        "layer": "method",
        "pm_required_default": True,
        "execution_replay_allowed": True,
        "malf_can_generate": False,
        "boundary_warning": ["pullback_entry_requires_method_context"],
    },
    "pullback_add": {
        "layer": "method",
        "pm_required_default": True,
        "execution_replay_allowed": True,
        "malf_can_generate": False,
        "boundary_warning": ["pullback_add_requires_pm_context"],
    },
    "distribution_reduce": {
        "layer": "method",
        "pm_required_default": True,
        "execution_replay_allowed": True,
        "malf_can_generate": False,
        "boundary_warning": ["do_not_infer_reduce_reason_from_malf"],
    },
    "exit_on_rhythm_failure": {
        "layer": "method",
        "pm_required_default": True,
        "execution_replay_allowed": True,
        "malf_can_generate": False,
        "boundary_warning": ["do_not_encode_accept_loss_in_malf"],
    },
    "reversal_flip": {
        "layer": "method",
        "pm_required_default": True,
        "execution_replay_allowed": True,
        "malf_can_generate": False,
        "boundary_warning": ["do_not_treat_reversal_as_malf_decision"],
    },
    "inventory_rebalance": {
        "layer": "method",
        "pm_required_default": True,
        "execution_replay_allowed": True,
        "malf_can_generate": False,
        "boundary_warning": ["inventory_rebalance_requires_pm_context"],
    },
    "wait_no_action": {
        "layer": "method",
        "pm_required_default": False,
        "execution_replay_allowed": False,
        "malf_can_generate": False,
        "boundary_warning": ["do_not_infer_wait_reason_from_malf_only"],
    },
}

PM_ACTION_CATALOG = {
    "open_center": {
        "layer": "pm",
        "state_mutation": True,
        "malf_can_generate": False,
        "boundary_warning": ["do_not_infer_center_position_from_malf"],
    },
    "add_on": {
        "layer": "pm",
        "state_mutation": True,
        "malf_can_generate": False,
        "boundary_warning": ["do_not_treat_addon_size_as_structure_fact"],
    },
    "reduce_add_on": {
        "layer": "pm",
        "state_mutation": True,
        "malf_can_generate": False,
        "boundary_warning": ["do_not_encode_profit_or_loss_reason_in_malf"],
    },
    "reduce_center": {
        "layer": "pm",
        "state_mutation": True,
        "malf_can_generate": False,
        "boundary_warning": ["center_reduction_requires_pm_evidence"],
    },
    "inventory_seed": {
        "layer": "pm",
        "state_mutation": True,
        "malf_can_generate": False,
        "boundary_warning": ["do_not_merge_inventory_seed_into_old_segment"],
    },
    "lock_candidate": {
        "layer": "pm",
        "state_mutation": True,
        "malf_can_generate": False,
        "boundary_warning": ["do_not_confirm_lock_from_dual_inventory_only"],
    },
    "unlock": {
        "layer": "pm",
        "state_mutation": True,
        "malf_can_generate": False,
        "boundary_warning": ["do_not_write_unlock_into_malf"],
    },
    "rebalance": {
        "layer": "pm",
        "state_mutation": True,
        "malf_can_generate": False,
        "boundary_warning": ["rebalance_requires_pm_ledger"],
    },
    "clear": {
        "layer": "pm",
        "state_mutation": True,
        "malf_can_generate": False,
        "boundary_warning": ["do_not_encode_clear_reason_in_malf"],
    },
    "hold": {
        "layer": "pm",
        "state_mutation": False,
        "malf_can_generate": False,
        "boundary_warning": ["hold_reason_requires_method_or_pm_context"],
    },
}

METHOD_PM_FORBIDDEN_FIELDS = {
    "buy_signal",
    "sell_signal",
    "trade_accept",
    "target_position",
    "position_size",
    "center_position_from_malf",
    "target_position_from_malf",
    "lock_confirmed_by_malf",
}

METHOD_PM_BRIDGE_GATE_FIELDS = [
    "method_action",
    "method_status",
    "method_reason",
    "pm_required",
    "pm_action",
    "execution_intent",
    "execution_event_type",
]

INTERFACE_BOUNDARY_GATE_FIELDS = [
    "interface_layer",
    "rhythm_meaning",
    "tachibana_applicability",
    "method_action",
    "pm_action",
    "execution_intent",
]

RHYTHM_SAMPLE_ROW_GATE_FIELDS = [
    "sample_id",
    "source_scope",
    "snapshot_quality_status",
    "malf_background",
    "qualification_rule_id",
    "rhythm_meaning",
    "tachibana_applicability",
    "pm_complexity",
    "meaning_reason",
    "boundary_warning",
    "evidence_level",
]

COGNITIVE_PIPELINE_GATE_FIELDS = [
    "front_filter_system_audit",
    "contract_check_result",
    "eligible_for_malf_run",
    "malf_snapshot_ref",
    "snapshot_quality_status",
    "rhythm_meaning",
    "tachibana_applicability",
    "candidate_table_gate",
    "rhythm_sample_row_gate",
    "method_pm_bridge_gate",
    "interface_boundary_gate",
    "backtest_input_gate",
    "institution_constraint_need",
]

DATA_LAYER_FORBIDDEN_FIELDS = {
    "rhythm_meaning",
    "tachibana_applicability",
    "method_action",
    "pm_action",
    "target_position",
    "trade_accept",
    "signal_decision",
}

SIGNAL_LAYER_FORBIDDEN_FIELDS = {
    "rhythm_meaning",
    "tachibana_applicability",
    "method_action",
    "pm_action",
    "signal_decision_from_rhythm",
    "trade_accept_from_meaningful",
    "trade_reject_from_not_meaningful",
}

BACKTEST_LAYER_FORBIDDEN_WRITES = {
    "rhythm_meaning",
    "tachibana_applicability",
    "structure_suitable",
    "qualification_rule_id",
    "malf_background",
}

INTERFACE_BOUNDARY_CATALOG = {
    "data": {
        "layer": "data",
        "may_read_structure_qualification": False,
        "may_write_structure_qualification": False,
        "may_write_trade_decision": False,
        "forbidden_fields": sorted(DATA_LAYER_FORBIDDEN_FIELDS),
        "boundary_warning": ["data_layer_must_remain_fact_only"],
    },
    "signal": {
        "layer": "signal",
        "may_read_structure_qualification": False,
        "may_write_structure_qualification": False,
        "may_write_trade_decision": False,
        "forbidden_fields": sorted(SIGNAL_LAYER_FORBIDDEN_FIELDS),
        "boundary_warning": ["signal_layer_must_not_front_run_structure_qualification"],
    },
    "backtest": {
        "layer": "backtest",
        "may_read_structure_qualification": True,
        "may_write_structure_qualification": False,
        "may_write_trade_decision": False,
        "forbidden_fields": sorted(BACKTEST_LAYER_FORBIDDEN_WRITES),
        "boundary_warning": ["backtest_layer_consumes_adapter_output_only"],
    },
    "tachibana_adapter": {
        "layer": "tachibana_adapter",
        "may_read_structure_qualification": True,
        "may_write_structure_qualification": True,
        "may_write_trade_decision": False,
        "forbidden_fields": sorted(BACKTEST_INPUT_FORBIDDEN_FIELDS),
        "boundary_warning": ["adapter_writes_structure_qualification_not_trade_decision"],
    },
}

PM_COMPLEXITY_VALUES = {"none", "low", "medium", "high"}
RHYTHM_MEANING_VALUES = {"meaningful", "limited", "not_meaningful", "unknown"}
APPPLICABILITY_BY_RHYTHM = {
    "meaningful": "suitable",
    "limited": "conditional",
    "not_meaningful": "unsuitable",
    "unknown": "unknown",
}
LIMITED_REQUIRED_RULES = {
    "Q-ALIVE-PM-MIXED",
    "Q-EXTREME-ADDON",
    "Q-PRESSURE-ADJUST",
    "Q-REDUCE-WINDOW",
    "Q-NO-TRADE",
    "Q-LOCK-WAIT",
    "Q-SEED-AFTER-CLEAR",
    "Q-CLEAR-RESET",
    "Q-LOCK-CANDIDATE",
    "Q-UNLOCK",
    "Q-SOURCE-DISRUPTED",
}
NOT_MEANINGFUL_RULES = {
    "NM-NO-STRUCTURE",
    "NM-NO-RHYTHM-OBJECT",
    "NM-NOISE-DOMINATED",
    "NM-EVENT-DOMINATED",
}

QUALIFICATION_RULE_CATALOG = {
    "Q-ALIVE-CLEAN": {
        "rhythm_meaning": "meaningful",
        "tachibana_applicability": "suitable",
        "pm_complexity": "none",
        "pm_required": False,
        "candidate_stage_after": "tachibana_candidate",
        "rule_family": "positive",
        "boundary_warning": [
            "do_not_infer_position_size_from_malf",
            "do_not_convert_rhythm_meaning_to_signal_accept",
        ],
    },
    "Q-ALIVE-PM-MIXED": {
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "medium",
        "pm_required": True,
        "candidate_stage_after": "tachibana_candidate",
        "rule_family": "limited",
        "boundary_warning": ["do_not_write_center_or_inventory_state_into_malf"],
    },
    "Q-SEED-AFTER-CLEAR": {
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "high",
        "pm_required": True,
        "candidate_stage_after": "tachibana_candidate",
        "rule_family": "limited",
        "boundary_warning": ["do_not_merge_new_seed_into_old_segment"],
    },
    "Q-EXTREME-ADDON": {
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "high",
        "pm_required": True,
        "candidate_stage_after": "tachibana_candidate",
        "rule_family": "limited",
        "boundary_warning": ["do_not_treat_large_addon_as_structure_fact"],
    },
    "Q-PRESSURE-ADJUST": {
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "medium",
        "pm_required": True,
        "candidate_stage_after": "tachibana_candidate",
        "rule_family": "limited",
        "boundary_warning": ["do_not_merge_pressure_adjustment_into_clean_wave"],
    },
    "Q-REDUCE-WINDOW": {
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "medium",
        "pm_required": True,
        "candidate_stage_after": "tachibana_candidate",
        "rule_family": "limited",
        "boundary_warning": ["do_not_infer_profit_or_loss_reason_from_reduce_only"],
    },
    "Q-NO-TRADE": {
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "low",
        "pm_required": False,
        "candidate_stage_after": "tachibana_candidate",
        "rule_family": "limited",
        "boundary_warning": ["do_not_infer_range_from_no_trade"],
    },
    "Q-LOCK-WAIT": {
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "medium",
        "pm_required": True,
        "candidate_stage_after": "tachibana_candidate",
        "rule_family": "limited",
        "boundary_warning": ["do_not_infer_range_from_no_trade"],
    },
    "Q-CLEAR-RESET": {
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "high",
        "pm_required": True,
        "candidate_stage_after": "tachibana_candidate",
        "rule_family": "limited",
        "boundary_warning": ["do_not_encode_clear_reason_in_malf"],
    },
    "Q-LOCK-CANDIDATE": {
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "high",
        "pm_required": True,
        "candidate_stage_after": "tachibana_candidate",
        "rule_family": "limited",
        "boundary_warning": ["do_not_confirm_lock_from_dual_inventory_only"],
    },
    "Q-UNLOCK": {
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "high",
        "pm_required": True,
        "candidate_stage_after": "tachibana_candidate",
        "rule_family": "limited",
        "boundary_warning": ["do_not_write_unlock_into_malf"],
    },
    "Q-SOURCE-DISRUPTED": {
        "rhythm_meaning": "unknown",
        "tachibana_applicability": "unknown",
        "pm_complexity": "high",
        "pm_required": False,
        "candidate_stage_after": "structure_candidate",
        "rule_family": "blocked",
        "boundary_warning": ["source_disrupted_keep_unknown"],
    },
    "NM-NO-STRUCTURE": {
        "rhythm_meaning": "not_meaningful",
        "tachibana_applicability": "unsuitable",
        "pm_complexity": "none",
        "pm_required": False,
        "candidate_stage_after": "rejected",
        "rule_family": "negative",
        "boundary_warning": ["do_not_apply_tachibana_without_structure_object"],
    },
    "NM-NO-RHYTHM-OBJECT": {
        "rhythm_meaning": "not_meaningful",
        "tachibana_applicability": "unsuitable",
        "pm_complexity": "none",
        "pm_required": False,
        "candidate_stage_after": "rejected",
        "rule_family": "negative",
        "boundary_warning": ["do_not_apply_tachibana_without_rhythm_object"],
    },
    "NM-NOISE-DOMINATED": {
        "rhythm_meaning": "not_meaningful",
        "tachibana_applicability": "unsuitable",
        "pm_complexity": "none",
        "pm_required": False,
        "candidate_stage_after": "rejected",
        "rule_family": "negative",
        "boundary_warning": ["do_not_extract_tachibana_rhythm_from_noise"],
    },
    "NM-EVENT-DOMINATED": {
        "rhythm_meaning": "not_meaningful",
        "tachibana_applicability": "unsuitable",
        "pm_complexity": "none",
        "pm_required": False,
        "candidate_stage_after": "rejected",
        "rule_family": "negative",
        "boundary_warning": ["do_not_replace_structure_qualification_with_event_reason"],
    },
}

RHYTHM_SAMPLE_CATALOG = {
    "1975-01": {
        "sample_id": "1975-01",
        "source_scope": "historical_review",
        "source_anchor": "docs/tachibana/monthly/1975-01.md",
        "snapshot_quality_status": "ready",
        "malf_snapshot_ref": None,
        "malf_background": "alive_wave",
        "qualification_rule_id": "Q-ALIVE-CLEAN",
        "rhythm_meaning": "meaningful",
        "tachibana_applicability": "suitable",
        "pm_complexity": "none",
        "pm_required": False,
        "meaning_reason": ["structure_clean_alive_wave", "rhythm_meaning_meaningful"],
        "boundary_warning": [
            "do_not_infer_position_size_from_malf",
            "do_not_convert_rhythm_meaning_to_signal_accept",
        ],
        "evidence_level": ["E4_research_mapping"],
    },
    "RULE-SAMPLE-Q-ALIVE-PM-MIXED": {
        "sample_id": "RULE-SAMPLE-Q-ALIVE-PM-MIXED",
        "source_scope": "synthetic_rule_fixture",
        "source_anchor": "docs/tachibana/index/MALF-立花结构状态到仓位节奏意义判定准则-v0.1.md",
        "snapshot_quality_status": "ready",
        "malf_snapshot_ref": "fixture:not-real",
        "malf_background": "alive_wave",
        "qualification_rule_id": "Q-ALIVE-PM-MIXED",
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "medium",
        "pm_required": True,
        "meaning_reason": ["alive_wave_pm_mixed", "rhythm_meaning_limited"],
        "boundary_warning": ["do_not_write_center_or_inventory_state_into_malf"],
        "evidence_level": ["E4_research_mapping"],
    },
    "RULE-SAMPLE-Q-SEED-AFTER-CLEAR": {
        "sample_id": "RULE-SAMPLE-Q-SEED-AFTER-CLEAR",
        "source_scope": "historical_review",
        "source_anchor": "docs/tachibana/index/MALF-立花1976-03与07交易段结构资格审计-v0.1.md",
        "snapshot_quality_status": "ready",
        "malf_snapshot_ref": None,
        "malf_background": "break_birth",
        "qualification_rule_id": "Q-SEED-AFTER-CLEAR",
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "high",
        "pm_required": True,
        "meaning_reason": ["seed_after_clear_new_segment", "rhythm_meaning_limited"],
        "boundary_warning": ["do_not_merge_new_seed_into_old_segment"],
        "evidence_level": ["E2_trade_fact", "E4_research_mapping"],
    },
    "1976-11-A": {
        "sample_id": "1976-11-A",
        "source_scope": "historical_review",
        "source_anchor": "docs/tachibana/index/MALF-立花1976-11交易段结构资格审计-v0.1.md",
        "snapshot_quality_status": "ready",
        "malf_snapshot_ref": None,
        "malf_background": "alive_wave",
        "qualification_rule_id": "Q-EXTREME-ADDON",
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "high",
        "pm_required": True,
        "meaning_reason": ["extreme_addon_pm_dominant", "rhythm_meaning_limited"],
        "boundary_warning": ["do_not_treat_large_addon_as_structure_fact"],
        "evidence_level": ["E2_trade_fact", "E4_research_mapping"],
    },
    "RULE-SAMPLE-Q-PRESSURE-ADJUST": {
        "sample_id": "RULE-SAMPLE-Q-PRESSURE-ADJUST",
        "source_scope": "historical_review",
        "source_anchor": "docs/tachibana/index/MALF-立花1976-03与07交易段结构资格审计-v0.1.md",
        "snapshot_quality_status": "ready",
        "malf_snapshot_ref": None,
        "malf_background": "pullback",
        "qualification_rule_id": "Q-PRESSURE-ADJUST",
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "medium",
        "pm_required": True,
        "meaning_reason": ["pressure_adjustment_pm_required", "rhythm_meaning_limited"],
        "boundary_warning": ["do_not_merge_pressure_adjustment_into_clean_wave"],
        "evidence_level": ["E2_trade_fact", "E4_research_mapping"],
    },
    "RULE-SAMPLE-Q-REDUCE-WINDOW": {
        "sample_id": "RULE-SAMPLE-Q-REDUCE-WINDOW",
        "source_scope": "historical_review",
        "source_anchor": "docs/tachibana/index/MALF-立花1976-03与07交易段结构资格审计-v0.1.md",
        "snapshot_quality_status": "ready",
        "malf_snapshot_ref": None,
        "malf_background": "stagnation",
        "qualification_rule_id": "Q-REDUCE-WINDOW",
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "medium",
        "pm_required": True,
        "meaning_reason": ["reduce_window_pm_required", "rhythm_meaning_limited"],
        "boundary_warning": ["do_not_infer_profit_or_loss_reason_from_reduce_only"],
        "evidence_level": ["E2_trade_fact", "E4_research_mapping"],
    },
    "RULE-SAMPLE-Q-NO-TRADE": {
        "sample_id": "RULE-SAMPLE-Q-NO-TRADE",
        "source_scope": "historical_review",
        "source_anchor": "docs/tachibana/monthly/1975-08.md",
        "snapshot_quality_status": "ready",
        "malf_snapshot_ref": None,
        "malf_background": "range",
        "qualification_rule_id": "Q-NO-TRADE",
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "low",
        "pm_required": False,
        "meaning_reason": ["no_trade_waiting_only", "rhythm_meaning_limited"],
        "boundary_warning": ["do_not_infer_range_from_no_trade"],
        "evidence_level": ["E4_research_mapping"],
    },
    "RULE-SAMPLE-Q-LOCK-WAIT": {
        "sample_id": "RULE-SAMPLE-Q-LOCK-WAIT",
        "source_scope": "historical_review",
        "source_anchor": "docs/tachibana/index/MALF-立花1976-04至05交易段结构资格审计-v0.1.md",
        "snapshot_quality_status": "ready",
        "malf_snapshot_ref": None,
        "malf_background": "range",
        "qualification_rule_id": "Q-LOCK-WAIT",
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "medium",
        "pm_required": True,
        "meaning_reason": ["lock_wait_pm_required", "rhythm_meaning_limited"],
        "boundary_warning": ["do_not_infer_range_from_no_trade"],
        "evidence_level": ["E2_trade_fact", "E4_research_mapping"],
    },
    "RULE-SAMPLE-Q-CLEAR-RESET": {
        "sample_id": "RULE-SAMPLE-Q-CLEAR-RESET",
        "source_scope": "historical_review",
        "source_anchor": "docs/tachibana/index/MALF-立花1976-03与07交易段结构资格审计-v0.1.md",
        "snapshot_quality_status": "ready",
        "malf_snapshot_ref": None,
        "malf_background": "stagnation",
        "qualification_rule_id": "Q-CLEAR-RESET",
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "high",
        "pm_required": True,
        "meaning_reason": ["clear_reset_pm_required", "rhythm_meaning_limited"],
        "boundary_warning": ["do_not_encode_clear_reason_in_malf"],
        "evidence_level": ["E2_trade_fact", "E4_research_mapping"],
    },
    "RULE-SAMPLE-Q-LOCK-CANDIDATE": {
        "sample_id": "RULE-SAMPLE-Q-LOCK-CANDIDATE",
        "source_scope": "historical_review",
        "source_anchor": "docs/tachibana/index/MALF-立花1976-04至05交易段结构资格审计-v0.1.md",
        "snapshot_quality_status": "ready",
        "malf_snapshot_ref": None,
        "malf_background": "transition",
        "qualification_rule_id": "Q-LOCK-CANDIDATE",
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "high",
        "pm_required": True,
        "meaning_reason": ["lock_candidate_dual_inventory", "rhythm_meaning_limited"],
        "boundary_warning": ["do_not_confirm_lock_from_dual_inventory_only"],
        "evidence_level": ["E2_trade_fact", "E4_research_mapping"],
    },
    "RULE-SAMPLE-Q-UNLOCK": {
        "sample_id": "RULE-SAMPLE-Q-UNLOCK",
        "source_scope": "historical_review",
        "source_anchor": "docs/tachibana/index/MALF-立花1976-04至05交易段结构资格审计-v0.1.md",
        "snapshot_quality_status": "ready",
        "malf_snapshot_ref": None,
        "malf_background": "transition",
        "qualification_rule_id": "Q-UNLOCK",
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "pm_complexity": "high",
        "pm_required": True,
        "meaning_reason": ["unlock_pm_event", "rhythm_meaning_limited"],
        "boundary_warning": ["do_not_write_unlock_into_malf"],
        "evidence_level": ["E2_trade_fact", "E4_research_mapping"],
    },
    "1976-09": {
        "sample_id": "1976-09",
        "source_scope": "historical_review",
        "source_anchor": "docs/tachibana/index/MALF-立花1976-09制度资料口径审计-v0.1.md",
        "snapshot_quality_status": "ready",
        "malf_snapshot_ref": None,
        "malf_background": "unknown",
        "qualification_rule_id": "Q-SOURCE-DISRUPTED",
        "rhythm_meaning": "unknown",
        "tachibana_applicability": "unknown",
        "pm_complexity": "high",
        "pm_required": False,
        "meaning_reason": ["source_disrupted_keep_unknown", "rhythm_meaning_unknown"],
        "boundary_warning": ["do_not_mix_unit_change_ex_rights_and_structure_qualification"],
        "evidence_level": ["E2_trade_fact", "E3_source_audit"],
    },
    "NM-NO-STRUCTURE-FIXTURE": {
        "sample_id": "NM-NO-STRUCTURE-FIXTURE",
        "source_scope": "synthetic_test_fixture",
        "source_anchor": "docs/tachibana/index/MALF-立花not_meaningful反例登记表-v0.1.md",
        "snapshot_quality_status": "ready",
        "malf_snapshot_ref": "fixture:not-real",
        "malf_background": "no_structure",
        "qualification_rule_id": "NM-NO-STRUCTURE",
        "rhythm_meaning": "not_meaningful",
        "tachibana_applicability": "unsuitable",
        "pm_complexity": "none",
        "pm_required": False,
        "meaning_reason": ["negative_type_nm_no_structure", "rhythm_meaning_not_meaningful"],
        "boundary_warning": ["do_not_apply_tachibana_without_structure_object"],
        "evidence_level": ["E1_malf_snapshot", "E4_research_mapping"],
    },
    "RULE-SAMPLE-NM-NO-RHYTHM-OBJECT": {
        "sample_id": "RULE-SAMPLE-NM-NO-RHYTHM-OBJECT",
        "source_scope": "synthetic_test_fixture",
        "source_anchor": "docs/tachibana/index/MALF-立花not_meaningful反例登记表-v0.1.md",
        "snapshot_quality_status": "ready",
        "malf_snapshot_ref": "fixture:not-real",
        "malf_background": "no_rhythm_object",
        "qualification_rule_id": "NM-NO-RHYTHM-OBJECT",
        "rhythm_meaning": "not_meaningful",
        "tachibana_applicability": "unsuitable",
        "pm_complexity": "none",
        "pm_required": False,
        "meaning_reason": ["no_tachibana_rhythm_object", "rhythm_meaning_not_meaningful"],
        "boundary_warning": ["do_not_apply_tachibana_without_rhythm_object"],
        "evidence_level": ["E1_malf_snapshot", "E4_research_mapping"],
    },
    "RULE-SAMPLE-NM-NOISE-DOMINATED": {
        "sample_id": "RULE-SAMPLE-NM-NOISE-DOMINATED",
        "source_scope": "synthetic_test_fixture",
        "source_anchor": "docs/tachibana/index/MALF-立花not_meaningful反例登记表-v0.1.md",
        "snapshot_quality_status": "ready",
        "malf_snapshot_ref": "fixture:not-real",
        "malf_background": "noise_dominated",
        "qualification_rule_id": "NM-NOISE-DOMINATED",
        "rhythm_meaning": "not_meaningful",
        "tachibana_applicability": "unsuitable",
        "pm_complexity": "none",
        "pm_required": False,
        "meaning_reason": ["noise_dominated_no_rhythm", "rhythm_meaning_not_meaningful"],
        "boundary_warning": ["do_not_extract_tachibana_rhythm_from_noise"],
        "evidence_level": ["E1_malf_snapshot", "E4_research_mapping"],
    },
    "RULE-SAMPLE-NM-EVENT-DOMINATED": {
        "sample_id": "RULE-SAMPLE-NM-EVENT-DOMINATED",
        "source_scope": "synthetic_test_fixture",
        "source_anchor": "docs/tachibana/index/MALF-立花not_meaningful反例登记表-v0.1.md",
        "snapshot_quality_status": "ready",
        "malf_snapshot_ref": "fixture:not-real",
        "malf_background": "event_dominated",
        "qualification_rule_id": "NM-EVENT-DOMINATED",
        "rhythm_meaning": "not_meaningful",
        "tachibana_applicability": "unsuitable",
        "pm_complexity": "none",
        "pm_required": False,
        "meaning_reason": ["event_dominated_no_structure_qualification", "rhythm_meaning_not_meaningful"],
        "boundary_warning": ["do_not_replace_structure_qualification_with_event_reason"],
        "evidence_level": ["E1_malf_snapshot", "E4_research_mapping"],
    },
}

BACKTEST_INPUT_GATE_FIELDS = [
    "candidate_table_gate",
    "method_pm_bridge_gate",
    "rhythm_meaning",
    "tachibana_applicability",
    "qualification_rule_id",
    "boundary_warning",
    "evidence_level",
    "method_action",
    "method_status",
    "method_reason",
    "pm_required",
    "pm_action",
    "execution_intent",
    "execution_event_type",
]


def get_qualification_rule_catalog() -> dict[str, dict[str, Any]]:
    return json.loads(json.dumps(QUALIFICATION_RULE_CATALOG))


def get_method_action_catalog() -> dict[str, dict[str, Any]]:
    return json.loads(json.dumps(METHOD_ACTION_CATALOG))


def get_pm_action_catalog() -> dict[str, dict[str, Any]]:
    return json.loads(json.dumps(PM_ACTION_CATALOG))


def get_interface_boundary_catalog() -> dict[str, dict[str, Any]]:
    return json.loads(json.dumps(INTERFACE_BOUNDARY_CATALOG))


def audit_method_pm_action_catalog(
    method_catalog: dict[str, dict[str, Any]] | None = None,
    pm_catalog: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if method_catalog is None:
        method_catalog = get_method_action_catalog()
    if pm_catalog is None:
        pm_catalog = get_pm_action_catalog()

    invalid_actions: dict[str, list[str]] = {}

    def add_issue(action_id: str, issue: str) -> None:
        invalid_actions.setdefault(action_id, []).append(issue)

    for action_id, action in method_catalog.items():
        if action.get("layer") != "method":
            add_issue(action_id, f"invalid_method_action_layer:{action.get('layer')}")
        if action.get("malf_can_generate") is not False:
            add_issue(action_id, "method_action_must_not_be_generated_by_malf")
        if not isinstance(action.get("pm_required_default"), bool):
            add_issue(action_id, f"invalid_method_pm_required_default:{action.get('pm_required_default')}")
        if not isinstance(action.get("execution_replay_allowed"), bool):
            add_issue(action_id, f"invalid_method_execution_replay_allowed:{action.get('execution_replay_allowed')}")
        if not isinstance(action.get("boundary_warning"), list) or not action.get("boundary_warning"):
            add_issue(action_id, "action_requires_boundary_warning")

    for action_id, action in pm_catalog.items():
        if action.get("layer") != "pm":
            add_issue(action_id, f"invalid_pm_action_layer:{action.get('layer')}")
        if action.get("malf_can_generate") is not False:
            add_issue(action_id, "pm_action_must_not_be_generated_by_malf")
        if not isinstance(action.get("state_mutation"), bool):
            add_issue(action_id, f"invalid_pm_state_mutation:{action.get('state_mutation')}")
        if not isinstance(action.get("boundary_warning"), list) or not action.get("boundary_warning"):
            add_issue(action_id, "action_requires_boundary_warning")

    missing_method_actions = sorted(METHOD_ACTIONS.difference(method_catalog.keys()))
    missing_pm_actions = sorted(PM_ACTIONS.difference(pm_catalog.keys()))
    extra_method_actions = sorted(set(method_catalog).difference(METHOD_ACTIONS))
    extra_pm_actions = sorted(set(pm_catalog).difference(PM_ACTIONS))

    result = "pass"
    if invalid_actions or missing_method_actions or missing_pm_actions or extra_method_actions or extra_pm_actions:
        result = "blocked"

    return {
        "result": result,
        "method_action_count": len(method_catalog),
        "pm_action_count": len(pm_catalog),
        "invalid_actions": invalid_actions,
        "missing_method_actions": missing_method_actions,
        "missing_pm_actions": missing_pm_actions,
        "extra_method_actions": extra_method_actions,
        "extra_pm_actions": extra_pm_actions,
    }


def audit_interface_boundary_catalog(
    catalog: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if catalog is None:
        catalog = get_interface_boundary_catalog()

    required_layers = {"data", "signal", "backtest", "tachibana_adapter"}
    invalid_layers: dict[str, list[str]] = {}

    def add_issue(layer_id: str, issue: str) -> None:
        invalid_layers.setdefault(layer_id, []).append(issue)

    for layer_id, layer in catalog.items():
        if layer.get("layer") != layer_id:
            add_issue(layer_id, f"layer_id_mismatch:{layer.get('layer')}")
        for field in (
            "may_read_structure_qualification",
            "may_write_structure_qualification",
            "may_write_trade_decision",
        ):
            if not isinstance(layer.get(field), bool):
                add_issue(layer_id, f"invalid_boundary_boolean:{field}:{layer.get(field)}")
        if not isinstance(layer.get("forbidden_fields"), list):
            add_issue(layer_id, "layer_requires_forbidden_fields_list")
        if not isinstance(layer.get("boundary_warning"), list) or not layer.get("boundary_warning"):
            add_issue(layer_id, "layer_requires_boundary_warning")

    if catalog.get("data", {}).get("may_write_structure_qualification") is not False:
        add_issue("data", "data_must_not_write_structure_qualification")
    if catalog.get("data", {}).get("may_write_trade_decision") is not False:
        add_issue("data", "data_must_not_write_trade_decision")
    if catalog.get("signal", {}).get("may_read_structure_qualification") is not False:
        add_issue("signal", "signal_must_not_read_structure_qualification")
    if catalog.get("signal", {}).get("may_write_trade_decision") is not False:
        add_issue("signal", "signal_must_not_write_trade_decision")
    if catalog.get("backtest", {}).get("may_write_structure_qualification") is not False:
        add_issue("backtest", "backtest_must_not_write_structure_qualification")
    if catalog.get("tachibana_adapter", {}).get("may_write_trade_decision") is not False:
        add_issue("tachibana_adapter", "adapter_must_not_write_trade_decision")

    missing_layers = sorted(required_layers.difference(catalog.keys()))
    extra_layers = sorted(set(catalog).difference(required_layers))
    result = "pass"
    if invalid_layers or missing_layers or extra_layers:
        result = "blocked"

    return {
        "result": result,
        "layer_count": len(catalog),
        "invalid_layers": invalid_layers,
        "missing_layers": missing_layers,
        "extra_layers": extra_layers,
    }


def audit_qualification_rule_catalog(
    catalog: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if catalog is None:
        catalog = get_qualification_rule_catalog()

    invalid_rules: dict[str, list[str]] = {}
    valid_rule_count = 0
    required_fields = {
        "rhythm_meaning",
        "tachibana_applicability",
        "pm_complexity",
        "pm_required",
        "candidate_stage_after",
        "rule_family",
        "boundary_warning",
    }
    for rule_id, rule in catalog.items():
        issues: list[str] = []
        missing_fields = sorted(required_fields.difference(rule.keys()))
        for field in missing_fields:
            issues.append(f"missing_rule_field:{field}")

        rhythm_meaning = rule.get("rhythm_meaning")
        applicability = rule.get("tachibana_applicability")
        pm_complexity = rule.get("pm_complexity")
        pm_required = rule.get("pm_required")
        boundary_warning = rule.get("boundary_warning")

        if rhythm_meaning not in RHYTHM_MEANING_VALUES:
            issues.append(f"invalid_rule_rhythm_meaning:{rhythm_meaning}")
        if applicability != APPPLICABILITY_BY_RHYTHM.get(rhythm_meaning):
            issues.append("rule_catalog_applicability_mismatch")
        if pm_complexity not in PM_COMPLEXITY_VALUES:
            issues.append(f"invalid_rule_pm_complexity:{pm_complexity}")
        if not isinstance(pm_required, bool):
            issues.append(f"invalid_rule_pm_required:{pm_required}")
        if not isinstance(boundary_warning, list) or not boundary_warning:
            issues.append("rule_requires_boundary_warning")
        if rule_id.startswith("NM-") and rhythm_meaning != "not_meaningful":
            issues.append("nm_rule_requires_not_meaningful")
        if rule_id.startswith("Q-") and rhythm_meaning == "not_meaningful":
            issues.append("q_rule_must_not_be_not_meaningful")

        if issues:
            invalid_rules[rule_id] = issues
        else:
            valid_rule_count += 1

    pending_limited_rules = sorted(LIMITED_REQUIRED_RULES.difference(catalog.keys()))
    pending_not_meaningful_rules = sorted(NOT_MEANINGFUL_RULES.difference(catalog.keys()))
    result = "pass"
    if invalid_rules or pending_limited_rules or pending_not_meaningful_rules:
        result = "blocked"

    return {
        "result": result,
        "defined_rule_count": len(catalog),
        "valid_rule_count": valid_rule_count,
        "invalid_rule_count": len(invalid_rules),
        "invalid_rules": invalid_rules,
        "pending_limited_rules": pending_limited_rules,
        "pending_not_meaningful_rules": pending_not_meaningful_rules,
    }


def get_rhythm_sample_catalog() -> dict[str, dict[str, Any]]:
    return json.loads(json.dumps(RHYTHM_SAMPLE_CATALOG))


def audit_rhythm_sample_catalog(samples: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    if samples is None:
        samples = get_rhythm_sample_catalog()

    blocked_samples: dict[str, dict[str, Any]] = {}
    passed_sample_count = 0
    covered_rule_ids = set()
    for sample_id, row in samples.items():
        row_with_id = {**row, "sample_id": row.get("sample_id", sample_id)}
        qualification_rule_id = row_with_id.get("qualification_rule_id")
        if qualification_rule_id:
            covered_rule_ids.add(str(qualification_rule_id))
        gate = audit_rhythm_sample_row_gate(row_with_id)
        if gate["result"] == "pass":
            passed_sample_count += 1
        else:
            blocked_samples[sample_id] = gate

    missing_rule_ids = sorted(set(QUALIFICATION_RULE_CATALOG).difference(covered_rule_ids))
    sample_count = len(samples)
    return {
        "result": "pass" if not blocked_samples and not missing_rule_ids else "blocked",
        "sample_count": sample_count,
        "passed_sample_count": passed_sample_count,
        "blocked_sample_count": len(blocked_samples),
        "covered_rule_ids": sorted(covered_rule_ids),
        "missing_rule_ids": missing_rule_ids,
        "blocked_samples": blocked_samples,
    }


def audit_front_filter_system(
    qualification_rule_catalog: dict[str, dict[str, Any]] | None = None,
    rhythm_sample_catalog: dict[str, dict[str, Any]] | None = None,
    method_action_catalog: dict[str, dict[str, Any]] | None = None,
    pm_action_catalog: dict[str, dict[str, Any]] | None = None,
    interface_boundary_catalog: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    audits = {
        "qualification_rule_catalog": audit_qualification_rule_catalog(qualification_rule_catalog),
        "rhythm_sample_catalog": audit_rhythm_sample_catalog(rhythm_sample_catalog),
        "method_pm_action_catalog": audit_method_pm_action_catalog(method_action_catalog, pm_action_catalog),
        "interface_boundary_catalog": audit_interface_boundary_catalog(interface_boundary_catalog),
    }
    blocked_audits = [name for name, audit in audits.items() if audit.get("result") != "pass"]
    return {
        "result": "pass" if not blocked_audits else "blocked",
        "blocked_audits": blocked_audits,
        "audits": audits,
    }


def run_front_filter(snapshot_path: str | Path) -> dict[str, Any]:
    snapshot = _read_snapshot(Path(snapshot_path))
    base = _base_report(snapshot)

    if snapshot.get("snapshot_quality_status") != "ready":
        return {
            **base,
            "front_filter_result": "blocked",
            "candidate_stage_after": "structure_candidate",
            "rhythm_meaning": "unknown",
            "tachibana_applicability": "unknown",
            "qualification_rule_id": None,
            "pm_required": False,
            "rule_match_reason": ["blocked_by_malf_snapshot_not_ready"],
            "applicability_reason": ["no_ready_malf_snapshot", "rhythm_meaning_unknown"],
            "boundary_warning": ["do_not_upgrade_ready_snapshot_without_front_filter"],
            "next_action": "action:rerun_malf",
        }

    malf_background = str(snapshot.get("malf_background", "unknown"))
    fields = snapshot.get("wave_range_break_fields", {})
    if not isinstance(fields, dict):
        fields = {}

    if malf_background == "alive_wave" and fields.get("wave_core_state") == "alive":
        return {
            **base,
            "front_filter_result": "pass",
            "candidate_stage_after": "tachibana_candidate",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "qualification_rule_id": "Q-ALIVE-CLEAN",
            "pm_required": False,
            "rule_match_reason": ["matched_q_alive_clean"],
            "applicability_reason": ["structure_clean_alive_wave", "rhythm_meaning_meaningful"],
            "boundary_warning": [
                "do_not_infer_position_size_from_malf",
                "do_not_convert_rhythm_meaning_to_signal_accept",
                "do_not_generate_trade_from_rhythm_meaning_only",
            ],
            "next_action": "action:fill_qualification_record",
        }

    if malf_background == "break_birth" and fields.get("birth_type") == "seed_after_clear":
        return _limited_report(
            base,
            "Q-SEED-AFTER-CLEAR",
            "matched_q_seed_after_clear",
            ["structure_clear_reset_pm_required", "rhythm_meaning_limited"],
            ["do_not_merge_new_seed_into_old_segment"],
        )

    if malf_background == "pullback" and fields.get("pressure_adjustment") is True:
        return _limited_report(
            base,
            "Q-PRESSURE-ADJUST",
            "matched_q_pressure_adjust",
            ["structure_alive_but_pm_required", "rhythm_meaning_limited"],
            ["do_not_merge_pressure_adjustment_into_clean_wave"],
        )

    if malf_background == "range" and fields.get("no_trade_wait") is True:
        return _limited_report(
            base,
            "Q-LOCK-WAIT",
            "matched_q_lock_wait",
            ["structure_no_trade_not_range", "rhythm_meaning_limited"],
            ["do_not_infer_range_from_no_trade"],
        )

    if malf_background == "stagnation" and fields.get("clear_reset") is True:
        return _limited_report(
            base,
            "Q-CLEAR-RESET",
            "matched_q_clear_reset",
            ["structure_clear_reset_pm_required", "rhythm_meaning_limited"],
            ["do_not_encode_clear_reason_in_malf"],
        )

    if fields.get("source_disrupted") is True:
        return {
            **base,
            "front_filter_result": "blocked",
            "candidate_stage_after": "structure_candidate",
            "rhythm_meaning": "unknown",
            "tachibana_applicability": "unknown",
            "qualification_rule_id": "Q-SOURCE-DISRUPTED",
            "pm_required": False,
            "rule_match_reason": ["matched_q_source_disrupted"],
            "applicability_reason": ["source_disrupted_keep_unknown", "rhythm_meaning_unknown"],
            "boundary_warning": [
                "do_not_mix_unit_change_ex_rights_and_structure_qualification",
                "do_not_convert_rhythm_meaning_to_signal_accept",
                "do_not_generate_trade_from_rhythm_meaning_only",
            ],
            "next_action": "action:research_audit_only",
        }

    if fields.get("negative_type") == "NM-NO-STRUCTURE":
        return {
            **base,
            "front_filter_result": "rejected",
            "candidate_stage_after": "rejected",
            "rhythm_meaning": "not_meaningful",
            "tachibana_applicability": "unsuitable",
            "qualification_rule_id": "NM-NO-STRUCTURE",
            "pm_required": False,
            "rule_match_reason": ["matched_nm_no_structure"],
            "applicability_reason": ["negative_type_nm_no_structure", "rhythm_meaning_not_meaningful"],
            "boundary_warning": [
                "do_not_convert_applicability_to_signal_accept",
                "do_not_convert_rhythm_meaning_to_signal_accept",
                "do_not_generate_trade_from_rhythm_meaning_only",
            ],
            "next_action": "action:research_audit_only",
        }

    if malf_background == "unknown":
        return _unknown_report(base, "blocked_by_unknown_malf_background", "action:keep_pending")

    return _unknown_report(base, "no_qualification_rule", "action:keep_pending")


def build_qualification_record_draft(
    front_filter_report: dict[str, Any],
    *,
    ashare_sample_id: str,
    symbol_name: str,
    candidate_stage_before: str = "structure_candidate",
) -> dict[str, Any]:
    ts_code = str(front_filter_report.get("ts_code", "UNKNOWN"))
    window_start = str(front_filter_report.get("window_start", "UNKNOWN"))
    window_end = str(front_filter_report.get("window_end", "UNKNOWN"))
    front_filter_result = front_filter_report.get("front_filter_result", "blocked")
    next_action = front_filter_report.get("next_action", "action:keep_pending")
    candidate_stage_after = front_filter_report.get("candidate_stage_after", "structure_candidate")

    record_status = "draft" if front_filter_result == "pass" else "blocked"
    rule_match_confidence = "high" if front_filter_result == "pass" else "blocked"
    draft_next_action = "action:fill_candidate_table" if front_filter_result == "pass" else next_action

    draft = {
        "qualification_record_id": f"ASHARE-QUAL-{ts_code}-{window_start}-{window_end}-v0.1",
        "ashare_sample_id": ashare_sample_id,
        "ts_code": ts_code,
        "symbol_name": symbol_name,
        "sample_window_start": window_start,
        "sample_window_end": window_end,
        "record_status": record_status,
        "candidate_stage_before": candidate_stage_before,
        "candidate_stage_after": candidate_stage_after,
        "malf_snapshot_ref": front_filter_report.get("malf_snapshot_ref"),
        "snapshot_quality_status": front_filter_report.get("snapshot_quality_status"),
        "malf_background": front_filter_report.get("malf_background", "unknown"),
        "wave_range_break_fields_ref": "front_filter_report.wave_range_break_fields",
        "malf_evidence_ref": [front_filter_report.get("evidence_ref")]
        if front_filter_report.get("evidence_ref")
        else [],
        "qualification_rule_id": front_filter_report.get("qualification_rule_id"),
        "secondary_rule_ids": [],
        "rhythm_meaning": front_filter_report.get("rhythm_meaning", "unknown"),
        "meaning_reason": front_filter_report.get("applicability_reason", []),
        "rule_match_reason": front_filter_report.get("rule_match_reason", []),
        "rule_match_confidence": rule_match_confidence,
        "snapshot_quality_status": front_filter_report.get("snapshot_quality_status"),
        "boundary_warning": front_filter_report.get("boundary_warning", []),
        "tachibana_applicability": front_filter_report.get("tachibana_applicability", "unknown"),
        "applicability_reason": front_filter_report.get("applicability_reason", []),
        "evidence_level": _evidence_level(front_filter_report),
        "pm_complexity": _pm_complexity(front_filter_report),
        "pm_required": front_filter_report.get("pm_required", False),
        "contract_check_result": front_filter_report.get("contract_check_result", "unknown"),
        "eligible_for_malf_run": front_filter_report.get("eligible_for_malf_run", False),
        "institution_constraint_need": front_filter_report.get("institution_constraint_need", "none"),
        "interface_layer": "tachibana_adapter",
        "next_action": draft_next_action,
        "front_filter_result": front_filter_result,
    }
    draft["record_consistency"] = audit_qualification_record_consistency(draft)
    draft["rhythm_sample_row_gate"] = audit_rhythm_sample_row_gate(draft)
    draft["candidate_table_gate"] = audit_candidate_table_update_gate(draft)
    draft["method_pm_bridge_gate"] = audit_method_pm_bridge_gate(draft)
    draft["interface_boundary_gate"] = audit_interface_boundary_gate(draft)
    draft["backtest_input_gate"] = audit_backtest_input_gate(draft)
    draft["front_filter_system_audit"] = audit_front_filter_system()
    draft["cognitive_pipeline_gate"] = audit_cognitive_pipeline_gate(draft)
    return draft


def audit_qualification_record_consistency(record: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    stage = record.get("candidate_stage_after")
    rhythm_meaning = record.get("rhythm_meaning")
    applicability = record.get("tachibana_applicability")
    qualification_rule_id = record.get("qualification_rule_id")
    next_action = record.get("next_action")

    forbidden_fields = sorted(FORBIDDEN_OUTPUT_FIELDS.intersection(record.keys()))
    for field in forbidden_fields:
        issues.append(f"forbidden_record_field:{field}")

    if stage == "tachibana_candidate":
        if rhythm_meaning not in {"meaningful", "limited"}:
            issues.append("tachibana_candidate_requires_meaningful_or_limited")
        if applicability not in {"suitable", "conditional"}:
            issues.append("tachibana_candidate_requires_suitable_or_conditional")
        if not qualification_rule_id:
            issues.append("tachibana_candidate_requires_qualification_rule_id")

    if rhythm_meaning == "meaningful" and applicability != "suitable":
        issues.append("meaningful_requires_suitable")
    if applicability == "suitable" and rhythm_meaning != "meaningful":
        issues.append("suitable_requires_meaningful")
    if rhythm_meaning == "limited" and applicability != "conditional":
        issues.append("limited_requires_conditional")
    if applicability == "conditional" and rhythm_meaning != "limited":
        issues.append("conditional_requires_limited")
    if rhythm_meaning == "unknown" and stage == "tachibana_candidate":
        issues.append("unknown_must_not_be_tachibana_candidate")
    if rhythm_meaning == "not_meaningful":
        if applicability != "unsuitable":
            issues.append("not_meaningful_requires_unsuitable")
        if stage != "rejected":
            issues.append("not_meaningful_requires_rejected_stage")
        if next_action != "action:research_audit_only":
            issues.append("not_meaningful_must_research_audit_only")
    if applicability == "unsuitable" and next_action == "action:fill_candidate_table":
        issues.append("unsuitable_must_not_fill_candidate_table")
    if next_action and not str(next_action).startswith("action:"):
        issues.append(f"next_action_missing_action_prefix:{next_action}")

    return {
        "result": "fail" if issues else "pass",
        "issues": issues,
    }


def audit_candidate_table_update_gate(record: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    stage = record.get("candidate_stage_after")
    rhythm_meaning = record.get("rhythm_meaning")
    applicability = record.get("tachibana_applicability")
    qualification_rule_id = record.get("qualification_rule_id")
    next_action = record.get("next_action")
    boundary_warning = record.get("boundary_warning")
    evidence_level = record.get("evidence_level")
    record_consistency = record.get("record_consistency")

    forbidden_fields = sorted(FORBIDDEN_OUTPUT_FIELDS.intersection(record.keys()))
    for field in forbidden_fields:
        issues.append(f"candidate_table_forbidden_field:{field}")

    if not isinstance(record_consistency, dict) or record_consistency.get("result") != "pass":
        issues.append("record_consistency_failed")
        if isinstance(record_consistency, dict):
            for issue in record_consistency.get("issues", []):
                issues.append(f"record_consistency_issue:{issue}")

    if stage != "tachibana_candidate":
        issues.append("candidate_table_requires_tachibana_candidate")
    if rhythm_meaning not in {"meaningful", "limited"}:
        issues.append("candidate_table_requires_meaningful_or_limited")
    if applicability not in {"suitable", "conditional"}:
        issues.append("candidate_table_requires_suitable_or_conditional")
    if not qualification_rule_id or str(qualification_rule_id).startswith("NM-"):
        issues.append("candidate_table_requires_qualification_rule_id")
    if not boundary_warning:
        issues.append("candidate_table_requires_boundary_warning")
    if not isinstance(evidence_level, list) or "E1_malf_snapshot" not in evidence_level:
        issues.append("candidate_table_requires_e1_malf_snapshot")
    if next_action != "action:fill_candidate_table":
        issues.append("candidate_table_requires_fill_candidate_table_action")
    if stage == "rejected" or rhythm_meaning == "not_meaningful" or applicability == "unsuitable":
        issues.append("candidate_table_blocks_rejected_or_unsuitable")

    if issues:
        blocked_next_action = (
            "action:research_audit_only"
            if stage == "rejected" or rhythm_meaning == "not_meaningful" or applicability == "unsuitable"
            else "action:keep_pending"
        )
        return {
            "result": "blocked",
            "allowed_candidate_stage": stage or "unknown",
            "next_action": blocked_next_action,
            "issues": issues,
            "required_fields_checked": CANDIDATE_TABLE_GATE_FIELDS,
        }

    return {
        "result": "pass",
        "allowed_candidate_stage": "tachibana_candidate",
        "next_action": "action:fill_candidate_table",
        "issues": [],
        "required_fields_checked": CANDIDATE_TABLE_GATE_FIELDS,
    }


def audit_method_pm_bridge_gate(record: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    method_action = record.get("method_action")
    method_status = record.get("method_status")
    method_reason = record.get("method_reason")
    pm_required = record.get("pm_required")
    pm_action = record.get("pm_action")
    execution_intent = record.get("execution_intent")
    execution_event_type = record.get("execution_event_type")

    forbidden_fields = sorted(METHOD_PM_FORBIDDEN_FIELDS.intersection(record.keys()))
    for field in forbidden_fields:
        issues.append(f"method_pm_forbidden_field:{field}")

    if method_action not in METHOD_ACTIONS:
        issues.append(f"method_pm_invalid_method_action:{method_action}")
    if method_status not in METHOD_STATUSES:
        issues.append(f"method_pm_invalid_method_status:{method_status}")
    if not isinstance(method_reason, list) or not method_reason:
        issues.append("method_pm_requires_method_reason")
    if not isinstance(pm_required, bool):
        issues.append("method_pm_requires_pm_required_boolean")
    if pm_required is True:
        if pm_action not in PM_ACTIONS:
            issues.append("method_pm_requires_pm_action_when_pm_required")
    elif pm_action and pm_action not in PM_ACTIONS:
        issues.append(f"method_pm_invalid_pm_action:{pm_action}")
    if execution_intent not in {"replay_observed_action", "replay_hypothesis_plan", "audit_only"}:
        issues.append("method_pm_requires_execution_intent")
    if execution_intent in {"replay_observed_action", "replay_hypothesis_plan"} and not execution_event_type:
        issues.append("method_pm_requires_execution_event_type")

    if issues:
        return {
            "result": "blocked",
            "bridge_status": "method_pm_review_required",
            "next_action": "action:method_pm_review",
            "issues": issues,
            "required_fields_checked": METHOD_PM_BRIDGE_GATE_FIELDS,
        }

    return {
        "result": "pass",
        "bridge_status": "method_pm_ready",
        "next_action": "action:build_backtest_input_snapshot",
        "issues": [],
        "required_fields_checked": METHOD_PM_BRIDGE_GATE_FIELDS,
    }


def audit_interface_boundary_gate(record: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    layer = record.get("interface_layer", "tachibana_adapter")

    if layer == "data":
        for field in sorted(DATA_LAYER_FORBIDDEN_FIELDS.intersection(record.keys())):
            issues.append(f"data_layer_must_not_write:{field}")
    elif layer == "signal":
        for field in sorted({"rhythm_meaning", "tachibana_applicability"}.intersection(record.keys())):
            issues.append(f"signal_layer_must_not_read:{field}")
        for field in sorted(SIGNAL_LAYER_FORBIDDEN_FIELDS.intersection(record.keys())):
            if field not in {"rhythm_meaning", "tachibana_applicability"}:
                issues.append(f"signal_layer_forbidden_field:{field}")
    elif layer == "backtest":
        for field in sorted(BACKTEST_LAYER_FORBIDDEN_WRITES.intersection(record.keys())):
            issues.append(f"backtest_layer_must_not_write:{field}")
    elif layer != "tachibana_adapter":
        issues.append(f"unknown_interface_layer:{layer}")

    if issues:
        return {
            "result": "blocked",
            "interface_layer": layer,
            "next_action": "action:clean_interface_boundary",
            "issues": issues,
            "required_fields_checked": INTERFACE_BOUNDARY_GATE_FIELDS,
        }

    return {
        "result": "pass",
        "interface_layer": layer,
        "next_action": "action:continue",
        "issues": [],
        "required_fields_checked": INTERFACE_BOUNDARY_GATE_FIELDS,
    }


def audit_rhythm_sample_row_gate(row: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    snapshot_quality = row.get("snapshot_quality_status")
    malf_background = row.get("malf_background")
    qualification_rule_id = row.get("qualification_rule_id")
    rhythm_meaning = row.get("rhythm_meaning")
    applicability = row.get("tachibana_applicability")
    pm_complexity = row.get("pm_complexity")
    meaning_reason = row.get("meaning_reason")
    boundary_warning = row.get("boundary_warning")
    evidence_level = row.get("evidence_level")

    if rhythm_meaning not in RHYTHM_MEANING_VALUES:
        issues.append(f"invalid_rhythm_meaning:{rhythm_meaning}")
    if applicability != APPPLICABILITY_BY_RHYTHM.get(rhythm_meaning):
        issues.append("rhythm_applicability_mapping_mismatch")
    if pm_complexity not in PM_COMPLEXITY_VALUES:
        issues.append(f"invalid_pm_complexity:{pm_complexity}")
    if not isinstance(meaning_reason, list) or not meaning_reason:
        issues.append("rhythm_row_requires_meaning_reason")
    if not boundary_warning:
        issues.append("rhythm_row_requires_boundary_warning")
    if not isinstance(evidence_level, list) or not evidence_level:
        issues.append("rhythm_row_requires_evidence_level")

    rule_definition = None
    if qualification_rule_id:
        rule_definition = QUALIFICATION_RULE_CATALOG.get(str(qualification_rule_id))
        if not rule_definition:
            issues.append(f"unknown_qualification_rule_id:{qualification_rule_id}")
        else:
            if rhythm_meaning != rule_definition["rhythm_meaning"]:
                issues.append(f"rule_catalog_rhythm_mismatch:{qualification_rule_id}")
            if applicability != rule_definition["tachibana_applicability"]:
                issues.append(f"rule_catalog_applicability_mismatch:{qualification_rule_id}")
            if pm_complexity != rule_definition["pm_complexity"]:
                issues.append(f"rule_catalog_pm_complexity_mismatch:{qualification_rule_id}")
            if "pm_required" in row and row.get("pm_required") != rule_definition["pm_required"]:
                issues.append(f"rule_catalog_pm_required_mismatch:{qualification_rule_id}")

    if snapshot_quality != "ready":
        if rhythm_meaning != "unknown":
            issues.append("non_ready_snapshot_requires_unknown")
        if applicability != "unknown":
            issues.append("non_ready_snapshot_requires_unknown_applicability")
    if malf_background in {None, "unknown"} and rhythm_meaning != "unknown":
        issues.append("unknown_malf_background_requires_unknown")

    if rhythm_meaning == "meaningful":
        if malf_background != "alive_wave":
            issues.append("meaningful_requires_alive_wave")
        if qualification_rule_id != "Q-ALIVE-CLEAN":
            issues.append("meaningful_requires_q_alive_clean")
        if pm_complexity not in {"none", "low"}:
            issues.append("meaningful_requires_low_pm_complexity")
    if rhythm_meaning == "limited":
        if qualification_rule_id not in LIMITED_REQUIRED_RULES:
            issues.append(f"limited_requires_limited_rule:{qualification_rule_id}")
    if rhythm_meaning == "not_meaningful":
        if not qualification_rule_id or not str(qualification_rule_id).startswith("NM-"):
            issues.append("not_meaningful_requires_nm_rule")
        if qualification_rule_id not in NOT_MEANINGFUL_RULES:
            issues.append(f"unknown_nm_rule:{qualification_rule_id}")
    if qualification_rule_id == "Q-EXTREME-ADDON" and rhythm_meaning != "limited":
        issues.append("q_extreme_addon_requires_limited")
    if qualification_rule_id == "NM-NO-STRUCTURE" and rhythm_meaning != "not_meaningful":
        issues.append("nm_no_structure_requires_not_meaningful")

    if issues:
        next_action = "action:repair_rhythm_sample_row"
        if snapshot_quality != "ready" or malf_background in {None, "unknown"}:
            next_action = "action:keep_pending"
        return {
            "result": "blocked",
            "row_status": "rhythm_row_review_required",
            "next_action": next_action,
            "issues": issues,
            "required_fields_checked": RHYTHM_SAMPLE_ROW_GATE_FIELDS,
        }

    next_action = "action:fill_candidate_table"
    if rhythm_meaning == "not_meaningful":
        next_action = "action:research_audit_only"
    if rhythm_meaning == "unknown":
        next_action = "action:keep_pending"
    return {
        "result": "pass",
        "row_status": "rhythm_row_ready",
        "next_action": next_action,
        "issues": [],
        "required_fields_checked": RHYTHM_SAMPLE_ROW_GATE_FIELDS,
    }


def audit_cognitive_pipeline_gate(record: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    contract_check_result = record.get("contract_check_result", "unknown")
    eligible_for_malf_run = record.get("eligible_for_malf_run", False)
    malf_snapshot_ref = record.get("malf_snapshot_ref")
    snapshot_quality_status = record.get("snapshot_quality_status")
    rhythm_meaning = record.get("rhythm_meaning")
    applicability = record.get("tachibana_applicability")
    institution_constraint_need = record.get("institution_constraint_need")
    front_filter_system_audit = record.get("front_filter_system_audit")

    if not isinstance(front_filter_system_audit, dict) or front_filter_system_audit.get("result") != "pass":
        issues.append("pipeline_requires_front_filter_system_audit_pass")
        if isinstance(front_filter_system_audit, dict):
            for audit_name in front_filter_system_audit.get("blocked_audits", []):
                issues.append(f"front_filter_system_audit_issue:{audit_name}")
    if contract_check_result not in {"pass", "warn"}:
        issues.append("pipeline_requires_contract_pass_or_warn")
    if eligible_for_malf_run is not True:
        issues.append("pipeline_requires_eligible_for_malf_run")
    if not malf_snapshot_ref or snapshot_quality_status != "ready":
        issues.append("pipeline_requires_ready_malf_snapshot")
    if rhythm_meaning not in {"meaningful", "limited"}:
        issues.append("pipeline_requires_meaningful_or_limited")
    if applicability not in {"suitable", "conditional"}:
        issues.append("pipeline_requires_suitable_or_conditional")
    if institution_constraint_need != "execution_feasibility":
        issues.append("pipeline_requires_institution_constraint_need")

    gate_requirements = [
        ("candidate_table_gate", "pipeline_requires_candidate_table_gate_pass"),
        ("rhythm_sample_row_gate", "pipeline_requires_rhythm_sample_row_gate_pass"),
        ("method_pm_bridge_gate", "pipeline_requires_method_pm_bridge_gate_pass"),
        ("interface_boundary_gate", "pipeline_requires_interface_boundary_gate_pass"),
        ("backtest_input_gate", "pipeline_requires_backtest_input_gate_pass"),
    ]
    for field, issue_code in gate_requirements:
        gate = record.get(field)
        if not isinstance(gate, dict) or gate.get("result") != "pass":
            issues.append(issue_code)
            if isinstance(gate, dict):
                for issue in gate.get("issues", []):
                    issues.append(f"{field}_issue:{issue}")

    if issues:
        next_action = "action:method_pm_review"
        if (
            contract_check_result not in {"pass", "warn"}
            or eligible_for_malf_run is not True
            or not malf_snapshot_ref
            or snapshot_quality_status != "ready"
        ):
            next_action = "action:repair_data"
        elif rhythm_meaning in {"not_meaningful", "unknown"} or applicability in {"unsuitable", "unknown"}:
            next_action = "action:research_audit_only"
        return {
            "result": "blocked",
            "institution_adaptation_allowed": False,
            "next_action": next_action,
            "issues": issues,
            "required_fields_checked": COGNITIVE_PIPELINE_GATE_FIELDS,
        }

    return {
        "result": "pass",
        "institution_adaptation_allowed": True,
        "next_action": "action:start_institution_constraint_audit",
        "issues": [],
        "required_fields_checked": COGNITIVE_PIPELINE_GATE_FIELDS,
    }


def audit_backtest_input_gate(record: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    candidate_table_gate = record.get("candidate_table_gate")
    method_pm_bridge_gate = record.get("method_pm_bridge_gate")
    rhythm_meaning = record.get("rhythm_meaning")
    applicability = record.get("tachibana_applicability")
    qualification_rule_id = record.get("qualification_rule_id")
    boundary_warning = record.get("boundary_warning")
    evidence_level = record.get("evidence_level")
    execution_intent = record.get("execution_intent")
    execution_event_type = record.get("execution_event_type")

    forbidden_fields = sorted(BACKTEST_INPUT_FORBIDDEN_FIELDS.intersection(record.keys()))
    for field in forbidden_fields:
        issues.append(f"backtest_input_forbidden_field:{field}")

    if not isinstance(candidate_table_gate, dict) or candidate_table_gate.get("result") != "pass":
        issues.append("candidate_table_gate_not_passed")
        if isinstance(candidate_table_gate, dict):
            for issue in candidate_table_gate.get("issues", []):
                issues.append(f"candidate_table_gate_issue:{issue}")
    if not isinstance(method_pm_bridge_gate, dict) or method_pm_bridge_gate.get("result") != "pass":
        issues.append("method_pm_bridge_gate_not_passed")
        issues.append("backtest_input_requires_method_plan")
        if isinstance(method_pm_bridge_gate, dict):
            for issue in method_pm_bridge_gate.get("issues", []):
                issues.append(f"method_pm_bridge_gate_issue:{issue}")

    if rhythm_meaning not in {"meaningful", "limited"}:
        issues.append("backtest_input_requires_meaningful_or_limited")
    if applicability not in {"suitable", "conditional"}:
        issues.append("backtest_input_requires_suitable_or_conditional")
    if not qualification_rule_id or str(qualification_rule_id).startswith("NM-"):
        issues.append("backtest_input_requires_qualification_rule_id")
    if not boundary_warning:
        issues.append("backtest_input_requires_boundary_warning")
    if not isinstance(evidence_level, list) or "E1_malf_snapshot" not in evidence_level:
        issues.append("backtest_input_requires_e1_malf_snapshot")
    if execution_intent not in {"replay_observed_action", "replay_hypothesis_plan", "audit_only"}:
        issues.append("backtest_input_requires_execution_intent")
    if execution_intent in {"replay_observed_action", "replay_hypothesis_plan"} and not execution_event_type:
        issues.append("backtest_input_requires_execution_event_type")
    if execution_intent == "audit_only":
        issues.append("backtest_input_audit_only_is_not_executable")

    if issues:
        return {
            "result": "blocked",
            "mode": "research_audit",
            "next_action": "action:method_pm_review",
            "issues": issues,
            "required_fields_checked": BACKTEST_INPUT_GATE_FIELDS,
        }

    mode = "observed_replay" if execution_intent == "replay_observed_action" else "hypothesis_replay"
    return {
        "result": "pass",
        "mode": mode,
        "next_action": "action:build_backtest_input_snapshot",
        "issues": [],
        "required_fields_checked": BACKTEST_INPUT_GATE_FIELDS,
    }


def _read_snapshot(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("MALF snapshot must be a JSON object.")
    return payload


def _base_report(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "malf_snapshot_ref": snapshot.get("malf_snapshot_ref"),
        "ts_code": snapshot.get("ts_code"),
        "window_start": snapshot.get("window_start"),
        "window_end": snapshot.get("window_end"),
        "malf_background": snapshot.get("malf_background", "unknown"),
        "snapshot_quality_status": snapshot.get("snapshot_quality_status", "unknown"),
        "evidence_ref": snapshot.get("evidence_ref"),
    }


def _evidence_level(front_filter_report: dict[str, Any]) -> list[str]:
    levels = ["E1_malf_snapshot", "E4_research_mapping"]
    if front_filter_report.get("snapshot_quality_status") != "ready":
        return ["source_missing"]
    return levels


def _pm_complexity(front_filter_report: dict[str, Any]) -> str:
    if front_filter_report.get("front_filter_result") != "pass":
        return "none"
    if front_filter_report.get("rhythm_meaning") == "meaningful":
        return "none"
    if front_filter_report.get("pm_required") is True:
        return "medium"
    return "low"


def _limited_report(
    base: dict[str, Any],
    qualification_rule_id: str,
    rule_match_reason: str,
    applicability_reason: list[str],
    boundary_warning: list[str],
) -> dict[str, Any]:
    return {
        **base,
        "front_filter_result": "pass",
        "candidate_stage_after": "tachibana_candidate",
        "rhythm_meaning": "limited",
        "tachibana_applicability": "conditional",
        "qualification_rule_id": qualification_rule_id,
        "pm_required": True,
        "rule_match_reason": [rule_match_reason],
        "applicability_reason": applicability_reason,
        "boundary_warning": [
            *boundary_warning,
            "do_not_infer_position_size_from_malf",
            "do_not_convert_rhythm_meaning_to_signal_accept",
            "do_not_generate_trade_from_rhythm_meaning_only",
        ],
        "next_action": "action:fill_qualification_record",
    }


def _unknown_report(base: dict[str, Any], rule_reason: str, next_action: str) -> dict[str, Any]:
    return {
        **base,
        "front_filter_result": "blocked",
        "candidate_stage_after": "structure_candidate",
        "rhythm_meaning": "unknown",
        "tachibana_applicability": "unknown",
        "qualification_rule_id": None,
        "pm_required": False,
        "rule_match_reason": [rule_reason],
        "applicability_reason": ["rhythm_meaning_unknown"],
        "boundary_warning": [
            "do_not_upgrade_ready_snapshot_without_front_filter",
            "do_not_convert_rhythm_meaning_to_signal_accept",
            "do_not_generate_trade_from_rhythm_meaning_only",
        ],
        "next_action": next_action,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the read-only MALF/Tachibana front cognitive filter.")
    parser.add_argument("--snapshot", help="Path to a ready MALF snapshot JSON file.")
    parser.add_argument("--audit-rule-catalog", action="store_true", help="Audit the built-in qualification rule catalog and exit.")
    parser.add_argument("--audit-rhythm-samples", action="store_true", help="Audit the built-in rhythm sample catalog and exit.")
    parser.add_argument("--audit-method-pm-actions", action="store_true", help="Audit the built-in Method/PM action catalogs and exit.")
    parser.add_argument("--audit-interface-boundary", action="store_true", help="Audit the built-in Data/Signal/Backtest interface boundary catalog and exit.")
    parser.add_argument("--audit-front-filter-system", action="store_true", help="Run all front-filter catalog and boundary audits and exit.")
    parser.add_argument("--record-draft", action="store_true", help="Emit a qualification record draft instead of the raw front-filter report.")
    parser.add_argument("--ashare-sample-id", default="ASHARE-FIXTURE-TBD", help="A-share sample id for --record-draft.")
    parser.add_argument("--symbol-name", default="UNKNOWN", help="Symbol name for --record-draft.")
    parser.add_argument("--candidate-stage-before", default="structure_candidate", help="Stage before this front-filter run.")
    args = parser.parse_args(argv)

    if args.audit_rule_catalog:
        report = audit_qualification_rule_catalog()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_rhythm_samples:
        report = audit_rhythm_sample_catalog()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_method_pm_actions:
        report = audit_method_pm_action_catalog()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_interface_boundary:
        report = audit_interface_boundary_catalog()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_front_filter_system:
        report = audit_front_filter_system()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if not args.snapshot:
        parser.error("--snapshot is required unless an --audit-* mode is used")

    report = run_front_filter(args.snapshot)
    illegal_fields = sorted(FORBIDDEN_OUTPUT_FIELDS.intersection(report.keys()))
    if illegal_fields:
        report["front_filter_result"] = "invalid"
        report["boundary_warning"] = [*report.get("boundary_warning", []), "forbidden_output_field_present"]
        report["forbidden_output_fields"] = illegal_fields
    if args.record_draft:
        report = build_qualification_record_draft(
            report,
            ashare_sample_id=args.ashare_sample_id,
            symbol_name=args.symbol_name,
            candidate_stage_before=args.candidate_stage_before,
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["front_filter_result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
