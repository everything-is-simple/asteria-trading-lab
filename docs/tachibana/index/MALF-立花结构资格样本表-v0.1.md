# MALF-立花结构资格样本表 v0.1

## 版本定位

- 本文件是 [MALF-立花前置认知过滤器 v0.1](./MALF-立花前置认知过滤器-v0.1.md) 的第一份样本表。
- 它把已研究的 `1975-1976` 先锋电子交易段，先按 `tachibana_applicability` 落成可复核记录。
- 本表仍是人工研究表：真实 MALF 快照尚未跑出，`malf_snapshot_ref` 暂记为 `null`。
- 本表不输出交易信号，不定义 A 股制度适配，不修改 MALF 主定义。
- `sampled_unknown` 的升级纪律见 [MALF-立花样本升级门槛 v0.1](./MALF-立花样本升级门槛-v0.1.md)。
- 段级样本的横向规则收束见 [MALF-立花结构资格横向判读矩阵 v0.1](./MALF-立花结构资格横向判读矩阵-v0.1.md)。
- `结构状态 -> 仓位节奏意义` 的中间判定准则见 [MALF-立花结构状态到仓位节奏意义判定准则 v0.1](./MALF-立花结构状态到仓位节奏意义判定准则-v0.1.md)。
- 历史样本的 `rhythm_meaning` 回填审计见 [MALF-立花 rhythm_meaning 历史样本回填审计 v0.1](./MALF-立花rhythm_meaning历史样本回填审计-v0.1.md)。
- 段级样本对 `TachibanaBacktestInputSnapshot` 的第一轮试填见 [TachibanaBacktestInput 1976 段级样本试填审计 v0.1](./TachibanaBacktestInput-1976段级样本试填审计-v0.1.md)。
- `1975-06` 对 `TachibanaBacktestInputSnapshot` 的母单候选与双侧库存试填见 [TachibanaBacktestInput 1975-06 段级样本试填审计 v0.1](./TachibanaBacktestInput-1975-06段级样本试填审计-v0.1.md)。
- 机器代表样本目录见 `get_rhythm_sample_catalog()`；它只覆盖 `meaningful / limited / unknown / not_meaningful` 四类核心状态，并由 `audit_rhythm_sample_catalog()` 批量调用 `rhythm_sample_row_gate` 复核。
- `1976-01/02` 的第二组升级审计见 [MALF-立花 1976-01 至 02 样本升级审计 v0.1](./MALF-立花1976-01至02样本升级审计-v0.1.md)。
- A 股候选股票的结构资格样本表见 [Tachibana A 股候选股票结构资格样本表 v0.1](./Tachibana-A股候选股票结构资格样本表-v0.1.md)。
- `1976-03/07` 的交易段级审计见 [MALF-立花 1976-03 与 07 交易段结构资格审计 v0.1](./MALF-立花1976-03与07交易段结构资格审计-v0.1.md)。
- `1975-06` 的交易段级审计见 [MALF-立花 1975-06 交易段结构资格审计 v0.1](./MALF-立花1975-06交易段结构资格审计-v0.1.md)。
- `1976-04/05` 的交易段级审计见 [MALF-立花 1976-04 至 05 交易段结构资格审计 v0.1](./MALF-立花1976-04至05交易段结构资格审计-v0.1.md)。
- `1976-06/07/08/09` 的第一组升级审计见 [MALF-立花 1976-06 至 09 样本升级审计 v0.1](./MALF-立花1976-06至09样本升级审计-v0.1.md)。
- `1976-09` 的制度/资料口径审计见 [MALF-立花 1976-09 制度资料口径审计 v0.1](./MALF-立花1976-09制度资料口径审计-v0.1.md)。
- `1976-11` 的交易段级审计见 [MALF-立花 1976-11 交易段结构资格审计 v0.1](./MALF-立花1976-11交易段结构资格审计-v0.1.md)。
- `1976-12` 的交易段级审计见 [MALF-立花 1976-12 交易段结构资格审计 v0.1](./MALF-立花1976-12交易段结构资格审计-v0.1.md)。

