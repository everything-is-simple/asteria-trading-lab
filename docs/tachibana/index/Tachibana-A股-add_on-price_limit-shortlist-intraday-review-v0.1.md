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

本轮只 review 6 个 shortlist：

1. `600310.SH / 广西能源 / 2026-03-30`
2. `000020.SZ / 深华发Ａ / 2026-03-24`
3. `600758.SH / 辽宁能源 / 2026-03-30`
4. `002663.SZ / 普邦股份 / 2026-04-03`
5. `000670.SZ / 盈方微 / 2026-04-02`
6. `000899.SZ / 赣能股份 / 2026-03-30`

## 3. 证据来源

### 3.1 分钟线文件

- `Z:\new_tdx64\vipdoc\sh\fzline\sh600310.lc5`
- `Z:\new_tdx64\vipdoc\sz\fzline\sz000020.lc5`
- `Z:\new_tdx64\vipdoc\sh\fzline\sh600758.lc5`
- `Z:\new_tdx64\vipdoc\sz\fzline\sz002663.lc5`
- `Z:\new_tdx64\vipdoc\sz\fzline\sz000670.lc5`
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
| `600310.SH` | `广西能源` | `2026-03-30` | `7.26` | `6.18` | `7.26` | `5.94` | `up_limit_side` | `0.0000%` | `at_limit` 候选最强样本之一 |
| `000020.SZ` | `深华发Ａ` | `2026-03-24` | `20.58` | `18.90` | `23.10` | `18.90` | `down_limit_side` | `0.0000%` | `at_limit` 候选最强样本之一 |
| `002663.SZ` | `普邦股份` | `2026-04-03` | `2.20` | `1.97` | `2.409` | `1.971` | `down_limit_side` | `0.0507%` | `near_limit` 候选，且极贴边 |
| `000670.SZ` | `盈方微` | `2026-04-02` | `8.55` | `7.78` | `9.504` | `7.776` | `down_limit_side` | `0.0514%` | `near_limit` 候选，且极贴边 |
| `600758.SH` | `辽宁能源` | `2026-03-30` | `5.25` | `4.98` | `6.083` | `4.977` | `down_limit_side` | `0.0603%` | `near_limit` 候选，runup 较强 |
| `000899.SZ` | `赣能股份` | `2026-03-30` | `14.29` | `13.13` | `16.038` | `13.122` | `down_limit_side` | `0.0610%` | `near_limit` 候选，贴边稳定 |

## 5. 当前判断

### 5.1 可以先当 `at_limit` 候选继续推进的

- `600310.SH / 广西能源 / 2026-03-30`
- `000020.SZ / 深华发Ａ / 2026-03-24`

原因：

- 整日 `lc5` 已直接打到边界
- 一个是 `up_limit_side`
- 一个是 `down_limit_side`

这两个样本组合在一起，已经比单看 `300750.SZ / not_near_limit` 更能回答：

- `at_limit` 在 A 股真实窗口里是否能找到两侧对照

### 5.2 可以先当 `near_limit` 候选继续推进的

- `002663.SZ / 普邦股份 / 2026-04-03`
- `000670.SZ / 盈方微 / 2026-04-02`
- `600758.SH / 辽宁能源 / 2026-03-30`
- `000899.SZ / 赣能股份 / 2026-03-30`

原因：

- 它们都没有整日直接到板
- 但与最近边界只差 `0.05%` 到 `0.06%`
- 这已经足以支持“近板但未到板”的强候选判断

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

1. 先优先推进 `600310.SH` 与 `000020.SZ`
2. 再推进 `002663.SZ` 与 `000670.SZ`
3. 对这 4 个样本准备最小 MALF snapshot 与 front-filter 复核
4. 只有当结构资格也站住以后，才考虑补 reviewed relation evidence JSON

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
