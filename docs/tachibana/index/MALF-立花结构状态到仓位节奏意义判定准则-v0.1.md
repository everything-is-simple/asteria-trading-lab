# MALF-立花结构状态到仓位节奏意义判定准则 v0.1

## 版本定位

- 本文件承接 [MALF-立花前置认知过滤器 v0.1](./MALF-立花前置认知过滤器-v0.1.md)、[MALF-立花结构资格横向判读矩阵 v0.1](./MALF-立花结构资格横向判读矩阵-v0.1.md) 与 [Tachibana A 股候选股票结构资格样本表 v0.1](./Tachibana-A股候选股票结构资格样本表-v0.1.md)。
- 它把“结构状态 -> 仓位节奏意义”写成可判定、可复核的准则。
- 1975-1976 历史样本的回填验证见 [MALF-立花 rhythm_meaning 历史样本回填审计 v0.1](./MALF-立花rhythm_meaning历史样本回填审计-v0.1.md)。
- `not_meaningful` 的反例登记口径见 [MALF-立花 not_meaningful 反例登记表 v0.1](./MALF-立花not_meaningful反例登记表-v0.1.md)。
- 它不是 MALF 主定义修订，不是 Tachibana Method，不是 PM，不是 A 股制度规则。
- 它不输出买卖信号，不决定目标仓位，不定义 T+1、涨跌停、停牌或任何执行约束。

## 核心问题

本准则只回答：

> 给定一个 MALF 结构状态，立花式仓位节奏在这里是否有讨论意义？

它不回答：

- 应不应该买入或卖出。
- 应该建多少仓位。
- 是否通过 Signal。
- A 股制度下如何执行。

## 输出值

| 输出值 | 含义 | 与 `tachibana_applicability` 的关系 |
|---|---|---|
| `meaningful` | 结构状态清楚，立花式试探、推进、收束或等待节奏有明确讨论对象。 | 通常可映射为 `suitable`。 |
| `limited` | 结构状态有讨论价值，但 PM、证据缺口或边界风险主导，必须带限制条件。 | 通常映射为 `conditional`。 |
| `not_meaningful` | 结构状态不适合讨论立花仓位节奏，或讨论会造成边界污染。 | 通常映射为 `unsuitable`。 |
| `unknown` | MALF 快照、样本、来源或口径不足，不能判断意义。 | 映射为 `unknown`。 |

`meaningful` 不等于交易可做，`not_meaningful` 不等于看空，`unknown` 不等于放弃研究。

## 判定输入

| 输入 | 必要性 | 用途 |
|---|---:|---|
| `malf_snapshot_ref` | 必要 | 证明结构背景不是人工猜测。历史人工样本可暂用 `null`，但必须标注证据等级。 |
| `malf_background` | 必要 | 如 `alive_wave / pullback / range / break_birth / stagnation / transition / unknown`。 |
| `qualification_rule_id` | 条件必要 | 对齐横向矩阵的 `Q-*` 规则。 |
| `secondary_rule_ids` | 可选 | 复杂结构保留辅规则，避免压扁成单一状态。 |
| `pm_complexity` | 必要 | `none / low / medium / high`，只表示 PM 是否必须承接，不表示仓位大小。 |
| `evidence_level` | 必要 | 区分真实 MALF 快照、日线事实、书页证据、人工映射。 |
| `boundary_warning` | 必要 | 防止把结构意义误读为交易动作。 |

## 总闸门

| 闸门 | 通过条件 | 未通过处理 |
|---|---|---|
| G1: 结构可读 | `malf_background != unknown`，或历史人工样本有足够事实锚点。 | 输出 `unknown`。 |
| G2: 规则可对齐 | 能匹配一个主 `qualification_rule_id`，或能说明为什么暂不匹配。 | 输出 `unknown` 或 `not_meaningful`。 |
| G3: PM 不反噬结构 | 中心单、锁单、加码尺度、清仓原因不写回 MALF。 | 降为 `limited` 或 `not_meaningful`。 |
| G4: 边界警告完整 | 复杂结构必须带 `boundary_warning`。 | 不得输出 `meaningful`。 |
| G5: 制度后置 | 没有用 T+1、涨跌停、停牌先行决定结构意义。 | 判定无效，退回重填。 |

