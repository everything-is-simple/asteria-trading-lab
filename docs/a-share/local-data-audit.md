# 本地 Tongdaxin / 离线数据审计

这份说明只覆盖本机已有资产的只读审计，不定义新的行情下载流程，也不把大文件复制进仓库。

## 只读边界

- `Z:\new_tdx64` 只用于确认 Tongdaxin 本地 Python / `tqcenter.py` 形态是否可用。
- `Z:\tdx_offline_Data` 只用于统计离线目录形状、文件类型和可映射字段。
- `Z:\malf-data` 只用于识别旧 DuckDB 资产，不做导出落盘。
- 真实 `.day`、`.txt`、`.duckdb`、`.7z` 文件不进入 git，不 stage，不 push。

## 优先级

1. 本地 Tongdaxin Python / `PYMP`
2. 离线 `stock-day` / `stock` / `raw`
3. 旧 DuckDB 资产

## 最小字段映射

主输出只有四类：

- `symbol_master`
- `trading_calendar`
- `daily_bars`
- `sector_membership`

辅助事实单独保留：

- `adjustment_metadata`

字段映射与上传边界的唯一事实来源集中在 `src/data_sources/tdx_local/manifest.py`，`audit.py` 和测试只引用这份清单，不再各自维护分叉口径。

## 运行方式

```powershell
$env:PYTHONPATH='src'; python -m data_sources.tdx_local.audit --tdx-root Z:\new_tdx64 --offline-root Z:\tdx_offline_Data --duckdb-root Z:\malf-data
```
