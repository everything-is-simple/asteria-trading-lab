# Execution Policy Research Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把现有 `execution_policy_research_prep` 结果收口成正式的制度研究议题入口，生成按 `t1 / price_limit / suspension_resume` 分组的只读研究议题清单，并保持三道硬闸关闭。

**Architecture:** 继续沿用 `ashare_intake_validator.py` 的审计分层模式，在 `execution_policy_research_prep` 之后新增一个只读聚合层。该层不定义制度规则，不生成交易信号，不改变上游单条 prep 记录，只把逐候选记录按 `candidate_constraint_type` 汇总成可人工复核的研究议题。CLI、单测、文档同步收口。

**Tech Stack:** PowerShell, Python 3.11, `unittest`, 现有 `ashare_intake_validator.py` CLI 与只读审计约束。

---

## 子项目边界

这个计划只做一件事：

- 把 `prepare_execution_policy_research` 从“next_action 文案”落成真正的研究议题入口。

明确不在本计划范围：

- 补齐 `price_limit` 的真实制度事实字段；
- 扩充 `meaningful / limited / unknown / not_meaningful` 四类样本覆盖；
- 启动 Signal、A 股规则定义、回测执行层。

这三个方向各自独立，后续分别再写新计划。

## 文件结构

### 需要修改

- `src/ashare_intake_validator.py`
  - 新增 `audit_first_batch_execution_policy_research_agenda(...)`
  - 新增议题聚合 helper
  - 新增 CLI 参数与分支
- `tests/test_ashare_intake_validator.py`
  - 新增 agenda 层单测
  - 新增 agenda 层 CLI 测试
- `docs/04_施工计划_当前进度版.md`
  - 把“补 prepare_execution_policy_research 层”改成“agenda 层已完成/当前进入 agenda 复核”
- `docs/03_Design_系统设计文档.md`
  - 在真实链路状态中追加 agenda 层
- `docs/tachibana/method-pm-plans/first-batch-v0.1/README.md`
  - 补一段 agenda 层说明，固定“研究议题入口”口径

### 需要新增

- `docs/tachibana/execution-policy-research-agenda/first-batch-v0.1/README.md`
  - 记录首批 3 类议题、状态与验证命令

## 目标输出契约

每条研究议题聚合记录建议采用以下最小结构：

```python
{
    "record_type": "AShareExecutionPolicyResearchAgendaItem",
    "candidate_constraint_type": "t1",
    "agenda_status": "ready_for_research",
    "agenda_reason": ["execution_policy_research_topic_has_ready_candidates"],
    "sample_count": 2,
    "ready_sample_ids": [
        "ASHARE-000001.SZ-2026-03-24-2026-04-03",
        "ASHARE-300750.SZ-2026-03-24-2026-04-03",
    ],
    "blocked_sample_ids": [],
    "evidence_ref": [
        "ASHARE-CONSTRAINT-000001.SZ-2026-04-03-v0.1",
        "ASHARE-CONSTRAINT-300750.SZ-2026-04-03-v0.1",
    ],
    "institution_rule_definition_allowed": False,
    "signal_generation_allowed": False,
    "backtest_execution_allowed": False,
    "next_action": "action:prepare_execution_policy_research",
}
```

状态收口规则：

- `review_required` -> `ready_for_research`
- `evidence_incomplete` -> `await_additional_evidence`
- `carry_forward_required` -> `carry_forward_required`
- 任何未知状态 -> `blocked`

## Task 1: 为 agenda 层写失败测试

**Files:**
- Modify: `tests/test_ashare_intake_validator.py:3109-3382`
- Modify: `src/ashare_intake_validator.py:1543-1620`

- [ ] **Step 1: 写 agenda 层的失败单测**

