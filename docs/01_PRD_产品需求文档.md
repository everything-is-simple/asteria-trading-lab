# 01_PRD — Asteria Trading Lab 产品需求文档

**版本**: v0.2  
**日期**: 2026-06-28  
**状态**: 研究与审计链路已通电，交易规则与回测执行层未启动

## 1. 产品定位

Asteria Trading Lab 是一个面向 A 股的研究型系统，用来把立花义正 1975-1976 交易方法，通过 MALF 结构语言重新表达，并在 A 股制度约束下做可复核的样本审计。

项目定位是：

- 研究
- 定义
- 审计
- 回测规格准备

它**不是**生产交易系统，也**不是**自动发出买卖信号的系统。

## 2. 核心目标

当前主目标不是“直接改出 A 股交易规则”，而是先回答：

1. 什么结构状态下，立花节奏值得讨论。
2. 哪些样本能从 MALF 前置过滤器进入 Method/PM。
3. 哪些 A 股制度约束需要进入后续研究，而不是提前写成交易策略。

## 3. 当前已完成

### 3.1 原始立花研究

- 1975-1976 共 24 个月原始资料数字化
- 月报、章节精读、术语表、映射总表
- Pioneer v0.1 原始回测与 15 笔交易段复盘

### 3.2 MALF 前置过滤器

- `tachibana_front_filter.py` 已落地
- 已形成 `meaningful / limited / not_meaningful / unknown` 结构资格语义
- 已建立 Method / PM / Data / Signal / Backtest 边界约束

### 3.3 A 股首批真实样本链路

- 首批 5 只真实样本接入包已建立
- 其中 3 只样本已推进到 Method/PM 与制度审计链路
- 制度事实包、执行可行性、候选约束、人工复核、归档、research prep 已打通

## 4. 当前进行中

- `execution_policy_research_prep` 已通过验证
- 当前批次状态已推进到 `action:prepare_execution_policy_research`
- 三道硬闸仍保持 `false`：
  - `institution_rule_definition_allowed`
  - `signal_generation_allowed`
  - `backtest_execution_allowed`

## 5. 暂未完成

- 正式 A 股规则定义：T+1、涨跌停、停复牌
- PAS 模块代码实现
- Signal 模块代码实现
- A 股适配版完整回测执行层

## 6. 成功标准

当前阶段成功，不以“找到可交易股票”为标准，而以以下条件为标准：

- 结构资格判定能在真实样本上复核
- 制度事实链路能只读推进
- 文档、代码、样本、CLI 状态一致
- 不混入 `buy_signal / trade_accept / target_position` 一类交易语义
