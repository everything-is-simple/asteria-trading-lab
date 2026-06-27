# MALF-立花 not_meaningful 反例登记表 v0.1

## 版本定位

- 本文件承接 [MALF-立花结构状态到仓位节奏意义判定准则 v0.1](./MALF-立花结构状态到仓位节奏意义判定准则-v0.1.md)、[MALF-立花 rhythm_meaning 历史样本回填审计 v0.1](./MALF-立花rhythm_meaning历史样本回填审计-v0.1.md) 与 [Tachibana A 股结构资格理由码表 v0.1](./Tachibana-A股结构资格理由码表-v0.1.md)。
- 它定义 `rhythm_meaning=not_meaningful` 的反例登记口径。
- 它不是交易排除规则，不是 Signal reject，不是选股黑名单，不是 A 股制度规则。
- 它只回答：什么证据足以说明某个结构状态不值得进入立花式仓位节奏讨论。

## 为什么需要本表

历史样本回填中，`meaningful=4`、`limited=19`、`unknown=1`、`not_meaningful=0`。这不是说所有真实结构都适合立花法，而是说明：

- 1975-1976 先锋电子研究样本本身来自立花实战记录，天然偏向“有讨论价值”。
- 不能从历史样本硬造 `not_meaningful`。
- 但 A 股真实候选池会包含大量不适合立花节奏的结构，必须提前定义“关门条件”。

本表补的是前置过滤器的关门能力。

## not_meaningful 的定义

`rhythm_meaning=not_meaningful` 表示：

> 当前结构状态与立花式试探、推进、收束、等待等仓位节奏没有合理讨论对象，或一旦讨论就会把非结构事实误当成结构节奏。

它不表示：

- 股票看空。
- 交易失败。
- Signal reject。
- 永久不可研究。
- A 股制度不可执行。

## 判定铁律

| 编号 | 铁律 | 说明 |
|---|---|---|
| N-1 | `not_meaningful` 必须基于结构证据。 | 不能只因行业、流动性、板块、涨跌停或人工偏好得出。 |
| N-2 | 证据不足时用 `unknown`，不是 `not_meaningful`。 | 缺数据、缺 MALF 快照、口径扰动时先保持 unknown。 |
| N-3 | PM 复杂不等于 `not_meaningful`。 | 中心单、锁单、加码尺度复杂通常是 `limited`。 |
| N-4 | 无交易不等于 `not_meaningful`。 | 无交易可能是等待、资料缺失或节奏外空窗。 |
| N-5 | `not_meaningful` 不得进入 Method / PM / Backtest Input。 | 只进入研究审计或 rejected 记录。 |

## 反例类型目录

| 反例类型 | 结构证据要求 | 默认输出 | 理由码建议 | 说明 |
|---|---|---|---|---|
| `NM-NO-STRUCTURE` | MALF 快照 ready，但无法形成 wave/range/break/stagnation 等可读结构，且不是数据缺失。 | `not_meaningful` | `rhythm_meaning_not_meaningful` | 结构本身没有节奏对象。 |
| `NM-NO-RHYTHM-OBJECT` | 有价格波动，但没有可复核的试探、推进、收束或等待节奏对象。 | `not_meaningful` | `structure_unsuitable_for_tachibana_rhythm` | 波动不等于立花节奏。 |
| `NM-NOISE-DOMINATED` | MALF 显示碎片化、短促反复、无可延续结构，且样本质量 ready。 | `not_meaningful` | `rhythm_meaning_not_meaningful` | 与 `unknown` 区分：数据足够，但结构噪声主导。 |
| `NM-EVENT-DOMINATED` | 结构主要由单一事件跳变支配，MALF 无可延续节奏，且事件不是可被 Method / PM 承接的普通波段。 | `not_meaningful` | `structure_unsuitable_for_tachibana_rhythm` | 事件资料不足时仍应 `unknown`。 |
| `NM-LIQUIDITY-ONLY` | 只有流动性或成交活跃理由，没有结构资格。 | `unknown` 或 `not_meaningful` | `do_not_treat_liquidity_as_structure` | 若结构未跑出，先 unknown；若快照 ready 且无结构对象，可 not_meaningful。 |
| `NM-INDUSTRY-ONLY` | 只有行业热度或主题理由，没有结构资格。 | `unknown` 或 `not_meaningful` | `do_not_use_industry_hot_score_as_structure_evidence` | 不能用行业热度替代结构节奏。 |
| `NM-PM-ONLY` | 只有仓位/交易动作事实，没有可读 MALF 结构背景。 | `unknown` 或 `not_meaningful` | `do_not_convert_applicability_to_signal_accept` | 如果只是缺结构证据，用 unknown；若快照 ready 仍无对象，可 not_meaningful。 |

