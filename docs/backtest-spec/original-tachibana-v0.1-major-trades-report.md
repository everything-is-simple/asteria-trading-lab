# 原始立花法 v0.1 每一大笔交易回测报告

## 定义

本报告按用户定义的“一大笔交易”统计：从第一笔开仓/加码开始，经过未平仓库存累积，直到库存归零平仓为止。总表只做索引；逐笔查账见 `original-tachibana-major-trades/` 下 15 份单笔报告。

记号语义：`—5` 表示买入 5 记录单位并增加多头；`5—` 表示卖出 5 记录单位并增加空头或减少多头；未平仓横杠左侧为空头，右侧为多头。

单位说明：本报告按 `价格点 × 记录单位` 展开；part4 记录 PIONEER 自 1976-09-21 起交易单位改为 100 股，资金层不得全样本统一乘 1000。

## 总览

| 指标 | 数值 |
|---|---:|
| 大笔交易数 | 15 |
| 盈利大笔交易 | 10 |
| 亏损大笔交易 | 5 |
| 胜率 | 66.67% |
| 总 PnL | 80187 |
| Gross Profit | 85737 |
| Gross Loss | -5550 |
| Profit Factor | 15.45 |
| 最佳大笔交易 | S013 / 41140 |
| 最差大笔交易 | S015 / -2200 |

## 数据完整性检查

| 项目 | 数值 |
|---|---:|
| 月度 JSON | 24 |
| 日级记录 | 729 |
| 交易记录 | 159 |
| 交易行缺成交价 | 0 |
| 交易行缺未平仓 | 0 |

## 逐笔明细

| ID | 单笔报告 | 起始 | 结束 | 方向 | 最大多头 | 最大空头 | PnL | 结果 | 开单/加码序列 | 平仓序列 |
|---|---|---|---|---|---:|---:|---:|---|---|---|
| S001 | [明细](./original-tachibana-major-trades/S001.md) | 1975-01-04 | 1975-07-29 | short | 40 | 40 | 17007 | win | 10 — / 5 — / 5 — / 2 — / 1 — / 2 — / 3 — / — 2 / — 5 / 2 — / 3 — / 5 — / 5 — / 5 — / 5 — / — 20 / 10 — / 10 — / 2 — / — 3 / — 5 / — 2 / — 3 / — 3 / — 20 / 3 — / — 5 / 1 — / 1 — / — 1 / 2 — / 2 — / — 5 / — 5 / — 10 / — 5 / — 5 / 2 — / 15 — / 5 — / 23 — / 2 — / 5 — | — 2 / — 3 / — 3 / — 5 / — 20 / — 2 / 5 — / 10 — / — 1 / — 2 / — 2 / 15 — / — 2 / — 5 / — 5 / — 5 / — 10 |
| S002 | [明细](./original-tachibana-major-trades/S002.md) | 1975-09-05 | 1975-09-22 | long | 3 | 0 | 700 | win | — 1 / — 2 | 3 — |
| S003 | [明细](./original-tachibana-major-trades/S003.md) | 1975-09-29 | 1975-10-08 | long | 2 | 0 | 10 | win | — 1 / — 1 | 2— |
| S004 | [明细](./original-tachibana-major-trades/S004.md) | 1975-10-17 | 1975-10-31 | short | 6 | 6 | -150 | loss | 2— / 3— / 1— / —2 / —2 / —2 | 6—6 |
| S005 | [明细](./original-tachibana-major-trades/S005.md) | 1975-11-06 | 1975-12-25 | long | 20 | 2 | 11080 | win | — 2 / — 3 / — 5 / — 5 / — 5 / 2 — | — 2 / 20 — |
| S006 | [明细](./original-tachibana-major-trades/S006.md) | 1976-01-10 | 1976-01-29 | long | 5 | 0 | -700 | loss | — 1 / — 2 / — 2 | 5 — |
| S007 | [明细](./original-tachibana-major-trades/S007.md) | 1976-02-09 | 1976-03-24 | long | 12 | 0 | 5120 | win | — 2 / — 3 / — 5 / — 2 / — 3 / — 5 / — 2 | 5 — / 5 — / 2 — / 5 — / 5 — |
| S008 | [明细](./original-tachibana-major-trades/S008.md) | 1976-03-29 | 1976-05-21 | long | 20 | 10 | 7320 | win | — 2 / — 3 / — 5 / 2 — / — 2 / — 3 / — 5 / 10 — / 2 — / 5 — / 1 — / 5 — | 5 — / — 10 |
| S009 | [明细](./original-tachibana-major-trades/S009.md) | 1976-06-15 | 1976-07-02 | short | 0 | 10 | 2260 | win | 2 — / 3 — / 2 — / 3 — | — 10 |
| S010 | [明细](./original-tachibana-major-trades/S010.md) | 1976-07-13 | 1976-08-11 | short | 0 | 15 | -1810 | loss | 2 — / 3 — / 5 — / 2 — / 3 — | — 5 / — 10 |
| S011 | [明细](./original-tachibana-major-trades/S011.md) | 1976-08-16 | 1976-08-24 | long | 5 | 0 | -690 | loss | — 2 / — 3 | 5 — |
| S012 | [明细](./original-tachibana-major-trades/S012.md) | 1976-09-04 | 1976-09-13 | short | 0 | 2 | 400 | win | 2 — | — 2 |
| S013 | [明细](./original-tachibana-major-trades/S013.md) | 1976-10-08 | 1976-11-13 | long | 200 | 0 | 41140 | win | — 10 / — 2 / — 2 / — 2 / — 2 / — 2 / — 2 / — 2 / —2 / —2 / —20 / —50 / —102 | 200 — |
| S014 | [明细](./original-tachibana-major-trades/S014.md) | 1976-11-17 | 1976-11-18 | long | 5 | 0 | 700 | win | —5 | 5 — |
| S015 | [明细](./original-tachibana-major-trades/S015.md) | 1976-11-19 | 1976-12-24 | short | 5 | 150 | -2200 | loss | —5 / 10 — / 5 — / 5 — / 20 — / 5 — / 5 — / 5 — / 10 — / 20 — / 20 — / 50 — | —50 / —50 / —50 |

