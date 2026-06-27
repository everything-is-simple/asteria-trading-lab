# Tachibana rhythm_meaning Data / Signal / Backtest 接口接缝补丁 v0.1

## 版本定位

- 本文件是 [Tachibana Data / Signal / Backtest 接口边界审计 v0.1](./Tachibana-Data-Signal-Backtest-接口边界审计-v0.1.md) 的补丁文档。
- 它承接 [MALF-立花结构状态到仓位节奏意义判定准则 v0.1](./MALF-立花结构状态到仓位节奏意义判定准则-v0.1.md) 与 [Tachibana Backtest Input 适配层草案 v0.1](./Tachibana-Backtest-Input-适配层草案-v0.1.md)。
- 它只定义 `rhythm_meaning` 如何穿过 Data / Signal / Backtest 边界，不修改 MALF、Data、Signal、Backtest 的通用定义。
- 它不是交易信号，不输出 `accept / reject / defer`，不定义 T+1、涨跌停、停牌、整手或任何 A 股执行规则。

## 要解决的接口问题

`rhythm_meaning` 是“结构状态下，立花仓位节奏是否有讨论意义”的中间裁决。它位于 MALF 事实与 `tachibana_applicability` 之间：

```mermaid
flowchart LR
  A["Data: 市场事实"] --> B["MALF Snapshot: 结构事实"]
  B --> C["rhythm_meaning: 仓位节奏意义"]
  C --> D["tachibana_applicability: 立花适用性"]
  D --> E["Tachibana Method / PM"]
  E --> F["TachibanaBacktestInputSnapshot"]
  F --> G["Backtest 执行层"]
```

如果不显式定义这个接缝，后续有两个风险：

| 风险 | 后果 |
|---|---|
| 把 `rhythm_meaning=meaningful` 当成 Signal `accept`。 | 结构资格被误写成交易裁决。 |
| 把 `rhythm_meaning=not_meaningful / unknown` 当成交易 `reject / defer`。 | 研究过滤被误写成买卖判断。 |

因此，本文件只做一件事：规定 `rhythm_meaning` 是前置认知过滤器的研究字段，可以被 Backtest Input 作为上下文携带，但永远不能被 Signal 或 Backtest 改写为交易裁决。

## 字段定义

| 字段 | 类型 | 允许值 | 写入者 | 读取者 | 含义 |
|---|---|---|---|---|---|
| `rhythm_meaning` | enum | `meaningful / limited / not_meaningful / unknown` | MALF-立花前置过滤器 / 节奏意义准则 | 样本表、Backtest Input、研究审计 | 结构状态下立花仓位节奏是否值得讨论。 |
| `meaning_reason` | list | 受控理由码 | 节奏意义准则 / 理由码表 | 样本表、Backtest Input | 支撑 `rhythm_meaning` 的理由。 |
| `meaning_boundary_warning` | list | 受控边界警告 | 节奏意义准则 / 理由码表 | Backtest Input、研究审计 | 防止把节奏意义误写成交易动作。 |

`rhythm_meaning` 的含义必须先于 `tachibana_applicability`，但不替代它：

| `rhythm_meaning` | 可映射的 `tachibana_applicability` | Backtest Input 处理 |
|---|---|---|
| `meaningful` | `suitable` 候选 | 可生成执行型研究快照，但仍需 Method / PM 输出动作。 |
| `limited` | `conditional` | 可生成带限制的执行型研究快照，必须携带限制理由和边界警告。 |
| `not_meaningful` | `unsuitable` | 只能进入 `research_audit`，不得进入 Method / PM / Backtest 成交。 |
| `unknown` | `unknown` | 只能进入资料补证或 MALF 快照补证队列。 |

## 分层归属

| 层 | 可以做 | 不可以做 |
|---|---|---|
| Data | 提供 OHLCV、复权口径、交易日历、停牌事实、候选元数据。 | 写入 `rhythm_meaning`，判断结构是否适合立花节奏。 |
| MALF | 输出结构事实，如 wave、range、break、transition、stagnation。 | 输出买卖动作、仓位规模、Signal 决策。 |
| 前置过滤器 | 基于 MALF 事实写入 `rhythm_meaning`，再映射 `tachibana_applicability`。 | 因为某次历史盈利或亏损而修改 MALF 主定义。 |
| Signal | 保持通用 `accept / reject / defer` 语义。 | 直接消费 `rhythm_meaning` 并生成 `accept / reject / defer`。 |
| Method / PM | 在 `meaningful / limited` 且 `suitable / conditional` 后讨论动作和仓位节奏。 | 反向要求 MALF 改写结构事实。 |
| Backtest Input | 作为上下文字段携带 `rhythm_meaning`、理由和边界警告。 | 用 `rhythm_meaning` 单独生成成交事件。 |
| Backtest | 执行已经形成的 Method / PM 计划，记录成交、持仓、PnL、执行失败原因。 | 用绩效反推 `rhythm_meaning`，或把执行失败写成结构不适用。 |

## Backtest Input 字段补丁

在 `TachibanaBacktestInputSnapshot` 的“结构资格字段”中补入以下字段：