## 与 unknown 的边界

| 情况 | 应判 `unknown` | 可判 `not_meaningful` |
|---|---|---|
| MALF 快照缺失 | 是 | 否 |
| 日线窗口缺失或质量不合格 | 是 | 否 |
| 资料口径扰动 | 是 | 否 |
| MALF 快照 ready，但结构对象不可读 | 否 | 是 |
| 只有行业/流动性理由 | 通常是 | 仅当结构快照 ready 且无节奏对象 |
| PM 动作复杂 | 否，通常为 `limited` | 只有在无结构对象且 PM 事实无法承接时 |

## 与 limited 的边界

| 情况 | 应判 `limited` | 可判 `not_meaningful` |
|---|---|---|
| 有向推进存在，但中心单/加码/锁单复杂 | 是 | 否 |
| 清零后新试探形成种子 | 是 | 否 |
| 无交易但有持仓压力或等待语义 | 是 | 否 |
| 有结构对象，但需要 PM 承接 | 是 | 否 |
| 没有可讨论的结构节奏对象 | 否 | 是 |
| 结构讨论会迫使交易动作倒推 MALF | 否 | 是 |

## 登记模板

```yaml
negative_sample_id: NM-TBD-v0.1
source_scope: ashare_real_sample | historical_review | synthetic_test_fixture
sample_ref: TBD
malf_snapshot_ref: TBD
malf_snapshot_quality: ready
malf_background: TBD
candidate_stage_before: structure_candidate
rhythm_meaning: not_meaningful
tachibana_applicability: unsuitable
negative_type: NM-NO-STRUCTURE
meaning_reason:
  - rhythm_meaning_not_meaningful
  - structure_unsuitable_for_tachibana_rhythm
boundary_warning:
  - do_not_convert_applicability_to_signal_accept
next_action: action:research_audit_only
evidence_level:
  - E1_malf_snapshot
  - E2_ashare_daily_fact
review_note: "说明为什么不是 unknown，也不是 limited。"
```

## 当前登记队列

| negative_sample_id | 来源 | 当前状态 | 说明 |
|---|---|---|---|
| `NM-PENDING-001` | A 股真实样本待补 | `pending_data` | 需要 ready MALF 快照，但无可讨论结构节奏对象的样本。 |
| `NM-PENDING-002` | A 股真实样本待补 | `pending_data` | 需要数据质量 ready、但结构噪声主导的样本。 |
| `NM-PENDING-003` | A 股真实样本待补 | `pending_data` | 需要行业/流动性理由强、但结构资格不成立的样本。 |

当前没有把任何 1975-1976 历史样本改判为 `not_meaningful`。历史样本仍以 [MALF-立花 rhythm_meaning 历史样本回填审计 v0.1](./MALF-立花rhythm_meaning历史样本回填审计-v0.1.md) 的分布为准。

## 对 A 股适配的含义

- A 股真实候选池必须允许 `not_meaningful`，否则前置过滤器只能放行或待定，无法真正过滤。
- `not_meaningful` 必须来自结构证据，不得来自制度约束。
- `not_meaningful` 样本不进入 Tachibana Method / PM / Backtest Input，只保留为研究审计。
- 如果未来发现大量 `not_meaningful` 都来自同一类 MALF 背景，应再抽象新的 `NM-*` 类型，而不是修订 MALF 主定义。

## 当前结论

- `not_meaningful` 是前置过滤器的必要出口，但历史立花样本不适合硬造该类反例。
- 本表先定义反例证据门槛和登记模板，等待真实 A 股 MALF 快照补样本。
- 至此，`rhythm_meaning` 四类中，`meaningful / limited / unknown` 已有历史样本验证，`not_meaningful` 已有登记口径和待补队列。