## 字段口径

| 字段 | 含义 |
|---|---|
| `sample_id` | 月份或交易段编号。 |
| `source_anchor` | 月报入口；后续可补章节、PDF 页码、图片编号。 |
| `malf_snapshot_ref` | 真实 MALF 快照引用；当前统一为 `null`。 |
| `malf_background` | 人工归纳的结构背景：`alive_wave / pullback / range / break_birth / stagnation / transition / unknown`。 |
| `rhythm_meaning` | 仓位节奏意义的中间裁决：`meaningful / limited / not_meaningful / unknown`；历史样本 v0.1 可由 `tachibana_applicability` 反推补填，真实样本必须先判定。 |
| `tachibana_applicability` | 前置过滤器输出：`suitable / conditional / unsuitable / unknown`。 |
| `applicability_reason` | 为什么进入该资格。 |
| `method_candidates` | 可进入 Method 讨论的动作候选。 |
| `pm_required` | 是否必须进入 PM。 |
| `boundary_warning` | 防止越界的提醒。 |
| `evidence_level` | 当前证据性质。 |

## 判读规则

| 判读项 | `suitable` | `conditional` | `unsuitable` | `unknown` |
|---|---|---|---|---|
| 结构清晰度 | 有明确有向推进，且动作节奏可被结构背景承接。 | 有结构线索，但混入 PM、心理或人工解释。 | 结构背景与立花仓位节奏讨论无关或会造成误读。 | MALF 快照缺失且月报/章节证据不足。 |
| Method 进入条件 | 可以讨论试仓、加码、减仓、等待或清仓语义。 | 可以讨论，但必须保留限制条件和证据等级。 | 不进入 Method 动作解释，只保留研究记录。 | 暂不进入 Method。 |
| PM 进入条件 | 若动作涉及手数、中心单、均价、锁单，则进入 PM。 | 通常需要 PM，但必须先说明结构背景不足之处。 | 不进入 PM 推演。 | 暂不进入 PM。 |
| 边界风险 | 主要防止把 MALF 当成信号。 | 主要防止把 PM 或心理解释塞回 MALF。 | 主要防止过度解释。 | 主要防止 fallback。 |

当前人工样本优先使用 `suitable` 与 `conditional`。当月报只保留 raw 事实、明确要求“不预判多空语义”时，必须使用 `unknown`，不为了覆盖进度强行标注为 `conditional`。`unknown` 只有通过 [样本升级门槛](./MALF-立花样本升级门槛-v0.1.md) 后才能升级。

## 第一批样本