| 字段 | 类型 | 必填 | 来源 | 约束 |
|---|---|---|---|---|
| `rhythm_meaning` | enum | 是 | 节奏意义准则 | 执行型快照只允许 `meaningful / limited`。 |
| `meaning_reason` | list | 是 | 理由码表 | 必须能解释 `rhythm_meaning`，不能写买卖理由。 |
| `meaning_boundary_warning` | list | 条件必填 | 理由码表 / 边界审计 | `limited / not_meaningful / unknown` 必填；`meaningful` 可为空但建议记录。 |

执行型快照的最低入口条件改为双闸门：

| 闸门 | 允许进入执行型 Backtest Input | 只能进入 `research_audit` |
|---|---|---|
| `rhythm_meaning` | `meaningful / limited` | `not_meaningful / unknown` |
| `tachibana_applicability` | `suitable / conditional` | `unsuitable / unknown` |

两个闸门必须同时满足。任何一侧为 `not_meaningful / unsuitable / unknown`，都不能生成成交型回测输入。

## 禁止字段与禁止推导

以下字段不得出现在 `TachibanaBacktestInputSnapshot`、A 股结构资格底稿或 Signal 接口中：

| 禁止字段 | 禁止原因 |
|---|---|
| `signal_decision_from_rhythm` | 把节奏意义伪装成 Signal 决策。 |
| `trade_accept_from_meaningful` | `meaningful` 只表示值得讨论，不表示应该交易。 |
| `trade_reject_from_not_meaningful` | `not_meaningful` 只表示立花节奏无意义，不表示看空或卖出。 |
| `trade_defer_from_unknown_rhythm` | `unknown` 是证据不足，不是 Signal defer。 |
| `target_position_from_rhythm` | `rhythm_meaning` 不输出目标仓位。 |
| `backtest_gate_by_rhythm_only` | Backtest 入口不能只看节奏意义，必须还有 Method / PM 计划。 |

禁止推导：

| 推导写法 | 裁决 |
|---|---|
| `meaningful -> accept` | 永禁。 |
| `limited -> defer` | 永禁。 |
| `not_meaningful -> reject` | 永禁。 |
| `unknown -> defer_insufficient_probability` | 永禁。 |
| `execution_failed -> rhythm_meaning_not_meaningful` | 永禁。 |
| `PnL_positive -> rhythm_meaning_meaningful` | 永禁。 |

## 接口不变量

| 编号 | 不变量 |
|---|---|
| `R-1` | `rhythm_meaning` 是前置认知过滤字段，不是交易裁决。 |
| `R-2` | Data 不能写入 `rhythm_meaning`。 |
| `R-3` | Signal 不能把 `rhythm_meaning` 映射为 `accept / reject / defer`。 |
| `R-4` | Backtest 不能用成交、未成交或 PnL 反推 `rhythm_meaning`。 |
| `R-5` | A 股制度约束仍是执行约束，不能参与 `rhythm_meaning` 判定。 |
| `R-6` | `rhythm_meaning` 只能控制是否值得进入立花 Method / PM 讨论，不能直接生成动作或仓位。 |

这些不变量由 `interface_boundary_gate` 做机器化边界审计：

| 越界场景 | 机器阻断码 |
|---|---|
| Data 层写入 `rhythm_meaning`。 | `data_layer_must_not_write:rhythm_meaning` |
| Signal 层读取 `rhythm_meaning`。 | `signal_layer_must_not_read:rhythm_meaning` |
| Signal 层输出 `signal_decision_from_rhythm`。 | `signal_layer_forbidden_field:signal_decision_from_rhythm` |
| Backtest 层用执行结果回写 `rhythm_meaning`。 | `backtest_layer_must_not_write:rhythm_meaning` |
| Backtest 层回写 `tachibana_applicability` 或 `structure_suitable`。 | `backtest_layer_must_not_write:tachibana_applicability` / `backtest_layer_must_not_write:structure_suitable` |

## 示例

```yaml
adapter_version: tachibana_backtest_input_v0.1
mode: observed_replay
sample_id: 1976-04-A
malf_background:
  - transition
  - lock_candidate
rhythm_meaning: limited
meaning_reason:
  - rhythm_meaning_limited
meaning_boundary_warning:
  - do_not_convert_rhythm_meaning_to_signal_accept
  - do_not_generate_trade_from_rhythm_meaning_only
tachibana_applicability: conditional
qualification_rule_id: Q-LOCK-CANDIDATE
method_action: inventory_rebalance
pm_required: true
execution_intent: replay_observed_action
```

这个样例只说明：1976-04-A 可以作为“带限制的仓位节奏研究样本”进入 Method / PM 和 observed replay。它不说明当下应该买、卖、加仓、减仓或锁单。

## 当前裁决

- `rhythm_meaning` 应作为 `TachibanaBacktestInputSnapshot` 的结构资格上下文字段补入。
- `rhythm_meaning` 不需要 MALF 通用定义修订；它属于 MALF-立花前置过滤器的派生研究字段。
- `Signal_Definitive_v2_0` 不需要为它增加规则；禁止把它接入 Signal `accept / reject / defer`。
- `Backtest_Definitive_v2_0` 不需要为它增加结构裁决能力；Backtest 只在 Method / PM 已经生成计划后执行。
- A 股适配仍保持后置：真实 A 股样本必须先通过结构资格与节奏意义判定，再讨论制度执行约束。
