# MALF-立花结构资格横向判读矩阵 v0.1

## 版本定位

- 本文件承接 [MALF-立花前置认知过滤器 v0.1](./MALF-立花前置认知过滤器-v0.1.md) 与 [MALF-立花结构资格样本表 v0.1](./MALF-立花结构资格样本表-v0.1.md)。
- 它把已经完成的段级审计样本横向归类，形成可复核的结构资格判读规则。
- 横向规则在进入 `tachibana_applicability` 前，应先经 [MALF-立花结构状态到仓位节奏意义判定准则 v0.1](./MALF-立花结构状态到仓位节奏意义判定准则-v0.1.md) 形成 `rhythm_meaning`。
- `Q-*` 规则的历史样本回填结果见 [MALF-立花 rhythm_meaning 历史样本回填审计 v0.1](./MALF-立花rhythm_meaning历史样本回填审计-v0.1.md)。
- 本文件不修改 MALF 主定义，不输出交易信号，不新增 A 股制度适配，不替代 Method / PM。
- 1976 段级样本对 Backtest Input 的试填审计见 [TachibanaBacktestInput 1976 段级样本试填审计 v0.1](./TachibanaBacktestInput-1976段级样本试填审计-v0.1.md)。
- 1975-06 母单候选与双侧库存对 Backtest Input 的试填审计见 [TachibanaBacktestInput 1975-06 段级样本试填审计 v0.1](./TachibanaBacktestInput-1975-06段级样本试填审计-v0.1.md)。

## 解决的问题

样本表已经回答“某一段是什么资格”，但还需要回答：

1. 遇到同类结构时，前置过滤器下一次应该怎么判？
2. 哪些状态可以进入 Method / PM，哪些只能保持 `unknown`？
3. 哪些 PM 语义必须被拦在 MALF 外面？

本文件就是这些问题的第一版横向矩阵。

## 判读总原则

| 原则 | 含义 |
|---|---|
| 结构先行 | 先看 MALF 背景或人工结构背景，再看动作链。 |
| PM 不回流 | 中心单、锁单、解锁、清仓原因、加码尺度，只能触发 `pm_required = true`。 |
| 清零断段 | `clear -> reset_after_clear` 后，后续新仓位不得自动并入旧段。 |
| 双侧保真 | 双侧库存必须保留左右两侧事实，不能净额化成单一方向。 |
| 无交易不反推 | 无交易只能作为事实，不能自动反推 `range`、等待纪律或结构有效。 |
| 资料扰动优先 unknown | 交易单位变化、除权、样本太短或关键事实扰动时，优先保持 `unknown`。 |

## 横向规则矩阵

