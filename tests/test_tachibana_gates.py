from tests.tachibana_front_filter_support import *


class TachibanaGatesTest(unittest.TestCase):
    def test_candidate_table_gate_blocks_failed_record_consistency(self) -> None:
        record = {
            "qualification_record_id": "ASHARE-QUAL-BAD-v0.1",
            "candidate_stage_after": "tachibana_candidate",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "qualification_rule_id": "Q-ALIVE-CLEAN",
            "next_action": "action:fill_candidate_table",
            "boundary_warning": ["do_not_infer_position_size_from_malf"],
            "evidence_level": ["E1_malf_snapshot", "E4_research_mapping"],
            "record_consistency": {
                "result": "fail",
                "issues": ["forbidden_record_field:target_position"],
            },
        }

        gate = audit_candidate_table_update_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("record_consistency_failed", gate["issues"])
        self.assertIn("record_consistency_issue:forbidden_record_field:target_position", gate["issues"])

    def test_candidate_table_gate_blocks_missing_evidence_boundary_and_rule(self) -> None:
        record = {
            "qualification_record_id": "ASHARE-QUAL-MISSING-v0.1",
            "candidate_stage_after": "tachibana_candidate",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "qualification_rule_id": None,
            "next_action": "action:fill_candidate_table",
            "boundary_warning": [],
            "evidence_level": [],
            "record_consistency": {"result": "pass", "issues": []},
        }

        gate = audit_candidate_table_update_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("candidate_table_requires_qualification_rule_id", gate["issues"])
        self.assertIn("candidate_table_requires_boundary_warning", gate["issues"])
        self.assertIn("candidate_table_requires_e1_malf_snapshot", gate["issues"])

    def test_candidate_table_gate_blocks_forbidden_trade_fields(self) -> None:
        record = {
            "qualification_record_id": "ASHARE-QUAL-TRADE-FIELD-v0.1",
            "candidate_stage_after": "tachibana_candidate",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "qualification_rule_id": "Q-ALIVE-CLEAN",
            "next_action": "action:fill_candidate_table",
            "boundary_warning": ["do_not_infer_position_size_from_malf"],
            "evidence_level": ["E1_malf_snapshot", "E4_research_mapping"],
            "record_consistency": {"result": "pass", "issues": []},
            "trade_accept": True,
        }

        gate = audit_candidate_table_update_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("candidate_table_forbidden_field:trade_accept", gate["issues"])

    def test_method_pm_bridge_gate_allows_clean_wait_plan_without_pm_action(self) -> None:
        record = {
            "method_action": "wait_no_action",
            "method_status": "hypothesis",
            "method_reason": ["active_waiting"],
            "pm_required": False,
            "execution_intent": "replay_hypothesis_plan",
            "execution_event_type": "hold",
        }

        gate = audit_method_pm_bridge_gate(record)

        self.assertEqual(gate["result"], "pass")
        self.assertEqual(gate["bridge_status"], "method_pm_ready")
        self.assertEqual(gate["next_action"], "action:build_backtest_input_snapshot")
        self.assertEqual(gate["issues"], [])
        self.assertIn("method_action", gate["required_fields_checked"])
        self.assertIn("pm_required", gate["required_fields_checked"])

    def test_method_pm_bridge_gate_blocks_unknown_method_action_and_missing_pm_action(self) -> None:
        record = {
            "method_action": "buy_breakout",
            "method_status": "hypothesis",
            "method_reason": ["staged_execution"],
            "pm_required": True,
            "execution_intent": "replay_hypothesis_plan",
            "execution_event_type": "open",
        }

        gate = audit_method_pm_bridge_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertEqual(gate["bridge_status"], "method_pm_review_required")
        self.assertEqual(gate["next_action"], "action:method_pm_review")
        self.assertIn("method_pm_invalid_method_action:buy_breakout", gate["issues"])
        self.assertIn("method_pm_requires_pm_action_when_pm_required", gate["issues"])

    def test_method_pm_bridge_gate_blocks_malf_derived_pm_fields(self) -> None:
        record = {
            "method_action": "inventory_rebalance",
            "method_status": "hypothesis",
            "method_reason": ["inventory_awareness"],
            "pm_required": True,
            "pm_action": "rebalance",
            "execution_intent": "replay_hypothesis_plan",
            "execution_event_type": "rebalance",
            "center_position_from_malf": 10,
        }

        gate = audit_method_pm_bridge_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("method_pm_forbidden_field:center_position_from_malf", gate["issues"])

    def test_interface_boundary_gate_blocks_data_layer_structure_and_trade_fields(self) -> None:
        record = {
            "interface_layer": "data",
            "ts_code": "000001.SZ",
            "tachibana_applicability": "suitable",
            "target_position": 0.5,
        }

        gate = audit_interface_boundary_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertEqual(gate["next_action"], "action:clean_interface_boundary")
        self.assertIn("data_layer_must_not_write:tachibana_applicability", gate["issues"])
        self.assertIn("data_layer_must_not_write:target_position", gate["issues"])

    def test_interface_boundary_gate_blocks_signal_layer_consuming_rhythm_or_applicability(self) -> None:
        record = {
            "interface_layer": "signal",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "signal_decision": "accept",
            "signal_decision_from_rhythm": "accept",
        }

        gate = audit_interface_boundary_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("signal_layer_must_not_read:rhythm_meaning", gate["issues"])
        self.assertIn("signal_layer_must_not_read:tachibana_applicability", gate["issues"])
        self.assertIn("signal_layer_forbidden_field:signal_decision_from_rhythm", gate["issues"])

    def test_interface_boundary_gate_blocks_backtest_layer_rewriting_structure(self) -> None:
        record = {
            "interface_layer": "backtest",
            "execution_failed": True,
            "rhythm_meaning": "not_meaningful",
            "tachibana_applicability": "unsuitable",
            "structure_suitable": False,
        }

        gate = audit_interface_boundary_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("backtest_layer_must_not_write:rhythm_meaning", gate["issues"])
        self.assertIn("backtest_layer_must_not_write:tachibana_applicability", gate["issues"])
        self.assertIn("backtest_layer_must_not_write:structure_suitable", gate["issues"])

    def test_interface_boundary_gate_allows_tachibana_adapter_context_fields(self) -> None:
        record = {
            "interface_layer": "tachibana_adapter",
            "rhythm_meaning": "limited",
            "tachibana_applicability": "conditional",
            "method_action": "wait_no_action",
            "pm_required": False,
            "execution_intent": "replay_hypothesis_plan",
        }

        gate = audit_interface_boundary_gate(record)

        self.assertEqual(gate["result"], "pass")
        self.assertEqual(gate["next_action"], "action:continue")
        self.assertEqual(gate["issues"], [])

    def test_rhythm_sample_row_gate_allows_clean_alive_wave_meaningful_row(self) -> None:
        row = {
            "sample_id": "1975-01",
            "source_scope": "historical_review",
            "snapshot_quality_status": "ready",
            "malf_background": "alive_wave",
            "qualification_rule_id": "Q-ALIVE-CLEAN",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "pm_complexity": "none",
            "meaning_reason": ["rhythm_meaning_meaningful"],
            "boundary_warning": ["do_not_infer_position_size_from_malf"],
            "evidence_level": ["E1_malf_snapshot", "E4_research_mapping"],
        }

        gate = audit_rhythm_sample_row_gate(row)

        self.assertEqual(gate["result"], "pass")
        self.assertEqual(gate["row_status"], "rhythm_row_ready")
        self.assertEqual(gate["next_action"], "action:fill_candidate_table")
        self.assertEqual(gate["issues"], [])

    def test_rhythm_sample_row_gate_blocks_meaningful_when_pm_complexity_is_high(self) -> None:
        row = {
            "sample_id": "1976-11",
            "source_scope": "historical_review",
            "snapshot_quality_status": "ready",
            "malf_background": "alive_wave",
            "qualification_rule_id": "Q-EXTREME-ADDON",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "pm_complexity": "high",
            "meaning_reason": ["rhythm_meaning_meaningful"],
            "boundary_warning": ["do_not_treat_addon_size_as_structure_strength"],
            "evidence_level": ["E1_malf_snapshot", "E4_research_mapping"],
        }

        gate = audit_rhythm_sample_row_gate(row)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("meaningful_requires_low_pm_complexity", gate["issues"])
        self.assertIn("q_extreme_addon_requires_limited", gate["issues"])

    def test_rhythm_sample_row_gate_blocks_rule_catalog_mismatches(self) -> None:
        row = {
            "sample_id": "BAD-CATALOG",
            "source_scope": "fixture",
            "snapshot_quality_status": "ready",
            "malf_background": "pullback",
            "qualification_rule_id": "Q-PRESSURE-ADJUST",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "pm_complexity": "none",
            "meaning_reason": ["rhythm_meaning_meaningful"],
            "boundary_warning": ["do_not_infer_position_size_from_malf"],
            "evidence_level": ["E1_malf_snapshot"],
        }

        gate = audit_rhythm_sample_row_gate(row)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("rule_catalog_rhythm_mismatch:Q-PRESSURE-ADJUST", gate["issues"])
        self.assertIn("rule_catalog_applicability_mismatch:Q-PRESSURE-ADJUST", gate["issues"])
        self.assertIn("rule_catalog_pm_complexity_mismatch:Q-PRESSURE-ADJUST", gate["issues"])

    def test_rhythm_sample_row_gate_blocks_unknown_qualification_rule_id(self) -> None:
        row = {
            "sample_id": "UNKNOWN-RULE",
            "source_scope": "fixture",
            "snapshot_quality_status": "ready",
            "malf_background": "pullback",
            "qualification_rule_id": "Q-NOT-IN-CATALOG",
            "rhythm_meaning": "limited",
            "tachibana_applicability": "conditional",
            "pm_complexity": "medium",
            "meaning_reason": ["rhythm_meaning_limited"],
            "boundary_warning": ["do_not_infer_position_size_from_malf"],
            "evidence_level": ["E1_malf_snapshot"],
        }

        gate = audit_rhythm_sample_row_gate(row)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("unknown_qualification_rule_id:Q-NOT-IN-CATALOG", gate["issues"])

    def test_rhythm_sample_row_gate_allows_no_structure_not_meaningful_row(self) -> None:
        row = {
            "sample_id": "NM-FIXTURE",
            "source_scope": "synthetic_test_fixture",
            "snapshot_quality_status": "ready",
            "malf_background": "no_structure",
            "qualification_rule_id": "NM-NO-STRUCTURE",
            "rhythm_meaning": "not_meaningful",
            "tachibana_applicability": "unsuitable",
            "pm_complexity": "none",
            "meaning_reason": ["rhythm_meaning_not_meaningful"],
            "boundary_warning": ["do_not_convert_applicability_to_signal_accept"],
            "evidence_level": ["E1_malf_snapshot", "E2_ashare_daily_fact"],
        }

        gate = audit_rhythm_sample_row_gate(row)

        self.assertEqual(gate["result"], "pass")
        self.assertEqual(gate["row_status"], "rhythm_row_ready")
        self.assertEqual(gate["next_action"], "action:research_audit_only")

    def test_rhythm_sample_row_gate_blocks_not_ready_snapshot_from_meaningful(self) -> None:
        row = {
            "sample_id": "PENDING",
            "source_scope": "ashare_real_sample",
            "snapshot_quality_status": "incomplete",
            "malf_background": "alive_wave",
            "qualification_rule_id": "Q-ALIVE-CLEAN",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "pm_complexity": "none",
            "meaning_reason": ["rhythm_meaning_meaningful"],
            "boundary_warning": ["do_not_upgrade_without_malf_snapshot"],
            "evidence_level": ["source_missing"],
        }

        gate = audit_rhythm_sample_row_gate(row)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("non_ready_snapshot_requires_unknown", gate["issues"])
        self.assertIn("non_ready_snapshot_requires_unknown_applicability", gate["issues"])

    def test_cognitive_pipeline_gate_allows_institution_discussion_only_after_all_prior_gates_pass(self) -> None:
        record = {
            "ashare_sample_id": "ASHARE-READY-001",
            "contract_check_result": "pass",
            "eligible_for_malf_run": True,
            "malf_snapshot_ref": "SNAP-READY",
            "snapshot_quality_status": "ready",
            "rhythm_meaning": "limited",
            "tachibana_applicability": "conditional",
            "institution_constraint_need": "execution_feasibility",
            "candidate_table_gate": {"result": "pass", "issues": []},
            "rhythm_sample_row_gate": {"result": "pass", "issues": []},
            "method_pm_bridge_gate": {"result": "pass", "issues": []},
            "interface_boundary_gate": {"result": "pass", "issues": []},
            "backtest_input_gate": {"result": "pass", "mode": "hypothesis_replay", "issues": []},
            "front_filter_system_audit": {"result": "pass", "blocked_audits": []},
        }

        gate = audit_cognitive_pipeline_gate(record)

        self.assertEqual(gate["result"], "pass")
        self.assertTrue(gate["institution_adaptation_allowed"])
        self.assertEqual(gate["next_action"], "action:start_institution_constraint_audit")
        self.assertEqual(gate["issues"], [])

    def test_cognitive_pipeline_gate_blocks_institution_discussion_when_contract_or_need_is_missing(self) -> None:
        record = {
            "ashare_sample_id": "ASHARE-BLOCKED-001",
            "contract_check_result": "fail",
            "eligible_for_malf_run": False,
            "malf_snapshot_ref": None,
            "snapshot_quality_status": "source_missing",
            "rhythm_meaning": "unknown",
            "tachibana_applicability": "unknown",
            "institution_constraint_need": "none",
            "candidate_table_gate": {"result": "blocked", "issues": ["candidate_table_requires_tachibana_candidate"]},
            "rhythm_sample_row_gate": {"result": "blocked", "issues": ["non_ready_snapshot_requires_unknown"]},
            "method_pm_bridge_gate": {"result": "blocked", "issues": ["method_pm_requires_execution_intent"]},
            "interface_boundary_gate": {"result": "pass", "issues": []},
            "backtest_input_gate": {"result": "blocked", "mode": "research_audit", "issues": ["backtest_input_requires_method_plan"]},
            "front_filter_system_audit": {"result": "blocked", "blocked_audits": ["rhythm_sample_catalog"]},
        }

        gate = audit_cognitive_pipeline_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertFalse(gate["institution_adaptation_allowed"])
        self.assertEqual(gate["next_action"], "action:repair_data")
        self.assertIn("pipeline_requires_contract_pass_or_warn", gate["issues"])
        self.assertIn("pipeline_requires_eligible_for_malf_run", gate["issues"])
        self.assertIn("pipeline_requires_ready_malf_snapshot", gate["issues"])
        self.assertIn("pipeline_requires_institution_constraint_need", gate["issues"])
        self.assertIn("pipeline_requires_front_filter_system_audit_pass", gate["issues"])
        self.assertIn("front_filter_system_audit_issue:rhythm_sample_catalog", gate["issues"])

    def test_cognitive_pipeline_gate_blocks_when_front_filter_system_audit_is_missing(self) -> None:
        record = {
            "ashare_sample_id": "ASHARE-NO-SYSTEM-AUDIT",
            "contract_check_result": "pass",
            "eligible_for_malf_run": True,
            "malf_snapshot_ref": "SNAP-READY",
            "snapshot_quality_status": "ready",
            "rhythm_meaning": "limited",
            "tachibana_applicability": "conditional",
            "institution_constraint_need": "execution_feasibility",
            "candidate_table_gate": {"result": "pass", "issues": []},
            "rhythm_sample_row_gate": {"result": "pass", "issues": []},
            "method_pm_bridge_gate": {"result": "pass", "issues": []},
            "interface_boundary_gate": {"result": "pass", "issues": []},
            "backtest_input_gate": {"result": "pass", "mode": "hypothesis_replay", "issues": []},
        }

        gate = audit_cognitive_pipeline_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("pipeline_requires_front_filter_system_audit_pass", gate["issues"])

    def test_backtest_input_gate_blocks_candidate_without_method_pm_plan(self) -> None:
        record = {
            "qualification_record_id": "ASHARE-QUAL-NO-METHOD-v0.1",
            "candidate_stage_after": "tachibana_candidate",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "qualification_rule_id": "Q-ALIVE-CLEAN",
            "next_action": "action:fill_candidate_table",
            "boundary_warning": ["do_not_infer_position_size_from_malf"],
            "evidence_level": ["E1_malf_snapshot", "E4_research_mapping"],
            "record_consistency": {"result": "pass", "issues": []},
            "candidate_table_gate": {
                "result": "pass",
                "issues": [],
                "next_action": "action:fill_candidate_table",
            },
        }

        gate = audit_backtest_input_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertEqual(gate["mode"], "research_audit")
        self.assertEqual(gate["next_action"], "action:method_pm_review")
        self.assertIn("backtest_input_requires_method_plan", gate["issues"])
        self.assertIn("backtest_input_requires_execution_intent", gate["issues"])

    def test_backtest_input_gate_allows_hypothesis_replay_when_method_pm_bridge_is_present(self) -> None:
        record = {
            "qualification_record_id": "ASHARE-QUAL-METHOD-v0.1",
            "candidate_stage_after": "tachibana_candidate",
            "rhythm_meaning": "limited",
            "tachibana_applicability": "conditional",
            "qualification_rule_id": "Q-LOCK-WAIT",
            "next_action": "action:fill_candidate_table",
            "boundary_warning": [
                "do_not_infer_position_size_from_malf",
                "do_not_generate_trade_from_rhythm_meaning_only",
            ],
            "evidence_level": ["E1_malf_snapshot", "E4_research_mapping"],
            "record_consistency": {"result": "pass", "issues": []},
            "candidate_table_gate": {
                "result": "pass",
                "issues": [],
                "next_action": "action:fill_candidate_table",
            },
            "method_action": "wait_no_action",
            "method_status": "hypothesis",
            "method_reason": ["active_waiting"],
            "pm_required": True,
            "pm_action": "hold",
            "method_pm_bridge_gate": {
                "result": "pass",
                "issues": [],
                "next_action": "action:build_backtest_input_snapshot",
            },
            "execution_intent": "replay_hypothesis_plan",
            "execution_event_type": "hold",
        }

        gate = audit_backtest_input_gate(record)

        self.assertEqual(gate["result"], "pass")
        self.assertEqual(gate["mode"], "hypothesis_replay")
        self.assertEqual(gate["next_action"], "action:build_backtest_input_snapshot")
        self.assertEqual(gate["issues"], [])
        self.assertIn("method_action", gate["required_fields_checked"])
        self.assertIn("candidate_table_gate", gate["required_fields_checked"])

    def test_backtest_input_gate_blocks_rhythm_only_and_forbidden_signal_fields(self) -> None:
        record = {
            "qualification_record_id": "ASHARE-QUAL-RHYTHM-ONLY-v0.1",
            "candidate_stage_after": "tachibana_candidate",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "qualification_rule_id": "Q-ALIVE-CLEAN",
            "next_action": "action:fill_candidate_table",
            "boundary_warning": ["do_not_generate_trade_from_rhythm_meaning_only"],
            "evidence_level": ["E1_malf_snapshot", "E4_research_mapping"],
            "record_consistency": {"result": "pass", "issues": []},
            "candidate_table_gate": {
                "result": "pass",
                "issues": [],
                "next_action": "action:fill_candidate_table",
            },
            "method_action": "trend_probe_entry",
            "method_status": "hypothesis",
            "method_reason": ["staged_execution"],
            "pm_required": False,
            "execution_intent": "replay_hypothesis_plan",
            "execution_event_type": "open",
            "signal_decision_from_rhythm": "accept",
        }

        gate = audit_backtest_input_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("backtest_input_forbidden_field:signal_decision_from_rhythm", gate["issues"])

    def test_record_consistency_detects_stage_meaning_and_forbidden_field_contradictions(self) -> None:
        bad_record = {
            "qualification_record_id": "ASHARE-QUAL-BAD-v0.1",
            "candidate_stage_after": "tachibana_candidate",
            "rhythm_meaning": "unknown",
            "tachibana_applicability": "suitable",
            "qualification_rule_id": None,
            "next_action": "action:fill_candidate_table",
            "record_status": "draft",
            "boundary_warning": [],
            "target_position": 0.5,
        }

        audit = audit_qualification_record_consistency(bad_record)

        self.assertEqual(audit["result"], "fail")
        self.assertIn("tachibana_candidate_requires_meaningful_or_limited", audit["issues"])
        self.assertIn("suitable_requires_meaningful", audit["issues"])
        self.assertIn("tachibana_candidate_requires_qualification_rule_id", audit["issues"])
        self.assertIn("forbidden_record_field:target_position", audit["issues"])

    def test_record_consistency_detects_not_meaningful_candidate_table_upgrade(self) -> None:
        bad_record = {
            "qualification_record_id": "ASHARE-QUAL-BAD-NM-v0.1",
            "candidate_stage_after": "rejected",
            "rhythm_meaning": "not_meaningful",
            "tachibana_applicability": "unsuitable",
            "qualification_rule_id": "NM-NO-STRUCTURE",
            "next_action": "action:fill_candidate_table",
            "record_status": "draft",
            "boundary_warning": [],
        }

        audit = audit_qualification_record_consistency(bad_record)

        self.assertEqual(audit["result"], "fail")
        self.assertIn("not_meaningful_must_research_audit_only", audit["issues"])
        self.assertIn("unsuitable_must_not_fill_candidate_table", audit["issues"])
