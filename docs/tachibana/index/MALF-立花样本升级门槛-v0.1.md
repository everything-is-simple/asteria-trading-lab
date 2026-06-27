# MALF-立花样本升级门槛 v0.1

## 版本定位

- 本文件是 [MALF-立花结构资格样本表 v0.1](./MALF-立花结构资格样本表-v0.1.md) 的升级纪律。
- 它只回答：`sampled_unknown` 样本在什么证据条件下，可以升级为 `conditional` 或 `suitable`。
- 它不修改 MALF 主定义，不新增交易规则，不输出买卖信号，不处理 A 股制度适配。

## 为什么需要升级门槛

`sampled_unknown` 不是“没研究”，而是“已经纳入样本体系，但证据不足以判定结构资格”。  
如果没有升级门槛，后续逐图判读很容易把 raw 仓位、成交频率或研究直觉误写成结构资格。

## 四类证据

| 证据代码 | 证据来源 | 可证明什么 | 不能证明什么 |
|---|---|---|---|
| `E1_malf_snapshot` | 真实 MALF 快照。 | wave / range / break / birth / lifespan / probability 位姿。 | 中心单、锁单、手数意义。 |
| `E2_monthly_fact` | 月报、JSON、交易谱截图。 | 成交、价格、库存、无交易事实。 | 结构资格本身。 |
| `E3_book_statement` | 章节、OCR、操作法原文。 | 立花对动作动机、纪律、认错、锁单、加码的自述。 | MALF 结构事实。 |
| `E4_research_mapping` | 我们的映射表、边界审计、样本表。 | 结构与 Method / PM 的边界关系。 | 替代 E1/E2/E3 的原始证据。 |

## 升级裁决表

| 目标状态 | 最低证据组合 | 必须满足 | 仍然禁止 |
|---|---|---|---|
| `unknown -> conditional` | `E2_monthly_fact + E4_research_mapping`，且至少有一个清楚的动作链。 | 能说明“值得讨论”，但仍保留限制条件。 | 不能把动作链倒推为 MALF 结构事实。 |
| `unknown -> conditional` | `E2_monthly_fact + E3_book_statement`，但无真实 MALF 快照。 | 书中自述能解释动作语义或 PM 动机。 | 不能省略 `boundary_warning`。 |
| `unknown -> suitable` | 原则上需要 `E1_malf_snapshot + E2_monthly_fact`。 | 结构方向清晰，动作节奏简洁，PM 解释不压倒结构解释。 | 不能仅凭活跃交易日多、仓位变大或盈利清仓升级。 |
| `unknown -> unsuitable` | `E1_malf_snapshot` 或强反例证据显示结构背景与立花节奏讨论无关。 | 能说明为什么不进入 Method / PM。 | 不能把 `unsuitable` 解释为看空或交易失败。 |
| 保持 `unknown` | 只有 raw 价格、成交、库存事实，且月报明确“不预判”。 | 继续等待逐图判读、章节回链或 MALF 快照。 | 不准用经验补结论。 |

## 逐图判读检查清单

每个 `sampled_unknown` 月份升级前，至少回答：

| 检查项 | 通过标准 |
|---|---|
| `source_image_checked` | 已核对当月交易谱截图，确认 `trade_raw / position_raw` 无转录误读。 |
| `price_path_checked` | 已确认月内价格路径，不只看月初/月末。 |
| `action_chain_segmented` | 已拆出交易段，而不是把整月混成一个动作。 |
| `malf_background_claim` | 若声称 `alive_wave / range / break_birth / transition`，必须说明证据来源。 |
| `method_candidate_claim` | 若给 Method 候选动作，必须能指出对应成交链或书中自述。 |
| `pm_required_decision` | 若出现中心单、加码单、锁单、双侧库存、均价压力，必须标 PM。 |
| `boundary_warning_present` | 必须写明不能倒推 MALF、不能误读锁单、不能把无交易等同 range 等警告。 |

## 当前 sampled_unknown 队列

| 样本 | 当前状态 | 最可能的升级方向 | 升级前必须补的证据 |
|---|---|---|---|
| `1976-09` | `unknown` | 保持 `unknown` | 已完成制度/资料口径审计；作为“有理由 unknown”样本保留。 |

已完成出队：

| 样本 | 出队裁决 | 审计文件 |
|---|---|---|
| `1976-01` | `conditional` | [MALF-立花 1976-01 至 02 样本升级审计 v0.1](./MALF-立花1976-01至02样本升级审计-v0.1.md) |
| `1976-02` | `conditional` | [MALF-立花 1976-01 至 02 样本升级审计 v0.1](./MALF-立花1976-01至02样本升级审计-v0.1.md) |
| `1976-06` | `conditional` | [MALF-立花 1976-06 至 09 样本升级审计 v0.1](./MALF-立花1976-06至09样本升级审计-v0.1.md) |
| `1976-07` | `conditional` | [MALF-立花 1976-06 至 09 样本升级审计 v0.1](./MALF-立花1976-06至09样本升级审计-v0.1.md) |
| `1976-08` | `conditional` | [MALF-立花 1976-06 至 09 样本升级审计 v0.1](./MALF-立花1976-06至09样本升级审计-v0.1.md) |

## 禁止升级的反模式

| 反模式 | 为什么错 |
|---|---|
| 活跃交易日多，所以升级为 `suitable`。 | 交易频率不是结构资格。 |
| 月末仓位大，所以升级为 `suitable`。 | 仓位大小属于 PM，不属于 MALF 背景。 |
| 无交易很多，所以升级为 `range`。 | 无交易可能是等待、资料缺失、制度限制或主动纪律。 |
| 清零了，所以一定是 `exit_on_rhythm_failure`。 | 清零可能是止盈、换向、整理、单位变化或记录口径问题。 |
| 有双侧库存，所以一定是锁单。 | 锁单需要动机证据或交易链证据。 |

## 当前结论

- `sampled_unknown` 是样本体系的一等状态，不是临时占位。
- `1976-09` 证明 `sampled_unknown` 可以是最终研究状态之一：当交易单位变化、除权和少量成交共同扰动时，不应为了覆盖率强行升级。
- 未完成升级门槛前，不进入 A 股制度改造。