```python
def test_execution_policy_research_agenda_groups_prep_records_by_constraint_type(self) -> None:
    fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        plan_dir, fact_root, verdict_dir = write_execution_policy_case(
            tmp_path,
            feasibility_status="executable",
        )
        review_root = tmp_path / "policy-reviews"
        write_execution_policy_review_file(
            review_root,
            sample_id="ASHARE-000001.SZ-2026-01-05-2026-01-06",
            ts_code="000001.SZ",
            candidate_reviews=[
                {
                    "candidate_constraint_type": "t1",
                    "review_status": "review_required",
                    "review_reason": ["planned_event_requires_t1_policy_review"],
                },
                {
                    "candidate_constraint_type": "price_limit",
                    "review_status": "evidence_incomplete",
                    "review_reason": ["price_limit_state_still_unknown_on_planned_event"],
                },
            ],
        )

        report = audit_first_batch_execution_policy_research_agenda(
            fixture_root,
            plan_dir,
            fact_root,
            review_root,
        )

    self.assertEqual(report["result"], "pass")
    self.assertEqual(report["execution_policy_research_agenda_count"], 3)
    agendas = {
        item["candidate_constraint_type"]: item
        for item in report["execution_policy_research_agendas"]
    }
    self.assertEqual(agendas["t1"]["agenda_status"], "ready_for_research")
    self.assertEqual(agendas["t1"]["sample_count"], 1)
    self.assertEqual(agendas["price_limit"]["agenda_status"], "await_additional_evidence")
    self.assertEqual(agendas["suspension_resume"]["agenda_status"], "carry_forward_required")
    self.assertEqual(report["next_action"], "action:prepare_execution_policy_research")
```

- [ ] **Step 2: 跑单测，确认它先失败**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_ashare_intake_validator.AShareIntakeValidatorTest.test_execution_policy_research_agenda_groups_prep_records_by_constraint_type -v
```

Expected:

```text
ERROR: name 'audit_first_batch_execution_policy_research_agenda' is not defined
```

- [ ] **Step 3: 写最小实现骨架**

```python
def audit_first_batch_execution_policy_research_agenda(
    data_root: str | Path,
    plan_dir: str | Path,
    institution_fact_root: str | Path,
    review_dir: str | Path,
) -> dict[str, Any]:
    prep_report = audit_first_batch_execution_policy_research_prep(
        data_root,
        plan_dir,
        institution_fact_root,
        review_dir,
    )
    if prep_report["result"] != "pass":
        return {
            "result": "blocked",
            "execution_policy_research_agenda_count": 0,
            "execution_policy_research_agendas": [],
            "execution_policy_research_agenda_blocked_count": 0,
            "execution_policy_research_agenda_blocked_items": [],
            "agenda_status_counts": {},
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": prep_report["next_action"],
            "issues": ["execution_policy_research_agenda_requires_valid_research_prep"],
            "execution_policy_research_prep_report": prep_report,
        }
    return {
        "result": "pass",
        "execution_policy_research_agenda_count": 0,
        "execution_policy_research_agendas": [],
        "execution_policy_research_agenda_blocked_count": 0,
        "execution_policy_research_agenda_blocked_items": [],
        "agenda_status_counts": {},
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": "action:prepare_execution_policy_research",
        "issues": [],
        "execution_policy_research_prep_report": prep_report,
    }
