# Tachibana Backtest Input 适配层草案 v0.1

## 版本定位

- 本文件承接 [MALF-立花结构资格横向判读矩阵 v0.1](./MALF-立花结构资格横向判读矩阵-v0.1.md)、[Tachibana Data / Signal / Backtest 接口边界审计 v0.1](./Tachibana-Data-Signal-Backtest-接口边界审计-v0.1.md)、[Tachibana Method v1 定义草案](./Tachibana-Method-雏形.md) 与 [Tachibana Position Management v1 定义草案](./Tachibana-Position-Management-雏形.md)。
- `rhythm_meaning` 的接口接缝见 [Tachibana rhythm_meaning Data / Signal / Backtest 接口接缝补丁 v0.1](./Tachibana-rhythm_meaning-Data-Signal-Backtest-接口接缝补丁-v0.1.md)。
- 它定义 `TachibanaBacktestInputSnapshot` 的第一版研究契约，用于把前置过滤器、横向矩阵、Method 与 PM 的结果交给 Backtest 执行层。
- 本文件不修改 MALF 主定义，不修改 `Signal_Definitive_v2_0`，不新增 A 股制度规则。
- 它不是交易信号，不输出 `accept / reject / defer`，也不替代 `TradeDecisionSnapshot`。
- 1976 段级样本试填审计见 [TachibanaBacktestInput 1976 段级样本试填审计 v0.1](./TachibanaBacktestInput-1976段级样本试填审计-v0.1.md)。
- 1975-06 母单候选与双侧库存试填审计见 [TachibanaBacktestInput 1975-06 段级样本试填审计 v0.1](./TachibanaBacktestInput-1975-06段级样本试填审计-v0.1.md)。
- A 股候选股票进入本适配层前，应先通过 [Tachibana A 股候选股票结构资格样本表 v0.1](./Tachibana-A股候选股票结构资格样本表-v0.1.md)。
- 当前 A 股候选股票数据接入缺口见 [Tachibana A 股候选股票数据接入审计 v0.1](./Tachibana-A股候选股票数据接入审计-v0.1.md)。
- A 股最小接入包字段验收见 [Tachibana A 股最小接入包字段契约 v0.1](./Tachibana-A股最小接入包字段契约-v0.1.md)。
- 当前 A 股最小接入包验收结果见 [Tachibana A 股最小接入包验收报告 v0.1](./Tachibana-A股最小接入包验收报告-v0.1.md)。
- A 股最小接入包复核流程见 [Tachibana A 股最小接入包复核流程 v0.1](./Tachibana-A股最小接入包复核流程-v0.1.md)。
- A 股单窗口结构资格判定底稿见 [Tachibana A 股结构资格判定记录模板 v0.1](./Tachibana-A股结构资格判定记录模板-v0.1.md)。
- A 股结构资格升级闸门见 [Tachibana A 股结构资格升级闸门检查清单 v0.1](./Tachibana-A股结构资格升级闸门检查清单-v0.1.md)。
- A 股结构资格理由码见 [Tachibana A 股结构资格理由码表 v0.1](./Tachibana-A股结构资格理由码表-v0.1.md)。
- A 股制度约束正式改造前，还必须通过 [Tachibana A 股制度改造启动闸门 v0.1](./Tachibana-A股制度改造启动闸门-v0.1.md)。

## 解决的问题

通用 Backtest 当前更习惯消费 `TradeDecisionSnapshot(decision=accept)`，但立花研究路线不能为了进入回测而伪造 Signal 决策。

因此需要一个 Tachibana 专用输入适配层：

```mermaid
flowchart LR
  A["Data"] --> B["MALF Snapshot"]
  B --> C["前置认知过滤器"]
  C --> D["横向判读矩阵"]
  D --> E["Tachibana Method"]
  E --> F["Tachibana PM"]
  F --> G["TachibanaBacktestInputSnapshot"]
  G --> H["Backtest 执行层"]
```

它只回答：在已经通过结构资格闸门后，哪些字段可以作为回测执行输入；哪些字段必须停留在研究备注中；哪些字段永远不能由 MALF 或过滤器生成。

## 入口条件

