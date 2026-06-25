# 立花义正 part4 交易谱 PM 标注 v0.1

## 定位

本文件根据 `Z:\market-life-cycle\立花义正交易法-part4` 的实战交易谱说明，补充 `lock_purpose / mother_position / add_on / reverse_probe` 人工标注。

结构化标注文件见 `data/pioneer-1975-1976/annotations/part4-pm-annotations-v0.1.json`。本文件解释这些标注为什么存在，避免把双侧库存、锁单和加码误读成普通买卖信号。

## 新增硬规则

part4 确认了一条会影响资金口径的事实：PIONEER 自 `1976-09-21` 起交易单位改为 `100股`。因此：

| 项 | v0.1 处理 |
|---|---|
| 回测金额层 | 继续用 `point_unit = 成交价点数 × 记录单位`。 |
| 真实股数层 | 必须后续按日期建立交易单位表。 |
| 禁止项 | 不得把 1975-1976 全样本统一乘 `1000`。 |
| 不受影响 | 胜率、盈亏比、Profit Factor、夏普率等比率指标不因股数乘数变化而改变。 |

## 锁单目的重标注

part4 对锁单的说明比昨天的量化报告更细：锁单不等于利润保护，也不等于自动反手。尤其 1976 年 4-5 月附近，立花明确说锁单具有测试单性质，用于保护和维持母单，让自己能继续持有核心部位。

因此 PM 层仍保持：

```text
gross_long > 0 && gross_short > 0 => lock_candidate
```

但解释层必须另加人工字段：

```text
lock_purpose = reverse_probe / mother_position_protection / profit_lock / reversal_bridge / failure_repair / spread_like / unknown
```

## 重点交易段

| ID | part4 解释 | 本轮标注 |
|---|---|---|
| `S001` | 1975 年主训练段，不是干净单向交易。1-3 月有犹豫、反向测试和母单建立失败；5-6 月母单从 `—10` 扩到 `—40`，5/15-6/6 的小交易被书中说明为测试单，且与母单无直接关联。 | `mother_position=long`，`lock_purpose=reverse_probe/mother_position_protection/failure_repair`，`add_on=long`，保留 `mixed_inventory_must_not_be_netted`。 |
| `S004` | 1975 年 10 月的 `—2 / —2 / —2` 被书中评价为不佳锁单，不能解释成正常利润保护。 | `lock_purpose=failure_repair`，`risk_tags=bad_lock_habit/low_execution_quality`。 |
| `S005` | 1975 年 11-12 月接近他自己的标准分批：`—2 -> —5 -> —10 -> —15 -> —20 -> 2—20 -> —20 -> 0`。 | `mother_position=long candidate`，`lock_purpose=reverse_probe/mother_position_protection`。 |
| `S008` | 1976 年 4-5 月的双侧库存，书中明确排除“降低均价、确保获利、反手铺路”，强调是测试单性质的反向锁单，用来保护母单。 | `lock_purpose=reverse_probe/mother_position_protection`，`mother_position=long`。 |
| `S013` | 1976 年 10-11 月大赢交易；账面上 `—10 ... —102 -> 200—` 是很漂亮的多头清仓。但 part4 同时说明 9/21 后单位变小，10 月中旬至 11 月初买得过碎，是小单位实验。 | `unit_context=post_1976_09_21_100_share_unit_experiment`，`add_on=long`，`risk_tags=winner_but_not_clean_template/scale_alert`。 |
| `S015` | 1976 年 11-12 月空头大亏段，属于 100 股单位后的过频分批/实验失败样本。 | `mother_position=short candidate`，`add_on=short`，`risk_tags=over_frequent_averaging/large_loss/not_standard_template`。 |

## 对回测报告的影响

当前十五大交易报告可以保留为 `point_unit` 量化账本；但解释层必须降级为“交易谱回放统计”，不能宣称已经完整解释立花的全部意图。

下一轮如果要把这些标注接入代码，优先顺序是：

1. 在日级回放输出中加载 `part4-pm-annotations-v0.1.json`。
2. 给对应日期/交易段补 `lock_purpose`、`mother_position`、`reverse_probe`、`risk_tags`。
3. 单笔交易报告中并列显示“数值事实”和“书页解释”。
4. 资金层单独建立日期依赖的 `share_multiplier`，不要污染现有 `point_unit` 绩效。