| sample_id | source_anchor | malf_snapshot_ref | malf_background | tachibana_applicability | applicability_reason | method_candidates | pm_required | boundary_warning | evidence_level |
|---|---|---|---|---|---|---|---:|---|---|
| `1975-01` | [1975-01](../monthly/1975-01.md) | `null` | `alive_wave` | `suitable` | 分批试仓、推进、减仓都处于可讨论的波段节奏中。 | `trend_probe_entry / trend_confirmation_add / distribution_reduce` | true | `do_not_infer_position_size_from_malf` | `malf_mapping` |
| `1975-02` | [1975-02](../monthly/1975-02.md) | `null` | `alive_wave` | `conditional` | 空头试探与连续加码很适合讨论波段节奏，但交易谱中已有多空库存变化，不能只靠 MALF 定义。 | `trend_probe_entry / trend_confirmation_add / inventory_rebalance` | true | `do_not_treat_short_addon_as_malf_signal` | `malf_mapping` |
| `1975-03` | [1975-03](../monthly/1975-03.md) | `null` | `stagnation` | `conditional` | 价格压力下仓位链复杂，适合讨论节奏承压、修正与库存处理，但不能把压力心理写入 MALF。 | `exit_on_rhythm_failure / inventory_rebalance / wait_no_action` | true | `do_not_encode_pressure_as_malf_psychology` | `malf_mapping` |
| `1975-04` | [1975-04](../monthly/1975-04.md) | `null` | `alive_wave` | `suitable` | 延续空头、加码、月底减仓的动作链较清晰，是结构推进与仓位节奏相互承接的正样本。 | `trend_probe_entry / trend_confirmation_add / distribution_reduce` | true | `do_not_infer_position_size_from_malf` | `malf_mapping` |
| `1975-05` | [1975-05](../monthly/1975-05.md) | `null` | `transition` | `conditional` | 本月围绕空头库存反复调整，并开始出现锁单/库存意识相关章节线索，必须由 PM 承接。 | `inventory_rebalance / trend_confirmation_add / wait_no_action` | true | `do_not_confirm_lock_from_mixed_inventory_only` | `malf_mapping` |
| `1975-06-A` | [1975-06](../monthly/1975-06.md) / [段级审计](./MALF-立花1975-06交易段结构资格审计-v0.1.md) | `null` | `alive_wave / mother_build_candidate` | `conditional` | `—20 -> —30 -> —35 -> —40` 是多头母单扩张候选段，值得进入分批加码讨论，但母单/中心单不能由 MALF 自动确认。 | `trend_confirmation_add / open_center_candidate` | true | `do_not_call_mother_position_from_malf_only` | `fact / pm_annotation / malf_mapping` |
| `1975-06-B` | [1975-06](../monthly/1975-06.md) / [段级审计](./MALF-立花1975-06交易段结构资格审计-v0.1.md) | `null` | `transition / lock_candidate` | `conditional` | `—40 -> 2 — 40` 进入双侧库存状态，适合讨论锁单候选和库存再平衡，但锁单目的必须由 PM 证明。 | `inventory_rebalance / lock_candidate` | true | `do_not_confirm_lock_from_dual_inventory_only` | `fact / pm_annotation / malf_mapping` |
| `1975-06-C` | [1975-06](../monthly/1975-06.md) / [段级审计](./MALF-立花1975-06交易段结构资格审计-v0.1.md) | `null` | `transition / inventory_rebalance` | `conditional` | `2 — 40 -> 7 — 30 -> 12 — 30 -> 25 — 20` 同时包含多头兑现、反向测试和双侧库存保持，不能净额化成单一方向。 | `distribution_reduce / reverse_probe / inventory_rebalance` | true | `do_not_net_dual_inventory_into_single_direction` | `fact / pm_annotation / malf_mapping` |
| `1975-06-D` | [1975-06](../monthly/1975-06.md) / [段级审计](./MALF-立花1975-06交易段结构资格审计-v0.1.md) | `null` | `transition / next_segment_seed` | `conditional` | `25 — 20 -> 27 — 20` 是月末双侧库存延续，可作为跨月 PM 种子，但不是 MALF 的反转结论。 | `inventory_seed / trend_confirmation_add` | true | `do_not_treat_month_end_inventory_as_malf_reversal` | `fact / pm_annotation / malf_mapping` |
| `1975-07` | [1975-07](../monthly/1975-07.md) | `null` | `stagnation` | `conditional` | 多头库存逐步兑现，适合讨论利润保护与节奏收束，但不能把减仓动机写成 MALF 衰竭字段。 | `distribution_reduce / exit_on_rhythm_failure / wait_no_action` | true | `do_not_encode_profit_protection_in_malf` | `malf_mapping` |
| `1975-08` | [1975-08](../monthly/1975-08.md) | `null` | `range` | `conditional` | 无交易可能对应等待或无推进，但不能反向证明一定是 range。 | `wait_no_action` | false | `do_not_infer_range_from_no_trade` | `our_interpretation` |
| `1975-09` | [1975-09](../monthly/1975-09.md) | `null` | `range` | `conditional` | 少量空头试探、清零、月底再试探，适合讨论轻仓观察与区间背景，但不能把少交易日直接判为 range。 | `trend_probe_entry / wait_no_action / distribution_reduce` | true | `do_not_infer_range_from_low_trade_count` | `malf_mapping` |
| `1975-10` | [1975-10](../monthly/1975-10.md) | `null` | `transition` | `conditional` | 多头试探、加码、双侧库存与月底清零交织，结构资格有价值但必须通过 PM 解释库存再平衡。 | `trend_probe_entry / trend_confirmation_add / inventory_rebalance / distribution_reduce` | true | `do_not_treat_dual_inventory_as_lock_without_evidence` | `malf_mapping` |
| `1975-11` | [1975-11](../monthly/1975-11.md) | `null` | `alive_wave` | `suitable` | 空头试探后分批加码，动作链简洁，适合作为同向推进背景下仓位节奏的正样本。 | `trend_probe_entry / trend_confirmation_add / wait_no_action` | true | `do_not_infer_center_position_from_malf` | `malf_mapping` |
| `1975-12` | [1975-12](../monthly/1975-12.md) | `null` | `stagnation` | `conditional` | 年末收束与利润保护有讨论价值，但利润保护属于 PM。 | `distribution_reduce / wait_no_action` | true | `do_not_encode_profit_protection_in_malf` | `malf_mapping` |
| `1976-01` | [1976-01](../monthly/1976-01.md) / [升级审计](./MALF-立花1976-01至02样本升级审计-v0.1.md) | `null` | `transition` | `conditional` | 图像确认 `—1 -> —3 -> —5 -> 0` 轻仓空头试探和月底清零链，具备 Method / PM 讨论价值，但结构背景较弱。 | `trend_probe_entry / trend_confirmation_add / exit_on_rhythm_failure` | true | `do_not_infer_structure_from_short_probe_only` | `fact / malf_mapping` |
| `1976-02` | [1976-02](../monthly/1976-02.md) / [升级审计](./MALF-立花1976-01至02样本升级审计-v0.1.md) | `null` | `alive_wave` | `conditional` | 图像确认 `—2 -> —5 -> —10 -> —12 -> —7` 空头库存推进与月底部分回补，值得进入节奏讨论，但中心单解释必须留在 PM。 | `trend_probe_entry / trend_confirmation_add / distribution_reduce` | true | `do_not_write_center_position_into_malf` | `fact / malf_mapping` |
| `1976-03-A` | [1976-03](../monthly/1976-03.md) / [段级审计](./MALF-立花1976-03与07交易段结构资格审计-v0.1.md) | `null` | `stagnation / pressure_transition` | `conditional` | `—10 -> —5 -> —10 -> —12` 是旧段压力调整，适合讨论仓位节奏承压，但不能并成干净 wave。 | `trend_confirmation_add / distribution_reduce` | true | `do_not_merge_pressure_adjustment_into_clean_wave` | `fact / malf_mapping` |
| `1976-03-B` | [1976-03](../monthly/1976-03.md) / [段级审计](./MALF-立花1976-03与07交易段结构资格审计-v0.1.md) | `null` | `stagnation / exit_window` | `conditional` | `—12 -> —10 -> —5 -> 0` 是旧段清零闭环，清仓原因和 reset 归 Method / PM。 | `distribution_reduce / clear / reset_after_clear` | true | `do_not_encode_clear_reason_in_malf` | `fact / malf_mapping` |
| `1976-03-C` | [1976-03](../monthly/1976-03.md) / [段级审计](./MALF-立花1976-03与07交易段结构资格审计-v0.1.md) | `null` | `break_birth / inventory_seed` | `conditional` | `0 -> —2 -> —5 -> —10` 是清零后新库存种子，可导入 4 月双侧库存链，但不能并入旧段。 | `trend_probe_entry / trend_confirmation_add / inventory_seed` | true | `do_not_merge_new_seed_into_old_segment` | `fact / malf_mapping` |
| `1976-04-A` | [1976-04](../monthly/1976-04.md) / [段级审计](./MALF-立花1976-04至05交易段结构资格审计-v0.1.md) | `null` | `transition / lock_candidate` | `conditional` | `—10 -> 2 — 10 -> 2 — 12 -> 2 — 15 -> 2 — 20` 形成双侧库存扩张链，适合进入 PM，但不能自动确认锁单目的。 | `inventory_rebalance / lock_candidate` | true | `do_not_confirm_lock_from_dual_inventory_only` | `fact / pm_annotation / malf_mapping` |
| `1976-04-B` | [1976-04](../monthly/1976-04.md) / [段级审计](./MALF-立花1976-04至05交易段结构资格审计-v0.1.md) | `null` | `range_or_transition_wait` | `conditional` | `2 — 20` 持有等待，价格上冲但双侧库存未解除，不能由无交易反推 range。 | `wait_no_action` | true | `do_not_infer_range_from_no_trade_with_lock_candidate` | `fact / pm_annotation / malf_mapping` |
| `1976-04-C` | [1976-04](../monthly/1976-04.md) / [段级审计](./MALF-立花1976-04至05交易段结构资格审计-v0.1.md) | `null` | `transition / inventory_rebalance` | `conditional` | `2 — 20 -> 2 — 10 -> 4 — 10 -> 4 — 5` 是双侧库存收束和跨月延续，不是 MALF 反转样本。 | `distribution_reduce / inventory_rebalance` | true | `do_not_net_dual_inventory_into_single_direction` | `fact / pm_annotation / malf_mapping` |
| `1976-05-A` | [1976-05](../monthly/1976-05.md) / [段级审计](./MALF-立花1976-04至05交易段结构资格审计-v0.1.md) | `null` | `transition / lock_candidate_continuation` | `conditional` | `4 — 5 -> 5 — 5 -> 10 — 5` 承接 4 月双侧库存并继续调整，不能当作新 MALF wave 自动开始。 | `inventory_rebalance / add_on_candidate` | true | `do_not_treat_cross_month_lock_as_new_malf_wave` | `fact / pm_annotation / malf_mapping` |
| `1976-05-B` | [1976-05](../monthly/1976-05.md) / [段级审计](./MALF-立花1976-04至05交易段结构资格审计-v0.1.md) | `null` | `transition / unlock` | `conditional` | `10 — 5 -> 10 —` 是解锁事件，属于 PM 状态机，不属于 MALF 结构定义。 | `unlock / inventory_rebalance` | true | `do_not_write_unlock_into_malf` | `fact / pm_annotation / malf_mapping` |
| `1976-05-C` | [1976-05](../monthly/1976-05.md) / [段级审计](./MALF-立花1976-04至05交易段结构资格审计-v0.1.md) | `null` | `stagnation / exit_window` | `conditional` | `10 — -> 0` 是清仓闭环，清仓原因和风险控制归 Method / PM。 | `clear / reset_after_clear` | true | `do_not_encode_clear_reason_in_malf` | `fact / pm_annotation / malf_mapping` |
| `1976-06` | [1976-06](../monthly/1976-06.md) / [升级审计](./MALF-立花1976-06至09样本升级审计-v0.1.md) | `null` | `transition` | `conditional` | 图像确认 `2 — -> 5 — -> 7 — -> 10 —` 分批多头库存链，值得讨论分批建仓，但真实 MALF wave 未跑出。 | `trend_probe_entry / trend_confirmation_add` | true | `do_not_treat_addon_chain_as_malf_wave` | `fact / malf_mapping` |
| `1976-07-A` | [1976-07](../monthly/1976-07.md) / [段级审计](./MALF-立花1976-03与07交易段结构资格审计-v0.1.md) | `null` | `exit_window / reset` | `conditional` | `—10 -> 0` 是上一段清零，不能作为 MALF 方向判断。 | `clear / reset_after_clear` | true | `do_not_treat_clear_as_malf_direction` | `fact / malf_mapping` |
| `1976-07-B` | [1976-07](../monthly/1976-07.md) / [段级审计](./MALF-立花1976-03与07交易段结构资格审计-v0.1.md) | `null` | `transition / inventory_seed` | `conditional` | `0 -> 2 — -> 5 — -> 10 — -> 12 — -> 15 —` 是清零后新段分批扩张，但中心单和加码单区分归 PM。 | `trend_probe_entry / trend_confirmation_add` | true | `do_not_merge_rebuild_addon_into_one_wave_claim` | `fact / malf_mapping` |
| `1976-07-C` | [1976-07](../monthly/1976-07.md) / [段级审计](./MALF-立花1976-03与07交易段结构资格审计-v0.1.md) | `null` | `stagnation / reduce_window` | `conditional` | `15 — -> 10 —` 是月底减仓事实，不能单独反推利润保护或节奏失败。 | `distribution_reduce` | true | `do_not_infer_profit_or_loss_reason_from_reduce_only` | `fact / malf_mapping` |
| `1976-08` | [1976-08](../monthly/1976-08.md) / [升级审计](./MALF-立花1976-06至09样本升级审计-v0.1.md) | `null` | `break_birth` | `conditional` | 图像确认空头试探、加码、清零链，适合讨论多空切换与节奏失败，但不能仅凭库存确认结构转折。 | `reversal_flip / trend_probe_entry / trend_confirmation_add / exit_on_rhythm_failure` | true | `do_not_infer_reversal_from_short_inventory_only` | `fact / malf_mapping` |
| `1976-09` | [1976-09](../monthly/1976-09.md) / [口径审计](./MALF-立花1976-09制度资料口径审计-v0.1.md) | `null` | `unknown` | `unknown` | 图像确认 `2 — -> 0`，但 9 月 21 日交易单位变化与 9 月 27 日除权造成制度/资料口径干扰，不能进入 Method。 | `none` | false | `do_not_mix_unit_change_ex_rights_and_structure_qualification` | `fact / source_audit` |
| `1976-10` | [1976-10](../monthly/1976-10.md) | `null` | `alive_wave` | `suitable` | 下行结构中小额右侧仓位推进，是同向推进背景的较干净样本。 | `trend_probe_entry / trend_confirmation_add` | true | `do_not_infer_center_position_from_malf` | `malf_mapping` |
| `1976-11-A` | [1976-11](../monthly/1976-11.md) / [段级审计](./MALF-立花1976-11交易段结构资格审计-v0.1.md) | `null` | `alive_wave` | `conditional` | `—24 -> —26 -> —28 -> —48 -> —98 -> —200` 处于同向推进背景，但极端加码尺度必须交给 PM。 | `trend_confirmation_add` | true | `do_not_treat_large_addon_as_structure_fact` | `fact / malf_mapping` |
| `1976-11-B` | [1976-11](../monthly/1976-11.md) / [段级审计](./MALF-立花1976-11交易段结构资格审计-v0.1.md) | `null` | `stagnation / break_candidate` | `conditional` | `—200 -> 0` 清仓可能对应节奏失败或结构转折，但认错、清仓和风险承受属于 Method / PM。 | `exit_on_rhythm_failure / clear` | true | `do_not_encode_accept_loss_in_malf` | `fact / malf_mapping` |
| `1976-11-C` | [1976-11](../monthly/1976-11.md) / [段级审计](./MALF-立花1976-11交易段结构资格审计-v0.1.md) | `null` | `transition / unknown` | `conditional` | `—5 -> 0 -> —5` 是清仓后的新小仓试探，不能并入上旬旧中心单。 | `trend_probe_entry / exit_on_rhythm_failure` | true | `do_not_merge_probe_after_clear_into_old_center` | `fact / malf_mapping` |
| `1976-11-D` | [1976-11](../monthly/1976-11.md) / [段级审计](./MALF-立花1976-11交易段结构资格审计-v0.1.md) | `null` | `break_birth` | `conditional` | `—5 -> 5 — -> 10 — -> 15 — -> 35 —` 是反手后新仓位骨架形成段，但反手与中心单重置不属于 MALF。 | `reversal_flip / trend_confirmation_add` | true | `do_not_treat_reversal_as_malf_decision` | `fact / malf_mapping` |
| `1976-12-A` | [1976-12](../monthly/1976-12.md) / [段级审计](./MALF-立花1976-12交易段结构资格审计-v0.1.md) | `null` | `alive_wave` | `conditional` | `35 — -> 40 — -> 45 — -> 50 —` 承接 11 月新仓位骨架并小额推进，但中心单候选不能由 MALF 自动推导。 | `trend_confirmation_add` | true | `do_not_infer_center_position_from_malf` | `fact / malf_mapping` |
| `1976-12-B` | [1976-12](../monthly/1976-12.md) / [段级审计](./MALF-立花1976-12交易段结构资格审计-v0.1.md) | `null` | `alive_wave` | `conditional` | `50 — -> 60 — -> 80 — -> 100 — -> 150 —` 是上行推进中的加速加码段，但加码尺度属于 PM。 | `trend_confirmation_add` | true | `do_not_treat_addon_scale_as_structure_strength` | `fact / malf_mapping` |
| `1976-12-C` | [1976-12](../monthly/1976-12.md) / [段级审计](./MALF-立花1976-12交易段结构资格审计-v0.1.md) | `null` | `stagnation / no_progress_candidate` | `conditional` | `150 —` 高位持仓观察，无交易不等于 range，大仓位等待必须由 PM 记录压力。 | `wait_no_action` | true | `do_not_infer_range_from_no_trade_with_large_inventory` | `fact / malf_mapping` |
| `1976-12-D` | [1976-12](../monthly/1976-12.md) / [段级审计](./MALF-立花1976-12交易段结构资格审计-v0.1.md) | `null` | `stagnation / exit_window` | `conditional` | `150 — -> 100 — -> 50 — -> 0` 是三段式收束清仓，利润保护和退出比例属于 PM。 | `distribution_reduce / clear` | true | `do_not_encode_profit_protection_in_malf` | `fact / malf_mapping` |

