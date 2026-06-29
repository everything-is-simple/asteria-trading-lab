# Tachibana A股 add_on price_limit shortlist intraday review v0.1

> 研究日期：2026-06-29
> 研究范围：对 `add_on / pullback_add` 样本池预筛 shortlist 的事件日 `lc5` 做最小 intraday review，确认哪些样本已经具备 `near_limit` 或 `at_limit` 的整日盘中支撑

## 1. 目标与边界

本 review 只回答一个问题：

**当前 shortlist 里，哪些样本已经有足够清楚的事件日整日盘中范围，可以支持 `near_limit` 或 `at_limit` 候选判断。**

本 review 不做以下事情：

- 不认定这些样本已经正式通过 `Q-PRESSURE-ADJUST`
- 不认定这些样本已经正式是 `pullback_add / add_on`
- 不把整日 `lc5` 支撑直接写成最终 reviewed relation evidence JSON
- 不替代后续 MALF snapshot 与 front-filter 复核

## 2. 当前 review 对象

本轮只 review 当前正式 shortlist 的 6 个样本：

1. `603538.SH / 美诺华 / 2026-04-01`
2. `603008.SH / 喜临门 / 2026-03-30`
3. `600310.SH / 广西能源 / 2026-03-30`
4. `603687.SH / 大胜达 / 2026-03-27`
5. `002663.SZ / 普邦股份 / 2026-04-03`
6. `000899.SZ / 赣能股份 / 2026-03-30`

## 3. 证据来源

### 3.1 分钟线文件

- `Z:\new_tdx64\vipdoc\sh\fzline\sh603538.lc5`
- `Z:\new_tdx64\vipdoc\sh\fzline\sh603008.lc5`
- `Z:\new_tdx64\vipdoc\sh\fzline\sh600310.lc5`
- `Z:\new_tdx64\vipdoc\sh\fzline\sh603687.lc5`
- `Z:\new_tdx64\vipdoc\sz\fzline\sz002663.lc5`
- `Z:\new_tdx64\vipdoc\sz\fzline\sz000899.lc5`

### 3.2 比对方法

对每个 shortlist 样本：

1. 读取事件日整日 `lc5`
2. 提取整日 `intraday_high / intraday_low`
3. 与同日涨跌停边界 `limit_up_price / limit_down_price` 比对
4. 只输出：
   - 最近边界方向
   - 最近边界距离
   - 当前最小判断

## 4. 最小 review 表

| ts_code | 名称 | trade_date | intraday_high | intraday_low | limit_up_price | limit_down_price | nearest_intraday_side | nearest_intraday_gap_pct | 当前最小判断 |
|---|---|---|---:|---:|---:|---:|---|---:|---|
| `603538.SH` | `美诺华` | `2026-04-01` | `41.72` | `36.81` | `44.990` | `36.810` | `down_limit_side` | `0.0000%` | `at_limit` 候选，但更像触边后打开的压力调整 |
| `603008.SH` | `喜临门` | `2026-03-30` | `15.77` | `14.67` | `17.930` | `14.670` | `down_limit_side` | `0.0000%` | `at_limit` 候选，但收盘明显打开 |
| `600310.SH` | `广西能源` | `2026-03-30` | `7.26` | `6.18` | `7.260` | `5.940` | `up_limit_side` | `0.0000%` | `at_limit` 候选里最关键的 `up_limit_side` 对照 |
| `603687.SH` | `大胜达` | `2026-03-27` | `16.47` | `14.85` | `18.150` | `14.850` | `down_limit_side` | `0.0000%` | `at_limit` 候选，但保留较强 `pressure_adjust` 研究价值 |
| `002663.SZ` | `普邦股份` | `2026-04-03` | `2.20` | `1.97` | `2.409` | `1.971` | `down_limit_side` | `0.0500%` | `near_limit` 候选，且极贴边 |
| `000899.SZ` | `赣能股份` | `2026-03-30` | `14.29` | `13.13` | `16.038` | `13.122` | `down_limit_side` | `0.0600%` | `near_limit` 候选，贴边稳定 |

## 5. 当前判断

### 5.1 可以先当 `at_limit` 候选继续推进的

- `603538.SH / 美诺华 / 2026-04-01`
- `603008.SH / 喜临门 / 2026-03-30`
- `600310.SH / 广西能源 / 2026-03-30`
- `603687.SH / 大胜达 / 2026-03-27`

原因：

- 整日 `lc5` 已直接打到边界
- 一个是 `up_limit_side`
- 一个是 `down_limit_side`

这组样本组合在一起，已经比单看 `300750.SZ / not_near_limit` 更能回答：

