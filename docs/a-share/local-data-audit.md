# A 股本地数据资产只读审计

本页记录 `MALF -> 立花法 -> A 股制度事实审计` 下一阶段的数据源边界。这里不是正式数据落盘方案，也不是交易规则定义。

## 本机资产

| 资产 | 路径 | 当前用途 |
|---|---|---|
| Tongdaxin 本地程序 | `Z:\new_tdx64` | 主线本地事实源；已看到 `vipdoc`、`PYPlugins\user\tqcenter.py`、本地 DLL 与通达信目录结构。 |
| Tongdaxin 离线数据 | `Z:\tdx_offline_Data` | 主线离线事实源；当前包含 `stock / stock-day / index / index-day / block / block-day / raw` 等目录。 |
| 旧 DuckDB 资产 | `Z:\malf-data` | 主线历史沉淀事实源；当前包含 `market_base_day.duckdb / market_base_week.duckdb / market_base_month.duckdb / market_meta.duckdb / raw_market.duckdb / data_control.duckdb`。 |

这些目录只允许只读审计。不得复制真实 `.day / .txt / .7z / .duckdb` 到仓库，也不得直接写入 `Z:\asteria-trading-labs-data`。

## 数据源优先级

| 层级 | 数据源 | 用途 |
|---|---|---|
| 主账本 | 本地 Tongdaxin + DuckDB | 作为 A 股样本事实、日线、板块、元数据的优先来源。 |
| 免费校验 | Baostock | 校验交易日、日线和基础 A 股事实。 |
| 研究补洞 | AkShare | 覆盖面广但稳定性不足，只用于研究补洞，不做主账本。 |
| 长期备选 | Tushare Pro | 可作为后续权限/积分充分时的公共数据层。 |

## 字段映射草案

| 输出 | 主来源 | 边界 |
|---|---|---|
| `symbol_master` | DuckDB `market_meta.instrument_master`；回退到 Tongdaxin/离线文件名 | 只记录标的身份、市场、名称、来源引用。 |
| `trading_calendar` | DuckDB `market_meta.trade_calendar`；回退到本地日线出现过的日期 | 只记录交易日事实，不解释制度规则。 |
| `daily_bars` | 离线日线、Tongdaxin `vipdoc`、DuckDB `market_base_day` | 只记录 OHLCV 与来源引用。 |
| `sector_membership` | DuckDB `market_meta.industry_block_relation`；无 DuckDB 时阻断 | 只记录板块/行业成员关系，不写选股结论。 |
| `adjustment_metadata` | 离线复权包、DuckDB 事件痕迹 | 辅助事实，不算首批主输出。 |

## 只读原型

`src/data_sources/tdx_local/` 提供 `audit_local_data_assets()`，只输出路径、文件摘要、字段映射和边界策略。

最小读取入口为：

| API | 输出 | 说明 |
|---|---|---|
| `read_symbol_master(tdx_root, offline_root, limit=None)` | `symbol_master` | 从 `.day` 和 `.txt` 文件名提取 `ts_code / market / source_ref`，缺少名称时 `symbol_name=None`。 |
| `read_trading_calendar(tdx_root, offline_root, limit_files=200)` | `trading_calendar` | 优先读取 DuckDB 交易日表，回退到本地日线文件抽取出现过的 `trade_date`。 |
| `read_daily_bars(offline_root, ts_code, adjustment="raw", limit=None)` | `daily_bars` | `raw` 读取通达信 32-byte `.day`；`non_adjusted / forward_adjusted / backward_adjusted` 读取对应文本日线。 |
| `read_sector_membership(offline_root, limit_files=200)` | `sector_membership` | 优先读取 DuckDB 成员关系；没有真实来源时返回 `blocked / sector_membership_source_missing`，不得把板块指数日线冒充成成分股。 |
| `inspect_duckdb_assets(duckdb_root)` | DuckDB 摘要 | 列出本地 `.duckdb` 的库、表、字段、行数估计，不抽大表明细。 |
| `probe_pytdx_reader(tdx_root)` | pytdx 能力探测 | 只探测 `TdxDailyBarReader / BlockReader` 和 `vipdoc` 定位能力，不批量读取历史数据。 |
| `build_minimal_read_report(tdx_root, offline_root, duckdb_root)` | 能力摘要 | 汇总四类主输出、DuckDB introspection、pytdx 探测和主账本顺序，不写正式数据目录。 |

该原型固定：

- `formal_data_write_allowed=false`
- `raw_market_file_export_allowed=false`
- `signal_generation_allowed=false`
- `backtest_execution_allowed=false`

它不解压、不复制、不安装 `duckdb / pytdx`，也不读取 DuckDB 内容。读取函数只按需解析少量本地日线文件，并且输出中不得出现 `buy_signal / trade_accept / target_position / ashare_t1_action / limit_up_strategy`。

当前主账本顺序固定为：

- `symbol_master=duckdb_first`
- `trading_calendar=duckdb_first`
- `sector_membership=duckdb_first`
- `daily_bars=file_first`

`pytdx.reader` 当前只作为交叉校验器，不替换现有 `.day/.txt` 解析底座。AkShare / Baostock / Tushare 仍保持在正式读取链路之外。
