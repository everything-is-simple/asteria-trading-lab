# MALF-立花前置认知过滤器 v0.1

## 版本定位

- 本文件是 `MALF -> Tachibana` 的第一份前置认知过滤器定义。
- 它放在 [MALF-立花映射总表](./MALF-立花映射总表.md) 和 [Tachibana Method v1 定义草案](./Tachibana-Method-雏形.md) / [Tachibana Position Management v1 定义草案](./Tachibana-Position-Management-雏形.md) 之间。
- 五步攻坚总控状态见 [MALF-立花前置认知过滤器攻坚总控矩阵 v0.1](./MALF-立花前置认知过滤器攻坚总控矩阵-v0.1.md)。
- “结构状态 -> 仓位节奏意义”的独立判定准则见 [MALF-立花结构状态到仓位节奏意义判定准则 v0.1](./MALF-立花结构状态到仓位节奏意义判定准则-v0.1.md)。
- 它不修改 MALF 主定义，不新增 A 股制度规则，不生成买卖信号，不决定仓位手数。
- 它只回答一个问题：在某个 MALF 结构背景下，立花式仓位节奏是否值得进入 Method / PM 讨论。

## 核心问题

A 股适配的第一问题不是 `T+1 怎么改`，而是：

> 哪类股票、哪种结构状态下，立花法的仓位节奏才有意义？

这个问题先由 MALF 提供结构背景，再由本过滤器做资格判定。只有通过前置过滤，后续 Method / PM / A 股适配才有讨论对象。

## 输入与输出

### 输入：只读 MALF 结构背景

| 输入组 | 字段或语义 | 使用方式 |
|---|---|---|
| `core` | `system_state / wave_id / direction / wave_core_state / current_effective_guard_price / progress_extreme_price` | 判断是否存在可讨论的有向结构。 |
| `range` | `range_state / range_kind / boundary_high_now / boundary_low_now / span_bars` | 判断是否处于等待、震荡、无推进背景。 |
| `break / birth` | `birth_type / birth_range_kind / candidate_wait_span / confirmation_distance_pct` | 判断是否出现新节奏、反手背景或回撤后再启动。 |
| `lifespan` | `new_count / no_new_span / wave_span_total / progress_pct / rank 字段` | 判断节奏推进、停滞、成熟或衰竭是否值得讨论。 |
| `probability` | `P1-P4` 四视图、`dominant_side / momentum / completeness` | 作为结构位姿信息，不直接转成动作。 |
| `reason_codes` | `uninitialized / peer_sample_too_small / insufficient_history` 等 | 控制 `unknown` 与证据不足状态。 |

### 输出：资格判定，不是交易裁决

| 输出值 | 定义 | 允许进入的后续层 |
|---|---|---|
| `suitable` | 结构背景足以讨论立花式试仓、加码、减仓、等待或清仓节奏。 | Method + PM |
| `conditional` | 结构背景有讨论价值，但必须带限制条件或人工证据。 | Method + PM，需显式 reason |
| `unsuitable` | 结构背景不支持立花式仓位节奏讨论，或讨论会污染 MALF / Method 边界。 | 只记录，不进入 PM 推演 |
| `unknown` | MALF 快照缺失、样本不足或证据不够，不能判定。 | 等待更多 MALF / 月报证据 |

## 铁律

| 编号 | 规则 | 禁止事项 |
|---|---|---|
| `F-1` | 本过滤器只读 MALF，不写回 MALF。 | 不准新增 MALF 字段表达中心单、锁单、均价。 |
| `F-2` | 本过滤器只判定讨论资格，不输出交易动作。 | 不准输出 buy/sell、accept/reject、position_size。 |
| `F-3` | `suitable` 不等于可以买，`unsuitable` 不等于看空。 | 不准把资格判定误读为信号。 |
| `F-4` | 证据不足必须输出 `unknown`。 | 不准用主观经验 fallback。 |
| `F-5` | PM 语义必须留在 Tachibana PM。 | 不准让中心单、加码单、锁单、利润保护回流 MALF。 |
| `F-6` | A 股制度约束后置。 | 不准用 T+1、涨跌停先决定结构资格。 |

## 结构资格矩阵

