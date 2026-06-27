# 首批 Method/PM 计划草案 v0.1

**生成日期**: 2026-06-27
**生成方**: Claude (Opus 4.8) —— **研究映射型草稿，等待人工评审**
**对象**: PR #1 中产出的 3 条 `tachibana_candidate` 真实样本判定记录

---

## 0. 这是什么、不是什么（核心边界）

### 这是

- 3 份 JSON 草案，每份对应一条 `tachibana_candidate` 真实样本，按 `audit_method_pm_plan_draft_contract` 字段契约填写
- 把立花 1975-1976 历史段（横向矩阵已认证的 `qualification_rule_id` ↔ method/pm action 映射）作为**类比证据**回填到 A 股 2026-03 窗口
- 让整条认知链路从 `method_pm_readiness=blocked` 推进到 `backtest_input_snapshot_count=3 (gate=pass)`，进而推进到 `institution_constraint_gate=pass`、`institution_feasibility_audit=3 records, executable_status=pending_constraint_evidence`

### 这不是

- ❌ **不是**机器自动生成的交易计划。`method_pm_auto_generation_allowed=False` 是全链路硬闸；Claude 没有违反它，这些草案是基于**横向矩阵已有的 rule → action 映射** + **立花本人历史段的类比证据**，每一份都强制 `method_status=hypothesis` + `method_evidence_ref` 指向横向矩阵和历史段
- ❌ **不是**立花本人在 2026-03 窗口上的真实交易记录。这些股票在该窗口立花没有交易过；草案仅作为"如果立花面对这个结构会怎么做"的假设映射
- ❌ **不是**信号、不是仓位指令、不是 A 股制度规则。所有草案禁用字段（`buy_signal / trade_accept / target_position / position_size / ashare_t1_action / limit_up_strategy ...`）零出现
- ❌ **不是**直接落入正式数据目录的自动写入。草案位于 `docs/tachibana/method-pm-plans/`，不会被 `audit_first_batch_cognitive_pipeline` 自动拾取 —— **必须经人工评审后才合入正式链路**

### 三个硬闸所有草案都满足

- `method_pm_auto_generation_allowed = False`
- `malf_action_backflow_allowed = False`
- `signal_generation_allowed = False`
- `backtest_execution_allowed = False`
- `institution_rule_definition_allowed = False`

---

## 1. 草案清单

| 文件 | ts_code | qualification_rule | rhythm_meaning | method_action | pm_required | pm_action | execution_intent |
|---|---|---|---|---|---|---|---|
| [ASHARE-000001.SZ-2026-03-24-2026-04-03.json](./ASHARE-000001.SZ-2026-03-24-2026-04-03.json) | 000001.SZ 平安银行 | Q-ALIVE-CLEAN | meaningful | `trend_probe_entry` | false | n/a | `replay_hypothesis_plan` |
| [ASHARE-300750.SZ-2026-03-24-2026-04-03.json](./ASHARE-300750.SZ-2026-03-24-2026-04-03.json) | 300750.SZ 宁德时代 | Q-PRESSURE-ADJUST | limited | `pullback_add` | true | `add_on` | `replay_hypothesis_plan` |
| [ASHARE-600000.SH-2026-03-24-2026-04-03.json](./ASHARE-600000.SH-2026-03-24-2026-04-03.json) | 600000.SH 浦发银行 | Q-LOCK-WAIT | limited | `wait_no_action` | true | `lock_candidate` | `replay_hypothesis_plan` |

每份草案都包含 `research_notes` 字段，记录：
- 这是 hypothesis（非 observed）
- 类比映射的立花历史段（如 `1975-01 / 1976-03-A / 1976-04-B`）
- 横向矩阵规则锚点
- 已知语义张力（如 600000.SH 的 `wait_no_action + replay_hypothesis_plan` 张力）

---

## 2. 全链路通电状态（用本批草案）

`docs/tachibana/method-pm-plans/first-batch-v0.1/` 作为 `plan_dir` 输入：

```
$ python -m ashare_intake_validator --root Z:\asteria-trading-labs-data \
    --audit-first-batch-method-pm-plan-merge docs/tachibana/method-pm-plans/first-batch-v0.1

result = pass
method_pm_plan_ready_count = 3
method_pm_plan_blocked_count = 0
unmatched_review_count = 0
backtest_input_snapshot_allowed = True
institution_adaptation_allowed = False  ← 仍然硬闸
```

```
$ python -m ashare_intake_validator --root ... \
    --audit-first-batch-backtest-input-snapshots docs/tachibana/method-pm-plans/first-batch-v0.1

result = pass, snapshot_count = 3, blocked = 0
mode = hypothesis_replay (all 3)
next = action:institution_constraint_gate_review
```