## 初步观察

- `suitable` 当前只给结构相对干净、动作节奏较容易讨论的样本，如 `1975-01`、`1975-04`、`1975-11`、`1976-10`。
- `conditional` 是当前主类，因为多数立花样本都混合了结构、Method 和 PM，不能只靠 MALF 解释。
- `unsuitable` 暂不强行标注；需要真实 MALF 快照或更明确的反例后再使用。
- `unknown` 当前只保留给 `1976-09` 这类“有理由 unknown”样本：它不是未研究，而是交易单位变化、除权和轻仓短链共同阻断结构资格升级。

## 1975-1976 全月覆盖清单

本表用于确认每个月份是否已经进入结构资格样本体系。`coverage_status` 不等于研究完成度，只表示是否已有资格判读入口。

| 月份 | coverage_status | 当前资格 | 主要结构背景 | 下一步 |
|---|---|---|---|---|
| `1975-01` | `sampled` | `suitable` | `alive_wave` | 补章节页码和真实 MALF 快照。 |
| `1975-02` | `sampled` | `conditional` | `alive_wave` | 补真实 MALF 快照和加空章节锚点。 |
| `1975-03` | `sampled` | `conditional` | `stagnation` | 补逆势压力下仓位处理的章节锚点。 |
| `1975-04` | `sampled` | `suitable` | `alive_wave` | 补延续空头结构与减仓的真实 MALF 快照。 |
| `1975-05` | `sampled` | `conditional` | `transition` | 补方向压力、锁单/库存意识边界。 |
| `1975-06` | `sampled_split` | `conditional` | `alive_wave / transition / lock_candidate` | 已完成交易段级审计；后续补真实 MALF 快照和母单/锁单页码锚点。 |
| `1975-07` | `sampled` | `conditional` | `stagnation` | 补利润保护与分批兑现章节锚点。 |
| `1975-08` | `sampled` | `conditional` | `range` | 验证无交易不能反推 range。 |
| `1975-09` | `sampled` | `conditional` | `range` | 补轻仓试探与等待边界。 |
| `1975-10` | `sampled` | `conditional` | `transition` | 补多空调整和库存再平衡边界。 |
| `1975-11` | `sampled` | `suitable` | `alive_wave` | 补继续分批处理样本的真实 MALF 快照。 |
| `1975-12` | `sampled` | `conditional` | `stagnation` | 补年末收束的章节锚点。 |
| `1976-01` | `sampled` | `conditional` | `transition` | 已完成第二组升级审计；后续补真实 MALF 快照。 |
| `1976-02` | `sampled` | `conditional` | `alive_wave` | 已完成第二组升级审计；后续区分中心单和加码单。 |
| `1976-03` | `sampled_split` | `conditional` | `stagnation / break_birth / inventory_seed` | 已完成交易段级审计；后续补真实 MALF 快照和 reset 页码锚点。 |
| `1976-04` | `sampled_split` | `conditional` | `transition / lock_candidate / inventory_rebalance` | 已完成交易段级审计；后续补真实 MALF 快照和锁单页码锚点。 |
| `1976-05` | `sampled_split` | `conditional` | `transition / unlock / exit_window` | 已完成交易段级审计；后续补真实 MALF 快照和清仓动机锚点。 |
| `1976-06` | `sampled` | `conditional` | `transition` | 已完成第一组升级审计；后续补真实 MALF 快照。 |
| `1976-07` | `sampled_split` | `conditional` | `exit_window / transition / reduce_window` | 已完成交易段级审计；后续补真实 MALF 快照和分批基准锚点。 |
| `1976-08` | `sampled` | `conditional` | `break_birth` | 已完成第一组升级审计；后续确认转折证据。 |
| `1976-09` | `sampled_unknown` | `unknown` | `unknown` | 已完成制度/资料口径审计；保持有理由 unknown。 |
| `1976-10` | `sampled` | `suitable` | `alive_wave` | 补真实 MALF 快照后可做正样本。 |
| `1976-11` | `sampled_split` | `conditional` | `alive_wave / stagnation / transition / break_birth` | 已完成交易段级审计；后续补真实 MALF 快照。 |
| `1976-12` | `sampled_split` | `conditional` | `alive_wave / stagnation` | 已完成交易段级审计；后续补真实 MALF 快照。 |

