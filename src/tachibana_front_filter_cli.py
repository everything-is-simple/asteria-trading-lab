from __future__ import annotations

import argparse
import json

from tachibana_front_filter_audits import (
    audit_front_filter_system,
    audit_interface_boundary_catalog,
    audit_method_pm_action_catalog,
    audit_qualification_rule_catalog,
    audit_rhythm_sample_catalog,
)
from tachibana_front_filter_catalogs import FORBIDDEN_OUTPUT_FIELDS
from tachibana_front_filter_runtime import build_qualification_record_draft, run_front_filter

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