```
$ python -m ashare_intake_validator --root ... \
    --audit-first-batch-institution-constraint-gate docs/tachibana/method-pm-plans/first-batch-v0.1

institution_gate_count = 3, blocked = 0
all gate_status = pass
next = action:start_institution_constraint_audit
institution_rule_definition_allowed = False  ← 仍然硬闸
signal_generation_allowed = False           ← 仍然硬闸
```

```
$ python -m ashare_intake_validator --root ... \
    --audit-first-batch-institution-feasibility-records docs/tachibana/method-pm-plans/first-batch-v0.1

institution_feasibility_record_count = 3
all executable_status = pending_constraint_evidence
all blocked_reason = ["institution_constraint_evidence_not_loaded"]
all carry_forward_required = true
backtest_execution_allowed = False  ← 仍然硬闸
next = action:collect_institution_constraint_evidence
```

### 链路最终停在哪、为什么

```
readiness → front_filter_run → record_drafts → sample_table_trial
         → method_pm_readiness  (本批草案合入后 → pass)
         → backtest_input_snapshot (3 个 hypothesis_replay snapshots, pass)
         → institution_constraint_gate (3 个 pass, allowed_constraint_scope=[execution_feasibility_audit])
         → institution_feasibility_records (3 条 AShareExecutionFeasibilityAudit, executable_status=pending_constraint_evidence)
         → [STOP] action:collect_institution_constraint_evidence
                                ↓
                       需要 ashare/institution-facts-v0.1/*.csv 制度事实包
                       （从 DuckDB tradability_fact 19.2M 行按窗口提取生成）
```

**institution_adaptation_allowed = False** 三道全局硬闸全程保持。

---

## 3. 草案如何映射到立花历史段（类比证据链）

### 3.1 平安银行 000001.SZ + Q-ALIVE-CLEAN + trend_probe_entry

**横向矩阵锚点**：`Q-ALIVE-CLEAN | 有向推进清楚，动作链分批、尺度稳定 | suitable | 试仓、同向加码、分批减仓、等待`

**立花历史段类比源**：`1975-01`、`1975-04`、`1975-11`、`1976-10`（按横向矩阵 §典型样本列）

**为什么选 `trend_probe_entry`（试仓）而不是 `trend_confirmation_add`（同向加码）？**
- `trend_probe_entry` 是干净 alive 推进的**首动作**（最小风险）
- `trend_confirmation_add` 需要前置 probe 已开仓的事实
- 草案是从 0 开始的"如果立花面对这个结构"，因此走 probe

### 3.2 宁德时代 300750.SZ + Q-PRESSURE-ADJUST + pullback_add + add_on

**横向矩阵锚点**：`Q-PRESSURE-ADJUST | 旧段内先减后加、压力调整或库存再平衡，尚未清零 | conditional | 压力调整、库存再平衡、减仓后加回 | 把压力调整并成干净 wave 或清零重置 (boundary)`

**立花历史段类比源**：`1976-03-A`（横向矩阵明确指明）

**为什么 pm_required=true？**
- `_pm_required_from_trial_row` (`ashare_intake_validator.py:1464-1469`) 规定 `rhythm_meaning=limited → pm_required=True`
- 横向矩阵 `Q-PRESSURE-ADJUST` 注明 "PM 复杂度高"
- 所以补 `pm_action=add_on`

**边界**：`do_not_merge_pressure_adjustment_into_clean_wave` —— 压力调整不能升格成干净推进。

### 3.3 浦发银行 600000.SH + Q-LOCK-WAIT + wait_no_action + lock_candidate

**横向矩阵锚点**：`Q-LOCK-WAIT | 双侧库存存在期间无交易或等待 | conditional | wait_no_action`

**立花历史段类比源**：`1976-04-B`（横向矩阵明确指明）

**已知语义张力**：
- `wait_no_action` 在 `METHOD_ACTION_CATALOG` 内 `execution_replay_allowed=False`
- 但本草案用 `execution_intent=replay_hypothesis_plan` 推进
- 这是**故意保留的张力**，让人工 reviewer 决定是 (a) 维持此草案推进流水线，或 (b) 改 `execution_intent=audit_only`，接受停在 `backtest_input_gate`（gate 会拒绝 audit_only —— `backtest_input_audit_only_is_not_executable`）
- 当前选 (a) 是为了让链路一路推到 institution_feasibility 边界，把每个闸门都跑出 `pending_constraint_evidence` 状态

**边界**：`do_not_confirm_lock_from_dual_inventory_only` —— 锁单候选 ≠ 确认锁单。

---

## 4. 人工评审清单

如果你（或下一个开发者）要采纳这批草案，请按下列顺序复核：

