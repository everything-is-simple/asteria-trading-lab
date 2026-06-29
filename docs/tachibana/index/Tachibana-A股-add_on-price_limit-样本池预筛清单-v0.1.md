# Tachibana A股 add_on price_limit 样本池预筛清单 v0.1

> 研究日期：2026-06-29
> 研究范围：围绕 `2026-03-24` 至 `2026-04-03` 市场窗口，扩展 `add_on / pullback_add` 的真实近板样本池，优先寻找可能支持 `near_limit` 或 `at_limit` 的 planned-event 邻近样本

## 1. 目标与边界

本清单只做三件事：

1. 用真实本地日线数据预筛 `pullback_add / add_on` 邻近样本
2. 把候选按 `at_limit_candidate / near_limit_candidate` 分桶
3. 给最值得继续复核的样本补最小 review 表

本清单不做以下事情：

- 不宣称这些候选已经正式通过 `Q-PRESSURE-ADJUST`
- 不生成 MALF snapshot
- 不直接写 `method_action / pm_action / execution_event_type`
- 不把 price-limit 候选自动升级为规则定义、signal、仓位或 backtest 输入

因此，这里输出的是：

- **真实市场预筛候选**

而不是：

- `300750.SZ` 同等级别、已经完成 reviewed relation evidence 的正式样本

## 2. 当前筛法

本轮新增了只读预筛工具：

- [price_limit_sample_pool.py](/Z:/asteria-trading-lab/src/data_sources/tdx_local/price_limit_sample_pool.py)

对应测试：

- [test_tdx_local_price_limit_sample_pool.py](/Z:/asteria-trading-lab/tests/test_tdx_local_price_limit_sample_pool.py)

### 2.1 数据源

- `Z:\malf-data\market_base_day.duckdb`
- `Z:\malf-data\market_meta.duckdb`

### 2.2 基本过滤

只保留：

- `asset_type = stock`
- `timeframe = day`
- `tradability_status = tradable`
- 非 ST
- 非 ETF / LOF / 基金
- 非退市整理名称
- 非上市未满一年的新股

### 2.3 事件日启发式

当前预筛把“像 `pullback_add / pressure_adjust` 的邻近样本”粗略表达为：

- 前 6 个交易日存在一定 runup：
  - `runup_pct >= 12%`
- 前高相对最近均价仍有一定拉开：
  - `prior_peak_vs_recent_avg_pct >= 4%`
- 候选日收盘出现明显回撤：
  - `close_return_pct <= -2%`
- 候选日的最高价或最低价贴近当日涨跌停边界：
  - `nearest_limit_gap_pct <= 3%`

然后每只股票只保留：

- **离板边最近的一天**

再按：

1. `nearest_limit_gap_pct`
2. `runup_pct`
3. `abs(close_return_pct)`

做排序。

### 2.4 当前分桶

- `at_limit_candidate`：`nearest_limit_gap_pct <= 0.05`
- `near_limit_candidate`：`0.05 < nearest_limit_gap_pct <= 3.00`

这只是预筛桶，不等于正式 `price_limit_event_limit_proximity` 结论。

### 2.5 新增推进标记

本轮工具新增：

- `industry_window_overlap`
- `industry_window_status`

它们不改变 proximity 结论，只回答：

- 这个近板候选在当前真实数据里，是否具备窗口内可重叠行业标签
- 因而是否有资格继续进正式 `structure_candidate -> front_filter` 复核

## 3. 当前预筛结果总览

对真实窗口 `2026-03-24` 至 `2026-04-03` 跑预筛后，得到：

- 总候选数：`268`
- `at_limit_candidate`：`74`
- `near_limit_candidate`：`194`

边界侧分布：

- `near_limit_candidate + down_limit_side`：`186`
- `near_limit_candidate + up_limit_side`：`8`
- `at_limit_candidate + down_limit_side`：`71`
- `at_limit_candidate + up_limit_side`：`3`

行业标签推进状态分布：

- `near_limit_candidate + not_overlapping`：`194`
- `at_limit_candidate + not_overlapping`：`74`
- `overlapping`：`0`

当前最重要的观察不是“候选太少”，而是：

