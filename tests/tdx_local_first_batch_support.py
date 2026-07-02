from __future__ import annotations

import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ashare_intake_validator import (
    audit_first_batch_front_filter_run,
    audit_first_batch_readiness,
    audit_first_batch_record_drafts,
    audit_first_batch_sample_table_trial,
)
from data_sources.tdx_local import (
    apply_malf_snapshot_manual_review_verdicts,
    apply_qualification_record_draft_manual_verdicts,
    audit_formal_front_filter_review_package,
    audit_add_on_price_limit_shortlist_time_alignment,
    audit_first_batch_sample_coverage,
    audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested,
    audit_formal_institution_rule_definition_when_explicitly_requested,
    audit_formal_institution_rule_definition_write_when_explicitly_requested,
    audit_institution_rule_definition_contract_review_when_explicitly_requested,
    audit_institution_rule_definition_draft_review_gate_when_explicitly_requested,
    audit_institution_rule_definition_readiness_when_explicitly_requested,
    audit_trading_layer_read_gate_contract_when_explicitly_requested,
    audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested,
    build_first_batch_sample_package,
    build_default_add_on_price_limit_shortlist_malf_research_prep,
    prepare_malf_snapshot_draft_review,
    prepare_candidate_table_update_audit_when_explicitly_requested,
    prepare_formal_front_filter_review_package,
    prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested,
    prepare_formal_qualification_record_persistence_package_when_explicitly_requested,
    prepare_formal_qualification_record_write_audit,
    prepare_qualification_record_draft_review,
    review_add_on_price_limit_post_label_daily_malf_structure,
    review_add_on_price_limit_post_label_intraday_reopen,
    materialize_default_add_on_price_limit_core_malf_research_bundle,
    rescreen_add_on_price_limit_post_industry_window,
    build_shortlist_malf_research_prep,
    build_shortlist_sample_package,
    default_add_on_price_limit_shortlist_sample_entries,
    update_candidate_table_from_staged_qualification_records_when_explicitly_requested,
    write_candidate_table_to_formal_data_root_when_explicitly_confirmed,
    write_qualification_records_to_staging_when_explicitly_requested,
)
from tachibana_front_filter import run_front_filter


FORBIDDEN_FIELDS = {
    "buy_signal",
    "trade_accept",
    "target_position",
    "ashare_t1_action",
    "limit_up_strategy",
}

P7_FORBIDDEN_FIELDS = {
    *FORBIDDEN_FIELDS,
    "sell_signal",
    "trade_reject",
    "trade_defer",
    "signal_decision",
    "position_size",
    "limit_down_strategy",
    "industry_hot_score",
    "liquidity_rank_as_applicability",
    "rhythm_meaning_override",
    "tachibana_applicability_override",
}