| `rhythm_meaning` | `tachibana_applicability` | 是否生成执行型 `TachibanaBacktestInputSnapshot` | 处理方式 |
|---|---|---|---|
| `meaningful` | `suitable` | 可以。 | 生成研究回放或假设回测输入。 |
| `limited` | `conditional` | 可以，但必须携带 `meaning_reason`、`qualification_rule_id`、`boundary_warning` 与 `evidence_level`。 | 生成带限制条件的研究输入。 |
| `not_meaningful` | `unsuitable` | 不可以。 | 只进入样本记录或 `research_audit`，不进入 Method / PM / Backtest。 |
| `unknown` | `unknown` | 不可以。 | 只进入资料审计或 MALF 快照补证队列。 |

关键点：`meaningful / limited` 与 `suitable / conditional` 只表示“值得进入立花 Method / PM 讨论”，不表示“应该交易”。`research_audit` 可保存资料记录，但不得产生执行型回测输入。

## 机器入口门禁

从 A 股结构资格样本表进入本适配层前，必须先通过 `backtest_input_gate`。该门禁不生成 Method / PM 动作，只检查已有判定记录是否已经具备回测输入资格。

| 门禁条件 | 要求 | 阻断处理 |
|---|---|---|
| 样本表门禁 | `candidate_table_gate.result=pass`。 | 回到结构资格样本表或判定底稿。 |
| 节奏意义 | `rhythm_meaning=meaningful/limited`。 | `not_meaningful/unknown` 只进入 `research_audit`。 |
| 立花适用性 | `tachibana_applicability=suitable/conditional`。 | `unsuitable/unknown` 不进入 Backtest Input。 |
| 资格规则 | `qualification_rule_id` 非空且不是 `NM-*`。 | 保留研究备注。 |
| 边界与证据 | `boundary_warning` 非空，`evidence_level` 包含 `E1_malf_snapshot`。 | 回到结构资格补证。 |
| Method 计划 | 有 `method_action`、`method_status`、`method_reason`。 | 输出 `action:method_pm_review`，不得生成快照。 |
| PM 承接 | `pm_required=true` 时必须有 `pm_action`。 | 回到 PM。 |
| Method / PM 桥接门 | `method_pm_bridge_gate.result=pass`。 | 输出 `action:method_pm_review`，不得生成快照。 |
| 执行意图 | `execution_intent=replay_observed_action/replay_hypothesis_plan`，且有 `execution_event_type`。 | `audit_only` 只能研究审计。 |
| 禁止字段 | 不得出现 Signal、交易裁决、由 MALF 推断仓位或锁单的字段。 | 退回清洗。 |

门禁通过时，`backtest_input_gate.result=pass`，`next_action=action:build_backtest_input_snapshot`；否则 `result=blocked`，`mode=research_audit`，`next_action=action:method_pm_review`。

`method_pm_bridge_gate` 是 Backtest Input 之前的独立洁净性检查。它只证明 Method / PM 计划已经存在且没有污染 MALF 或 Signal；它不负责判断结构是否适合立花法，也不负责生成买卖信号。

## 适配模式

| mode | 用途 | 输入来源 | 禁止事项 |
|---|---|---|---|
| `observed_replay` | 回放立花历史交易事实。 | 月报、交易谱、重建 JSON、人工校勘。 | 不得把历史动作包装成未来信号。 |
| `hypothesis_replay` | 测试 Method / PM 抽象规则在样本上的执行效果。 | Method / PM 规则草案、结构资格样本。 | 不得跳过结构资格闸门。 |
| `research_audit` | 保存 `unknown / unsuitable` 或资料扰动样本。 | 样本表、制度资料口径审计。 | 不得进入 Backtest 成交与 PnL。 |

## Snapshot 字段草案

### 1. 身份与时间锚点

