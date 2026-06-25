# 立花义正 1975-1976 最终来源校勘记录

## 本轮结论

本轮对以下四组来源做最终对齐：

- `Z:\market-life-cycle\2012.(Japan)【立花义正】\24 张交易谱-截图-pioneer-trade-1975-1976-source`
- `Z:\market-life-cycle\2012.(Japan)【立花义正】\1975-1976-24 张交易谱-截图`
- `Z:\market-life-cycle\2012.(Japan)【立花义正】\立花义正交易法-part1-3`
- `Z:\market-life-cycle\2012.(Japan)【立花义正】\立花义正交易法-part4`

截至本文件生成时，两个外部交易谱截图目录与仓库内 `data/pioneer-1975-1976/source-images/` 均为 24 张 JPG；逐张 SHA256 比对不一致数为 0。仓库中的 24 张月度交易谱图片可作为当前 JSON、月报、回测报告的同源图像底座。

本轮不再扩大读书范围，而是把已读出的关键规则冻结到系统口径。后续只在发现具体歧义时回查原页。

## 已冻结规则

| 主题 | 最终口径 |
|---|---|
| 交易记号 | `—N` 在买卖栏表示买入 N 记录单位；`N—` 表示卖出 N 记录单位。 |
| 未平仓记号 | 横杠左侧为 `gross_short`，横杠右侧为 `gross_long`；`10—2` 必须保存为空头 10 与多头 2，不能净成空头 8。 |
| 成交时点 | 前一日收盘后从报纸抄收盘价并作判断；若交易，则下一交易日开盘前电话下市价单；成交价为下一交易日开盘价，通常在再下一份报纸中回填。 |
| 同日收盘价 | 交易日同日收盘价只能用于成交后的记录和盯市，不能用来生成当日交易。 |
| 交易单位 | 1975 早期有 1000 股口径说明；part4 明确 PIONEER 自 1976-09-21 起交易单位改为 100 股。因此 v0.1 只列 `价格点 × 记录单位` 账本，不得全样本统一乘 1000。 |
| 锁单 | 双侧库存只自动生成 `lock_candidate`；`lock_purpose` 必须人工标注。 |
| 母单/中心单 | `mother_position`、`center_position` 不能仅凭库存数量自动确认，必须结合书页解释或人工标注。 |
| MALF | MALF 只提供 `wave / range / break / progress / probability` 结构背景，不管理仓位、心理、锁单和清仓。 |

## 本轮系统修订

| 文件/模块 | 修订方向 |
|---|---|
| `src/original_tachibana/major_trades.py` | 大交易报告加载 `part4-pm-annotations-v0.1.json`，在总报告和单笔报告中并列展示人工 PM 标注。 |
| `src/original_tachibana/quant_report.py` | 把量化报告的读法改成逐笔成交价、记录数量、库存和 PnL，避免把记录单位误写成固定股数。 |
| `src/original_tachibana/performance.py` | `unit_size` 改为 v0.1 点单位算术单位，不再写成真实一手定义。 |
| `docs/backtest-spec/original-tachibana-v0.1-major-trades-report.md` | 重生成后包含 Part4 PM 人工标注摘要。 |
| `docs/backtest-spec/original-tachibana-major-trades/Sxxx.md` | 重生成后每笔报告保留逐笔成交价，同时对 S001、S004、S005、S008、S013、S015 显示书页解释层。 |
| `README.md` 与 `research/sources/README.md` | 更新推荐阅读顺序与本地来源说明，把本文件作为 part1-3/part4 后的校勘入口。 |

## 仍保留人工边界

当前十五大交易报告是可靠的数值账本和交易谱回放，但不是对立花每一次心理、意图、母单目的的完全自动解释。

以下内容仍需人工校勘：

- 某个 `lock_candidate` 到底是反向测试、母单保护、利润锁定、反手过渡、失败补救还是类价差。
- 某个库存骨架是否已经构成 `mother_position` 或 `center_position`。
- 某次减仓是否应解释为利润保护、风险回收、节奏失败或普通退出。
- 清仓后的新方向是否是真正 `reversal_flip`，还是普通试探或重新建仓。
- 真实资金金额层必须先建立日期依赖交易单位表，再把 `point_unit` 换成股数金额。

## 下一步边界

本文件结束“书本记录交易回测”的 v0.1 校勘阶段。下一步若继续做系统，应优先二选一：

1. 原始立花法保持不动，做 A 股可用版本的交易单位、T+1、涨跌停、手续费和标的筛选适配。
2. 原始立花法保持不动，接 MALF 做结构背景判断，但 MALF 只输出背景，不接管 Position Management。