## 结构状态意义矩阵

| malf_background | 常见 `qualification_rule_id` | 节奏意义 | 默认输出 | Method / PM 入口 |
|---|---|---|---|---|
| `alive_wave` 且动作链稳定 | `Q-ALIVE-CLEAN` | 有方向、有推进、有分批节奏，立花法的仓位节奏有清楚对象。 | `meaningful` | Method 可讨论试探、推进、收束；PM 只承接手数与中心单候选。 |
| `alive_wave` 但 PM 复杂 | `Q-ALIVE-PM-MIXED / Q-EXTREME-ADDON` | 方向推进有意义，但中心单、母单或加码尺度会主导解释。 | `limited` | Method 可讨论节奏，PM 必须承接中心单、加码尺度和风险压力。 |
| `pullback` 或压力调整 | `Q-PRESSURE-ADJUST / Q-REDUCE-WINDOW` | 节奏是否延续需要观察，适合讨论减仓、加回、等待。 | `limited` | Method 讨论调整语义，PM 承接库存压力。 |
| `range` 或 no-progress | `Q-NO-TRADE / Q-LOCK-WAIT` | 等待可能有意义，但无交易不能自动证明 range。 | `limited / unknown` | 有持仓时 PM 记录压力；无持仓时只保留观察。 |
| `break_birth` | `Q-SEED-AFTER-CLEAR` | 旧节奏结束，新节奏可能开始，适合讨论重试或反手背景。 | `limited` | Method 可讨论新试探；PM 必须重置段与中心单候选。 |
| `stagnation` 或 exit window | `Q-CLEAR-RESET / Q-REDUCE-WINDOW` | 原节奏收束或失败，适合讨论退出、清零、等待。 | `limited` | Method / PM 承接退出语义；MALF 不写清仓原因。 |
| `transition` | `Q-LOCK-CANDIDATE / Q-UNLOCK / Q-PRESSURE-ADJUST` | 结构仍在切换，仓位节奏有研究价值但边界风险高。 | `limited` | PM 必须保留双侧库存、解锁或库存再平衡事实。 |
| `unknown` | `Q-SOURCE-DISRUPTED` 或无规则 | 结构意义不可判。 | `unknown` | 不进入 Method / PM。 |
| 明确与立花节奏无关 | 待真实反例补充 | 不适合作为立花仓位节奏讨论对象。 | `not_meaningful` | 只保留研究记录。 |

## 输出映射

| rhythm_meaning | tachibana_applicability | candidate_stage 建议 | next_action 建议 |
|---|---|---|---|
| `meaningful` | `suitable` | `tachibana_candidate` | `action:fill_qualification_record` 或 `action:method_pm_review` |
| `limited` | `conditional` | `tachibana_candidate` 或保留 `structure_candidate` | `action:fill_qualification_record`，必要时 `action:method_pm_review` |
| `not_meaningful` | `unsuitable` | `rejected` 或研究记录 | `action:research_audit_only` |
| `unknown` | `unknown` | `unknown / universe_candidate / structure_candidate` | `action:repair_data / action:run_malf_snapshot / action:keep_pending` |

## 不得升级为 `meaningful` 的情况

| 情况 | 正确处理 |
|---|---|
| 缺 MALF 快照且没有历史人工证据锚点。 | `unknown`。 |
| 只有行业、流动性、板块或人工选股理由。 | `unknown` 或保留低阶候选。 |
| 无交易或少交易次数。 | `limited / unknown`，不得直接判定为 range 节奏。 |
| 双侧库存、锁单候选、解锁、极端加码。 | `limited`，必须 PM 承接。 |
| 清仓、认错、利润保护、风险承受解释主导。 | `limited`，不得写回 MALF。 |
| 资料口径、交易单位、除权或样本链条扰动。 | `unknown`。 |
| 用 T+1、涨跌停、停牌先行裁决。 | 判定无效，退回结构资格层重填。 |

