from __future__ import annotations

from tachibana_front_filter_audits import (
    audit_backtest_input_gate,
    audit_candidate_table_update_gate,
    audit_cognitive_pipeline_gate,
    audit_front_filter_system,
    audit_interface_boundary_catalog,
    audit_interface_boundary_gate,
    audit_method_pm_action_catalog,
    audit_method_pm_bridge_gate,
    audit_qualification_record_consistency,
    audit_qualification_rule_catalog,
    audit_rhythm_sample_catalog,
    audit_rhythm_sample_row_gate,
)
from tachibana_front_filter_catalogs import (
    BACKTEST_INPUT_FORBIDDEN_FIELDS,
    BACKTEST_INPUT_GATE_FIELDS,
    CANDIDATE_TABLE_GATE_FIELDS,
    COGNITIVE_PIPELINE_GATE_FIELDS,
    DATA_LAYER_FORBIDDEN_FIELDS,
    FORBIDDEN_OUTPUT_FIELDS,
    INTERFACE_BOUNDARY_CATALOG,
    INTERFACE_BOUNDARY_GATE_FIELDS,
    LIMITED_REQUIRED_RULES,
    METHOD_ACTION_CATALOG,
    METHOD_ACTIONS,
    METHOD_PM_BRIDGE_GATE_FIELDS,
    METHOD_PM_FORBIDDEN_FIELDS,
    METHOD_STATUSES,
    NOT_MEANINGFUL_RULES,
    PM_ACTION_CATALOG,
    PM_ACTIONS,
    QUALIFICATION_RULE_CATALOG,
    RHYTHM_SAMPLE_CATALOG,
    RHYTHM_SAMPLE_ROW_GATE_FIELDS,
    SIGNAL_LAYER_FORBIDDEN_FIELDS,
    get_interface_boundary_catalog,
    get_method_action_catalog,
    get_pm_action_catalog,
    get_qualification_rule_catalog,
    get_rhythm_sample_catalog,
)
from tachibana_front_filter_cli import main
from tachibana_front_filter_runtime import build_qualification_record_draft, run_front_filter


if __name__ == "__main__":
    raise SystemExit(main())