## 重点样本

S013 是 1976-10 到 1976-11 的大笔多头交易：`—10 / —2 / —2 / —2 / —2 / —2 / —2 / —2 / —2 / —2 / —2 / —20 / —50 / —102` 买入累积到多头 200 记录单位，随后 `200 —` 卖出清仓，PnL 约 +41140 点单位。详见单独报告。

## Part4 PM 人工标注摘要

| ID | 主解释 | 母单 | 锁单目的 | 加码 | 风险标签 |
|---|---|---|---|---|---|
| S001 | failed_short_to_long_mother_building_with_reverse_probes | side=long; status=confirmed_by_book_commentary; size_path=date=1975-05-01; gross_long=10, date=1975-05-30; gross_long=15, date=1975-05-31; gross_long=20, date=1975-06-09; gross_long=30, date=1975-06-11; gross_long=35, date=1975-06-13; gross_long=40 | reverse_probe, mother_position_protection, failure_repair | side=long; status=confirmed_by_book_commentary; note=Mother position was expanded from 10 to 40 units before the delayed full exit. | hesitation_on_1975_01_27, delayed_full_exit, mixed_inventory_must_not_be_netted |
| S004 | weak_october_failure_repair_lock_then_clear | side=unknown; status=not_confirmed | failure_repair | side=long; status=not_confirmed | bad_lock_habit, low_execution_quality |
| S005 | standard_staged_long_method_with_small_lock | side=long; status=candidate; size_path=raw=-2 -> -5 -> -10 -> -15 -> -20 | reverse_probe, mother_position_protection | side=long; status=confirmed_by_sequence | - |
| S008 | long_mother_position_protected_by_reverse_probe_lock | side=long; status=confirmed_by_book_commentary; comfortable_inventory_examples=2-20 | reverse_probe, mother_position_protection | side=long; status=candidate | lock_is_manual_purpose_not_numeric_fact |
| S013 | post_unit_change_experimental_long_scale_in | side=long; status=candidate | - | side=long; status=confirmed_by_sequence; note=Many small buys after the unit change culminate in a large one-shot clear at 200-. | post_unit_change, experimental_small_unit_averaging, scale_alert, winner_but_not_clean_template |
| S015 | post_unit_change_experimental_short_scale_in_with_large_loss | side=short; status=candidate | - | side=short; status=confirmed_by_sequence | post_unit_change, over_frequent_averaging, scale_alert, large_loss, not_standard_template |

这些标注来自 `data/pioneer-1975-1976/annotations/part4-pm-annotations-v0.1.json`，用于把书页解释并列放在数值账本旁边；机器仍只把双侧库存自动标为 `lock_candidate`，不自动确认锁单目的。

## 限制

- 本报告基于现有 JSON 重建。若后续逐图校对发现 `trade_raw`、`position_raw` 或价格字段抄录错误，需要重跑本报告。
- 双侧库存段先按库存事实归入同一大笔交易；锁单是否成立仍需人工校勘。
- 本报告不使用执行日同日收盘价生成交易，只用它做成交后的盯市。
