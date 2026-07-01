from __future__ import annotations

from ashare_intake_utils import _audit_stage_reason_consistency
from ashare_execution_constraint_pipeline import (
    audit_first_batch_execution_constraint_snapshots,
    audit_first_batch_execution_feasibility_gate,
    audit_first_batch_execution_feasibility_outcomes,
    audit_first_batch_execution_feasibility_verdict_merge,
    audit_first_batch_execution_feasibility_verdicts,
    audit_first_batch_institution_constraint_gate,
    audit_first_batch_institution_feasibility_records,
    audit_execution_feasibility_verdict_draft_contract,
)
from ashare_execution_policy_pipeline import (
    audit_execution_policy_review_draft_contract,
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
from ashare_intake_cli import main
from ashare_intake_contracts import audit_ashare_institution_fact_package, validate_intake_package


if __name__ == "__main__":
    raise SystemExit(main())
