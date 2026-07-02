# Price Limit Relation Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow the execution-policy candidate pipeline to consume reviewed planned-event price-limit relation evidence so `300750.SZ / add_on` can move from `proximity_unknown` to `not_near_limit` without parsing raw `lc5` data in the validator.

**Architecture:** Add a small reviewed evidence JSON artifact, pass an optional relation-evidence index through the existing execution constraint snapshot path, and let candidates inherit the snapshot relation fields naturally. Invalid relation evidence blocks the candidate audit instead of silently falling back.

**Tech Stack:** Python standard library, `unittest`, existing `ashare_intake_validator.py` helper patterns, JSON evidence files under `docs/tachibana/`.

---

## File Structure

- Create: `docs/tachibana/price-limit-event-relations/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json`
  - Stores the reviewed planned-event relation evidence for `300750.SZ / add_on`.
- Modify: `src/ashare_intake_validator.py`
  - Add optional `relation_evidence_dir` arguments to `audit_first_batch_execution_policy_candidates()`, `audit_first_batch_execution_feasibility_outcomes()`, `audit_first_batch_execution_feasibility_verdict_merge()`, `audit_first_batch_execution_feasibility_verdicts()`, `audit_first_batch_execution_feasibility_gate()`, and `audit_first_batch_execution_constraint_snapshots()`.
  - Add a relation evidence reader/index and validation helper.
  - Pass matched evidence into `_execution_constraint_snapshot()` and `_price_limit_event_relation()`.
  - Add CLI argument `--price-limit-event-relation-dir`.
- Modify: `tests/test_ashare_intake_validator.py`
  - Add a test helper to write relation evidence JSON.
  - Add TDD coverage for legal evidence, illegal enum blocking, and forbidden trading fields staying absent.

## Task 1: Add Reviewed Evidence Artifact

**Files:**
- Create: `docs/tachibana/price-limit-event-relations/first-batch-v0.1/ASHARE-300750.SZ-2026-03-24-2026-04-03.json`

- [ ] **Step 1: Create the reviewed evidence JSON**

Create the file with exactly this payload:

```json
{
  "record_type": "ASharePriceLimitEventRelationEvidence",
  "schema_version": "v0.1",
  "ashare_sample_id": "ASHARE-300750.SZ-2026-03-24-2026-04-03",
  "ts_code": "300750.SZ",
  "trade_date": "2026-04-03",
  "planned_event": "add_on",
  "method_action": "pullback_add",
  "price_limit_event_relation_status": "relation_constrained",
  "price_limit_event_fill_blocking_status": "fill_blocking_unknown",
  "price_limit_event_limit_proximity": "not_near_limit",
  "price_limit_event_relation_reason": [
    "planned_event_intraday_range_far_from_limit_bounds",
    "planned_event_not_near_limit_supported_by_reviewed_lc5_evidence"
  ],
  "price_limit_event_relation_ref": [
    "Z:\\new_tdx64\\vipdoc\\sz\\fzline\\sz300750.lc5",
    "docs/tachibana/index/Tachibana-A股-300750.SZ-add_on-price_limit-proximity-evidence-review-v0.1.md",
    "docs/tachibana/index/Tachibana-A股-300750.SZ-add_on-not_near_limit-收口草案-v0.1.md"
  ],
  "boundary_warning": [
    "relation_evidence_is_research_input_not_execution_rule",
    "do_not_emit_signal_from_relation_evidence",
    "do_not_infer_trade_accept_from_relation_evidence"
  ]
}
```

- [ ] **Step 2: Validate JSON syntax**

Run:

```powershell
python -m json.tool "docs\tachibana\price-limit-event-relations\first-batch-v0.1\ASHARE-300750.SZ-2026-03-24-2026-04-03.json" > $null
```

Expected: command exits with code `0` and prints nothing.

- [ ] **Step 3: Commit**

```powershell
git add "docs\tachibana\price-limit-event-relations\first-batch-v0.1\ASHARE-300750.SZ-2026-03-24-2026-04-03.json"
git commit -m "Add reviewed price limit relation evidence"
```

## Task 2: Write Failing Test For Legal Relation Evidence

**Files:**
- Modify: `tests/test_ashare_intake_validator.py`
- Modify later: `src/ashare_intake_validator.py`