| 字段 | 类型 | 必填 | 来源 | 含义 |
|---|---|---|---|---|
| `adapter_version` | string | 是 | 本文件 | 适配层版本，如 `tachibana_backtest_input_v0.1`。 |
| `snapshot_granularity` | enum | 是 | 适配层 | `segment_summary / event_row`。v0.1 先以段级快照试填，逐笔回放后续再拆。 |
| `mode` | enum | 是 | 适配层 | `observed_replay / hypothesis_replay / research_audit`。 |
| `sample_id` | string | 是 | 样本表 | 月份或交易段编号，如 `1976-04-A`。 |
| `segment_id` | string/null | 条件必填 | 样本表 / PM | 清零重建或跨段时必须填写。 |
| `symbol` | string | 是 | Data | 交易标的。历史样本可先用 `pioneer_electronics`。 |
| `bar_dt` | date | 是 | Data / 月报 | 动作发生日期或段级锚点日期。 |
| `timeframe` | enum | 是 | 本研究 | 当前固定为 `daily`。 |
| `source_anchor` | list | 是 | 月报 / 章节 / 截图 | 事实和解释锚点。 |

### 2. 结构资格字段

| 字段 | 类型 | 必填 | 来源 | 含义 |
|---|---|---|---|---|
| `malf_snapshot_ref` | string/null | 条件必填 | MALF | 真实 MALF 快照引用；人工样本阶段可为空但必须说明。 |
| `malf_background` | enum/list | 是 | 前置过滤器 | `alive_wave / pullback / range / break_birth / stagnation / transition / unknown`。 |
| `rhythm_meaning` | enum | 是 | 节奏意义准则 | `meaningful / limited`，执行型快照不得出现 `not_meaningful / unknown`。 |
| `meaning_reason` | list | 是 | 理由码表 / 节奏意义准则 | 为什么立花仓位节奏有意义或仅有限意义；不能写买卖理由。 |
| `meaning_boundary_warning` | list | 条件必填 | 接口接缝补丁 / 理由码表 | `limited` 必填；用于防止把节奏意义改写为交易裁决。 |
| `qualification_rule_id` | enum | 是 | 横向判读矩阵 | 如 `Q-LOCK-CANDIDATE`、`Q-CLEAR-RESET`。 |
| `secondary_rule_ids` | list | 否 | 横向判读矩阵 / 试填审计 | 单段同时具备减仓、清零、重建等辅状态时保留，不替代主规则。 |
| `tachibana_applicability` | enum | 是 | 前置过滤器 | `suitable / conditional`，不得出现 `unknown / unsuitable` 的执行输入。 |
| `applicability_reason` | string/list | 是 | 样本表 / 矩阵 | 为什么可以进入 Method / PM。 |
| `boundary_warning` | list | 是 | 横向判读矩阵 | 防止 PM 语义污染 MALF 的警告。 |
| `evidence_level` | enum/list | 是 | 样本升级门槛 | `E1_malf_snapshot / E2_monthly_fact / E3_book_statement / E4_research_mapping`。 |

### 3. Method 字段

| 字段 | 类型 | 必填 | 来源 | 含义 |
|---|---|---|---|---|
| `method_action` | enum | 是 | Method | `trend_probe_entry / trend_confirmation_add / pullback_entry / pullback_add / distribution_reduce / exit_on_rhythm_failure / reversal_flip / inventory_rebalance / wait_no_action`。 |
| `method_reason` | list | 是 | Method | 如 `staged_execution`、`active_waiting`、`accept_and_correct`。 |
| `method_candidates` | list | 否 | 前置过滤器 / 样本表 | 多个可能动作尚未裁决时保留候选。 |
| `method_status` | enum | 是 | 适配层 | `observed / inferred / hypothesis`。 |

### 4. PM 字段

| 字段 | 类型 | 必填 | 来源 | 含义 |
|---|---|---|---|---|
| `pm_required` | boolean | 是 | 前置过滤器 / Method | 是否必须进入 PM 承接仓位语义。 |
| `pm_action` | enum/null | 条件必填 | PM | `open_center / add_on / reduce_add_on / reduce_center / inventory_seed / lock_candidate / unlock / rebalance / clear / hold`。 |
| `gross_long` | number | 是 | PM / 交易记录 | 多头总手数。 |
| `gross_short` | number | 是 | PM / 交易记录 | 空头总手数。 |
| `net_position` | number | 是 | PM / 交易记录 | 净持仓，只作执行计算，不作结构方向裁决。 |
| `center_side` | enum | 条件必填 | PM | `long / short / none / mixed / unknown`。 |
| `center_size` | number/null | 条件必填 | PM | 中心单估计手数；证据不足则为空，不能因为 `center_side` 有方向就自动填规模。 |
| `add_on_size` | number/null | 否 | PM | 加码单估计手数。 |
| `average_price_long` | number/null | 否 | PM / Data | 多头均价。 |
| `average_price_short` | number/null | 否 | PM / Data | 空头均价。 |
| `lock_status` | enum | 是 | PM | `none / candidate / confirmed / unlocking / unknown`。 |
| `lock_candidate_size` | number/null | 否 | PM | 双侧库存重叠规模；不能由 MALF 推断。 |
| `scale_alert` | enum | 是 | 横向矩阵 / PM | `none / elevated / extreme / unknown`。 |
| `reset_after_clear` | boolean | 是 | 横向矩阵 / PM | 清零后是否开启新段。 |

