# 原始立花法回测规格笔记

## 文件定位

本文件是原始立花义正波段交易法回测规格的前置笔记，不是最终策略规则。

它只记录已经从月报、章节锚点和 PM 定义中暴露出来的规则候选，供后续起草正式回测规格时使用。交易事实裁决顺序见 [evidence-precedence.md](./evidence-precedence.md)。

## 当前可进入回测讨论的强样本

| 样本 | 事实 | 规则启发 | 归属层 |
|---|---|---|---|
| [1976-10](../tachibana/monthly/1976-10.md) | `—10 -> —24` | 前置中心单候选可以由较均衡的小额加码形成。 | Method + PM |
| [1976-11](../tachibana/monthly/1976-11.md) | `—24 -> —200` | 同向加码存在尺度升级问题，需要 `add_on_scale_alert`。 | PM |
| [1976-11](../tachibana/monthly/1976-11.md) | `—200 -> 0` | 节奏失败或风险失控时允许一次性清仓。 | Method + PM |
| [1976-11](../tachibana/monthly/1976-11.md) | `—5 -> 0 -> —5 -> 35 —` | 清仓后重新小仓试探，旧中心单不应延续。 | Method + PM |
| [1976-03](../tachibana/monthly/1976-03.md) | `—12 -> 0 -> —10` | 清零后可重新建立新段库存；3 月末 `—10` 是 4 月双侧库存种子。 | Method + PM |
| [1976-04](../tachibana/monthly/1976-04.md) | `— 10 -> 2 — 20 -> 4 — 5` | 双侧库存应作为 `inventory_rebalance / lock_candidate` 处理，不能直接压成净仓位。 | PM |
| [1976-05](../tachibana/monthly/1976-05.md) | `4 — 5 -> 10 — 5 -> 10 — -> 0` | 双侧库存可以跨月延续、解除一侧，再最终清仓。 | PM |
| [1976-12](../tachibana/monthly/1976-12.md) | `35 — -> 150 — -> 0` | 大仓位推进后可以分批退出，而不是只允许一次性清仓。 | PM |
| [1976-12](../tachibana/monthly/1976-12.md) | `150 — -> 100 — -> 50 — -> 0` | 三段式 `distribution_reduce -> clear` 可作为利润保护规则候选。 | PM |

## 最小状态字段候选

| 字段 | 含义 | 备注 |
|---|---|---|
| `segment_id` | 当前交易段编号 | 清仓到 `0` 后通常应重置。 |
| `side` | 当前研究解释方向 | `N —` / `—N` 的方向语义仍需保留为“我们的抽象解释”。 |
| `center_size` | 中心单候选规模 | 1976-11 月末 `35 —` 可作为 1976-12 前置中心单候选。 |
| `add_on_size` | 加码单候选规模 | 用于识别 `—24 -> —200`、`35 — -> 150 —`。 |
| `gross_position` | 单侧总暴露 | 用于触发加码尺度警戒。 |
| `gross_long` | 横杠右侧总手数，即多头库存 | 用于保留双侧库存事实。 |
| `gross_short` | 横杠左侧总手数，即空头库存 | 用于保留双侧库存事实。 |
| `lock_candidate_size` | 锁单候选规模 | 双侧同时存在时先标候选，后续再确认是否为锁单。 |
| `pm_action` | PM 动作 | `open_center / add_on / reduce_add_on / reduce_center / inventory_seed / lock_candidate / unlock / clear` 为第一批候选。 |
| `scale_alert` | 加码尺度警戒 | 当单笔加码或总仓位扩张明显偏离前序节奏时触发。 |
| `exit_mode` | 退出模式 | `one_shot_clear / staged_distribution / no_exit`。 |

## 候选规则

| 规则代码 | 草案描述 | 支撑样本 | 当前状态 |
|---|---|---|---|
| `reset_after_clear` | 持仓清零后，旧交易段结束；后续小仓试探不得自动并入旧中心单。 | [1976-11](../tachibana/monthly/1976-11.md) | 可进入正式规格草案。 |
| `center_then_add_on` | 若存在前置中心单候选，后续同向扩张应拆成中心单和加码单，不应只看净仓位。 | [1976-10](../tachibana/monthly/1976-10.md)、[1976-12](../tachibana/monthly/1976-12.md) | 可进入正式规格草案。 |
| `add_on_scale_alert` | 当加码从小额均衡推进突然升级为大额扩张，应记录风险警戒。 | [1976-11](../tachibana/monthly/1976-11.md)、[1976-12](../tachibana/monthly/1976-12.md) | 需定义数值阈值。 |
| `allow_one_shot_clear` | 极端仓位或节奏失败时，规则应允许一次性清仓。 | [1976-11](../tachibana/monthly/1976-11.md) | 可进入正式规格草案。 |
| `allow_staged_distribution` | 大仓位推进后，规则应允许分批退出并最终清仓。 | [1976-12](../tachibana/monthly/1976-12.md) | 可进入正式规格草案。 |
| `inventory_seed_after_clear` | 清仓后重新建仓应开启新段，并可成为下一月库存种子。 | [1976-03](../tachibana/monthly/1976-03.md) | 可进入正式规格草案。 |
| `preserve_dual_inventory` | 双侧仓位必须保留为左右两侧库存，不得只用净仓位覆盖。 | [1976-04](../tachibana/monthly/1976-04.md) | 可进入正式规格草案。 |
| `lock_requires_confirmation` | 双侧库存只能先标 `lock_candidate`，必须结合章节和前后月份确认后才能标为 `lock`。 | [1976-04](../tachibana/monthly/1976-04.md) | 可进入正式规格草案。 |
| `allow_unlock_then_clear` | 双侧库存解除一侧后，可以继续单侧持有，随后再清仓。 | [1976-05](../tachibana/monthly/1976-05.md) | 可进入正式规格草案。 |
| `malf_is_context_not_order` | MALF 只能提供 wave/range/progress/break 背景，不直接决定手数和退出模式。 | [MALF-立花映射总表](../tachibana/index/MALF-立花映射总表.md) | 作为架构约束保留。 |

## 尚不能自动化的部分

- `center_size` 的自动识别规则尚未确定，当前只能由月报研究解释标注。
- `scale_alert` 的阈值需要在更多月份上校验，不能只用 `—200` 和 `150 —` 两个极端样本定死。
- `distribution_reduce` 的触发条件尚未由 MALF 快照验证；现在只能说 1976-12 提供了退出模式样本。
- 锁单仍不能自动化定论；1976-03/04/05 已足以证明一条 `inventory_seed -> lock_candidate -> unlock -> clear` 的库存链，但是否命名为正式锁单仍需原文逐页校勘。
- A 股适配规则暂不进入本文件。