- [ ] **Step 1: Add a test helper**

Add this helper after `write_execution_policy_case()`:

```python
def write_price_limit_relation_evidence(
    relation_root: Path,
    *,
    sample_id: str,
    ts_code: str,
    trade_date: str = "2026-01-06",
    planned_event: str = "add_on",
    method_action: str = "pullback_add",
    relation_status: str = "relation_constrained",
    fill_blocking_status: str = "fill_blocking_unknown",
    limit_proximity: str = "not_near_limit",
) -> Path:
    relation_root.mkdir(parents=True, exist_ok=True)
    path = relation_root / f"{sample_id}.json"
    path.write_text(
        json.dumps(
            {
                "record_type": "ASharePriceLimitEventRelationEvidence",
                "schema_version": "v0.1",
                "ashare_sample_id": sample_id,
                "ts_code": ts_code,
                "trade_date": trade_date,
                "planned_event": planned_event,
                "method_action": method_action,
                "price_limit_event_relation_status": relation_status,
                "price_limit_event_fill_blocking_status": fill_blocking_status,
                "price_limit_event_limit_proximity": limit_proximity,
                "price_limit_event_relation_reason": [
                    "planned_event_intraday_range_far_from_limit_bounds",
                    "planned_event_not_near_limit_supported_by_reviewed_lc5_evidence",
                ],
                "price_limit_event_relation_ref": [
                    "unit-test:reviewed-lc5-evidence",
                    "unit-test:not-near-limit-review",
                ],
                "boundary_warning": [
                    "relation_evidence_is_research_input_not_execution_rule",
                    "do_not_emit_signal_from_relation_evidence",
                    "do_not_infer_trade_accept_from_relation_evidence",
                ],
            }
        ),
        encoding="utf-8",
    )
    return path
```

- [ ] **Step 2: Add the failing legal-evidence test**

Add this test after `test_execution_policy_candidates_emit_relation_constrained_for_add_on`:

```python
    def test_execution_policy_candidates_use_reviewed_not_near_limit_relation_evidence(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir, fact_root, review_dir = write_execution_policy_case(
                tmp_path,
                ts_code="300750.SZ",
                execution_event_type="add_on",
                method_action="pullback_add",
                pm_action="add_on",
                feasibility_status="constrained",
                verdict_reason=["manual_constraint_confirmed"],
                blocked_reason=["limit_state_unknown_on_planned_event"],
            )
            relation_dir = tmp_path / "price-limit-event-relations"
            write_price_limit_relation_evidence(
                relation_dir,
                sample_id="ASHARE-300750.SZ-2026-01-05-2026-01-06",
                ts_code="300750.SZ",
            )

            report = audit_first_batch_execution_policy_candidates(
                fixture_root,
                plan_dir,
                fact_root,
                review_dir,
                relation_dir,
            )

        candidates = {
            item["candidate_constraint_type"]: item
            for item in report["execution_policy_candidates"]
        }
        price_limit = candidates["price_limit"]
        self.assertEqual(report["result"], "pass")
        self.assertEqual(price_limit["candidate_status"], "review_required")
        self.assertEqual(price_limit["price_limit_event_relation_status"], "relation_constrained")
        self.assertEqual(
            price_limit["price_limit_event_fill_blocking_status"],
            "fill_blocking_unknown",
        )
        self.assertEqual(
            price_limit["price_limit_event_limit_proximity"],
            "not_near_limit",
        )
        self.assertEqual(
            price_limit["price_limit_event_relation_reason"],
            [
                "planned_event_intraday_range_far_from_limit_bounds",
                "planned_event_not_near_limit_supported_by_reviewed_lc5_evidence",
            ],
        )
        self.assertIn(
            "unit-test:reviewed-lc5-evidence",
            price_limit["price_limit_event_relation_ref"],
        )
```

