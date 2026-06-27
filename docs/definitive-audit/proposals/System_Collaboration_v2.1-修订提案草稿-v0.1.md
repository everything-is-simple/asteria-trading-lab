# System_Collaboration v2.1 修订提案草稿 v0.1

**提案日期**: 2026-06-27
**提案方**: Claude (Opus 4.8)
**承接**: [Definitive v2.0 接口契约重审报告 v0.1](../Definitive-v2.0-接口契约重审报告-v0.1.md) §4 "System_Collaboration v2.0 —— 需要重大修订"
**提案性质**: **草稿**。本文件**不修改**任何 `Z:\asteria-trading-labs-Definitive-validated\` 下的原始定义。只是把 12 处修订点位草拟成可评审的修订草案，供后续正式 v2.1 评审流程采纳。

---

## 0. 为什么需要 v2.1

| 现状（v2.0） | 问题 |
|---|---|
| 主链假设 `data → MALF → PAS → Signal → Backtest` 线性 | 无法显式容纳 Front Filter / Tachibana Method/PM / A-Share Institution Audit 三个新角色 |
| 7 问自检清单 | 无法捕捉"执行语义泄漏到结构定义层"违规 |
| 6 条代码层硬闸 (`ashare_intake_validator.py`) | 5 条在 v2.0 自检框架**无对应** |
| `04_Four_Behavior_Pattern` 构造行为约束 | 不约束"构造行为不得包含执行语义" |

**结果**：代码层超前于定义层。如果换开发者拿 v2.0 当上线 checklist，抓不出当前代码层已经在执行的违规防护。

---

## 1. 修订总览（12 处）

| # | 文件:位置 | 修订类型 | 影响范围 |
|---|---|---|---|
| 1 | `01_Module_Roles:9-32` | 矩阵增行 | 角色定义 |
| 2 | `01_Module_Roles:39-76` | 新增章节 2.9 / 2.10 / 2.11 | 角色简介 |
| 3 | `02_Collaboration_Rules:36-39` | 主链图修订 | 信息流定义 |
| 4 | `02_Collaboration_Rules:100-115` | 事件链增项 | 时序定义 |
| 5 | `03_Probability_Discipline:91-93` | PR-5 补充 | 决策权语义 |
| 6 | `03_Probability_Discipline:153-168` | reason_codes 表新增 | 错误码登记 |
| 7 | `04_Four_Behavior_Pattern:23-31` | 模块对照表增行 | 行为映射 |
| 8 | `04_Four_Behavior_Pattern:38-45` | 构造行为约束补充 | 行为约束 |
| 9 | `05_Conflict_Self_Check:10-19` | 7 问→8 问 | 自检清单 |
| 10 | `05_Conflict_Self_Check:99-110` | 零容忍单测增项 | 测试条目 |
| 11 | `MANIFEST:47-57` | 系统铁律新增 F-6/F-7 | 系统宪法 |
| 12 | `MANIFEST:58-62` | covers_modules 更新 | 覆盖声明 |

---

## 2. 详细修订草案

### 修订 1：`01_Module_Roles:9-32` —— 独占职责矩阵新增 3 行

**当前矩阵**（节选）：

| 事项 | 唯一 owner | 严禁出现 |
|---|---|---|
| ...（v2.0 原有 33 行） | ... | ... |

**草案新增**：

| 事项 | 唯一 owner | 严禁出现 |
|---|---|---|
| MALF Snapshot 到 Tachibana 候选的结构资格过滤 | **Front Filter** | MALF（不下沉资格过滤）; Signal（不上沉到资格层） |
| 立花法动作规划（中心单/锁单/加码/认错） | **Tachibana Method/PM** | MALF（不持仓位语义）; Signal（不持动作规划） |
| A 股制度约束的执行可行性审计 | **A-Share Institution Audit Layer** | Backtest（不定义制度规则，只消费裁决）; Signal（不读制度证据） |

### 修订 2：`01_Module_Roles:39-76` —— 新增 2.9 / 2.10 / 2.11

**草案 §2.9 Front Filter**：
- **擅长**：消费 MALF/PAS 已发布快照，输出 `rhythm_meaning + tachibana_applicability + qualification_rule_id`
- **不干**：不读 PriceBar；不算指标；不生成交易动作；不给目标仓位；不写 Signal 决策字段
- **服务出口**：`FrontFilterSnapshot`（结构资格快照）

**草案 §2.10 Tachibana Method/PM Adapter**：
- **擅长**：基于 Front Filter pass 的候选，编排立花法动作（中心单/锁单/加码/认错），输出 `method_action + pm_action + execution_intent`
- **不干**：不下沉到 MALF（不写结构事实）；不上沉到 Signal（不裁 accept/reject）；不写 A 股制度规则
- **服务出口**：`MethodPmPlanSnapshot`

**草案 §2.11 A-Share Institution Audit Layer**：
- **擅长**：消费 Method/PM 计划 + 制度事实包，产出 `AShareExecutionConstraintSnapshot / AShareExecutionFeasibilityAudit / AShareExecutionFeasibilityVerdict`
- **不干**：不定义制度规则（`institution_rule_definition_allowed=False` 永真）；不生成 Signal；不允许回测成交
- **服务出口**：`AShareExecutionFeasibilityVerdict`

### 修订 3：`02_Collaboration_Rules:36-39` —— 主链单向图

**当前**：`data → MALF → PAS → Signal → Backtest`

**草案**：
```
data → MALF → [Front Filter] → PAS → [Method/PM Adapter] → Signal → [Institution Audit] → Backtest
                                                                            ↑
                                              institution-facts (旁支输入)