## 与 A 股样本表的关系

A 股候选样本应先取得 `rhythm_meaning`，再写 `tachibana_applicability`：

1. `universe_candidate` 只说明股票可识别，不允许写 `rhythm_meaning=meaningful`。
2. `structure_candidate` 有日线窗口和 MALF 快照后，才允许判定 `rhythm_meaning`。
3. `rhythm_meaning=meaningful/limited` 后，才允许升级为 `tachibana_candidate`。
4. `tachibana_candidate` 仍不是交易信号，只是 Method / PM 的讨论对象。

## 推荐记录字段

| 字段 | 含义 |
|---|---|
| `rhythm_meaning` | `meaningful / limited / not_meaningful / unknown`。 |
| `meaning_reason` | 使用受控理由码说明为什么有意义或无意义。 |
| `meaning_gate_result` | G1-G5 的通过、警告或阻断状态。 |
| `meaning_boundary_warning` | 与本次意义判定直接相关的边界警告。 |
| `meaning_to_applicability_mapping` | 映射到 `tachibana_applicability` 的理由。 |

## 机器行门禁

每一行“结构状态 -> 仓位节奏意义”样本，都必须通过 `rhythm_sample_row_gate`。该门禁不替代人工结构判断，只检查样本行是否符合本准则的基本约束。

| 检查项 | 要求 | 阻断示例 |
|---|---|---|
| 快照质量 | 非历史人工样本必须有 `snapshot_quality_status=ready` 才能输出 `meaningful/limited/not_meaningful`。 | `non_ready_snapshot_requires_unknown`。 |
| 结构背景 | `malf_background=unknown` 时只能输出 `rhythm_meaning=unknown`。 | `unknown_malf_background_requires_unknown`。 |
| 映射一致 | `meaningful -> suitable`、`limited -> conditional`、`not_meaningful -> unsuitable`、`unknown -> unknown`。 | `rhythm_applicability_mapping_mismatch`。 |
| PM 复杂度 | `meaningful` 只允许 `pm_complexity=none/low`。 | `meaningful_requires_low_pm_complexity`。 |
| 受限规则 | `Q-EXTREME-ADDON / Q-LOCK-WAIT / Q-CLEAR-RESET` 等必须输出 `limited`。 | `q_extreme_addon_requires_limited`。 |
| 反例规则 | `NM-*` 必须输出 `not_meaningful`，并映射 `unsuitable`。 | `nm_no_structure_requires_not_meaningful`。 |
| 证据与边界 | 必须有 `meaning_reason`、`boundary_warning`、`evidence_level`。 | `rhythm_row_requires_boundary_warning`。 |

门禁通过时输出 `row_status=rhythm_row_ready`；阻断时输出 `row_status=rhythm_row_review_required`，不得写入候选样本表或 Method / PM。

## 当前结论

- 立花法适配的核心不是先改交易规则，而是先判断结构状态下仓位节奏是否有意义。
- `limited` 是 A 股适配前最重要的现实状态：它允许进入 Method / PM，但保留结构边界。
- 历史样本回填显示：`meaningful` 只覆盖少数干净推进样本，`limited` 才是主力状态，`unknown` 必须作为有理由阻断保留。
- `not_meaningful` 不从历史样本硬造，先由 [MALF-立花 not_meaningful 反例登记表 v0.1](./MALF-立花not_meaningful反例登记表-v0.1.md) 定义证据门槛，等待真实 A 股 MALF 快照补样本。
- MALF 只提供结构事实和背景；本准则只判断节奏意义；Method / PM 才处理交易动作与仓位语义。
- 后续真实 A 股样本进入前，必须先用本准则完成 `rhythm_meaning` 判定，再写 `tachibana_applicability`。
