# 首批真实样本窗口清单

本页记录首批真实 A 股样本窗口。它服务于：

- `Tongdaxin + DuckDB -> A 股最小接入包`
- `ready snapshot -> 前置过滤器 -> 判定底稿 -> 样本表试填`

它不是选股结论，也不是交易许可。

## 当前样本

| ts_code | symbol_name | sample_window_start | sample_window_end | 预期结构覆盖目标 | 选择理由 | 主要来源 |
|---|---|---|---|---|---|---|
| `000001.SZ` | `平安银行` | `2026-03-24` | `2026-04-03` | `meaningful` | 作为首批“相对干净推进”样本，验证真实窗口能否落到 `Q-ALIVE-CLEAN`。 | `Z:\tdx_offline_Data\raw\sz\lday\sz000001.day` + `Z:\malf-data\market_meta.duckdb` |
| `300750.SZ` | `宁德时代` | `2026-03-24` | `2026-04-03` | `limited` | 作为高波动回撤窗口，验证 `limited / conditional` 路径。 | `Z:\tdx_offline_Data\raw\sz\lday\sz300750.day` + `Z:\malf-data\market_meta.duckdb` |
| `600000.SH` | `浦发银行` | `2026-03-24` | `2026-04-03` | `limited` | 作为 `range_wait` 型有限样本，保留第二个 `limited` 对照。 | `Z:\tdx_offline_Data\raw\sh\lday\sh600000.day` + `Z:\malf-data\market_meta.duckdb` |
| `601127.SH` | `赛力斯` | `2026-03-24` | `2026-04-03` | `unknown` | 结构暂不下判，保留真实 `unknown` 覆盖，防止链路只收正样本。 | `Z:\tdx_offline_Data\raw\sh\lday\sh601127.day` + `Z:\malf-data\market_meta.duckdb` |
| `002714.SZ` | `牧原股份` | `2026-03-24` | `2026-04-03` | `not_meaningful` | 作为显式反例窗口，验证 `rejected / research_audit_only` 路径。 | `Z:\tdx_offline_Data\raw\sz\lday\sz002714.day` + `Z:\malf-data\market_meta.duckdb` |

## 当前边界

- 日线窗口来自真实本地 `.day` 文件。
- 元数据与行业标签来自真实本地 DuckDB。
- 当前 `malf-snapshots-v0.1/*.json` 是 **研究映射型 ready snapshot**：
  - 用于把真实样本窗口送入前置过滤器和样本表试填链路；
  - 不是自动 MALF 引擎计算结果；
  - 不生成 `buy_signal / trade_accept / target_position`。

## 当前已写入的正式数据目录

已写入 `Z:\asteria-trading-labs-data\ashare\`：

- `candidate-universe-v0.1.csv`
- `sw-industry-membership-v0.1.csv`
- `daily-window-v0.1/<ts_code>.csv`
- `malf-snapshots-v0.1/<ts_code>-2026-03.json`
- `first-batch-sample-manifest-v0.1.json`

## 已知缺口

- 当前行业标签取自 DuckDB `industry_block_relation` 的最新可用快照；其 `effective_from=2026-04-23` 晚于本轮窗口终点 `2026-04-03`。
- 因此，这批样本已经足够支撑“真实窗口 + 前置过滤器 + 样本表试填”的首轮链路，但 **还不等于完成独立的、时间对齐的申万口径接入**。
- 下一轮应补：
  - 独立时间对齐的行业标签源；
  - 自动 MALF snapshot 生成能力；
  - 再用同一批窗口回灌复核。
