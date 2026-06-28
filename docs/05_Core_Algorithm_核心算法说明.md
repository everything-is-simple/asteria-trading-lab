# 05_Core_Algorithm — 核心算法说明

**版本**: v0.2  
**日期**: 2026-06-28

## 1. 已实现的核心算法

### 1.1 Pioneer 原始回测算法

位于 `src/original_tachibana/`，已实现：

- `Inventory` / `EngineState` 仓位状态机
- 单笔交易段回放
- 权益曲线与绩效统计
- 大交易报告与量化报告

### 1.2 前置认知过滤器算法

位于 `src/tachibana_front_filter.py`，已实现：

- 结构资格分类：
  - `meaningful`
  - `limited`
  - `not_meaningful`
  - `unknown`
- `rhythm_meaning -> tachibana_applicability` 映射
- `candidate_table_gate`
- Method / PM / Data / Signal / Backtest 边界校验

### 1.3 本地数据读取算法

位于 `src/data_sources/tdx_local/`，已实现：

- Tongdaxin `.day` 32-byte 记录解析
- `.txt` 日线读取
- DuckDB 只读探测与映射
- 首批样本接入包构建
- 最小制度事实包构建

## 2. 当前制度审计算法

位于 `src/ashare_intake_validator.py`，当前已打通：

- execution feasibility verdict
- verdict merge
- outcomes
- execution policy candidates
- review merge
- archive
- research prep

这些算法当前只表达“执行事实状态”，不表达交易许可。

## 3. 当前算法边界

系统明确禁止输出：

- `buy_signal`
- `sell_signal`
- `trade_accept`
- `target_position`
- `position_size`
- `ashare_t1_action`
- `limit_up_strategy`
- `limit_down_strategy`

## 4. 当前仍是定义态的算法

以下内容目前仍以 Definitive 文档为主，代码未完整实现：

- MALF 完整状态机引擎
- Signal
- A 股完整回测执行器

因此本文件不应把这些部分写成“已实现算法”，只能写成“后续算法目标”。

同时补充当前项目口径：

- `PAS` 在本项目中已明确搁置，不作为后续算法目标排期。
- 后续“算法缺口”与“工程进度”判断，应围绕 Method/PM、制度审计链路和 A 股规则研究展开，而不是围绕 `PAS` 展开。

## 5. 当前最重要的算法缺口

不是“买卖公式”，而是：

- `price_limit` 证据补全
- `prepare_execution_policy_research` 研究入口整理
- 更多真实样本下的结构资格稳定性验证