- **候选并不稀缺**
- 但它们高度集中在 `down_limit_side`
- 并且全部停在 `industry_window_status = not_overlapping`
- 且大部分只是“近跌停/到跌停的回撤日”，还没有被证明就是正式 `Q-PRESSURE-ADJUST / pullback_add / add_on`

换句话说：

- 现在的缺口已不再是“找不到真实近板样本”
- 而是两层同时存在：
  - 如何从这些真实近板回撤日里，继续收窄出更像 `pressure_adjust + add_on` 的正式扩样对象
  - 以及如何补齐时间对齐行业标签，让它们真正有资格进正式结构复核

## 4. `at_limit_candidate` 最小 review 表

| ts_code | 名称 | trade_date | nearest_limit_side | nearest_limit_gap_pct | runup_pct | close_return_pct | 最小 review 判断 | 下一步 |
|---|---|---|---|---:|---:|---:|---|---|
| `000020.SZ` | `深华发Ａ` | `2026-03-24` | `down_limit_side` | `0.00` | `78.82` | `-9.76` | 典型“高位回撤 + 跌停触边”候选，值得优先看是否属于旧段内压力调整而非纯失败下杀 | 补 MALF 窗口与 front-filter 复核 |
| `600310.SH` | `广西能源` | `2026-03-30` | `up_limit_side` | `0.00` | `51.38` | `-4.24` | 少见的 `up_limit_side` 触边样本，值得优先复核其是否更像“回撤后加回受上边界约束” | 重点复核是否可形成 `near/at upper limit` 对照 |
| `002310.SZ` | `东方新能` | `2026-03-26` | `down_limit_side` | `0.00` | `46.76` | `-8.16` | 回撤幅度大且触及下边界，具备 `at_limit` 研究价值，但也可能只是普通情绪杀跌 | 先核对窗口结构是否仍有库存调整语义 |
| `603016.SH` | `新宏泰` | `2026-04-03` | `down_limit_side` | `0.00` | `37.26` | `-10.00` | 到板边很明确，适合当 `at_limit` 极端例子看，但不一定像 `add_on` | 适合作为“到板边但可能不适合 add_on”的反向对照 |
| `603687.SH` | `大胜达` | `2026-03-27` | `down_limit_side` | `0.00` | `35.58` | `-5.27` | 回撤并未完全一字跌停，仍触到下边界，值得看其是否更接近压力调整 | 可进第二梯队复核 |

## 5. `near_limit_candidate` 最小 review 表

| ts_code | 名称 | trade_date | nearest_limit_side | nearest_limit_gap_pct | runup_pct | close_return_pct | 最小 review 判断 | 下一步 |
|---|---|---|---|---:|---:|---:|---|---|
| `002663.SZ` | `普邦股份` | `2026-04-03` | `down_limit_side` | `0.05` | `12.96` | `-8.22` | 离跌停只差 `0.05%`，是当前最贴边的 `near_limit` 候选之一 | 优先核对是否能形成 reviewed `near_limit` 样本 |
| `000670.SZ` | `盈方微` | `2026-04-02` | `down_limit_side` | `0.05` | `15.91` | `-9.72` | 接近下边界但未完全到板，具备 `near_limit` 研究吸引力 | 可与 `300750.SZ / not_near_limit` 做强对照 |
| `600758.SH` | `辽宁能源` | `2026-03-30` | `down_limit_side` | `0.06` | `53.41` | `-9.95` | runup 很强，且与跌停只差 `0.06%`，是很值得复核的高优先候选 | 建议进入第一批最小 review |
| `000899.SZ` | `赣能股份` | `2026-03-30` | `down_limit_side` | `0.06` | `20.17` | `-7.96` | 贴边程度高于多数候选，兼具一定前序推进 | 适合看是否更像“压力调整而非纯下杀” |
| `600249.SH` | `两面针` | `2026-04-03` | `down_limit_side` | `0.06` | `44.11` | `-9.94` | 具备较强前序 runup 与近板回撤，值得进入 `near_limit` 候选层 | 可与 `600758.SH` 做近板强弱对照 |

## 6. 当前最值得先复核的 shortlist

如果只挑一轮最小人工复核，我建议先看这 6 个：