- `at_limit` 在 A 股真实窗口里是否能找到 reopened 触边后的多样本对照
- `up_limit_side` 是否也能进入 `pressure_adjust` 候选面

### 5.2 可以先当 `near_limit` 候选继续推进的

- `002663.SZ / 普邦股份 / 2026-04-03`
- `000899.SZ / 赣能股份 / 2026-03-30`

原因：

- 它们都没有整日直接到板
- 但与最近边界只差 `0.05%` 到 `0.06%`
- 这已经足以支持“近板但未到板”的强候选判断
- 并且能给 reopened 触边样本补一层稳定的 `near_limit` 比较面

### 5.3 压成下一拍核心 4 样本

如果把目标继续收窄成：

- 先挑出最值得进 MALF snapshot / front-filter research prep 的核心样本
- 暂时优先保留更像 `pressure_adjust` 的 reopened 触边面
- 把 `near_limit_compare` 留作补位与对照

那么当前最自然的核心 4 样本就是：

1. `603538.SH / 美诺华 / 2026-04-01`
2. `603008.SH / 喜临门 / 2026-03-30`
3. `600310.SH / 广西能源 / 2026-03-30`
4. `603687.SH / 大胜达 / 2026-03-27`

原因很直接：

- 它们都已经有整日 `lc5` 触边证据
- 都属于 `reopened_after_limit_touch`
- 收盘都明显离开板边，更像“触边后打开”的压力调整
- 其中 `600310.SH` 还保留了当前最稀缺的 `up_limit_side` 对照

这组 4 样本比把 `near_limit` 样本也一起塞进下一拍更顺，因为它们更集中地回答一个问题：

- `pullback_add / add_on` 语义到底会不会更贴近 reopened touch 的 `pressure_adjust`

而 `002663.SZ / 000899.SZ` 更适合作为：

- `near_limit_compare` 备份对照
- 当核心 4 样本里有任何一个在 snapshot / front-filter research prep 里失去结构吸引力时，再补进来

### 5.4 第二梯队里更像 `pressure_adjust / pullback_add` 的候选

如果继续往“多样本可比”而不是“极端跌停大全”推进，本轮还可以再从候选池里单独拎出一层：

- 盘中已经触边或极贴边
- 但收盘并没有继续钉死在同一侧边界
- 当日收盘回撤幅度也没有恶化到最极端

这类样本不一定更“强”，但更像：

- `pressure_adjust`
- `pullback_add`
- 或至少更像“旧段内受边界挤压后的调整”，而不是纯失败下杀

补一张第二梯队最小对照表：

| ts_code | 名称 | trade_date | nearest_intraday_side | nearest_intraday_gap_pct | 收盘距同侧边界 | runup_pct | close_return_pct | 当前最小判断 |
|---|---|---|---|---:|---:|---:|---:|---|
| `603538.SH` | `美诺华` | `2026-04-01` | `down_limit_side` | `0.0000%` | `8.10%` | `60.90` | `-2.71` | 盘中到下边界，但收盘明显打开，较像高位压力调整而非封死跌停 |
| `600310.SH` | `广西能源` | `2026-03-30` | `up_limit_side` | `0.0000%` | `12.95%` | `51.38` | `-4.24` | 盘中到上边界但收盘回落较多，仍是当前最稀缺的 `up_limit_side` 压力调整对照 |
| `603008.SH` | `喜临门` | `2026-03-30` | `down_limit_side` | `0.0000%` | `7.16%` | `32.48` | `-3.56` | 到下边界后收盘打开，较像旧段内挤压调整 |
| `603687.SH` | `大胜达` | `2026-03-27` | `down_limit_side` | `0.0000%` | `5.25%` | `35.58` | `-5.27` | 盘中触边、收盘未封死，保留较强 `pressure_adjust` 研究价值 |
| `600815.SH` | `厦工股份` | `2026-03-26` | `up_limit_side` | `0.0200%` | `11.00%` | `34.48` | `-2.10` | 稀缺的 `up_limit_side` 极贴边未封死样本，可补 `at/near upper limit` 第二对照 |
| `002560.SZ` | `通达股份` | `2026-04-03` | `up_limit_side` | `0.0300%` | `12.15%` | `39.08` | `-3.37` | 与 `600310.SH` 一起形成更像“冲边后回落”的上边界样本面 |

这批样本的意义不在于立刻替代第一梯队，而在于它们让我们第一次能在同一窗口里分开看两种情况：

1. 盘中已经触边，但更像调整中的受压回落
2. 盘中触边且更接近情绪性杀跌/封板极值