```

- [ ] **Step 4: 实现聚合逻辑直到测试通过**

```python
def _execution_policy_research_agenda_items(preps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for prep in preps:
        grouped.setdefault(str(prep["candidate_constraint_type"]), []).append(prep)

    items: list[dict[str, Any]] = []
    for constraint_type, records in grouped.items():
        statuses = {str(item["research_prep_status"]) for item in records}
        if "review_required" in statuses:
            agenda_status = "ready_for_research"
            agenda_reason = ["execution_policy_research_topic_has_ready_candidates"]
            next_action = "action:prepare_execution_policy_research"
        elif "evidence_incomplete" in statuses:
            agenda_status = "await_additional_evidence"
            agenda_reason = ["execution_policy_research_topic_requires_additional_evidence"]
            next_action = "action:collect_additional_execution_evidence"
        elif "carry_forward_required" in statuses:
            agenda_status = "carry_forward_required"
            agenda_reason = ["execution_policy_research_topic_carry_forward_required"]
            next_action = "action:collect_additional_execution_evidence"
        else:
            agenda_status = "blocked"
            agenda_reason = ["execution_policy_research_topic_blocked"]
            next_action = "action:collect_additional_execution_evidence"

        items.append(
            {
                "record_type": "AShareExecutionPolicyResearchAgendaItem",
                "candidate_constraint_type": constraint_type,
                "agenda_status": agenda_status,
                "agenda_reason": agenda_reason,
                "sample_count": len(records),
                "ready_sample_ids": [
                    item["ashare_sample_id"]
                    for item in records
                    if item["research_prep_status"] == "review_required"
                ],
                "blocked_sample_ids": [
                    item["ashare_sample_id"]
                    for item in records
                    if item["research_prep_status"] != "review_required"
                ],
                "evidence_ref": _unique_preserve_order(
                    ref
                    for item in records
                    for ref in _list_value(item.get("evidence_ref"))
                ),
                "institution_rule_definition_allowed": False,
                "signal_generation_allowed": False,
                "backtest_execution_allowed": False,
                "next_action": next_action,
            }
        )
    return sorted(items, key=lambda item: item["candidate_constraint_type"])
```

- [ ] **Step 5: 重新跑单测，确认通过**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_ashare_intake_validator.AShareIntakeValidatorTest.test_execution_policy_research_agenda_groups_prep_records_by_constraint_type -v
```

Expected:

```text
OK
```

- [ ] **Step 6: Commit**

```powershell
git add tests/test_ashare_intake_validator.py src/ashare_intake_validator.py
git commit -m "Add execution policy research agenda layer"
```

## Task 2: 为 agenda 层补 CLI 与阻断测试

**Files:**
- Modify: `tests/test_ashare_intake_validator.py:3326-3382`
- Modify: `src/ashare_intake_validator.py:3388-3417`

- [ ] **Step 1: 写 CLI 失败测试**

```python
def test_cli_runs_execution_policy_research_agenda(self) -> None:
    fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        plan_dir, fact_root, verdict_dir = write_execution_policy_case(
            tmp_path,
            feasibility_status="executable",
        )
        review_root = tmp_path / "policy-reviews"
        write_execution_policy_review_file(
            review_root,
            sample_id="ASHARE-000001.SZ-2026-01-05-2026-01-06",
            ts_code="000001.SZ",
            candidate_reviews=[
                {
                    "candidate_constraint_type": "t1",
                    "review_status": "review_required",
                    "review_reason": ["planned_event_requires_t1_policy_review"],
                }
            ],
        )

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "ashare_intake_validator",
                "--root",
                str(fixture_root),
                "--audit-first-batch-execution-policy-research-agenda",
                str(review_root),
                "--method-pm-plan-dir",
                str(plan_dir),
                "--institution-fact-root",
                str(fact_root),
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

    self.assertEqual(completed.returncode, 0, completed.stderr)
    report = json.loads(completed.stdout)
    self.assertEqual(report["result"], "pass")
    self.assertEqual(report["execution_policy_research_agenda_count"], 3)
```

- [ ] **Step 2: 跑 CLI 测试，确认先失败**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_ashare_intake_validator.AShareIntakeValidatorTest.test_cli_runs_execution_policy_research_agenda -v
```

Expected:

```text
FAIL: unrecognized arguments: --audit-first-batch-execution-policy-research-agenda
```

- [ ] **Step 3: 增加 parser 参数与 CLI 分支**

```python
parser.add_argument(
    "--audit-first-batch-execution-policy-research-agenda",
    help="Build read-only execution policy research agenda items from research prep results.",
)

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
```

- [ ] **Step 4: 增加一个阻断用例**

```python
def test_execution_policy_research_agenda_blocks_when_prep_blocks(self) -> None:
    with patch(
        "ashare_intake_validator.audit_first_batch_execution_policy_research_prep",
        return_value={
            "result": "blocked",
            "next_action": "action:collect_additional_execution_evidence",
            "issues": ["execution_policy_research_prep_requires_valid_execution_policy_archive"],
        },
    ):
        report = audit_first_batch_execution_policy_research_agenda(
            ROOT / "tests" / "fixtures" / "ashare-intake-ready",
            Path("plans"),
            Path("facts"),
            Path("reviews"),
        )

    self.assertEqual(report["result"], "blocked")
    self.assertEqual(report["issues"], ["execution_policy_research_agenda_requires_valid_research_prep"])
```

- [ ] **Step 5: 跑 agenda 相关测试**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_ashare_intake_validator -v
```

Expected:

```text
OK
```

- [ ] **Step 6: Commit**

```powershell
git add tests/test_ashare_intake_validator.py src/ashare_intake_validator.py
git commit -m "Wire CLI for execution policy research agenda"
```

## Task 3: 刷新文档并固化首批议题口径

**Files:**
- Modify: `docs/04_施工计划_当前进度版.md`
- Modify: `docs/03_Design_系统设计文档.md`
- Modify: `docs/tachibana/method-pm-plans/first-batch-v0.1/README.md`
- Create: `docs/tachibana/execution-policy-research-agenda/first-batch-v0.1/README.md`

- [ ] **Step 1: 先写 README 文档用例**

```markdown
# 首批 Execution Policy Research Agenda

本目录保存首批真实样本在 `execution_policy_research_prep` 之后的分组研究议题。

## 本批议题

| 议题 | agenda_status | 样本数 | 说明 |
|---|---|---:|---|
| `t1` | `ready_for_research` | 2 | 两条样本已经具备进入制度研究准备的条件。 |
| `price_limit` | `await_additional_evidence` | 2 | 涨跌停关键事实仍为 `unknown`，必须先补证据。 |
| `suspension_resume` | `carry_forward_required` | 2 | 本窗口未触发，暂续传。 |
```

- [ ] **Step 2: 更新施工计划**

```markdown
### 优先级 1

补 `execution_policy_research_agenda` 层，把当前 6 条 research prep 记录整理成 3 条研究议题：

- `t1`
- `price_limit`
- `suspension_resume`
```

- [ ] **Step 3: 更新系统设计链路**

```markdown
`readiness -> front_filter_run -> record_drafts -> sample_table_trial -> method_pm_plan_merge -> backtest_input_snapshots -> institution_feasibility_records -> execution_constraint_snapshots -> execution_feasibility_gate -> execution_feasibility_verdicts -> verdict_merge -> execution_feasibility_outcomes -> execution_policy_candidates -> execution_policy_review_merge -> execution_policy_archive -> execution_policy_research_prep -> execution_policy_research_agenda`
```

- [ ] **Step 4: 跑验证命令**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_ashare_intake_validator -v
git status --short
```

Expected:

```text
OK
M docs/03_Design_系统设计文档.md
M docs/04_施工计划_当前进度版.md
M docs/tachibana/method-pm-plans/first-batch-v0.1/README.md
A docs/tachibana/execution-policy-research-agenda/first-batch-v0.1/README.md
```

- [ ] **Step 5: Commit**

```powershell
git add docs/03_Design_系统设计文档.md docs/04_施工计划_当前进度版.md docs/tachibana/method-pm-plans/first-batch-v0.1/README.md docs/tachibana/execution-policy-research-agenda/first-batch-v0.1/README.md
git commit -m "Document execution policy research agenda"
```

## 总验证

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_ashare_intake_validator -v
python -m unittest discover -s tests
```

Expected:

```text
OK
```

## 完成判定

- `prepare_execution_policy_research` 不再只是 `next_action`，而是有真实 agenda 输出层。
- agenda 层把 6 条 prep 记录收口成 3 条议题：`t1 / price_limit / suspension_resume`。
- agenda 层继续保持三道硬闸关闭，不输出任何交易字段。
- CLI、单测、文档三处口径一致。

## 下一份计划

本计划完成后，下一份计划单独处理：

1. `price_limit` 事实字段补强；
2. `unknown / not_meaningful` 反例与覆盖扩展。