1. `600310.SH / 广西能源 / 2026-03-30`
2. `000020.SZ / 深华发Ａ / 2026-03-24`
3. `600758.SH / 辽宁能源 / 2026-03-30`
4. `002663.SZ / 普邦股份 / 2026-04-03`
5. `000670.SZ / 盈方微 / 2026-04-02`
6. `000899.SZ / 赣能股份 / 2026-03-30`

原因是：

- `600310.SH` 提供了当前稀缺的 `up_limit_side` 对照
- `000020.SZ` 提供了最强 `at_limit` 极端例子之一
- `600758.SH / 002663.SZ / 000670.SZ / 000899.SZ` 提供了更像 `near_limit` 的第一梯队样本

这批组合比继续只盯 `300750.SZ` 更能回答：

- `not_near_limit`
- `near_limit`
- `at_limit`

三者是否真能在多样本上形成稳定可比面。

但本轮继续往正式结构复核推进时，也暴露了一个新的真实阻断：

- shortlist 中尝试先推进的 `600310.SH / 000020.SZ / 002663.SZ / 000670.SZ`
- 在当前 DuckDB 口径下都没有 `2026-03-24` 至 `2026-04-03` 窗口内可重叠的 `industry` 标签
- 它们的 `industry_block_relation.effective_from` 目前都从 `2026-04-23` 才开始

因此当前不能在不借用未来标签的前提下，直接把这些样本推进到正式 `structure_candidate -> front_filter` 复核。

更强一点地说：

- **在当前 `2026-03-24` 至 `2026-04-03` 的 `268` 个近板候选里，我们还没有找到一只“既近板，又满足窗口内行业标签重叠”的真实样本。**

本轮进一步尝试把窗口后移到 `industry` 标签开始生效之后，再筛“可推进样本”时，又暴露出第二层真实边界：

- `industry_block_relation.relation_type='industry'` 的 `effective_from`
  - 当前全部从 `2026-04-23` 开始
- `market_base_day.base_bar`
  - 当前最新 `trade_dt` 也只到 `2026-04-23`

因此我们现在没有“标签已生效之后的一段后续真实日线窗口”可用来继续筛选。

这意味着：

- 当前阻断已经不只是“现有近板候选窗口里无重叠标签”
- 而是 **本地数据本身还没有覆盖到“标签已生效后的后续观察区间”**

### 6.1 本地 TDX 行业快照补充核对

本轮继续额外核对了：

- `Z:\new_tdx64\T0002\hq_cache\tdxhy.cfg`
- `Z:\new_tdx64\T0002\hq_cache\tdxzs.cfg`
- `Z:\new_tdx64\T0002\hq_cache\tdxzs3.cfg`

结论是：

- `tdxhy.cfg` 确实能提供 `股票 -> TDX 行业代码` 的**当前快照**
- `tdxzs.cfg / tdxzs3.cfg` 能把这些代码翻译为行业名称
- 对 shortlist 里的 6 个样本，这组快照与 DuckDB 里从 `2026-04-23` 开始生效的 `industry_block_relation` 是一致的

对应关系如下：

| ts_code | TDX 当前行业代码 | TDX 当前行业名 | DuckDB 行业事实最早生效 |
|---|---|---|---|
| `600310.SH` | `T010201` | `水力发电` | `2026-04-23` |
| `000020.SZ` | `T1204` | `元器件` | `2026-04-23` |
| `002663.SZ` | `T110101` | `建筑工程` | `2026-04-23` |
| `000670.SZ` | `T1204` | `元器件` | `2026-04-23` |
| `600758.SH` | `T010101` | `煤炭开采` | `2026-04-23` |
| `000899.SZ` | `T010202` | `火力发电` | `2026-04-23` |

这说明：

- `TDX` 本地缓存**可以作为当前行业归属的 research-only 辅助来源**
- 但它**没有给出历史生效区间**
- 因此它还不能直接证明这些行业标签在 `2026-03-24 ~ 2026-04-03` 窗口里已经生效

也就是说，这条线现在能解决的是：

- “这些股票当前属于哪个行业”

但还解决不了：

- “这些行业归属在事件窗口当时是否已经成立”

所以它暂时只能作为：

- **research-only current snapshot fallback**

而不能直接替代正式 `industry_window_overlap` 的时间对齐证据。

## 6.2 shortlist 的 intraday 最小证据