如果后续要继续判断 `add_on` 的 `near_limit / at_limit` 语义是否会逼近升级闸门，这批第二梯队会比继续只堆更多跌停样本更有解释力。

### 5.5 正式 review shortlist（本轮 6 样本）

如果把目标进一步收窄成：

- 从当前候选池里先挑出一组最像 `pressure_adjust`
- 同时保留最贴边的 `near_limit` 对照
- 让下一拍直接进入“多样本 near/at 判断面”

那么当前最合适的正式 review shortlist 已经可以固定成这 6 个：

| rank | ts_code | 名称 | trade_date | formal_review_bucket | nearest_intraday_side | intraday_limit_reopen_status | intraday_nearest_limit_gap_pct | intraday_close_gap_pct | runup_pct | close_return_pct | 当前最小 review 判断 |
|---:|---|---|---|---|---|---|---:|---:|---:|---:|---|
| 1 | `603538.SH` | `美诺华` | `2026-04-01` | `pressure_adjust_reopen` | `down_limit_side` | `reopened_after_limit_touch` | `0.00%` | `8.10%` | `60.90` | `-2.71` | 最像高位受压后打开的调整样本之一，适合作为 `pressure_adjust` 首选对照 |
| 2 | `603008.SH` | `喜临门` | `2026-03-30` | `pressure_adjust_reopen` | `down_limit_side` | `reopened_after_limit_touch` | `0.00%` | `7.16%` | `32.48` | `-3.56` | 盘中触边但收盘打开，形态上比封死跌停更接近旧段内受压回撤 |
| 3 | `600310.SH` | `广西能源` | `2026-03-30` | `pressure_adjust_reopen` | `up_limit_side` | `reopened_after_limit_touch` | `0.00%` | `12.95%` | `51.38` | `-4.24` | 当前最关键的 `up_limit_side` 压力调整对照，不能轻易丢 |
| 4 | `603687.SH` | `大胜达` | `2026-03-27` | `pressure_adjust_reopen` | `down_limit_side` | `reopened_after_limit_touch` | `0.00%` | `5.25%` | `35.58` | `-5.27` | 盘中触边、收盘未封死，仍保留较强 `pressure_adjust` 研究价值 |
| 5 | `002663.SZ` | `普邦股份` | `2026-04-03` | `near_limit_compare` | `down_limit_side` | `near_limit_without_touch` | `0.05%` | `1.98%` | `12.96` | `-8.22` | 最贴边的 `near_limit` 对照之一，适合作为“未触板但极贴边”样本 |
| 6 | `000899.SZ` | `赣能股份` | `2026-03-30` | `near_limit_compare` | `down_limit_side` | `near_limit_without_touch` | `0.06%` | `2.27%` | `20.17` | `-7.96` | 比较稳的 `near_limit` 候选，可与 `002663.SZ` 一起承接 near/at 对照面 |

这张表的意义是：

1. `603538 / 603008 / 600310 / 603687` 负责承接“更像 `pressure_adjust` 的 reopened 触边样本”
2. `002663 / 000899` 负责承接“极贴边但未触板”的 `near_limit` 对照
3. 这 6 个放在一起，已经比“继续只看 1 个 `not_near_limit` + 几个跌停极值”更接近真正的多样本比较面

## 6. 当前还不能说什么

尽管这 6 个样本已经有了整日 intraday 支撑，我们当前仍然不能直接说：

- 它们已经正式是 `price_limit_event_limit_proximity = near_limit / at_limit`
- 它们已经正式是 `Q-PRESSURE-ADJUST / pullback_add / add_on`

因为还缺：

1. 这些窗口是否真的像 `pressure_adjust`
2. 是否适合进入 MALF snapshot
3. front-filter 是否会把它们收敛到我们要的结构语义
4. 是否存在更精确的 planned-event 级说明

## 7. 下一步

下一步建议按这个顺序走：

1. 先优先推进核心 4 样本：`603538.SH / 603008.SH / 600310.SH / 603687.SH`
2. 把 `002663.SZ / 000899.SZ` 保留为 `near_limit_compare` 备份对照
3. 对核心 4 样本准备最小 MALF snapshot 与 front-filter research prep
4. 只有当结构资格也站住以后，才考虑补 reviewed relation evidence JSON

但在进入 MALF snapshot 之前，本轮还多得到了一层很有用的样本池观察：

- 当前前排 `at_limit_candidate` 里，并不都是“触边后继续封死”
- 把候选池前 `80` 个样本接上整日 `lc5` 后，出现了：
  - `44` 个 `reopened_after_limit_touch`
  - `30` 个 `closed_at_limit_after_touch`
  - `6` 个 `near_limit_without_touch`

