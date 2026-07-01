from __future__ import annotations

from typing import Any

from tachibana_front_filter_catalogs import (
    APPPLICABILITY_BY_RHYTHM,
    BACKTEST_INPUT_FORBIDDEN_FIELDS,
    BACKTEST_INPUT_GATE_FIELDS,
    BACKTEST_LAYER_FORBIDDEN_WRITES,
    CANDIDATE_TABLE_GATE_FIELDS,
    COGNITIVE_PIPELINE_GATE_FIELDS,
    DATA_LAYER_FORBIDDEN_FIELDS,
    FORBIDDEN_OUTPUT_FIELDS,
    INTERFACE_BOUNDARY_GATE_FIELDS,
    LIMITED_REQUIRED_RULES,
    METHOD_ACTIONS,
    METHOD_PM_BRIDGE_GATE_FIELDS,
    METHOD_PM_FORBIDDEN_FIELDS,
    METHOD_STATUSES,
    MINIMUM_SAMPLE_COUNT_BY_RHYTHM_MEANING,
    NOT_MEANINGFUL_RULES,
    PM_ACTIONS,
    PM_COMPLEXITY_VALUES,
    QUALIFICATION_RULE_CATALOG,
    RHYTHM_MEANING_VALUES,
    RHYTHM_SAMPLE_ROW_GATE_FIELDS,
    SIGNAL_LAYER_FORBIDDEN_FIELDS,
    get_interface_boundary_catalog,
    get_method_action_catalog,
    get_pm_action_catalog,
    get_qualification_rule_catalog,
    get_rhythm_sample_catalog,
)

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


def audit_rhythm_sample_catalog(samples: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    if samples is None:
        samples = get_rhythm_sample_catalog()

    blocked_samples: dict[str, dict[str, Any]] = {}
    industry_time_alignment_blocked_samples: dict[str, dict[str, Any]] = {}
    passed_sample_count = 0
    covered_rule_ids = set()
    sample_count_by_rhythm_meaning = {rhythm_meaning: 0 for rhythm_meaning in sorted(RHYTHM_MEANING_VALUES)}
    for sample_id, row in samples.items():
        row_with_id = {**row, "sample_id": row.get("sample_id", sample_id)}
        qualification_rule_id = row_with_id.get("qualification_rule_id")
        if qualification_rule_id:
            covered_rule_ids.add(str(qualification_rule_id))
        rhythm_meaning = row_with_id.get("rhythm_meaning")
        if rhythm_meaning in sample_count_by_rhythm_meaning:
            sample_count_by_rhythm_meaning[str(rhythm_meaning)] += 1
        gate = audit_rhythm_sample_row_gate(row_with_id)
        industry_time_alignment = _audit_sample_industry_time_alignment(row_with_id)
        if gate["result"] == "pass" and industry_time_alignment["result"] == "pass":
            passed_sample_count += 1
        else:
            blocked_samples[sample_id] = gate
        if industry_time_alignment["result"] != "pass":
            industry_time_alignment_blocked_samples[sample_id] = industry_time_alignment
            blocked_samples[sample_id] = {
                **gate,
                "result": "blocked",
                "issues": [
                    *gate.get("issues", []),
                    *industry_time_alignment.get("issues", []),
                ],
            }

    missing_rule_ids = sorted(set(QUALIFICATION_RULE_CATALOG).difference(covered_rule_ids))
    covered_rhythm_meanings = sorted(
        rhythm_meaning
        for rhythm_meaning, count in sample_count_by_rhythm_meaning.items()
        if count > 0
    )
    missing_rhythm_meanings = sorted(RHYTHM_MEANING_VALUES.difference(covered_rhythm_meanings))
    undercovered_rhythm_meanings = {
        rhythm_meaning: {
            "actual": sample_count_by_rhythm_meaning[rhythm_meaning],
            "minimum": minimum_count,
        }
        for rhythm_meaning, minimum_count in MINIMUM_SAMPLE_COUNT_BY_RHYTHM_MEANING.items()
        if sample_count_by_rhythm_meaning[rhythm_meaning] < minimum_count
    }
    industry_time_alignment_result = "pass" if not industry_time_alignment_blocked_samples else "blocked"
    sample_count = len(samples)
    return {
        "result": (
            "pass"
            if not blocked_samples
            and not missing_rule_ids
            and not missing_rhythm_meanings
            and not undercovered_rhythm_meanings
            and industry_time_alignment_result == "pass"
            else "blocked"
        ),
        "sample_count": sample_count,
        "passed_sample_count": passed_sample_count,
        "blocked_sample_count": len(blocked_samples),
        "industry_time_alignment_result": industry_time_alignment_result,
        "industry_time_alignment_blocked_count": len(industry_time_alignment_blocked_samples),
        "industry_time_alignment_blocked_samples": industry_time_alignment_blocked_samples,
        "sample_count_by_rhythm_meaning": sample_count_by_rhythm_meaning,
        "minimum_sample_count_by_rhythm_meaning": dict(sorted(MINIMUM_SAMPLE_COUNT_BY_RHYTHM_MEANING.items())),
        "covered_rhythm_meanings": covered_rhythm_meanings,
        "missing_rhythm_meanings": missing_rhythm_meanings,
        "undercovered_rhythm_meanings": undercovered_rhythm_meanings,
        "covered_rule_ids": sorted(covered_rule_ids),
        "missing_rule_ids": missing_rule_ids,
        "blocked_samples": blocked_samples,
    }


def _audit_sample_industry_time_alignment(row: dict[str, Any]) -> dict[str, Any]:
    sample_window_end = str(row.get("sample_window_end") or row.get("window_end") or "")
    industry_valid_from = str(row.get("current_industry_valid_from") or row.get("industry_valid_from") or "")
    industry_valid_to = str(row.get("current_industry_valid_to") or row.get("industry_valid_to") or "")
    issues: list[str] = []

    if sample_window_end and industry_valid_from and industry_valid_from > sample_window_end:
        issues.append("future_industry_label_valid_from_after_sample_window_end")
    if industry_valid_from and industry_valid_to and industry_valid_to < industry_valid_from:
        issues.append("industry_label_valid_to_before_valid_from")

    return {
        "result": "pass" if not issues else "blocked",
        "sample_id": row.get("sample_id"),
        "sample_window_end": sample_window_end or None,
        "current_industry_valid_from": industry_valid_from or None,
        "current_industry_valid_to": industry_valid_to or None,
        "issues": issues,
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