- [ ] **Step 3: Run test and verify RED**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_ashare_intake_validator.AShareIntakeValidatorTest.test_execution_policy_candidates_use_reviewed_not_near_limit_relation_evidence -v
```

Expected: FAIL or ERROR because `audit_first_batch_execution_policy_candidates()` does not yet accept the fifth `relation_dir` argument.

## Task 3: Implement Minimal Legal Evidence Path

**Files:**
- Modify: `src/ashare_intake_validator.py`
- Test: `tests/test_ashare_intake_validator.py`

- [ ] **Step 1: Add a relation evidence index helper**

Add this near `_read_json_object()`:

```python
def _price_limit_relation_evidence_index(
    relation_evidence_dir: str | Path | None,
) -> tuple[dict[tuple[str, str, str, str], dict[str, Any]], list[dict[str, Any]]]:
    if relation_evidence_dir is None:
        return {}, []
    evidence_dir = Path(relation_evidence_dir)
    if not evidence_dir.exists():
        return {}, [
            {
                "issues": ["price_limit_event_relation_evidence_dir_missing"],
                "next_action": "action:review_price_limit_event_relation_evidence",
                "path": str(evidence_dir),
            }
        ]

    index: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    blocked_items: list[dict[str, Any]] = []
    for path in sorted(evidence_dir.glob("*.json")):
        payload = _read_json_object(path)
        if payload is None:
            blocked_items.append(
                {
                    "issues": [f"invalid_price_limit_event_relation_evidence_json:{path.name}"],
                    "next_action": "action:review_price_limit_event_relation_evidence",
                    "path": str(path),
                }
            )
            continue
        issues = _price_limit_relation_evidence_issues(path, payload)
        if issues:
            blocked_items.append(
                {
                    "ashare_sample_id": payload.get("ashare_sample_id"),
                    "ts_code": payload.get("ts_code"),
                    "issues": issues,
                    "next_action": "action:review_price_limit_event_relation_evidence",
                    "path": str(path),
                }
            )
            continue
        key = (
            str(payload["ashare_sample_id"]),
            str(payload["ts_code"]),
            str(payload["trade_date"]),
            str(payload["planned_event"]),
        )
        index[key] = payload
    return index, blocked_items
