from __future__ import annotations

import argparse
import json
from pathlib import Path

from ashare_execution_constraint_pipeline import (
    audit_first_batch_execution_constraint_snapshots,
    audit_first_batch_execution_feasibility_gate,
    audit_first_batch_execution_feasibility_outcomes,
    audit_first_batch_execution_feasibility_verdict_merge,
    audit_first_batch_execution_feasibility_verdicts,
    audit_first_batch_institution_constraint_gate,
    audit_first_batch_institution_feasibility_records,
)
from ashare_execution_policy_pipeline import (
    audit_first_batch_execution_policy_archive,
    audit_first_batch_execution_policy_candidates,
    audit_first_batch_execution_policy_research_agenda,
    audit_first_batch_execution_policy_research_prep,
    audit_first_batch_execution_policy_review_merge,
)
from ashare_first_batch_pipeline import (
    audit_first_batch_backtest_input_readiness,
    audit_first_batch_backtest_input_snapshot_drafts,
    audit_first_batch_cognitive_pipeline,
    audit_first_batch_front_filter_run,
    audit_first_batch_method_pm_plan_merge,
    audit_first_batch_method_pm_readiness,
    audit_first_batch_readiness,
    audit_first_batch_record_drafts,
    audit_first_batch_sample_table_trial,
    audit_method_pm_plan_draft_contract,
)
from ashare_intake_contracts import audit_ashare_institution_fact_package, validate_intake_package
from ashare_intake_utils import _read_json_object

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the read-only A-share MALF/Tachibana intake package.")
    parser.add_argument("--root", required=True, help="Formal data root, for example Z:\\asteria-trading-labs-data")
    parser.add_argument(
        "--audit-first-batch-readiness",
        action="store_true",
        help="Aggregate front-filter system audit and intake contract readiness without upgrading candidates.",
    )
    parser.add_argument(
        "--audit-first-batch-front-filter-run",
        action="store_true",
        help="Run the front filter over readiness-approved first-batch candidates without writing sample tables.",
    )
    parser.add_argument(
        "--audit-first-batch-record-drafts",
        action="store_true",
        help="Build read-only qualification record drafts for first-batch candidates that passed the front filter.",
    )
    parser.add_argument(
        "--audit-first-batch-sample-table-trial",
        action="store_true",
        help="Map gate-passed first-batch record drafts into read-only candidate sample-table trial rows.",
    )
    parser.add_argument(
        "--audit-first-batch-method-pm-readiness",
        action="store_true",
        help="Audit whether first-batch structural candidates have independent Method/PM plans without MALF backflow.",
    )
    parser.add_argument(
        "--audit-first-batch-backtest-input-readiness",
        action="store_true",
        help="Audit whether first-batch candidates can build Backtest Input without bypassing Method/PM.",
    )
    parser.add_argument(
        "--audit-first-batch-cognitive-pipeline",
        action="store_true",
        help="Summarize the full first-batch cognitive pipeline and current blocking layer.",
    )
    parser.add_argument(
        "--audit-method-pm-plan-draft",
        help="Audit one manual Method/PM plan draft JSON file without generating actions from MALF.",
    )
    parser.add_argument(
        "--audit-first-batch-method-pm-plan-merge",
        help="Merge a directory of manual Method/PM plan draft JSON files into first-batch readiness.",
    )
    parser.add_argument(
        "--audit-first-batch-backtest-input-snapshots",
        help="Build read-only Backtest Input snapshot drafts from valid first-batch Method/PM plan JSON files.",
    )
    parser.add_argument(
        "--audit-first-batch-institution-constraint-gate",
        help="Audit whether first-batch Backtest Input snapshots may start institution-constraint review without defining rules.",
    )
    parser.add_argument(
        "--audit-first-batch-institution-feasibility-records",
        help="Build read-only A-share execution feasibility audit records after the institution constraint gate.",
    )
    parser.add_argument(
        "--audit-institution-fact-package",
        action="store_true",
        help="Validate read-only A-share institution fact CSVs without defining execution rules.",
    )
    parser.add_argument(
        "--audit-first-batch-execution-constraint-snapshots",
        help="Build read-only execution constraint snapshot drafts from first-batch plans and institution facts.",
    )
    parser.add_argument(
        "--audit-first-batch-execution-feasibility-gate",
        help="Mark execution feasibility audits as evidence-ready when constraint snapshots are linked, without trade decisions.",
    )
    parser.add_argument(
        "--audit-first-batch-execution-feasibility-verdicts",
        help="Build manual-review execution feasibility verdict drafts without trade decisions or position sizing.",
    )
    parser.add_argument(
        "--audit-first-batch-execution-feasibility-verdict-merge",
        help="Merge a directory of manual execution feasibility verdict JSON files into the audit-only verdict layer.",
    )
    parser.add_argument(
        "--audit-first-batch-execution-feasibility-outcomes",
        help="Build read-only execution feasibility outcome records from merged manual verdicts.",
    )
    parser.add_argument(
        "--audit-first-batch-execution-policy-candidates",
        help="Build read-only execution policy candidate audit records from execution feasibility outcomes.",
    )
    parser.add_argument(
        "--audit-first-batch-execution-policy-review-merge",
        help="Merge per-sample manual execution policy review JSON files into read-only candidate review records.",
    )
    parser.add_argument(
        "--audit-first-batch-execution-policy-archive",
        help="Build read-only execution policy archive records from merged candidate reviews.",
    )
    parser.add_argument(
        "--audit-first-batch-execution-policy-research-prep",
        help="Build read-only execution policy research prep records from execution policy archive results.",
    )
    parser.add_argument(
        "--audit-first-batch-execution-policy-research-agenda",
        help="Build read-only execution policy research agenda items from research prep results.",
    )
    parser.add_argument(
        "--method-pm-plan-dir",
        help="Method/PM plan directory required by execution-feasibility verdict merge.",
    )
    parser.add_argument(
        "--institution-fact-root",
        help="Institution fact package root for execution constraint snapshot drafts; defaults to --root.",
    )
    parser.add_argument(
        "--price-limit-event-relation-dir",
        help="Optional reviewed planned-event price-limit relation evidence directory.",
    )
    args = parser.parse_args(argv)

    if args.audit_first_batch_execution_policy_research_prep:
        if not args.method_pm_plan_dir:
            report = {
                "result": "blocked",
                "next_action": "action:prepare_execution_policy_research",
                "issues": ["missing_method_pm_plan_dir_for_execution_policy_research_prep"],
            }
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
        fact_root = args.institution_fact_root or args.root
        report = audit_first_batch_execution_policy_research_prep(
            args.root,
            args.method_pm_plan_dir,
            fact_root,
            args.audit_first_batch_execution_policy_research_prep,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_execution_policy_research_agenda:
        if not args.method_pm_plan_dir:
            report = {
                "result": "blocked",
                "next_action": "action:prepare_execution_policy_research",
                "issues": ["missing_method_pm_plan_dir_for_execution_policy_research_agenda"],
            }
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
        fact_root = args.institution_fact_root or args.root
        report = audit_first_batch_execution_policy_research_agenda(
            args.root,
            args.method_pm_plan_dir,
            fact_root,
            args.audit_first_batch_execution_policy_research_agenda,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_execution_policy_archive:
        if not args.method_pm_plan_dir:
            report = {
                "result": "blocked",
                "next_action": "action:review_execution_policy_archive",
                "issues": ["missing_method_pm_plan_dir_for_execution_policy_archive"],
            }
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
        fact_root = args.institution_fact_root or args.root
        report = audit_first_batch_execution_policy_archive(
            args.root,
            args.method_pm_plan_dir,
            fact_root,
            args.audit_first_batch_execution_policy_archive,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_execution_policy_review_merge:
        if not args.method_pm_plan_dir:
            report = {
                "result": "blocked",
                "next_action": "action:review_execution_policy_candidates",
                "issues": ["missing_method_pm_plan_dir_for_execution_policy_review_merge"],
            }
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
        fact_root = args.institution_fact_root or args.root
        report = audit_first_batch_execution_policy_review_merge(
            args.root,
            args.method_pm_plan_dir,
            fact_root,
            args.audit_first_batch_execution_policy_review_merge,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_execution_policy_candidates:
        if not args.method_pm_plan_dir:
            report = {
                "result": "blocked",
                "next_action": "action:review_execution_feasibility_verdicts",
                "issues": ["missing_method_pm_plan_dir_for_execution_policy_candidates"],
            }
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
        fact_root = args.institution_fact_root or args.root
        report = audit_first_batch_execution_policy_candidates(
            args.root,
            args.method_pm_plan_dir,
            fact_root,
            args.audit_first_batch_execution_policy_candidates,
            args.price_limit_event_relation_dir,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_execution_feasibility_outcomes:
        if not args.method_pm_plan_dir:
            report = {
                "result": "blocked",
                "next_action": "action:review_execution_feasibility_verdicts",
                "issues": ["missing_method_pm_plan_dir_for_execution_feasibility_outcomes"],
            }
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
        fact_root = args.institution_fact_root or args.root
        report = audit_first_batch_execution_feasibility_outcomes(
            args.root,
            args.method_pm_plan_dir,
            fact_root,
            args.audit_first_batch_execution_feasibility_outcomes,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_execution_feasibility_verdict_merge:
        if not args.method_pm_plan_dir:
            report = {
                "result": "blocked",
                "next_action": "action:review_execution_feasibility_verdicts",
                "issues": ["missing_method_pm_plan_dir_for_execution_feasibility_verdict_merge"],
            }
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
        fact_root = args.institution_fact_root or args.root
        report = audit_first_batch_execution_feasibility_verdict_merge(
            args.root,
            args.method_pm_plan_dir,
            fact_root,
            args.audit_first_batch_execution_feasibility_verdict_merge,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_execution_feasibility_verdicts:
        fact_root = args.institution_fact_root or args.root
        report = audit_first_batch_execution_feasibility_verdicts(
            args.root,
            args.audit_first_batch_execution_feasibility_verdicts,
            fact_root,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_execution_feasibility_gate:
        fact_root = args.institution_fact_root or args.root
        report = audit_first_batch_execution_feasibility_gate(
            args.root,
            args.audit_first_batch_execution_feasibility_gate,
            fact_root,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_execution_constraint_snapshots:
        fact_root = args.institution_fact_root or args.root
        report = audit_first_batch_execution_constraint_snapshots(
            args.root,
            args.audit_first_batch_execution_constraint_snapshots,
            fact_root,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_institution_fact_package:
        report = audit_ashare_institution_fact_package(args.root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_institution_feasibility_records:
        report = audit_first_batch_institution_feasibility_records(args.root, args.audit_first_batch_institution_feasibility_records)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_institution_constraint_gate:
        report = audit_first_batch_institution_constraint_gate(args.root, args.audit_first_batch_institution_constraint_gate)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_backtest_input_snapshots:
        report = audit_first_batch_backtest_input_snapshot_drafts(args.root, args.audit_first_batch_backtest_input_snapshots)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_method_pm_plan_merge:
        report = audit_first_batch_method_pm_plan_merge(args.root, args.audit_first_batch_method_pm_plan_merge)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_method_pm_plan_draft:
        draft = _read_json_object(Path(args.audit_method_pm_plan_draft))
        if draft is None:
            report = {
                "result": "blocked",
                "next_action": "action:repair_method_pm_plan_draft",
                "issues": ["invalid_method_pm_plan_draft_json"],
            }
        else:
            report = audit_method_pm_plan_draft_contract(draft)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_cognitive_pipeline:
        report = audit_first_batch_cognitive_pipeline(args.root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_backtest_input_readiness:
        report = audit_first_batch_backtest_input_readiness(args.root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_method_pm_readiness:
        report = audit_first_batch_method_pm_readiness(args.root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_sample_table_trial:
        report = audit_first_batch_sample_table_trial(args.root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_record_drafts:
        report = audit_first_batch_record_drafts(args.root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_front_filter_run:
        report = audit_first_batch_front_filter_run(args.root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_readiness:
        report = audit_first_batch_readiness(args.root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    report = validate_intake_package(args.root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["contract_check_result"] == "pass" else 1