### 5. 执行桥接字段

| 字段 | 类型 | 必填 | 来源 | 含义 |
|---|---|---|---|---|
| `execution_intent` | enum | 是 | 适配层 | `replay_observed_action / replay_hypothesis_plan / audit_only`。 |
| `execution_event_type` | enum/null | 条件必填 | 适配层 / Backtest | `open / add / reduce / close / hold / rebalance`。 |
| `execution_size` | number/null | 条件必填 | PM / 回放规则 | 本次执行手数；不能由 MALF 生成。 |
| `execution_side` | enum/null | 条件必填 | PM / 回放规则 | `long / short / both / none`。 |
| `execution_constraints_ref` | string/null | 否 | A 股制度改造启动闸门 / Backtest | 未来 A 股制度约束引用；必须先通过制度改造启动闸门，本文件暂不定义具体规则。 |
| `backtest_notes` | list | 否 | 适配层 | 资料缺口、证据限制、人工解释。 |

## 横向矩阵到适配层的映射

| `qualification_rule_id` | 适配层动作 | 必填保护字段 |
|---|---|---|
| `Q-ALIVE-CLEAN` | 可进入 Method / PM，通常不需要锁单字段。 | `do_not_infer_position_size_from_malf`。 |
| `Q-ALIVE-PM-MIXED` | 可进入，但必须由 PM 承接中心单、母单或加码解释。 | `center_side`、`center_size`、`scale_alert`。 |
| `Q-PRESSURE-ADJUST` | 可进入库存压力调整回放，但不得当成干净推进或清零重置。 | `pm_action=rebalance`、`secondary_rule_ids`。 |
| `Q-LOCK-CANDIDATE` | 可进入库存再平衡或锁单候选回放。 | `gross_long`、`gross_short`、`lock_status=candidate`。 |
| `Q-LOCK-WAIT` | 可记录等待和持仓压力，不强制生成成交事件。 | `execution_event_type=hold`、双侧库存字段。 |
| `Q-UNLOCK` | 可记录解除一侧库存。 | `lock_status=unlocking`、剩余单侧库存。 |
| `Q-CLEAR-RESET` | 可生成清仓或段落终止事件。 | `pm_action=clear`、`reset_after_clear=true`。 |
| `Q-SEED-AFTER-CLEAR` | 可生成新试探段。 | 新 `segment_id`，不得并回旧段。 |
| `Q-EXTREME-ADDON` | 可回放极端加码，但必须标风险尺度。 | `scale_alert=extreme`。 |
| `Q-REDUCE-WINDOW` | 可生成分批减仓或收束事件。 | `pm_action=reduce_add_on / reduce_center`。 |
| `Q-NO-TRADE` | 通常生成 `hold` 或 `audit_only`。 | 禁止用无交易反推 `range`。 |
| `Q-SOURCE-DISRUPTED` | 不生成执行输入，只进 `research_audit`。 | `execution_intent=audit_only`。 |

## 禁止字段

以下字段不得出现在 `TachibanaBacktestInputSnapshot` 中；如未来某层需要类似概念，应另建明确归属。