```

- [ ] **Step 2: Add evidence validation**

Add this near the helper above:

```python
def _price_limit_relation_evidence_issues(path: Path, payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required_fields = [
        "record_type",
        "schema_version",
        "ashare_sample_id",
        "ts_code",
        "trade_date",
        "planned_event",
        "price_limit_event_relation_status",
        "price_limit_event_fill_blocking_status",
        "price_limit_event_limit_proximity",
        "price_limit_event_relation_reason",
        "price_limit_event_relation_ref",
    ]
    for field in required_fields:
        if field not in payload:
            issues.append(f"price_limit_event_relation_evidence_missing_field:{field}")
    if issues:
        return issues
    if payload.get("record_type") != "ASharePriceLimitEventRelationEvidence":
        issues.append(f"invalid_price_limit_event_relation_evidence_record_type:{path.name}")
    relation_status = str(payload.get("price_limit_event_relation_status"))
    if relation_status not in PRICE_LIMIT_EVENT_RELATION_STATUSES:
        issues.append("invalid_price_limit_event_relation_evidence_enum:price_limit_event_relation_status")
    fill_status = str(payload.get("price_limit_event_fill_blocking_status"))
    if fill_status not in PRICE_LIMIT_EVENT_FILL_BLOCKING_STATUSES:
        issues.append("invalid_price_limit_event_relation_evidence_enum:price_limit_event_fill_blocking_status")
    proximity = str(payload.get("price_limit_event_limit_proximity"))
    if proximity not in PRICE_LIMIT_EVENT_LIMIT_PROXIMITY_STATUSES:
        issues.append("invalid_price_limit_event_relation_evidence_enum:price_limit_event_limit_proximity")
    if not isinstance(payload.get("price_limit_event_relation_reason"), list):
        issues.append("invalid_price_limit_event_relation_evidence_list:price_limit_event_relation_reason")
    if not isinstance(payload.get("price_limit_event_relation_ref"), list):
        issues.append("invalid_price_limit_event_relation_evidence_list:price_limit_event_relation_ref")
    return issues
```

- [ ] **Step 3: Thread evidence through snapshot generation**

Change `_execution_constraint_snapshot()` signature from:

```python
def _execution_constraint_snapshot(record: dict[str, Any], fact: dict[str, str]) -> dict[str, Any]:
```

to:

```python
def _execution_constraint_snapshot(
    record: dict[str, Any],
    fact: dict[str, str],
    relation_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
```

Change:

```python
price_limit_event_relation = _price_limit_event_relation(record, fact)
```

to:

```python
price_limit_event_relation = _price_limit_event_relation(record, fact, relation_evidence)
```

- [ ] **Step 4: Use relation evidence in `_price_limit_event_relation()`**

Change signature to:

```python
def _price_limit_event_relation(
    record: dict[str, Any],
    fact: dict[str, Any],
    relation_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
```

Before the `if planned_event == "add_on":` block, add:

```python
    if relation_evidence is not None:
        return {
            "status": relation_evidence["price_limit_event_relation_status"],
            "fill_blocking_status": relation_evidence["price_limit_event_fill_blocking_status"],
            "limit_proximity": relation_evidence["price_limit_event_limit_proximity"],
            "reason": _list_value(relation_evidence.get("price_limit_event_relation_reason")),
            "evidence_ref": _unique_preserve_order(
                [
                    *evidence_ref,
                    *_list_value(relation_evidence.get("price_limit_event_relation_ref")),
                ]
            ),
        }
```

- [ ] **Step 5: Add optional arguments through candidate and upstream functions**

Change `audit_first_batch_execution_policy_candidates()` signature to:

```python
def audit_first_batch_execution_policy_candidates(
    data_root: str | Path,
    plan_dir: str | Path,
    institution_fact_root: str | Path,
    verdict_dir: str | Path,
    relation_evidence_dir: str | Path | None = None,
) -> dict[str, Any]:
```

Change `audit_first_batch_execution_feasibility_outcomes()` signature to also accept `relation_evidence_dir: str | Path | None = None`, then pass it to `audit_first_batch_execution_feasibility_verdict_merge()`.

Change `audit_first_batch_execution_feasibility_verdict_merge()` signature to accept `relation_evidence_dir: str | Path | None = None`, then pass it to `audit_first_batch_execution_feasibility_verdicts()`.

Change `audit_first_batch_execution_feasibility_verdicts()` signature to accept `relation_evidence_dir: str | Path | None = None`, then pass it to `audit_first_batch_execution_constraint_snapshots()`.

Change `audit_first_batch_execution_feasibility_gate()` signature to accept `relation_evidence_dir: str | Path | None = None`, then pass it to `audit_first_batch_execution_constraint_snapshots()`.

Change `audit_first_batch_execution_constraint_snapshots()` signature to:

```python
def audit_first_batch_execution_constraint_snapshots(
    data_root: str | Path,
    plan_dir: str | Path,
    institution_fact_root: str | Path,
    relation_evidence_dir: str | Path | None = None,
) -> dict[str, Any]:
```

- [ ] **Step 6: Match evidence inside `audit_first_batch_execution_constraint_snapshots()`**

At the start of `audit_first_batch_execution_constraint_snapshots()`, call:

```python
relation_evidence_index, relation_evidence_blocked_items = _price_limit_relation_evidence_index(relation_evidence_dir)
```

If `relation_evidence_blocked_items` is non-empty, return a blocked report with:

```python
"result": "blocked",
"execution_constraint_snapshot_count": 0,
"execution_constraint_snapshots": [],
"execution_constraint_snapshot_blocked_count": len(relation_evidence_blocked_items),
"execution_constraint_snapshot_blocked_items": relation_evidence_blocked_items,
"institution_rule_definition_allowed": False,
"signal_generation_allowed": False,
"backtest_execution_allowed": False,
"next_action": "action:review_price_limit_event_relation_evidence",
"issues": ["price_limit_event_relation_evidence_invalid"],
```

Where the loop currently appends:

```python
snapshots.append(_execution_constraint_snapshot(record, fact))
```

replace with:

```python
relation_key = (
    str(record.get("ashare_sample_id")),
    str(fact.get("ts_code")),
    str(fact.get("trade_date")),
    str(record.get("planned_event") or record.get("execution_event_type") or ""),
)
snapshots.append(
    _execution_constraint_snapshot(
        record,
        fact,
        relation_evidence_index.get(relation_key),
    )
)
```

- [ ] **Step 7: Run legal-evidence test and verify GREEN**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_ashare_intake_validator.AShareIntakeValidatorTest.test_execution_policy_candidates_use_reviewed_not_near_limit_relation_evidence -v
```

Expected: PASS.

- [ ] **Step 8: Run existing add_on default test**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_ashare_intake_validator.AShareIntakeValidatorTest.test_execution_policy_candidates_emit_relation_constrained_for_add_on -v
```

Expected: PASS, proving no evidence still defaults to `proximity_unknown`.

- [ ] **Step 9: Commit**

```powershell
git add src\ashare_intake_validator.py tests\test_ashare_intake_validator.py
git commit -m "Use reviewed price limit relation evidence"
```

## Task 4: Add Blocked Test For Invalid Relation Evidence

**Files:**
- Modify: `tests/test_ashare_intake_validator.py`
- Modify later: `src/ashare_intake_validator.py` if the test exposes gaps

- [ ] **Step 1: Add failing invalid-enum test**

Add this test after the legal-evidence test:

```python
    def test_execution_policy_candidates_block_invalid_relation_evidence_enum(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir, fact_root, review_dir = write_execution_policy_case(
                tmp_path,
                ts_code="300750.SZ",
                execution_event_type="add_on",
                method_action="pullback_add",
                pm_action="add_on",
                feasibility_status="constrained",
                verdict_reason=["manual_constraint_confirmed"],
                blocked_reason=["limit_state_unknown_on_planned_event"],
            )
            relation_dir = tmp_path / "price-limit-event-relations"
            write_price_limit_relation_evidence(
                relation_dir,
                sample_id="ASHARE-300750.SZ-2026-01-05-2026-01-06",
                ts_code="300750.SZ",
                limit_proximity="unsupported_value",
            )

            report = audit_first_batch_execution_policy_candidates(
                fixture_root,
                plan_dir,
                fact_root,
                review_dir,
                relation_dir,
            )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["execution_policy_candidate_count"], 0)
        self.assertEqual(
            report["next_action"],
            "action:review_price_limit_event_relation_evidence",
        )
        self.assertIn("price_limit_event_relation_evidence_invalid", report["issues"])
        blocked_items = report["execution_feasibility_outcomes_report"][
            "execution_feasibility_verdict_merge"
        ]["execution_feasibility_verdict_drafts"]["execution_feasibility_gate"][
            "execution_constraint_snapshots"
        ]["execution_constraint_snapshot_blocked_items"]
        self.assertEqual(
            blocked_items[0]["issues"],
            ["invalid_price_limit_event_relation_evidence_enum:price_limit_event_limit_proximity"],
        )
```

- [ ] **Step 2: Run invalid-enum test and verify RED**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_ashare_intake_validator.AShareIntakeValidatorTest.test_execution_policy_candidates_block_invalid_relation_evidence_enum -v
```

Expected: FAIL if the blocked report shape is not yet threaded all the way to candidate audit. If it passes after Task 3, record that it passed because Task 3 already implemented the required blocked behavior.

- [ ] **Step 3: Thread blocked report propagation**

Ensure invalid evidence blocks before candidate generation and includes `price_limit_event_relation_evidence_invalid` in the top-level candidate audit issues. The nested blocked item must remain visible at this path:

```python
report["execution_feasibility_outcomes_report"][
    "execution_feasibility_verdict_merge"
]["execution_feasibility_verdict_drafts"]["execution_feasibility_gate"][
    "execution_constraint_snapshots"
]["execution_constraint_snapshot_blocked_items"]
```

- [ ] **Step 4: Run invalid-enum test and verify GREEN**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_ashare_intake_validator.AShareIntakeValidatorTest.test_execution_policy_candidates_block_invalid_relation_evidence_enum -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src\ashare_intake_validator.py tests\test_ashare_intake_validator.py
git commit -m "Block invalid price limit relation evidence"
```

## Task 5: Add Forbidden Fields Regression Test

**Files:**
- Modify: `tests/test_ashare_intake_validator.py`

- [ ] **Step 1: Add the forbidden-fields assertion test**

Add this test after the invalid-enum test:

```python
    def test_reviewed_relation_evidence_keeps_trading_fields_disabled(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir, fact_root, review_dir = write_execution_policy_case(
                tmp_path,
                ts_code="300750.SZ",
                execution_event_type="add_on",
                method_action="pullback_add",
                pm_action="add_on",
                feasibility_status="constrained",
                verdict_reason=["manual_constraint_confirmed"],
                blocked_reason=["limit_state_unknown_on_planned_event"],
            )
            relation_dir = tmp_path / "price-limit-event-relations"
            write_price_limit_relation_evidence(
                relation_dir,
                sample_id="ASHARE-300750.SZ-2026-01-05-2026-01-06",
                ts_code="300750.SZ",
            )

            report = audit_first_batch_execution_policy_candidates(
                fixture_root,
                plan_dir,
                fact_root,
                review_dir,
                relation_dir,
            )

        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        for candidate in report["execution_policy_candidates"]:
            for forbidden_field in [
                "trade_accept",
                "position_size",
                "limit_up_strategy",
                "limit_down_strategy",
                "signal_generation_allowed",
                "backtest_execution_allowed",
            ]:
                self.assertNotIn(forbidden_field, candidate)
```

- [ ] **Step 2: Run forbidden-fields test and verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_ashare_intake_validator.AShareIntakeValidatorTest.test_reviewed_relation_evidence_keeps_trading_fields_disabled -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```powershell
git add tests\test_ashare_intake_validator.py
git commit -m "Assert relation evidence keeps trading gates disabled"
```

## Task 6: Add CLI Argument And Real Artifact Smoke Test

**Files:**
- Modify: `src/ashare_intake_validator.py`
- Test: existing command-line invocation

- [ ] **Step 1: Add parser argument**

Near `--institution-fact-root`, add:

```python
    parser.add_argument(
        "--price-limit-event-relation-dir",
        help="Optional reviewed planned-event price-limit relation evidence directory.",
    )
```

- [ ] **Step 2: Pass CLI argument into candidate audit**

Change the candidate CLI call from:

```python
        report = audit_first_batch_execution_policy_candidates(
            args.root,
            args.method_pm_plan_dir,
            fact_root,
            args.audit_first_batch_execution_policy_candidates,
        )
```

to:

```python
        report = audit_first_batch_execution_policy_candidates(
            args.root,
            args.method_pm_plan_dir,
            fact_root,
            args.audit_first_batch_execution_policy_candidates,
            args.price_limit_event_relation_dir,
        )
```

- [ ] **Step 3: Run target unit tests**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_ashare_intake_validator -v
```

Expected: all tests PASS.

- [ ] **Step 4: Run real candidate smoke command**

Run:

```powershell
$env:PYTHONPATH='src'
python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-execution-policy-candidates Z:\asteria-trading-lab\docs\tachibana\execution-feasibility-verdicts\first-batch-v0.1 --method-pm-plan-dir Z:\asteria-trading-lab\docs\tachibana\method-pm-plans\first-batch-v0.1 --institution-fact-root Z:\asteria-trading-labs-data --price-limit-event-relation-dir Z:\asteria-trading-lab\docs\tachibana\price-limit-event-relations\first-batch-v0.1
```

Expected:

- command exits with code `0`
- JSON contains `"result": "pass"`
- price-limit candidate for `300750.SZ` contains `"price_limit_event_limit_proximity": "not_near_limit"`
- report-level hard gates remain false

- [ ] **Step 5: Commit**

```powershell
git add src\ashare_intake_validator.py tests\test_ashare_intake_validator.py
git commit -m "Expose price limit relation evidence to candidate audit"
```

## Task 7: Final Verification

**Files:**
- Verify all modified files

- [ ] **Step 1: Run focused test**

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_ashare_intake_validator -v
```

Expected: PASS.

- [ ] **Step 2: Run full test suite**

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
```

Expected: PASS.

- [ ] **Step 3: Inspect git status**

```powershell
git status --short
```

Expected: no unstaged modifications except intentional uncommitted docs if the current session chooses not to commit them.

- [ ] **Step 4: Commit remaining docs if not already committed**

```powershell
git add docs\tachibana\index\Tachibana-A股-300750.SZ-add_on-not_near_limit-收口草案-v0.1.md docs\tachibana\index\Tachibana-A股-300750.SZ-add_on-not_near_limit-实现对齐设计-v0.1.md docs\superpowers\plans\2026-06-29-price-limit-relation-evidence-implementation.md
git commit -m "Plan reviewed price limit relation evidence implementation"
```

Expected: commit succeeds.