| rule_id | 结构/仓位状态 | 典型样本 | 默认资格 | Method 允许讨论 | PM 必须承接 | MALF 禁止写入 |
|---|---|---|---|---|---|---|
| `Q-ALIVE-CLEAN` | 有向推进清楚，动作链分批、尺度稳定。 | `1975-01`、`1975-04`、`1975-11`、`1976-10` | `suitable` | 试仓、同向加码、分批减仓、等待。 | 手数、中心单候选、减仓比例。 | `position_size / center_position`。 |
| `Q-ALIVE-PM-MIXED` | 有向推进存在，但动作链混入中心单、加码单或母单解释。 | `1975-06-A`、`1976-12-A/B` | `conditional` | 分批扩张、中心单候选、加码语义。 | 中心单、母单、加码尺度。 | `mother_position / add_on_size`。 |
| `Q-PRESSURE-ADJUST` | 旧段内先减后加、压力调整或库存再平衡，尚未清零。 | `1976-03-A` | `conditional` | 压力调整、库存再平衡、减仓后加回。 | 当前库存、加回原因、均价压力。 | 把压力调整并成干净 wave 或清零重置。 |
| `Q-LOCK-CANDIDATE` | 双侧库存出现或跨月延续。 | `1975-06-B/C/D`、`1976-04-A/C`、`1976-05-A` | `conditional` | 库存再平衡、锁单候选、反向测试候选。 | `lock_candidate`、`lock_purpose`、双侧均价。 | `lock_position` 确认、净仓位方向。 |
| `Q-LOCK-WAIT` | 双侧库存存在期间无交易或等待。 | `1976-04-B` | `conditional` | `wait_no_action`。 | 双侧风险、持仓压力、均价暴露。 | 用无交易反推 `range` 或锁单目的。 |
| `Q-UNLOCK` | 双侧库存解除一侧，转为单侧库存。 | `1976-05-B` | `conditional` | 解锁、库存再平衡。 | `unlock`、剩余单侧风险。 | 把 `unlock` 写成 MALF 结构字段。 |
| `Q-CLEAR-RESET` | 库存清零，旧段结束。 | `1976-03-B`、`1976-07-A`、`1976-11-B`、`1976-12-D` | `conditional` | 清仓、旧段终止、等待新试探。 | `reset_after_clear`、清仓原因、盈亏压力。 | 清仓动机、认错心理、方向判断。 |
| `Q-SEED-AFTER-CLEAR` | 清零后重新小仓试探，形成新库存种子。 | `1976-03-C`、`1976-07-B`、`1976-11-C/D` | `conditional` | 新试探、反手背景、分批重建。 | 新 `segment_id`、中心单候选。 | 把新种子并回旧中心单。 |
| `Q-EXTREME-ADDON` | 同向加码尺度突然放大。 | `1976-11-A`、`1976-12-B` | `conditional` | 同向加码语义、节奏推进。 | `scale_alert`、加码尺度、风险承受。 | 把加码规模当作结构强度。 |
| `Q-REDUCE-WINDOW` | 持仓部分收束，未完全清仓。 | `1975-07`、`1976-07-C`、`1976-12-C/D` | `conditional` | 分批减仓、等待、收束。 | 利润保护、风险回收、剩余仓位。 | 仅凭减仓推断利润保护或节奏失败。 |
| `Q-NO-TRADE` | 无交易或低交易次数。 | `1975-08`、`1975-09`、`1976-12-C` | `conditional` 或 `unknown` | 等待、观察、记录。 | 若有持仓，记录压力；若无持仓，记录空仓观察。 | 自动判定为 `range`。 |
| `Q-SOURCE-DISRUPTED` | 制度、资料或样本链条扰动。 | `1976-09` | `unknown` | 暂不进入 Method。 | 暂不进入 PM。 | 用短链动作或制度事件倒推结构资格。 |

## 资格输出规则

| 输出 | 必要条件 | 常见触发 | 反例边界 |
|---|---|---|---|
| `suitable` | 结构背景较干净，动作链可被结构背景承接，PM 复杂度不主导判断。 | `Q-ALIVE-CLEAN`。 | 只要出现双侧库存、清零重建、极端加码或资料扰动，原则上降为 `conditional / unknown`。 |
| `conditional` | 有结构或动作研究价值，但 PM / Method 解释是必要条件。 | `Q-ALIVE-PM-MIXED`、`Q-LOCK-CANDIDATE`、`Q-CLEAR-RESET`、`Q-SEED-AFTER-CLEAR`、`Q-EXTREME-ADDON`。 | 不能删掉限制条件后当成交易规则。 |
| `unsuitable` | 结构背景与立花仓位节奏讨论无关，或讨论会导致边界污染。 | 需要后续真实 MALF 快照补反例。 | 当前人工样本暂不强行标注。 |
| `unknown` | MALF 快照缺失且月报/章节证据不足，或资料口径扰动阻断资格判断。 | `Q-SOURCE-DISRUPTED`。 | 不能为了覆盖率升级为 `conditional`。 |

## 边界警告索引

