# MALF-立花 rhythm_meaning 历史样本回填审计 v0.1

## 版本定位

- 本文件承接 [MALF-立花结构资格样本表 v0.1](./MALF-立花结构资格样本表-v0.1.md)、[MALF-立花结构资格横向判读矩阵 v0.1](./MALF-立花结构资格横向判读矩阵-v0.1.md) 与 [MALF-立花结构状态到仓位节奏意义判定准则 v0.1](./MALF-立花结构状态到仓位节奏意义判定准则-v0.1.md)。
- `not_meaningful` 的后续反例登记口径见 [MALF-立花 not_meaningful 反例登记表 v0.1](./MALF-立花not_meaningful反例登记表-v0.1.md)。
- 它不是新的交易样本表，而是把历史样本的 `tachibana_applicability` 回填为 `rhythm_meaning`，验证“结构状态 -> 仓位节奏意义”是否能覆盖既有研究。
- 本文件不修改 MALF 主定义，不输出交易信号，不定义 A 股制度规则，不替代 Method / PM。
- 它只回答：既有 1975-1976 研究样本在 `meaningful / limited / not_meaningful / unknown` 四类中如何落位。

## 回填原则

| 输入状态 | 默认回填 | 例外规则 |
|---|---|---|
| `tachibana_applicability=suitable` | `rhythm_meaning=meaningful` | 若 PM 复杂度后来被证实主导解释，应降为 `limited`。 |
| `tachibana_applicability=conditional` | `rhythm_meaning=limited` | 若只是证据不足而非结构有意义，应改为 `unknown`。 |
| `tachibana_applicability=unsuitable` | `rhythm_meaning=not_meaningful` | 当前历史样本暂未强行标注。 |
| `tachibana_applicability=unknown` | `rhythm_meaning=unknown` | 不得为了覆盖率升级为 `limited`。 |

`rhythm_meaning` 只说明仓位节奏是否有讨论意义，不说明该不该交易。

## 月级回填总表

| 月份 | 当前资格 | 主结构背景 | rhythm_meaning | 回填理由 | 备注 |
|---|---|---|---|---|---|
| `1975-01` | `suitable` | `alive_wave` | `meaningful` | 分批试仓、推进、减仓链条清楚，结构节奏有明确对象。 | 干净正样本。 |
| `1975-02` | `conditional` | `alive_wave` | `limited` | 空头试探与加码有节奏意义，但多空库存变化需要 PM 承接。 | 不升为 meaningful。 |
| `1975-03` | `conditional` | `stagnation` | `limited` | 压力下修正和库存处理有研究价值，但心理与 PM 解释主导。 | 压力样本。 |
| `1975-04` | `suitable` | `alive_wave` | `meaningful` | 延续空头、加码、减仓链条较干净。 | 干净正样本。 |
| `1975-05` | `conditional` | `transition` | `limited` | 库存反复调整与锁单意识线索需要 PM。 | 过渡样本。 |
| `1975-06` | `conditional` | `alive_wave / transition / lock_candidate` | `limited` | 母单候选、双侧库存、库存再平衡交织，节奏有意义但边界复杂。 | 已拆段审计。 |
| `1975-07` | `conditional` | `stagnation` | `limited` | 分批兑现与利润保护有意义，但退出动机归 PM。 | 收束样本。 |
| `1975-08` | `conditional` | `range` | `limited` | 等待/无交易有观察意义，但不能反推 range。 | 无交易边界样本。 |
| `1975-09` | `conditional` | `range` | `limited` | 少量试探与清零可讨论，但低交易次数不能直接证明区间。 | 轻仓观察样本。 |
| `1975-10` | `conditional` | `transition` | `limited` | 多空调整、双侧库存和清零交织，必须 PM 承接。 | 复杂库存样本。 |
| `1975-11` | `suitable` | `alive_wave` | `meaningful` | 空头试探后分批加码，动作链简洁。 | 干净正样本。 |
| `1975-12` | `conditional` | `stagnation` | `limited` | 年末收束有意义，但利润保护解释归 PM。 | 收束样本。 |
| `1976-01` | `conditional` | `transition` | `limited` | 轻仓试探和清零有研究价值，但结构背景弱。 | 不能升为 meaningful。 |
| `1976-02` | `conditional` | `alive_wave` | `limited` | 空头推进明确，但中心单解释需 PM。 | alive 但受限。 |
| `1976-03` | `conditional` | `stagnation / break_birth / inventory_seed` | `limited` | 压力调整、清零、新种子均有节奏意义，但必须拆段。 | 已拆段审计。 |
| `1976-04` | `conditional` | `transition / lock_candidate / inventory_rebalance` | `limited` | 双侧库存扩张、等待和收束均需 PM。 | 锁单候选样本。 |
| `1976-05` | `conditional` | `transition / unlock / exit_window` | `limited` | 双侧库存延续、解锁和清仓有意义，但属于 PM 边界高风险。 | 解锁样本。 |
| `1976-06` | `conditional` | `transition` | `limited` | 多头分批库存链有意义，但真实 MALF wave 未跑出。 | 待真实快照。 |
| `1976-07` | `conditional` | `exit_window / transition / reduce_window` | `limited` | 清零后新段扩张和减仓可讨论，但中心单与加码归 PM。 | 已拆段审计。 |
| `1976-08` | `conditional` | `break_birth` | `limited` | 转折、试探、加码、清零有意义，但不能凭库存确认结构转折。 | 转折边界样本。 |
| `1976-09` | `unknown` | `unknown` | `unknown` | 交易单位变化、除权和短链样本共同阻断结构意义判断。 | 有理由 unknown。 |
| `1976-10` | `suitable` | `alive_wave` | `meaningful` | 下行结构中小额右侧仓位推进较干净。 | 干净正样本。 |
| `1976-11` | `conditional` | `alive_wave / stagnation / transition / break_birth` | `limited` | 极端加码、清仓、反手和新骨架都需要 PM。 | 高 PM 复杂度。 |
| `1976-12` | `conditional` | `alive_wave / stagnation` | `limited` | 中心单候选、加速加码、大仓位等待和三段式退出均需 PM。 | 高 PM 复杂度。 |

