import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tachibana_front_filter import (
    audit_backtest_input_gate,
    audit_candidate_table_update_gate,
    audit_cognitive_pipeline_gate,
    audit_front_filter_system,
    audit_interface_boundary_gate,
    audit_interface_boundary_catalog,
    audit_method_pm_bridge_gate,
    audit_method_pm_action_catalog,
    audit_qualification_rule_catalog,
    audit_qualification_record_consistency,
    audit_rhythm_sample_catalog,
    audit_rhythm_sample_row_gate,
    build_qualification_record_draft,
    get_interface_boundary_catalog,
    get_method_action_catalog,
    get_pm_action_catalog,
    get_qualification_rule_catalog,
    get_rhythm_sample_catalog,
    run_front_filter,
)


FORBIDDEN_OUTPUT_FIELDS = {
    "buy_signal",
    "sell_signal",
    "trade_accept",
    "target_position",
    "ashare_t1_action",
    "position_size",
    "center_position",
}


def write_snapshot(root: Path, payload: dict) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "snapshot.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