| boundary_warning | 适用规则 | 含义 |
|---|---|---|
| `do_not_infer_position_size_from_malf` | `Q-ALIVE-CLEAN` | MALF 只给结构背景，不给手数。 |
| `do_not_call_mother_position_from_malf_only` | `Q-ALIVE-PM-MIXED` | 母单/中心单需要 PM 或书页证据；`center_side` 可候选，`center_size` 不自动填。 |
| `do_not_merge_pressure_adjustment_into_clean_wave` | `Q-PRESSURE-ADJUST` | 压力调整不能升格成干净推进。 |
| `do_not_confirm_lock_from_dual_inventory_only` | `Q-LOCK-CANDIDATE` | 双侧库存只能先标锁单候选。 |
| `do_not_net_dual_inventory_into_single_direction` | `Q-LOCK-CANDIDATE` | 双侧库存不得压成净仓位方向。 |
| `do_not_write_unlock_into_malf` | `Q-UNLOCK` | 解锁是 PM 状态机事件。 |
| `do_not_encode_clear_reason_in_malf` | `Q-CLEAR-RESET` | 清仓原因不是 MALF 字段。 |
| `do_not_merge_new_seed_into_old_segment` | `Q-SEED-AFTER-CLEAR` | 清零后新试探必须开启新段。 |
| `do_not_treat_addon_scale_as_structure_strength` | `Q-EXTREME-ADDON` | 加码尺度不是结构强度。 |
| `do_not_infer_range_from_no_trade` | `Q-NO-TRADE` | 无交易不等于 range。 |
| `do_not_mix_unit_change_ex_rights_and_structure_qualification` | `Q-SOURCE-DISRUPTED` | 制度/资料扰动下优先保持 unknown。 |

## 样本覆盖索引

| 规则 | 已覆盖样本 | 当前充分度 |
|---|---|---|
| `Q-ALIVE-CLEAN` | `1975-01`、`1975-04`、`1975-11`、`1976-10` | 初步充分，待真实 MALF 快照验证。 |
| `Q-ALIVE-PM-MIXED` | `1975-06-A`、`1976-12-A/B` | 初步充分。 |
| `Q-PRESSURE-ADJUST` | `1976-03-A` | 新增规则，样本偏少，待 `1975-03/05/10` 压力段复核。 |
| `Q-LOCK-CANDIDATE` | `1975-06-B/C/D`、`1976-04-A/C`、`1976-05-A` | 初步充分，需补页码锚点。 |
| `Q-LOCK-WAIT` | `1976-04-B` | 样本偏少。 |
| `Q-UNLOCK` | `1976-05-B` | 样本偏少但边界清楚。 |
| `Q-CLEAR-RESET` | `1976-03-B`、`1976-07-A`、`1976-11-B`、`1976-12-D` | 初步充分。 |
| `Q-SEED-AFTER-CLEAR` | `1976-03-C`、`1976-07-B`、`1976-11-C/D` | 初步充分。 |
| `Q-EXTREME-ADDON` | `1976-11-A`、`1976-12-B` | 初步充分，需 PM 尺度阈值。 |
| `Q-REDUCE-WINDOW` | `1975-07`、`1976-07-C`、`1976-12-C/D` | 初步充分。 |
| `Q-NO-TRADE` | `1975-08`、`1975-09`、`1976-12-C` | 仍需真实 MALF range 快照。 |
| `Q-SOURCE-DISRUPTED` | `1976-09` | 单一反例，但证据强。 |

## 当前结论

- 横向矩阵证明：绝大多数立花样本不是 `suitable`，而是 `conditional`。
- `conditional` 不是弱结论，而是前置过滤器的主力状态：它允许进入 Method / PM，同时保留边界警告。
- MALF 不需要为了立花法增加中心单、锁单、解锁、清仓原因、加码尺度等字段。
- 本矩阵已经由 [Tachibana Backtest Input 适配层草案 v0.1](./Tachibana-Backtest-Input-适配层草案-v0.1.md) 承接为 `qualification_rule_id` 与 `boundary_warning`。
- 1976 段级试填暴露并补入 `Q-PRESSURE-ADJUST`；这属于横向规则细化，不是 MALF 主定义修订。
- 1975-06 试填验证 `Q-ALIVE-PM-MIXED` 与 `Q-LOCK-CANDIDATE` 足以承接母单候选和双侧库存；无需继续新增 MALF 字段。
- `Q-*` 规则到 `meaningful/limited/not_meaningful/unknown` 的中间映射由 [MALF-立花结构状态到仓位节奏意义判定准则 v0.1](./MALF-立花结构状态到仓位节奏意义判定准则-v0.1.md) 承接。
- 历史样本回填审计显示，`Q-ALIVE-CLEAN` 主要落入 `meaningful`，多数 PM 复杂规则落入 `limited`，`Q-SOURCE-DISRUPTED` 保持 `unknown`。
- 后续 A 股适配应先套用本矩阵筛选结构资格，再经适配层形成可执行输入，最后才讨论 T+1、涨跌停、停牌等执行约束。