- [ ] **类比映射是否合理**：每份草案的 `method_action` 是否真的是该 `qualification_rule_id` 在横向矩阵 §典型样本列里能找到的对应动作？
- [ ] **历史段证据是否锚定**：`method_evidence_ref` 里的立花历史段（1975-01 / 1976-03-A / 1976-04-B 等）是否真的有对应记录？请打开对应的 `docs/tachibana/index/MALF-立花1976-XX交易段结构资格审计-v0.1.md` 检视
- [ ] **三道硬闸是否保持**：`signal_generation_allowed / backtest_execution_allowed / institution_rule_definition_allowed` 全程 False
- [ ] **600000.SH 的语义张力**：上面 §3.3 描述的 wait_no_action vs replay_hypothesis_plan 张力，你倾向于哪种决议？
- [ ] **是否需要补 not_meaningful / unknown 的草案**：当前 5 只样本中 002714.SZ (rejected) 和 601127.SH (blocked) 不在本批，因为它们 `candidate_stage` 不是 `tachibana_candidate`。这是设计正确的 —— 但你可能希望加一条"反例草案"或"unknown 占位草案"用于覆盖率

---

## 5. 不在本草案范围

- ❌ 不修改 `src/ashare_intake_validator.py` 或 `src/tachibana_front_filter.py` 任何代码
- ❌ 不向 `Z:\asteria-trading-labs-data` 自动写入草案（草案位于项目仓库内，不在数据目录）
- ❌ 不生成制度事实包（`ashare/institution-facts-v0.1/`） —— 下一公里
- ❌ 不生成 `AShareExecutionConstraintSnapshot`（需要制度事实包先到位）
- ❌ 不修改 Definitive v2.0 原始定义

---

## 6. 复跑脚本

```powershell
$env:PYTHONPATH = 'src'

# 单条草案契约审计
python -m ashare_intake_validator --root Z:\asteria-trading-labs-data `
  --audit-method-pm-plan-draft docs\tachibana\method-pm-plans\first-batch-v0.1\ASHARE-000001.SZ-2026-03-24-2026-04-03.json

# 草案合流到 readiness review_items
python -m ashare_intake_validator --root Z:\asteria-trading-labs-data `
  --audit-first-batch-method-pm-plan-merge docs\tachibana\method-pm-plans\first-batch-v0.1

# Backtest Input snapshot 草案
python -m ashare_intake_validator --root Z:\asteria-trading-labs-data `
  --audit-first-batch-backtest-input-snapshots docs\tachibana\method-pm-plans\first-batch-v0.1

# 制度约束启动闸门
python -m ashare_intake_validator --root Z:\asteria-trading-labs-data `
  --audit-first-batch-institution-constraint-gate docs\tachibana\method-pm-plans\first-batch-v0.1

# AShareExecutionFeasibilityAudit 底稿
python -m ashare_intake_validator --root Z:\asteria-trading-labs-data `
  --audit-first-batch-institution-feasibility-records docs\tachibana\method-pm-plans\first-batch-v0.1
```

---

## 7. 制度事实最小通电状态

1. **人工评审本批 3 份草案** —— 已阅并合入 main；后续仍可按 §4 清单复核修订。
2. **制度事实包最小通电** —— 已从 `Z:\malf-data\market_meta.duckdb` 的 `tradability_fact` 按 2026-03-24~04-03 窗口 + 3 个 ts_code 生成 `ashare/institution-facts-v0.1/*.csv`。
3. **执行证据链路** —— `--audit-first-batch-execution-constraint-snapshots`、`--audit-first-batch-execution-feasibility-gate`、`--audit-first-batch-execution-feasibility-verdicts` 均已通过；3 条样本从 `pending_constraint_evidence` 推进到 `evidence_ready`，默认 verdict 仍为 `not_evaluated`。
4. **人工 verdict 合流入口** —— `--audit-first-batch-execution-feasibility-verdict-merge <review-dir> --method-pm-plan-dir docs\tachibana\method-pm-plans\first-batch-v0.1` 已提供，只接受 `not_evaluated / executable / constrained / blocked / carry_forward_required` 这些人工复核状态。
5. **下一步** —— 人工复核 `AShareExecutionFeasibilityVerdict`；仍不得把 `evidence_ready` 或 `executable` 解释成 `trade_accept`、仓位许可、T+1 策略或涨跌停策略。
6. **覆盖反例 / unknown**：考虑给 002714.SZ (NM-NO-STRUCTURE) 和 601127.SH (unknown) 也填一份"为什么不进入 Method/PM"的占位草案。

---

**签字**: Claude (Opus 4.8) @ 2026-06-27
**配套验证**:
- 131 tests OK
- 3 份草案通过 `audit_method_pm_plan_draft_contract`
- 3 份草案通过 `audit_first_batch_method_pm_plan_merge`
- 3 份草案生成 3 个 `BacktestInputSnapshot` (gate=pass, mode=hypothesis_replay)
- 3 份草案生成 3 个 `AShareInstitutionConstraintGate` (status=pass)
- 3 份草案生成 3 条 `AShareExecutionFeasibilityAudit` (status=evidence_ready)
- 3 份草案生成 3 条 `AShareExecutionFeasibilityVerdict` (status=not_evaluated)
- 三道全局硬闸（signal/backtest/institution_rule_definition）全程 False