这意味着接下来的 shortlist 不必只围绕：

- “谁更贴边”

还可以更明确地围绕：

- “谁更像触边后打开的压力调整”
- “谁更像极贴边但未触板的 near_limit”

从这个角度看，`600310.SH / 美诺华 / 喜临门 / 大胜达 / 厦工股份 / 通达股份` 这一层第二梯队，反而对 `pullback_add / add_on` 语义更有研究价值，因为它们更接近：

- 盘中受边界挤压
- 但收盘没有继续停在板边

也就是更像：

- `pressure_adjust`

而不是简单的：

- 跌停极值样本

如果再进一步把这个判断写成可复跑 shortlist，当前真实窗口里，前 `10` 个更像 `Q-PRESSURE-ADJUST / pullback_add` 的候选已经可以稳定产出：

1. `603538.SH / 美诺华 / 2026-04-01`
2. `603008.SH / 喜临门 / 2026-03-30`
3. `600310.SH / 广西能源 / 2026-03-30`
4. `603687.SH / 大胜达 / 2026-03-27`
5. `605162.SH / 新中港 / 2026-03-30`
6. `000601.SZ / 韶能股份 / 2026-03-30`
7. `002800.SZ / 天顺股份 / 2026-04-01`
8. `002310.SZ / 东方新能 / 2026-03-26`
9. `603693.SH / 江苏新能 / 2026-03-26`
10. `600703.SH / 三安光电 / 2026-03-24`

这里面最值得继续盯住的，仍然是：

- `603538.SH`
- `603008.SH`
- `600310.SH`
- `603687.SH`

因为它们同时满足：

- 盘中已经触边
- 收盘明显打开
- 回撤幅度没有恶化到最极端

也因此，它们比“继续多找几只收盘直接钉死跌停”的样本，更适合承担下一拍的 `pressure_adjust / add_on` 研究推进。

### 7.1 当前真实阻断

本轮已经试跑过一版研究映射型 shortlist snapshot 包，目标样本包括：

- `600310.SH`
- `000020.SZ`
- `002663.SZ`
- `000670.SZ`

结果不是 front-filter 自身失败，而是更上游的样本接入被真实数据阻断：

- `industry_membership_window_not_overlapping:600310.SH`
- `industry_membership_window_not_overlapping:000020.SZ`
- `industry_membership_window_not_overlapping:002663.SZ`
- `industry_membership_window_not_overlapping:000670.SZ`

进一步核对 `market_meta.market_meta.industry_block_relation` 后，发现这些股票的当前 `industry` 关系事实都从：

- `2026-04-23`

才开始生效。

这意味着：

- 当前 `2026-03-24` 至 `2026-04-03` 的 shortlist 窗口
- 在真实 DuckDB 口径下
- **没有窗口内可重叠的行业标签**

因此当前不能直接把这些样本推进到正式 `structure_candidate -> front_filter` 链路，而不借用未来标签。

进一步把整个近板候选池都标上 `industry_window_status` 后，结果也一致：

- `268` 个候选里
- `overlapping = 0`
- `not_overlapping = 268`

所以当前不是只有 shortlist 巧合撞上这个问题，而是：

- **整个当前近板候选池，在真实数据口径下都还停在 proximity 研究候选层。**

而且本轮继续尝试把筛选窗口后移到 `industry` 标签开始生效之后时，又确认了更硬的现实边界：

- 当前 `industry` 标签的最早 `effective_from = 2026-04-23`
- 当前 `market_base_day` 的最新 `trade_dt = 2026-04-23`

所以本地数据里还没有“标签已生效之后的一段后续日线窗口”可供继续筛选。

这意味着当前要想继续把近板候选推进成正式结构复核样本，只剩两条路：

1. 补更新后的日线数据
2. 补更早生效、时间对齐的行业标签来源

### 7.2 本地 TDX 行业快照的新增结论

本轮也继续核对了本地 TDX 缓存里的行业快照：

- `tdxhy.cfg`
- `tdxzs.cfg`
- `tdxzs3.cfg`

它们能回答：

- shortlist 样本**当前**被归到哪个 TDX 行业

并且这组结果与 DuckDB 里从 `2026-04-23` 开始生效的 `industry_block_relation` 是一致的。例如：

- `600310.SH -> T010201 -> 水力发电`
- `000020.SZ -> T1204 -> 元器件`
- `002663.SZ -> T110101 -> 建筑工程`
- `000670.SZ -> T1204 -> 元器件`

但这里仍然有一个关键边界：

- 这些文件没有给出 `effective_from / effective_to`
- 因而只能证明“当前归属”
- 不能直接证明“`2026-03-24 ~ 2026-04-03` 事件窗口当时已经生效”

