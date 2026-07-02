# Price Limit Fact Enrichment Design

**Date:** 2026-06-28
**Status:** Draft for review
**Scope:** `institution_facts` 最小制度事实包中的 `price_limit` 字段补强

## 1. 背景

当前 `src/data_sources/tdx_local/institution_facts.py` 只把 `tradability_fact` 中的可交易性事实导出到最小制度事实包：

- `limit_up_price=""`
- `limit_down_price=""`
- `close_limit_status="unknown"`
- `touched_limit_status="unknown"`

这让 `execution_policy_candidates -> price_limit` 主题长期停留在“价格边界未知 + 触板状态未知”的混合缺口里。  
从当前链路看，真正阻碍研究准备入口收口的，不是“是否已经知道触板状态”，而是“连涨跌停价格边界都没有”。

因此，这个子项目只解决一个更小的问题：

> 在不污染制度审计边界的前提下，把 `limit_up_price / limit_down_price` 从长期留空提升为可审计的价格边界事实。

## 2. 目标

本次补强只追求以下结果：

1. `limit_up_price / limit_down_price` 在可推导时不再留空。
2. `close_limit_status / touched_limit_status` 继续保持显式事实优先，没有事实就维持 `unknown`。
3. 不引入交易许可、信号、仓位或规则定义语义。
4. 不改三道硬闸：
   - `institution_rule_definition_allowed = False`
   - `signal_generation_allowed = False`
   - `backtest_execution_allowed = False`

## 3. 采用口径

本设计采用工作假设方案 `2`：

- 允许根据 `board_type + is_st + is_new_stock_window + prev_close` 推导 `limit_up_price / limit_down_price`
- 不允许根据价格推断 `close_limit_status / touched_limit_status`
- `close_limit_status / touched_limit_status` 仍然只接受显式事实；没有显式事实就保持 `unknown`

## 4. 为什么不用其它方案

### 方案 1：只接受显式事实

优点：

- 边界最保守

缺点：

- 当前本地最小事实源里并没有可直接用的涨跌停价格字段
- `price_limit` 主题会继续长期停留在“价格边界未知”

### 方案 3：原始事实和推导事实都允许，并统一写入全部状态字段

优点：

- 字段更完整

缺点：

- 容易把“由规则推导出的价格边界”和“真实发生的触板/收板事实”混在一起
- 容易跨过制度审计边界，让 research prep 看起来像已经知道了更多事实

### 方案 2：半推导半显式

优点：

- 能补上研究准备最关键的价格边界
- 不伪造触板/收板事实
- 最符合当前“研究准备而非规则定义”的阶段目标

缺点：

- 需要文档里清楚标注：价格是推导事实，不是原始成交事实

## 5. 字段口径

### 允许补强的字段

- `limit_up_price`
- `limit_down_price`

它们在本次设计中属于：

- `board_rule_derived_fact`

也就是“依据 A 股公开板块制度 + 前收价得出的价格边界事实”。

### 保持显式事实优先的字段

- `close_limit_status`
- `touched_limit_status`

本次设计要求：

- 如果本地源没有显式状态，就维持 `unknown`
- 不允许根据 `high / low / close` 自动回推 `touched_up / touched_down / limit_up / limit_down`

原因：

- 这些状态看上去像简单判断，但实际上会牵涉停牌、撮合、收板、盘中触板但未封等更复杂的事实语义
- 这部分更适合作为后续单独研究主题，而不是在最小制度事实包里偷跑

## 6. 推导所需输入

本次设计预期使用以下输入：

- `prev_close`
- `board_type`
- `is_st`
- `is_new_stock_window`

其中：

- `board_type / is_st / is_new_stock_window` 已在 `src/data_sources/tdx_local/first_batch.py` 所产出的候选宇宙与样本接入链路中存在
- `prev_close` 需要在 `institution_facts` 构建时额外获得

## 7. 推导规则

在当前项目阶段，只采用最小可用规则：

- 主板：`+10% / -10%`
- 创业板：`+20% / -20%`
- 科创板：`+20% / -20%`
- 北交所：`+30% / -30%`
- ST：`+5% / -5%`

对于 `is_new_stock_window=true` 的样本：

- 本次设计不尝试完整覆盖所有“上市前若干日无涨跌停限制”的例外
- 在无法确认该窗口是否适用无涨跌停例外时，价格字段允许继续留空

也就是说，本次只补“可明确推导”的价格边界，不强行覆盖所有特殊板块例外。

## 8. 文件影响范围

### 需要修改

- `src/data_sources/tdx_local/institution_facts.py`
  - 增加价格边界推导逻辑
  - 增加最小来源标记或报告口径字段
- `tests/test_tdx_local_institution_facts.py`
  - 增加“可推导价格边界”的单测
  - 保留“状态字段仍为 unknown”的断言
- `src/README.md`
  - 更新 `institution_facts` 当前策略说明

### 当前不改

- `src/ashare_intake_validator.py`
- `tests/test_ashare_intake_validator.py`
- `execution_policy_*` 相关层的规则判断

原因：

- 这个子项目只补制度事实包，不直接修改后续审计层口径

## 9. 验证目标

完成后至少应能证明：

1. 最小制度事实包在可推导条件下输出非空的 `limit_up_price / limit_down_price`
2. `close_limit_status / touched_limit_status` 仍为 `unknown`
3. 缺失 `prev_close` 或特殊例外无法确认时，不强行生成错误价格
4. 现有只读、原子替换、禁用交易字段约束不被破坏

## 10. 不在本设计范围

- 不定义完整 A 股涨跌停规则引擎
- 不判断盘中是否真实触板
- 不判断收盘是否封板
- 不开放 `price_limit` 主题的最终规则定义
- 不把制度事实包升级为交易策略输入

## 11. 下一步

如果你认可这份设计，下一步就转为 implementation plan，目标拆成：

1. `institution_facts` 的最小推导逻辑
2. 对应单测红绿循环
3. README 口径同步
