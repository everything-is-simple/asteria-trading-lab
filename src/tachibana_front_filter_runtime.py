from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tachibana_front_filter_audits import (
    audit_backtest_input_gate,
    audit_candidate_table_update_gate,
    audit_cognitive_pipeline_gate,
    audit_front_filter_system,
    audit_interface_boundary_gate,
    audit_method_pm_bridge_gate,
    audit_qualification_record_consistency,
    audit_rhythm_sample_row_gate,
)

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
