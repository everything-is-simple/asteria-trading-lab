# src 占位

本目录预留给后续实现：

- 月表解析器
- 仓位状态转移规则
- 原始立花法回测引擎
- A 股适配版回测引擎

## 当前原型

- `original_tachibana/pm_state.py`：原始立花法最小 PM 状态机原型。
- `original_tachibana/performance.py`：基于 PM 回放生成权益曲线和正规绩效指标。
- `original_tachibana/major_trades.py`：按“一大笔交易”生成逐笔回测报告。
- `original_tachibana/audit_source_data.py`：审计 24 个 JSON 与 24 张源图的对应关系和账面一致性。
- 输出目标：`data/pioneer-1975-1976/backtest-v0.1/`。
- 单笔报告目标：`docs/backtest-spec/original-tachibana-major-trades/S001.md` 至 `S015.md`。

运行：

```powershell
$env:PYTHONPATH='src'; python -m original_tachibana.pm_state
$env:PYTHONPATH='src'; python -m original_tachibana.performance
$env:PYTHONPATH='src'; python -m original_tachibana.major_trades
$env:PYTHONPATH='src'; python -m original_tachibana.audit_source_data
```