## 段级代表样本回填

| segment_id | qualification_rule_id | rhythm_meaning | 原因 |
|---|---|---|---|
| `1975-06-A` | `Q-ALIVE-PM-MIXED` | `limited` | 有向推进有意义，但母单/中心单候选不能由 MALF 确认。 |
| `1975-06-B/C/D` | `Q-LOCK-CANDIDATE` | `limited` | 双侧库存只能作为锁单候选，不能净额化或确认锁单目的。 |
| `1976-03-A` | `Q-PRESSURE-ADJUST` | `limited` | 压力调整有意义，但不能并成干净 wave。 |
| `1976-03-B` | `Q-CLEAR-RESET` | `limited` | 清零闭环有意义，但清仓原因归 Method / PM。 |
| `1976-03-C` | `Q-SEED-AFTER-CLEAR` | `limited` | 新库存种子有意义，但必须开启新段。 |
| `1976-04-B` | `Q-LOCK-WAIT / Q-NO-TRADE` | `limited` | 等待有意义，但不是空仓等待，也不能由无交易反推 range。 |
| `1976-05-B` | `Q-UNLOCK` | `limited` | 解锁事件有 PM 意义，不是 MALF 字段。 |
| `1976-11-A` | `Q-EXTREME-ADDON` | `limited` | 同向推进有意义，但极端加码尺度必须由 PM 承接。 |
| `1976-12-B` | `Q-EXTREME-ADDON` | `limited` | 加速加码有节奏意义，但加码规模不是结构强度。 |
| `1976-09` | `Q-SOURCE-DISRUPTED` | `unknown` | 资料/制度口径扰动阻断意义判断。 |

## 分布统计

| rhythm_meaning | 月级样本数量 | 代表样本 | 解释 |
|---|---:|---|---|
| `meaningful` | 4 | `1975-01`、`1975-04`、`1975-11`、`1976-10` | 干净有向推进，PM 复杂度不主导。 |
| `limited` | 19 | `1975-06`、`1976-03`、`1976-04`、`1976-11`、`1976-12` | 主力状态，有讨论价值但必须带 PM / 边界警告。 |
| `not_meaningful` | 0 | 暂无 | 需要真实 MALF 快照或 A 股反例补充。 |
| `unknown` | 1 | `1976-09` | 有明确资料口径阻断。 |

## 行级复核要求

历史样本回填不再只看汇总分布。每一个月级或段级样本行，都应能落入 `rhythm_sample_row_gate` 的输入字段：

| 字段 | 历史样本填法 |
|---|---|
| `sample_id` | 月份或段级编号，如 `1975-01`、`1976-04-B`。 |
| `source_scope` | `historical_review`。 |
| `snapshot_quality_status` | 已有 MALF 快照时填 `ready`；人工历史映射缺快照时必须在证据等级中说明。 |
| `malf_background` | 来自结构资格样本表或段级审计。 |
| `qualification_rule_id` | 来自横向判读矩阵。 |
| `rhythm_meaning` | `meaningful / limited / not_meaningful / unknown`。 |
| `tachibana_applicability` | 必须与 `rhythm_meaning` 一致映射。 |
| `pm_complexity` | `none / low / medium / high`；PM 主导解释的样本不得填 `meaningful`。 |
| `meaning_reason / boundary_warning / evidence_level` | 必须保留，防止把节奏意义改写为交易裁决。 |

如果某一行无法通过 `rhythm_sample_row_gate`，应回到结构资格审计或证据补充，不得为了统计分布强行保留原判。

## 对 A 股适配的含义

- A 股样本不应期待大量 `meaningful`；更现实的主类会是 `limited`。
- `limited` 不是失败，而是“可以进入 Method / PM，但必须保留边界”的正常状态。
- `not_meaningful` 暂不从历史样本硬造；后续由 [MALF-立花 not_meaningful 反例登记表 v0.1](./MALF-立花not_meaningful反例登记表-v0.1.md) 承接真实 A 股 MALF 快照、低质量结构或与立花节奏无关的反例。
- `unknown` 必须保留为正式结果，尤其在数据缺失、口径扰动或 MALF 快照未 ready 时。

## 当前结论

- 历史样本验证了 `rhythm_meaning` 的中间层是必要的：如果直接从结构背景跳到 `tachibana_applicability`，会遮蔽 `limited` 这个主力状态。
- 1975-1976 样本中，真正干净的 `meaningful` 只占少数；绝大多数可研究样本都应以 `limited` 进入 Method / PM。
- 本回填审计进一步确认：MALF 主定义不需要增加中心单、锁单、加码尺度、清仓原因等字段。
- 下一步真实 A 股样本应先填 `rhythm_meaning`，再映射 `tachibana_applicability`，最后才进入 Method / PM；制度规则仍后置。
