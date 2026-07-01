from __future__ import annotations

from pathlib import Path
from typing import Any

from ashare_intake_constants import *
from ashare_intake_utils import *

def audit_ashare_institution_fact_package(data_root: str | Path) -> dict[str, Any]:
    root = Path(data_root)
    fact_dir = root / "ashare" / "institution-facts-v0.1"
    failed: list[str] = []
    fact_files: list[str] = []
    fact_count = 0

    _require_dir(fact_dir, "ashare/institution-facts-v0.1", failed)
    if fact_dir.exists():
        csv_files = sorted(fact_dir.glob("*.csv"))
        if not csv_files:
            failed.append("empty_dir:ashare/institution-facts-v0.1")
        for fact_file in csv_files:
            _check_institution_fact_file(fact_file, root, failed)
            rows = _read_csv_rows(fact_file)
            fact_count += len(rows)
            try:
                fact_files.append(fact_file.relative_to(root).as_posix())
            except ValueError:
                fact_files.append(str(fact_file))

    result = "pass" if not failed else "blocked"
    return {
        "result": result,
        "institution_fact_status": "ready" if result == "pass" else ("missing" if not fact_dir.exists() else "invalid"),
        "institution_fact_count": fact_count if result == "pass" else 0,
        "institution_fact_files": fact_files if result == "pass" else [],
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": "action:build_execution_constraint_snapshots"
        if result == "pass"
        else "action:repair_institution_fact_package",
        "failed_contract_items": failed,
        "required_fields": REQUIRED_INSTITUTION_FACT_FIELDS,
        "boundary_warning": [
            "institution_facts_are_execution_facts_not_rules",
            "do_not_use_institution_facts_as_structure_qualification",
            "do_not_emit_signal_from_institution_facts",
        ],
    }


def validate_intake_package(data_root: str | Path) -> dict[str, Any]:
    root = Path(data_root)
    ashare_dir = root / "ashare"
    candidate_file = ashare_dir / "candidate-universe-v0.1.csv"
    sw_file = ashare_dir / "sw-industry-membership-v0.1.csv"
    daily_dir = ashare_dir / "daily-window-v0.1"
    snapshot_dir = ashare_dir / "malf-snapshots-v0.1"

    failed: list[str] = []
    warnings: list[str] = []

    _require_file(candidate_file, "ashare/candidate-universe-v0.1.csv", failed)
    _require_file(sw_file, "ashare/sw-industry-membership-v0.1.csv", failed)
    _require_dir(daily_dir, "ashare/daily-window-v0.1", failed)
    _require_dir(snapshot_dir, "ashare/malf-snapshots-v0.1", failed)

    if candidate_file.exists():
        _check_csv_file(candidate_file, REQUIRED_CANDIDATE_FIELDS, failed)
        _check_candidate_rows(candidate_file, failed)
    if sw_file.exists():
        _check_csv_file(sw_file, REQUIRED_SW_FIELDS, failed)
        _check_sw_rows(sw_file, failed)
    if daily_dir.exists():
        daily_files = sorted(daily_dir.glob("*.csv"))
        if not daily_files:
            failed.append("empty_dir:ashare/daily-window-v0.1")
        for daily_file in daily_files:
            _check_csv_file(daily_file, REQUIRED_DAILY_FIELDS, failed)
            _check_daily_rows(daily_file, failed)
    if snapshot_dir.exists():
        snapshot_files = sorted(snapshot_dir.glob("*.json"))
        if not snapshot_files:
            failed.append("empty_dir:ashare/malf-snapshots-v0.1")
        for snapshot_file in snapshot_files:
            _check_snapshot_file(snapshot_file, failed)

    if candidate_file.exists() and sw_file.exists() and daily_dir.exists() and snapshot_dir.exists():
        _check_cross_file_consistency(candidate_file, sw_file, daily_dir, snapshot_dir, failed)

    stage_summary = _build_candidate_stage_summary(candidate_file, sw_file, daily_dir, snapshot_dir)
    failed_reason_codes = _map_failed_items_to_reason_codes(failed)
    stage_reason_consistency = _audit_stage_reason_consistency(stage_summary, failed_reason_codes)
    status = _package_status(candidate_file, sw_file, daily_dir, snapshot_dir, failed)
    result = "fail" if failed else ("warn" if warnings else "pass")
    eligible = result == "pass" and status == "ready"

    return {
        "data_root": str(root),
        "ashare_dir": str(ashare_dir),
        "intake_package_status": status,
        "contract_check_result": result,
        "eligible_for_malf_run": eligible,
        "eligible_for_structure_candidate": eligible,
        "eligible_for_tachibana_candidate": False,
        "candidate_stage_summary": stage_summary,
        "stage_reason_consistency": stage_reason_consistency,
        "failed_contract_items": failed,
        "failed_contract_reason_codes": failed_reason_codes,
        "warnings": warnings,
    }