```

明确：
- Front Filter 是 PAS 的**前置闸门**而非旁支
- Method/PM 在 PAS 之后、Signal 之前，是动作规划层
- Institution Audit 在 Signal 之后、Backtest 之前，是执行可行性层

### 修订 4：`02_Collaboration_Rules:100-115` —— 同 bar_dt 事件顺序

**当前**：`data → MALF → PAS → Signal → Backtest`

**草案补充事件链**：
```
T0 data
T1 MALF
T2 Front Filter  (新增)
T3 PAS
T4 Method/PM Adapter  (新增)
T5 Signal
T6 Institution Audit  (新增)
T7 Backtest
```

### 修订 5：`03_Probability_Discipline:91-93` —— PR-5 补充

**当前 PR-5**：MALF/PAS/regime/Backtest 永禁直接给"该不该交易"

**草案补充**：
> **资格否决 vs 交易决策语义区分**：Front Filter 的 `tachibana_applicability` 是"认知资格判定"——回答"这个结构条件**值得进入** Method/PM 讨论吗"；而 Signal 的 `decision` 是"交易决策"——回答"这笔 ProposedTrade **应该 accept** 吗"。两者**不矛盾**，但**不可混用**：Front Filter 永禁输出 `decision`，Signal 永禁输出 `tachibana_applicability`。

### 修订 6：`03_Probability_Discipline:153-168` —— reason_codes 表新增

**草案新增条目**：

| reason_code | 触发场景 |
|---|---|
| `front_filter_blocked` | Front Filter 拒绝升级到 tachibana_candidate |
| `front_filter_unknown` | MALF background=unknown，禁止人工升级 |
| `method_pm_not_ready` | Method/PM 计划草案缺失或不合契约 |
| `method_pm_auto_generation_not_allowed` | 试图让机器自动生成 method_action / pm_action |
| `malf_action_backflow_blocked` | 试图把 Method/PM 动作反写回 MALF |
| `institution_constraint_blocked` | 制度事实包阻断 |
| `institution_rule_definition_not_allowed` | 试图从 Institution Audit 层定义制度规则 |
| `execution_feasibility_not_evaluated` | Verdict 默认状态 |
| `backtest_execution_not_allowed` | 全链路硬闸：禁止回测成交 |
| `signal_generation_not_allowed` | 全链路硬闸：禁止 Signal 生成 |

### 修订 7：`04_Four_Behavior_Pattern:23-31` —— 模块四行为对照表新增 3 行

**草案新增**：

| 模块 | 构造 | 记录 | 统计 | 服务 |
|---|---|---|---|---|
| **Front Filter** | 把 MALF Snapshot 构造成 `rhythm_meaning + tachibana_applicability` | 记录 qualification_rule_id 命中 lifecycle | 统计资格分布、命中率 | `FrontFilterSnapshot` |
| **Method/PM Adapter** | 把 Front Filter pass 候选构造成 method/pm 计划草案 | 记录 method/pm 计划演化 lifecycle | 统计 method/pm 复杂度分布 | `MethodPmPlanSnapshot` |
| **Institution Audit** | 把制度事实包构造成 ExecutionConstraintSnapshot | 记录 FeasibilityAudit 状态流转 | 统计 constraint 触发分布 | `ExecutionFeasibilityVerdict` |

### 修订 8：`04_Four_Behavior_Pattern:38-45` —— 构造行为约束补充

**当前约束 1-3**：
1. 构造只识别已可识别的事实
2. 构造不给"该不该交易"裁决
3. 构造不重算上游

**草案新增约束 4**：
> **构造行为不得包含执行语义字段**。具体：`method_action / pm_action / execution_intent / order_side / order_id / fill_price / position_size / pnl / win_rate / ashare_t1_action / limit_up_strategy / limit_down_strategy` 这些字段**不得**作为 MALF / PAS / Front Filter 的构造输出。它们属于下游 Method/PM 层、Signal 层或 Backtest 层的构造输出。违反将触发零容忍单测失败（见修订 10）。

### 修订 9：`05_Conflict_Self_Check:10-19` —— 7 问改为 8 问

**当前 7 问**：
1. 我是不是侵占了别人的职责？
2. 我是不是依赖了别人的私有字段？
3. 我是不是写回了上游？
4. 我是不是暗藏 fallback？
5. 我是不是出了综合分？
6. Snapshot 6 必备项齐了吗？
7. 零容忍单测过了吗？

**草案新增 Q8**：
> **Q8: 我是不是把执行语义泄漏到了结构定义层？**
>
> grep 检查项：在你模块的输出 schema 里搜索以下字段名，**任意一个出现都算违规**：
> ```
> method_action / pm_action / execution_intent / order_side / order_id /
> fill_price / position_size / pnl / win_rate / expected_return /
> ashare_t1_action / limit_up_strategy / limit_down_strategy /
> signal_decision / trade_accept / target_position / buy_signal / sell_signal
> ```
>
> 仅在以下模块的输出 schema 中允许出现：
> - `method_action / pm_action / execution_intent` ← 仅 Method/PM Adapter
> - `signal_decision / trade_accept` ← 仅 Signal
> - `order_side / order_id / fill_price / position_size / pnl / win_rate` ← 仅 Backtest

### 修订 10：`05_Conflict_Self_Check:99-110` —— 零容忍单测增项

**草案新增 2 条测试**：
- **测试 7**：故意在 MALF / PAS / Front Filter 的输出中加入 `method_action` 字段 → schema fail
- **测试 8**：故意让 Front Filter 输出 `signal_generation_allowed=True` → validator fail
- **测试 9**：故意从 Backtest 写 `institution_rule_definition_allowed=True` → schema fail
- **测试 10**：故意从 Method/PM 输出 `target_position` 之外的仓位语义到 MALF schema → schema fail

### 修订 11：`MANIFEST:47-57` —— 系统铁律新增 F-6 / F-7

**当前铁律**：F-1 ~ F-5 + PR-1 ~ PR-5 + lineage_hash 链断 block（共 11 条）

**草案新增**：

- **F-6**：前置过滤器只输出认知资格判定（`rhythm_meaning / tachibana_applicability / qualification_rule_id`），不输出交易动作、不输出目标仓位、不输出制度规则定义。
- **F-7**：A 股制度审计层只输出 execution feasibility verdict，不定义制度规则（`institution_rule_definition_allowed` 永 False），不生成 Signal，不允许回测成交。

### 修订 12：`MANIFEST:58-62` —— covers_modules 更新

**当前**：
```
"covers_modules": [
  "已建: data, MALF v2.0, PAS v2.0, storage, UI",
  "待建: Signal v2.0"
]
```

**草案**：
```
"covers_modules": [
  "已建: data, MALF v2.0, PAS v2.0, Front Filter v0.1, storage, UI",
  "代码层已落地待按 v2.1 宪法补 self-check: Tachibana Method/PM Adapter, A-Share Institution Audit Layer",
  "待按宪法定义: Signal v2.0"
]
```

---

## 3. 评审检查清单

如本草案被采纳进入 v2.1 正式版，请按下列顺序复核：

- [ ] 12 处修订是否互相一致（无 self-contradicting）
- [ ] 新增的 F-6/F-7 是否与 F-1~F-5 没有冲突
- [ ] Q8 grep 检查项是否覆盖 `ashare_intake_validator.py:FORBIDDEN_FIELDS` 全集
- [ ] 4 条新零容忍单测是否在项目 `tests/` 下已有对应实现（已有：`test_ashare_intake_validator.py` 大量 FORBIDDEN_FIELDS 测试）
- [ ] 新角色的 Snapshot 6 必备项（identity / lineage / payload / completeness / reason_codes / immutable）是否完整定义

---

## 4. 不在本草案范围

- ❌ 不修改 `Z:\asteria-trading-labs-Definitive-validated\System_Collaboration_v2_0-claude-20260616\` 任何原始文件
- ❌ 不修改其他 3 套 Definitive v2.0 定义（Signal / Data / Backtest 已经审过，无需修订或仅文档级澄清）
- ❌ 不改 `src/ashare_intake_validator.py` —— 它的方向是对的，是本草案的"事实基础"
- ❌ 不进行 v2.1 正式版的 patch 操作 —— 那需要单独的评审签字流程

---

**签字**: Claude (Opus 4.8) @ 2026-06-27
**配套基础事实**:
- [Definitive v2.0 接口契约重审报告 v0.1](../Definitive-v2.0-接口契约重审报告-v0.1.md)
- [Tachibana-A股首批真实样本结构资格判定记录 v0.1](../../tachibana/index/Tachibana-A股首批真实样本结构资格判定记录-v0.1.md)
- `src/ashare_intake_validator.py:164-166`（3 道全局硬闸）/ `:371-372`（malf_action / method_pm_auto）/ `:386 等`（candidate_table_update）