| MALF 背景 | 结构含义 | 资格判定 | 可讨论的立花主题 | 不可越界事项 |
|---|---|---|---|---|
| `wave_core_state = alive` 且有明确同向推进 | 有方向、有进展，仓位节奏可能有对象。 | `suitable` | 试仓、同向加码、分批减仓、利润保护窗口 | MALF 不能决定手数和中心单。 |
| alive wave 中出现回撤后再推进 | 节奏仍可能成立，但需要确认回撤不是失败。 | `conditional` | `pullback_entry`、`pullback_add`、减仓后再观察 | 不能把回撤自动视为买点或加码点。 |
| `range_state = alive` 或长期 no-progress | 结构无明确推进，等待可能比动作更重要。 | `conditional` | `wait_no_action`、观察、反省、保护已有仓位 | 不能把所有无交易都归因于 range。 |
| break / birth 后新 wave 形成 | 旧节奏结束，新节奏可能开始。 | `conditional` | 反手背景、清仓后重试、新中心单候选 | 反手决策和中心单重置属于 Method / PM。 |
| wave 停滞、衰竭、推进失败 | 原节奏可能失效。 | `conditional` | `exit_on_rhythm_failure`、分批减仓、清仓讨论 | 不能把节奏失败写成 MALF 的认错心理。 |
| `system_state = transition` 且 Range 未解决 | 结构仍在整理，方向未完成确认。 | `conditional` 或 `unsuitable` | 等待、轻仓观察、记录 | 不能强行进入加码节奏。 |
| `uninitialized` 或关键概率字段 None 且 reason 为样本不足 | 结构背景不可判定。 | `unknown` | 暂缓判断 | 不准 fallback 成 suitable。 |
| 只有 PM 事实，没有可读结构背景 | 仓位变化存在，但结构资格未成立。 | `unknown` 或 `unsuitable` | 人工复盘、证据补充 | 不能用交易动作倒推 MALF 结构。 |

## 与 Tachibana Method 的接口

| 过滤器输出 | Method 可做 | Method 不可做 |
|---|---|---|
| `suitable` | 解释试仓、加码、减仓、等待等动作语义。 | 直接生成订单。 |
| `conditional` | 带上限制条件解释动作，标注证据等级。 | 把限制条件删掉后当作确定规则。 |
| `unsuitable` | 记录为什么不进入立花动作讨论。 | 反向解释成看多或看空。 |
| `unknown` | 等待 MALF 快照、月报证据或人工校勘。 | 用主观经验补结论。 |

## 与 Tachibana PM 的接口

PM 只有在 `suitable` 或 `conditional` 时才进入仓位推演。进入 PM 后，仍必须遵守：

- `center_position`、`add_on_position`、`average_price`、`lock_position`、`distribution_reduce` 由 PM 定义。
- MALF 只提供结构背景，不提供仓位骨架。
- 本过滤器可以说“此处值得讨论中心单候选”，但不能说“此处已经有中心单”。
- 本过滤器可以说“此处值得讨论加码节奏”，但不能说“应该加码多少”。

## 机器审计门禁

为避免本过滤器只停留在人工文档层，v0.1 同步建立只读机器审计。机器审计不新增交易规则，只复核前置过滤器自身是否仍然干净。

| 审计项 | 检查对象 | 通过含义 | 失败后果 |
|---|---|---|---|
| `audit_qualification_rule_catalog()` | `qualification_rule_id` 目录 | 所有理由码都有受控定义，且 `rhythm_meaning / tachibana_applicability / pm_complexity / pm_required` 一致。 | 不得新增样本判定。 |
| `audit_rhythm_sample_catalog()` | 最小代表样本目录 | 每个理由码至少有一条可复核样本，样本行与理由码目录一致。 | 不得升级候选样本表。 |
| `audit_method_pm_action_catalog()` | Method / PM 动作目录 | 试仓、加码、清仓、锁定、解锁等动作全部留在 Method / PM，且 `malf_can_generate=false`。 | 不得进入 Method / PM 桥接。 |
| `audit_interface_boundary_catalog()` | Data / Signal / Backtest / Adapter 接口边界 | Data 只存事实，Signal 不抢跑结构资格，Backtest 只消费适配层结果，Adapter 不写交易裁决。 | 不得生成 Backtest Input。 |
| `audit_front_filter_system()` | 以上四类审计总聚合 | 前置过滤器自身目录、样本、动作边界、接口边界全部通过。 | 不得进入 A 股制度约束审计。 |

`--record-draft` 输出必须携带 `front_filter_system_audit`。`cognitive_pipeline_gate` 只有在该系统审计为 `pass`，且数据契约、ready MALF 快照、结构资格、Method / PM、接口边界与 Backtest Input 全部通过后，才允许进入 `action:start_institution_constraint_audit`。