def write_day_records(path: Path, records: list[tuple[int, int, int, int, int, float, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = b"".join(
        struct.pack("<IIIIIfII", trade_date, open_i, high_i, low_i, close_i, amount, volume, 0)
        for trade_date, open_i, high_i, low_i, close_i, amount, volume in records
    )
    path.write_bytes(payload)




class TdxLocalFirstBatchSupport(unittest.TestCase):
    def _write_single_staged_qualification_record(self, staging_root: Path) -> Path:
        audit_report = {
            "result": "pass",
            "research_only": True,
            "audit_id": "candidate_table_update_audit_package_v0.1",
            "candidate_table_update_audit_result": "pass",
            "candidate_table_update_package_prepared": True,
            "candidate_table_update_performed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "candidate_table_update_audit_packages": [
                {
                    "candidate_table_update_audit_result": "pass",
                    "qualification_record_status": "formal_record_ready_for_persistence",
                    "qualification_record_id": "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1",
                    "ashare_sample_id": "ASHARE-ADDON-600310-20260605",
                    "ts_code": "600310.SH",
                    "symbol_name": "桂东电力",
                    "sample_window_start": "2026-04-23",
                    "sample_window_end": "2026-06-29",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                    "rhythm_meaning": "limited",
                    "tachibana_applicability": "conditional",
                    "source_qualification_record_persistence_performed": False,
                    "candidate_table_update_package_prepared": True,
                    "candidate_table_update_performed": False,
                    "candidate_table_update_allowed": False,
                    "trading_layer_read_allowed": False,
                }
            ],
        }
        write_qualification_records_to_staging_when_explicitly_requested(
            audit_report,
            staging_root=staging_root,
            generated_at="2026-06-30T21:00:00+08:00",
        )
        return staging_root / "qualification-records-v0.1" / "manifest.json"

    def _write_single_staged_candidate_table(self, root: Path) -> Path:
        qualification_manifest = self._write_single_staged_qualification_record(root / "qualification-staging")
        report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
            qualification_record_staging_manifest_path=qualification_manifest,
            candidate_table_staging_root=root / "candidate-staging",
            generated_at="2026-06-30T23:00:00+08:00",
        )
        self.assertEqual(report["result"], "pass")
        return root / "candidate-staging" / "candidate-table-v0.1" / "manifest.json"

    def _write_single_formal_candidate_table(self, root: Path) -> Path:
        staging_manifest = self._write_single_staged_candidate_table(root / "staging")
        formal_data_root = root / "formal-data"
        report = write_candidate_table_to_formal_data_root_when_explicitly_confirmed(
            candidate_table_staging_manifest_path=staging_manifest,
            formal_data_root=formal_data_root,
            confirm_formal_write=True,
            generated_at="2026-07-01T09:00:00+08:00",
        )
        self.assertEqual(report["result"], "pass")
        return formal_data_root / "ashare" / "candidate-table-v0.1" / "manifest.json"

    def _p6_contract_inputs(self, root: Path) -> dict[str, dict]:
        manifest_path = self._write_single_formal_candidate_table(root)
        p5_report = audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested(
            formal_candidate_table_manifest_path=manifest_path,
            generated_at="2026-07-01T10:00:00+08:00",
        )
        self.assertEqual(p5_report["result"], "pass")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return {
            "p5_readiness_report": p5_report,
            "formal_candidate_table_manifest": manifest,
            "method_pm_gate": {
                "result": "pass",
                "gate_id": "method_pm_bridge_gate_v0.1",
                "method_pm_readiness": "pass",
                "signal_generation_allowed": False,
                "backtest_execution_allowed": False,
            },
            "backtest_input_gate": {
                "result": "pass",
                "gate_id": "backtest_input_gate_v0.1",
                "backtest_input_readiness": "pass",
                "signal_generation_allowed": False,
                "backtest_execution_allowed": False,
            },
            "execution_constraint_artifact": {
                "result": "pass",
                "artifact_id": "execution_constraint_snapshot_v0.1",
                "audit_only": True,
                "execution_constraint_audit_only": True,
                "institution_rule_definition_allowed": False,
                "trading_layer_read_allowed": False,
                "signal_generation_allowed": False,
                "backtest_execution_allowed": False,
            },
        }

    def _p7_readiness_inputs(self, root: Path) -> dict[str, dict]:
        p6_report = audit_trading_layer_read_gate_contract_when_explicitly_requested(
            **self._p6_contract_inputs(root),
            generated_at="2026-07-01T11:00:00+08:00",
        )
        self.assertEqual(p6_report["result"], "pass")

        def draft_input(input_type: str) -> dict[str, object]:
            return {
                "result": "pass",
                "artifact_id": f"{input_type}_rule_draft_input_v0.1",
                "rule_draft_input_type": input_type,
                "draft_input_only": True,
                "research_only": True,
                "institution_rule_definition_allowed": False,
                "trading_layer_read_allowed": False,
                "signal_generation_allowed": False,
                "backtest_execution_allowed": False,
            }

        return {
            "p6_contract_report": p6_report,
            "t1_rule_draft_input": draft_input("t1"),
            "price_limit_rule_draft_input": draft_input("price_limit"),
            "suspension_resume_rule_draft_input": draft_input("suspension_resume"),
        }

    def _p7b_draft_review_inputs(self, root: Path) -> dict[str, dict]:
        p7a_report = audit_institution_rule_definition_readiness_when_explicitly_requested(
            **self._p7_readiness_inputs(root),
            generated_at="2026-07-01T12:00:00+08:00",
        )
        self.assertEqual(p7a_report["result"], "pass")

        def reviewed_draft_input(input_type: str) -> dict[str, object]:
            return {
                "result": "pass",
                "artifact_id": f"{input_type}_rule_draft_input_v0.1",
                "rule_draft_input_type": input_type,
                "draft_input_only": True,
                "draft_quality_status": "ready_for_review",
                "field_contract_status": "complete",
                "evidence_refs": [f"unit-test:{input_type}:evidence"],
                "boundary_review_status": "clean",
                "research_only": True,
                "institution_rule_definition_allowed": False,
                "trading_layer_read_allowed": False,
                "signal_generation_allowed": False,
                "backtest_execution_allowed": False,
            }

        return {
            "p7a_readiness_report": p7a_report,
            "t1_rule_draft_input": reviewed_draft_input("t1"),
            "price_limit_rule_draft_input": reviewed_draft_input("price_limit"),
            "suspension_resume_rule_draft_input": reviewed_draft_input("suspension_resume"),
        }

    def _p7c_contract_review_inputs(self, root: Path) -> dict[str, dict]:
        p7b_report = audit_institution_rule_definition_draft_review_gate_when_explicitly_requested(
            **self._p7b_draft_review_inputs(root),
            generated_at="2026-07-01T13:00:00+08:00",
        )
        self.assertEqual(p7b_report["result"], "pass")

        def contract_ready_draft_input(input_type: str) -> dict[str, object]:
            return {
                "result": "pass",
                "artifact_id": f"{input_type}_rule_draft_input_v0.1",
                "rule_draft_input_type": input_type,
                "draft_input_only": True,
                "draft_quality_status": "ready_for_review",
                "field_contract_status": "complete",
                "evidence_refs": [f"unit-test:{input_type}:evidence"],
                "boundary_review_status": "clean",
                "contract_review_status": "ready",
                "definition_contract_fields": [
                    "rule_draft_input_type",
                    "evidence_refs",
                    "boundary_review_status",
                ],
                "consumer_entrypoint": "institution_rule_definition",
                "research_only": True,
                "institution_rule_definition_allowed": False,
                "trading_layer_read_allowed": False,
                "signal_generation_allowed": False,
                "backtest_execution_allowed": False,
            }

        return {
            "p7b_draft_review_gate_report": p7b_report,
            "t1_rule_draft_input": contract_ready_draft_input("t1"),
            "price_limit_rule_draft_input": contract_ready_draft_input("price_limit"),
            "suspension_resume_rule_draft_input": contract_ready_draft_input("suspension_resume"),
        }

    def _p7d_open_gate_inputs(self, root: Path) -> dict[str, dict]:
        contract_review_inputs = self._p7c_contract_review_inputs(root)
        p7c_report = audit_institution_rule_definition_contract_review_when_explicitly_requested(
            **contract_review_inputs,
            generated_at="2026-07-01T14:00:00+08:00",
        )
        self.assertEqual(p7c_report["result"], "pass")

        return {
            "p7c_contract_review_report": p7c_report,
            "t1_rule_draft_input": contract_review_inputs["t1_rule_draft_input"],
            "price_limit_rule_draft_input": contract_review_inputs["price_limit_rule_draft_input"],
            "suspension_resume_rule_draft_input": contract_review_inputs["suspension_resume_rule_draft_input"],
            "explicit_open_gate_decision": {
                "result": "pass",
                "gate_decision": "approve_institution_rule_definition_only",
                "gate_scope": "institution_rule_definition_only",
                "approved_by": "unit-test-reviewer",
                "approval_evidence_refs": ["unit-test:open-gate-approval"],
                "acknowledged_no_trading_layer_read": True,
                "acknowledged_no_signal_generation": True,
                "acknowledged_no_backtest_execution": True,
                "institution_rule_definition_allowed": False,
                "trading_layer_read_allowed": False,
                "signal_generation_allowed": False,
                "backtest_execution_allowed": False,
            },
        }

    def _p7e_formal_rule_definition_inputs(self, root: Path) -> dict[str, dict]:
        open_gate_inputs = self._p7d_open_gate_inputs(root)
        p7d_report = audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested(
            **open_gate_inputs,
            generated_at="2026-07-01T15:00:00+08:00",
        )
        self.assertEqual(p7d_report["result"], "pass")

        return {
            "p7d_open_gate_report": p7d_report,
            "t1_rule_draft_input": open_gate_inputs["t1_rule_draft_input"],
            "price_limit_rule_draft_input": open_gate_inputs["price_limit_rule_draft_input"],
            "suspension_resume_rule_draft_input": open_gate_inputs["suspension_resume_rule_draft_input"],
            "formal_institution_rule_definition_input": {
                "artifact_id": "formal_institution_rule_definition_input_v0.1",
                "definition_scope": "institution_rule_definition_only",
                "definition_input_status": "ready_for_audit",
                "consumed_reviewed_draft_inputs": ["t1", "price_limit", "suspension_resume"],
                "field_contract_status": "complete",
                "boundary_review_status": "clean",
                "evidence_refs": ["unit-test:formal-rule-definition:evidence"],
                "formal_definition_fields": [
                    "rule_family",
                    "applicable_market_scope",
                    "constraint_expression",
                ],
                "institution_rule_definition_allowed": True,
                "trading_layer_read_allowed": False,
                "signal_generation_allowed": False,
                "backtest_execution_allowed": False,
            },
        }

    def _p8_formal_rule_definition_persistence_package_inputs(self, root: Path) -> dict[str, dict]:
        p7e_inputs = self._p7e_formal_rule_definition_inputs(root)
        p7e_report = audit_formal_institution_rule_definition_when_explicitly_requested(
            **p7e_inputs,
            generated_at="2026-07-01T16:00:00+08:00",
        )
        self.assertEqual(p7e_report["result"], "pass")
        return {
            "p7e_formal_rule_definition_report": p7e_report,
            "formal_institution_rule_definition_payload": p7e_inputs["formal_institution_rule_definition_input"],
        }

    def _p8_prepared_package_report(self, root: Path) -> dict[str, object]:
        inputs = self._p8_formal_rule_definition_persistence_package_inputs(root)
        report = prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested(
            **inputs,
            generated_at="2026-07-01T16:10:00+08:00",
        )
        self.assertEqual(report["result"], "pass")
        return report

    def _formal_rule_definition_write_audit_request(
        self,
        package_report: dict[str, object],
    ) -> dict[str, object]:
        return {
            "write_audit_requested": True,
            "write_audit_scope": "formal_institution_rule_definition",
            "target_kind": "formal_rule_definition_file",
            "target_package_id": package_report["package_id"],
            "target_package_version": package_report["package_version"],
            "real_data_root_write_confirmed": False,
            "manual_confirmation_required": True,
            "no_trading_no_signal_no_backtest_acknowledged": True,
        }



__all__ = [name for name in globals() if not name.startswith("__")]