本轮继续核对了 shortlist 对应的本地 `lc5` 文件：

- `Z:\new_tdx64\vipdoc\sz\fzline\sz000020.lc5`
- `Z:\new_tdx64\vipdoc\sh\fzline\sh600310.lc5`
- `Z:\new_tdx64\vipdoc\sh\fzline\sh600758.lc5`
- `Z:\new_tdx64\vipdoc\sz\fzline\sz002663.lc5`
- `Z:\new_tdx64\vipdoc\sz\fzline\sz000670.lc5`
- `Z:\new_tdx64\vipdoc\sz\fzline\sz000899.lc5`

并对事件日整日 5 分钟区间做了最小核对。结果如下：

| ts_code | trade_date | intraday_high | intraday_low | limit_up_price | limit_down_price | nearest_intraday_side | nearest_intraday_gap_pct | 当前最小判断 |
|---|---|---:|---:|---:|---:|---|---:|---|
| `000020.SZ` | `2026-03-24` | `20.58` | `18.90` | `23.10` | `18.90` | `down_limit_side` | `0.0000%` | 已有整日 intraday 支撑，可作为 `at_limit` 候选 |
| `600310.SH` | `2026-03-30` | `7.26` | `6.18` | `7.26` | `5.94` | `up_limit_side` | `0.0000%` | 已有整日 intraday 支撑，可作为 `at_limit` 候选 |
| `002663.SZ` | `2026-04-03` | `2.20` | `1.97` | `2.409` | `1.971` | `down_limit_side` | `0.0507%` | 已有整日 intraday 支撑，可作为 `near_limit` 候选 |
| `000670.SZ` | `2026-04-02` | `8.55` | `7.78` | `9.504` | `7.776` | `down_limit_side` | `0.0514%` | 已有整日 intraday 支撑，可作为 `near_limit` 候选 |
| `600758.SH` | `2026-03-30` | `5.25` | `4.98` | `6.083` | `4.977` | `down_limit_side` | `0.0603%` | 已有整日 intraday 支撑，可作为 `near_limit` 候选 |
| `000899.SZ` | `2026-03-30` | `14.29` | `13.13` | `16.038` | `13.122` | `down_limit_side` | `0.0610%` | 已有整日 intraday 支撑，可作为 `near_limit` 候选 |

这里先强调边界：

- 这些结论仍然只是 **事件日整日 intraday proximity support**
- 还不是正式 `planned_event` 精确时点的 reviewed relation evidence

但和单纯日线预筛相比，它已经明显更强，因为：

- 我们确认了真实 `lc5` 文件存在
- 我们确认了事件日盘中区间确实触边或极贴边
- 因此这些样本已经不再只是“看起来像近板”，而是“整日 intraday 范围可以支持 near/at-limit 候选”

更聚焦的 6 样本 intraday review 见：

- [Tachibana-A股-add_on-price_limit-shortlist-intraday-review-v0.1.md](./Tachibana-A股-add_on-price_limit-shortlist-intraday-review-v0.1.md)

## 7. 当前结论

本轮最重要的推进有三点：

1. 我们已经不再只有 `300750.SZ / not_near_limit` 这一条单点样本
2. 我们已经拿到一批真实市场里的 `near_limit / at_limit` 预筛候选，并且有了可重跑的只读筛法
3. shortlist 中至少 6 个样本已经补到事件日整日 `lc5` 证据，足以支撑更正式的最小 review

但同时要明确：

- 这些仍然只是 **price-limit 邻近样本池**
- 不是已经确认的 `Q-PRESSURE-ADJUST / pullback_add / add_on`

因此当前最稳妥的说法是：

- **样本池扩展已经打开了**
- **正式样本认定还没有完成**

## 8. 下一步

下一拍最自然的推进就是：

1. 先对上面 6 个 shortlist 补最小窗口 review
2. 判断它们哪些真的像 `pressure_adjust / pullback_add`
3. 再为最像的 2 到 3 个样本准备 MALF snapshot 与 front-filter 复核
4. 只有通过这一步，才考虑补 reviewed relation evidence JSON

如果这一步顺利，我们就能把当前线从：

- `300750.SZ / not_near_limit`

推进到：

- `not_near_limit + near_limit + at_limit` 的多样本可比面