这意味着：单条 MALF snapshot 通过，只能说明该结构背景可被讨论；不能绕过前置过滤器系统审计，也不能直接启动 T+1、涨跌停、停牌等 A 股制度改造。

## 第一批验证样本

第一批样本已经落到 [MALF-立花结构资格样本表 v0.1](./MALF-立花结构资格样本表-v0.1.md)。样本的横向规则收束见 [MALF-立花结构资格横向判读矩阵 v0.1](./MALF-立花结构资格横向判读矩阵-v0.1.md)。下表保留为摘要入口。

| 样本 | 结构问题 | 初始资格 | 说明 |
|---|---|---|---|
| [1975-01](../monthly/1975-01.md) | 分批试仓、推进、减仓是否处于可讨论节奏。 | `suitable` | 适合作为立花分批节奏正样本。 |
| [1975-06](../monthly/1975-06.md) | 大幅换向、新节奏 birth、中心单重置。 | `conditional` | 结构与 PM 高度交织，不能只靠 MALF 解释。 |
| [1975-08](../monthly/1975-08.md) | 无交易月份是 range、等待还是纪律。 | `conditional` | 适合检验 `wait_no_action`，但不能反推 range。 |
| [1975-12](../monthly/1975-12.md) | 年末收束、利润保护与清仓。 | `conditional` | 利润保护归 PM，MALF 只给背景。 |
| [1976-03](../monthly/1976-03.md) | 清零后重新建立月末库存种子。 | `conditional` | 适合检验 reset 后的新结构资格。 |
| [1976-04](../monthly/1976-04.md) | 双侧库存与上行收束。 | `conditional` | 先标 `lock_candidate`，不能自动判锁单。 |
| [1976-05](../monthly/1976-05.md) | 双侧库存解除后转单侧并清仓。 | `conditional` | 适合验证跨月库存链。 |
| [1976-10](../monthly/1976-10.md) | 下行结构中小额右侧仓位推进。 | `suitable` | 适合检验 MALF 对同向推进背景的承接。 |
| [1976-11](../monthly/1976-11.md) | `—24 -> —200 -> 0` 的极端加码与清仓。 | `conditional` | 加码尺度与清仓属于 PM，结构背景只做前置。 |
| [1976-12](../monthly/1976-12.md) | `35 — -> 150 — -> 0` 的大仓位推进和三段式退出。 | `conditional` | 适合验证分批退出与利润保护边界。 |

## 最小记录字段

后续建立样本表时，每条记录至少包含：

| 字段 | 类型 | 含义 |
|---|---|---|
| `sample_id` | string | 月份或交易段编号。 |
| `source_anchor` | list | 月报、章节、PDF 页码、图片编号。 |
| `malf_snapshot_ref` | string/null | 对应 MALF 快照；未跑出时为 null。 |
| `malf_background` | enum/list | `alive_wave / pullback / range / break_birth / stagnation / transition / unknown`。 |
| `tachibana_applicability` | enum | `suitable / conditional / unsuitable / unknown`。 |
| `applicability_reason` | list | 资格原因。 |
| `method_candidates` | list | 可进入讨论的 Method 动作，如 `trend_probe_entry`。 |
| `pm_required` | boolean | 是否必须进入 PM。 |
| `boundary_warning` | list | 如 `do_not_infer_center_position_from_malf`。 |
| `evidence_level` | enum | `fact / book_self_statement / our_interpretation / malf_mapping`。 |

## 当前结论

- MALF 主定义不需要为了立花法修订。
- 本过滤器是 MALF 与 Tachibana Method / PM 之间的前置资格层。
- 第一版以研究定义为主，不写阈值，不写交易信号，不写 A 股制度适配。
- 第一批样本表已开始承接 `结构状态 -> 仓位节奏意义` 的可复核记录。
- `rhythm_meaning=meaningful/limited/not_meaningful/unknown` 已由 [MALF-立花结构状态到仓位节奏意义判定准则 v0.1](./MALF-立花结构状态到仓位节奏意义判定准则-v0.1.md) 固化为前置过滤器的中间裁决层。
- 横向判读矩阵已把 `lock_candidate / reset_after_clear / inventory_seed / extreme_addon` 等边界样本收束成第一版可复核规则。
- `audit_front_filter_system()` 已成为本过滤器的一键机器总审计，且 `cognitive_pipeline_gate` 必须先确认该审计通过，才允许讨论 A 股制度约束。
- 真实 MALF 快照跑出后，本文件应升级为样本表和回测前置门禁。