## 下一步

- 跑出真实 MALF 快照后，用 `malf_snapshot_ref` 替换 `null`。
- 后续样本升级时补入 `rhythm_meaning`，并按 [MALF-立花结构状态到仓位节奏意义判定准则 v0.1](./MALF-立花结构状态到仓位节奏意义判定准则-v0.1.md) 映射到 `tachibana_applicability`。
- 当前历史样本的月级/段级回填先以 [MALF-立花 rhythm_meaning 历史样本回填审计 v0.1](./MALF-立花rhythm_meaning历史样本回填审计-v0.1.md) 保留，不强行把主样本表扩成宽表。
- 为每条样本补充 `source_anchor` 的章节、PDF 页码、图片编号。
- 保留 `1976-09` 作为“有理由 unknown”反例样本，用于校准前置过滤器不要为了覆盖率强行升级。
- 横向判读矩阵已经接入 [Tachibana Backtest Input 适配层草案 v0.1](./Tachibana-Backtest-Input-适配层草案-v0.1.md)，明确哪些资格字段可以进入回测适配层。
- `1976-03/04/05/07/11/12` 与 `1975-06` 已完成 Backtest Input 第一轮试填；A 股候选股票结构资格样本表已新增，下一步填入真实 A 股元数据与 MALF 快照。