| 禁止字段 | 禁止原因 |
|---|---|
| `signal_decision` | 会把结构资格误读为 Signal 裁决。 |
| `trade_accept / trade_reject / trade_defer` | 这些属于通用 Signal 语义。 |
| `signal_decision_from_rhythm` | 会把 `rhythm_meaning` 误写成 Signal 裁决。 |
| `trade_accept_from_meaningful` | `meaningful` 只表示仓位节奏值得讨论，不表示应该交易。 |
| `trade_reject_from_not_meaningful` | `not_meaningful` 只表示立花节奏无意义，不表示看空或卖出。 |
| `backtest_gate_by_rhythm_only` | 回测入口不能只看节奏意义，必须同时有适用性和 Method / PM 计划。 |
| `prediction_direction` | 立花 Method 不是先预测方向再下单。 |
| `target_position_from_malf` | MALF 不输出目标仓位。 |
| `center_position_from_malf` | 中心单属于 PM，不属于 MALF。 |
| `lock_confirmed_by_malf` | 锁单确认必须来自 PM / 书页证据 / 交易事实，不来自 MALF。 |
| `structure_strength_by_size` | 加码尺度不能被当作结构强度。 |

## 示例：1976-04-A

```yaml
adapter_version: tachibana_backtest_input_v0.1
snapshot_granularity: segment_summary
mode: observed_replay
sample_id: 1976-04-A
segment_id: 1976-04-dual-inventory-chain
symbol: pioneer_electronics
timeframe: daily
malf_snapshot_ref: null
malf_background:
  - transition
  - lock_candidate
rhythm_meaning: limited
meaning_reason:
  - rhythm_meaning_limited
meaning_boundary_warning:
  - do_not_convert_rhythm_meaning_to_signal_accept
  - do_not_generate_trade_from_rhythm_meaning_only
qualification_rule_id: Q-LOCK-CANDIDATE
secondary_rule_ids: []
tachibana_applicability: conditional
boundary_warning:
  - do_not_confirm_lock_from_dual_inventory_only
  - do_not_net_dual_inventory_into_single_direction
evidence_level:
  - E2_monthly_fact
  - E4_research_mapping
method_action: inventory_rebalance
method_status: observed
pm_required: true
pm_action: lock_candidate
gross_long: 2
gross_short: 20
net_position: -18
center_side: mixed
lock_status: candidate
scale_alert: none
reset_after_clear: false
execution_intent: replay_observed_action
execution_event_type: rebalance
backtest_notes:
  - 双侧库存可进入 PM，但不能由 MALF 确认锁单目的。
```

## v0.1 裁决

- `TachibanaBacktestInputSnapshot` 是 Tachibana 研究路线的专用适配层，不是通用 Signal 的替代品。
- `tachibana_applicability` 只控制能否进入 Method / PM / 回测适配，不控制交易是否成立。
- 回测执行层可以消费手数、方向、清仓、等待、双侧库存等事实，但不得反向修订 MALF 主定义、前置过滤器或横向判读矩阵。
- A 股适配后续只能接在 `execution_constraints_ref` 一侧，不能回头改写结构资格与 Method / PM 本体。
- 1976 段级样本试填显示，主体字段成立；v0.1 必须保留 `snapshot_granularity` 与 `secondary_rule_ids`，避免复杂交易段被单标签化。
- 1975-06 试填显示，母单候选和双侧库存可以由现有字段承接；`center_side` 可记录 PM 候选方向，但 `center_size` 不得自动生成。

## 下一步

下一轮应按 [Tachibana A 股最小接入包字段契约 v0.1](./Tachibana-A股最小接入包字段契约-v0.1.md) 导入最小接入包，按 [Tachibana A 股最小接入包复核流程 v0.1](./Tachibana-A股最小接入包复核流程-v0.1.md) 更新 [Tachibana A 股最小接入包验收报告 v0.1](./Tachibana-A股最小接入包验收报告-v0.1.md)，再按 [Tachibana A 股结构资格判定记录模板 v0.1](./Tachibana-A股结构资格判定记录模板-v0.1.md) 填写单窗口底稿，并用 [Tachibana A 股结构资格升级闸门检查清单 v0.1](./Tachibana-A股结构资格升级闸门检查清单-v0.1.md) 防止跳级，最后填充 [Tachibana A 股候选股票结构资格样本表 v0.1](./Tachibana-A股候选股票结构资格样本表-v0.1.md)，仍不进入 T+1、涨跌停、停牌等制度规则改造。