所以这条新增证据能帮助我们做的是：

- 给 shortlist 补一个更扎实的行业背景参考

但还不能帮助我们直接越过：

- `industry_membership_window_not_overlapping`

这个正式结构复核阻断。

## 8. 当前结论

本轮 review 已经把 shortlist 从：

- **日线级预筛候选**

推进到：

- **带整日 `lc5` 盘中支撑的 near_limit / at_limit 候选**

这一步还没有完成正式样本认定，但已经足以支撑我们继续做下一轮结构复核，而不是再回到“只有 `300750.SZ / not_near_limit` 一条”的单样本状态。

同时，本轮也明确暴露出一个新的真实边界：

- **shortlist 样本的近板证据已经够强**
- **但时间对齐行业标签暂时拦住了它们进入正式 front-filter 复核**

所以接下来的工作应拆成两条并行研究线：

1. 继续保留这些样本作为 `near_limit / at_limit` proximity 研究候选
2. 另行补时间对齐行业标签来源，才能把它们推进到正式结构资格复核链路

## 9. 当前已落地的 research prep 入口

为了不把这批样本硬塞进正式 `structure_candidate -> front_filter` 链路，本轮已经新增一个只读 research-prep helper：

- [first_batch.py](/Z:/asteria-trading-lab/src/data_sources/tdx_local/first_batch.py) 中的 `build_shortlist_malf_research_prep(...)`

对应测试：

- [test_tdx_local_first_batch.py](/Z:/asteria-trading-lab/tests/test_tdx_local_first_batch.py)

它的职责不是生成正式接入包，而是把 core 4 / backup 2 样本整理成一张诚实的准备清单。每条记录只提供：

- `ts_code / symbol_name / trade_date / sample_window_start / sample_window_end`
- `research_priority_group = core / backup`
- `formal_review_bucket / core_snapshot_focus`
- 窗口日线摘要与事件日摘要
- 当前行业参考
- `industry_window_status`
- `formal_front_filter_status`
- `formal_front_filter_issue`
- `snapshot_stub`
- `ashare_sample_id_suggestion`
- `suggested_front_filter_command`
- `suggested_record_draft_command`

这里最关键的边界有三条：

1. `research_only = true`
2. `formal_data_write_allowed = false`
3. `institution_rule_definition_allowed / signal_generation_allowed / backtest_execution_allowed` 全部保持 `false`

也就是说，它做的是：

- 把“下一拍该准备哪几个 snapshot、它们为什么被卡住、如果不卡下一步命令会是什么”整理出来

而不是：

- 假装这些样本已经具备 ready MALF snapshot
- 假装已经可以直接跑正式 front-filter

### 9.1 core 4 / backup 2 的当前 prep 分工

当前最自然的 research-prep 分工仍然是：

- **core 4**：`603538.SH / 603008.SH / 600310.SH / 603687.SH`
- **backup 2**：`002663.SZ / 000899.SZ`

helper 输出里，对这两层会分别保留：

- `research_priority_group = core`
- `research_priority_group = backup`

其中 backup 2 的职责仍然只是：

- `near_limit_compare`
- 当 core 4 任一样本在后续 snapshot / front-filter research prep 里失去结构吸引力时，再补位

### 9.2 helper 当前能给出的 formal 状态

当前 helper 对每个样本只会落在三种 formal 状态之一：

1. `formal_front_filter_status = blocked`
2. `formal_front_filter_status = snapshot_pending`
3. `formal_front_filter_status = ready`

但在我们现在这条真实研究线上，最重要的是前两种：

- `blocked`
  - 表示行业窗口不重叠
  - 典型问题码：`industry_membership_window_not_overlapping:<ts_code>`
- `snapshot_pending`
  - 表示行业窗口可以重叠
  - 但还缺 `snapshot_quality_status=ready`
  - 典型问题码：`pipeline_requires_ready_malf_snapshot`

因此这个 helper 的意义不是“把阻断消掉”，而是把阻断位置说清楚：

- 是还缺时间对齐行业标签
- 还是已经可以开始准备最小 MALF snapshot

### 9.3 当前这层真正推进了什么

这一步最实际的价值是：

1. core 4 / backup 2 已经不再只是口头 shortlist
2. 每个样本已经有了统一的 research-prep 字段形状
3. formal blocker 被精确拆成：
   - `industry_membership_window_not_overlapping`
   - `pipeline_requires_ready_malf_snapshot`

于是接下来我们就能把下一拍动作继续压小，而不需要重新回到“大而空地讨论要不要 front-filter”。
