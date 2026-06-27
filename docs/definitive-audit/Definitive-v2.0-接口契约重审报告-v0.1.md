# Definitive v2.0 接口契约重审报告（4 套定义合审）

**审计日期**: 2026-06-27
**审计方**: Claude (Opus 4.8) + 4 个 Explore 子代理并行审计
**审计对象**: `Z:\asteria-trading-labs-Definitive-validated\` 下 4 套 v2.0 Definitive 定义
**审计目的**: 回答原 handoff 的灵魂拷问 ——
> 作为通用定义的 Backtest / Data / Signal / System_Collaboration v2.0，能否在不修订定义的前提下支撑「立花义正波段交易法 + MALF 前置认知过滤器 + A 股制度审计层」这条新链路？

**配套不变量**（已在代码层固化）：
- 三层分工：MALF 只管结构事实 / Tachibana Method/PM 只管交易动作与仓位 / A 股适配只管制度约束
- 硬闸：`institution_rule_definition_allowed=False / signal_generation_allowed=False / backtest_execution_allowed=False`（见 `src/ashare_intake_validator.py:164-166`）

---

## 0. 结论摘要

| 文档集 | 文件数 | 结论 | 严重度 |
|---|---|---|---|
| **Signal Definitive v2.0** | 7 | **无需修订** | ✅ 干净 |
| **Data Definitive v2.0** | 6 | **无需修订**（4 个 P3/P4 可选文档澄清） | ✅ 干净 |
| **Backtest Definitive v2.0** | 7 | **需要轻微修订**（3 点文档级澄清，无架构改动） | 🟡 文档级 |
| **System_Collaboration v2.0** | 7 | **需要重大修订**（角色矩阵 + 协作规则 + 自检清单 + MANIFEST 共 12 处） | 🔴 定义层 |

**核心发现**：
1. 四套定义中**三套通用性良好**，可以原样支撑新链路
2. **唯一需要重大修订的是 System_Collaboration v2.0** —— 它的"模块角色矩阵"建立在 `MALF → PAS → Signal → Backtest` 的线性主链假设上，无法显式容纳「Front Filter + Tachibana Method/PM + A-Share Institution Audit」这三个新角色
3. **代码层硬闸超前于定义层**：`ashare_intake_validator.py` 已经实施了 6 条新硬闸，但其中 5 条在 System_Collaboration v2.0 的自检清单里**没有对应条目** —— 这意味着如果换一个开发者拿 v2.0 定义当上线 checklist，**抓不出**代码层已有的违规

---

## 1. Signal Definitive v2.0 —— 无需修订

### 1.1 核心契约（已锚定到 file:line）

| 契约项 | 锚定位置 | 内容 |
|---|---|---|
| Signal 是什么 | `Signal_00_Bridge:1-3` | 决策层（accept/reject/defer），系统中**唯一**拥有"该不该交易"裁决权的模块 |
| Signal lifecycle | `Signal_00_Bridge:34-51` | ProposedTrade → Gate → Lifespan(5 态) → Probability(4 视图审计) → Service(TradeDecisionSnapshot) |
| Gate 做什么 | `Signal_02_Gate:1-6, 56-90` | 5 必备规则 + 6 加分项做三态裁决；规则**只**用 CPS + WPS 公开字段 |
| 唯一对外契约 | `Signal_05_Service:1-6` | `TradeDecisionSnapshot` = ProposedTrade + DecisionResult + ProposalLifespan + Probability |
| 永禁输出 | `Signal_05_Service:107` | order_side / order_id / fill_price / position_size / pnl / win_rate / expected_return |

### 1.2 边界检查结果

**MALF → Signal 边界**：✅ 干净
- 输入严格基于 CPS（PAS）+ WPS（MALF）已发布快照；铁律 TC1-T1/T2 明确 **永禁** 回算波段/读 PriceBar OHLC
- entry 用 `cps.candidate.C`；stop 用 MALF `guard_price/boundary`；target 用 MALF `boundary_high_now/low_now`
- 无价格/动量/指标等结构外信号混入

**Signal → Method/PM 边界**：✅ 干净
- 立花法的"中心单 / 锁单 / 加码 / 认错"概念**零出现**在 Signal 7 份文件中
- Signal 输出是结构判断（decision + 理论参数），**不**预设执行动作
- ProposedTrade frozen dataclass **不**包含 position_size / fill_price / decision_accept 字段

**与 `signal_generation_allowed=False` 硬闸的兼容性**：✅ 完全兼容
- Signal v2.0 是被动管道，无自启动逻辑；输入源（CPS/WPS）被硬闸阻断时，Service 根本不会启动
- 立花前置过滤器的 `tachibana_applicability=meaningful` 可在外部调用层拦截，**无需**在 Signal 内部加 tachibana 感知逻辑

### 1.3 文档残留（不影响契约）

- `Signal_00_Bridge:17` 仍出现旧词 `executed`，但 `Signal_03_Lifespan:11-12` 已删除该态（属 v2.0.1 patch 残留）
- `Signal_04_Probability:60` 同样残留 `executed` 旧词
- **不影响接口契约**，可在下一版顺手清理

---

## 2. Data Definitive v2.0 —— 无需修订

### 2.1 核心契约（已锚定）

| 契约项 | 锚定位置 |
|---|---|
| 唯一对外接口 | `Data_00_Bridge:95` —— PriceBarService 是 Data 层唯一对外数据接口 |
| 信息单向流 | `Data_00_Bridge:52-67` —— Data 是源头，永不读 malf_pas/backtest；Signal 永不读 PriceBar |
| 存储三阶段 | `Data_00_Bridge:73-80` —— Stage1 SQLite WAL → Stage2 DuckDB 单文件 → Stage3 DuckDB+实体化表 |
| symbol 规范 | `Data_01_Ingest:162-176` —— `SH#600000` → `600000.SH`（CODE.EXCHANGE） |
| price_bar 主键 | `Data_02_Storage:16-31` —— `(symbol, bar_dt, price_line)` |

### 2.2 关键核查结果

**数据源耦合**：✅ 零硬编码 Tushare
- 全文搜索 6 份文档无 `tushare / ts_code / pro_api` 引用
- Ingest 绑定 TDX 离线是**正当的**（它本来就是 TDX 适配器），且路径可配置

**符号格式兼容**：✅
- v2.0 统一用 `CODE.EXCHANGE`（如 `600000.SH`）
- 我们 `readers.py` 实际产出的 `ts_code` 值就是这个格式 —— 两者无冲突

**DuckDB 三层 vs v2.0 概念对齐**：✅ 主要表 1:1 映射
- `instrument_master` ↔ `Data_02_Storage:instrument` + `Data_04_Universe:InstrumentRecord`
- `trade_calendar` ↔ `Data_02_Storage:trade_calendar`
- `base_bar` ↔ `Data_03_PriceBarService:PriceBar`

**两个概念缺口（设计本应如此）**：
- `industry_block_relation`：v2.0 Universe 只管 `board`（交易规则板块），不管行业归属 —— **行业归属归 A 股适配层或独立 dimension 表，不属于 Data 核心契约** ✅
- `tradability_fact`（19.2M 行）：v2.0 把制度判定归 Backtest/外部 ✅ —— 这与本审计 `docs/data/本地数据资产接入审计-v0.1.md` §2.7 的"A 股制度审计层天然底座"定位**完全一致**

### 2.3 可选文档增强（P3/P4，非必须）

| 文件 | 增强建议 |
|---|---|
| `Data_02_Storage:149-161` (ST-LEGACY) | 可补一句：`tradability_fact` 虽在 `market_meta.duckdb` 中，但属 A 股适配层，Data 层不为其提供服务接口 |
| `Data_01_Ingest:196-202` | 可注释 `params_default.toml` 路径可由环境变量/settings 覆盖 |
| `Data_04_Universe` 全文 | 可声明"行业归属(industry/sector)不在 Universe 职责范围" |
| MANIFEST | 可在 H:\Malf-Pas-data 复用表格中注明 `market_meta.duckdb` 包含 `tradability_fact` 但归 A 股适配层 |

---

## 3. Backtest Definitive v2.0 —— 需要轻微修订

### 3.1 核心契约（已锚定）

| 契约项 | 锚定位置 |
|---|---|
| 唯一输入 | `Backtest_00_Bridge:28-29` —— `TDS(decision=accept)` 是 Backtest 的唯一外部输入 |
| 唯一输出 | `Backtest_00_Bridge:35` —— `BacktestRunSnapshot` (BRS) |
| 永禁写回 | `Backtest_00_Bridge:59-63` —— 永禁写回 Signal/PAS/MALF |
| AShareFillModel 可插拔 | `Backtest_02_TradeExecution:6` —— A 股撮合规则封装，不硬编码 |
| 涨跌停判定 | `Backtest_02_TradeExecution:20` —— 必须用 `raw_none` |

### 3.2 关键核查结果

**执行语义污染**：低
- 没有"中心单 / 锁单 / 认错"语义
- "加码"轻微存在（`Backtest_03_PositionLifecycle:78` 多次 BUY 路径），但属会计层面的多次成交处理，**不**决定"何时加码"——加码触发权在上游 TDS ✅

**承接 MALF 结构事实的口径**：⚠️ **关键发现**
- Backtest 不直接消费 MALF 结构事实（wave / background / rhythm）
- 而是通过 TDS 的**溯源字段**间接引用：`architecture, bar_pattern, trade_direction, chain_consistency, decision_accept_share_rank, addons_hit`
- 即 Backtest 的输入口径是"信号已生成 + 已通过 accept 裁决后的快照"，**不是**"结构事实型"
- 这与三层分工**完全一致** —— Backtest 不应该也不需要知道 MALF 结构事实本身 ✅

**与 `backtest_execution_allowed=False` 硬闸的兼容性**：✅ 完全兼容
- v2.0 假设 TDS 已经 ready，不关心 TDS 是如何被 authorize 的
- 这不是冲突，而是**接口间隙** —— 项目需要在 validator 和 BacktestService 之间添加一个 authorization gate（将 `backtest_execution_allowed` 从 False 翻转为 True 并产出 TDS）

### 3.3 修订点位（3 处文档澄清）

| # | 文件:位置 | 修订建议 |
|---|---|---|
| 1 | `Backtest_00_Bridge:28-29` | 追加「输入来源说明」：TDS 是上游裁决链路的最终产物，当前支持两条链路：(a) 旧 Signal 链路 (b) 立花法 + MALF 前置过滤器链路。两者产出的 TDS 遵循相同 schema |
| 2 | `Backtest_03_PositionLifecycle:55-56, 110-118` | `target1_price / target2_price` 改为显式 Optional 说明：「立花法链路 TDS 可不提供 target 价格，target1_triggered 永不触发，不影响状态机运行」 |
| 3 | `Backtest_05_Service:200-202` | 接口前置条件注释：「`tds_list` 中每个 TDS 必须已通过上游 authorization gate（`backtest_execution_allowed=True`）；BacktestService 不做二次 authorization 检查」 |

---

## 4. System_Collaboration v2.0 —— 需要重大修订（核心发现）

### 4.1 核心契约（已锚定）

| 契约项 | 锚定位置 |
|---|---|
| 主链单向 | `00_Bridge:86-93` (mermaid) —— `data → MALF → PAS → Signal → Backtest`；regime 旁支 |
| 模块独占职责矩阵 | `01_Module_Roles:9-32` —— 33 行事项 × 唯一 owner |
| 5 责任分配原则 | `01_Module_Roles:82-88` |
| Snapshot 唯一协同形式 | `02_Collaboration_Rules:10-29` |
| 5 条信息流铁律 F-1~F-5 | `02_Collaboration_Rules:44-49` |
| 同 bar_dt 事件顺序 | `02_Collaboration_Rules:100-115` |
| 5 条概率铁律 PR-1~PR-5 | `03_Probability_Discipline:10-17` |
| PR-4 决策权独占 Signal | `03_Probability_Discipline:91-93` |
| 7 问上线自检 | `05_Conflict_Self_Check:10-19` |
| 系统铁律 | `MANIFEST:47-57` |
| 覆盖模块声明 | `MANIFEST:58-62` |

### 4.2 角色覆盖检查（**核心问题**）

| v2.0 已有角色 | 对应新三层 | 覆盖情况 |
|---|---|---|
| MALF (2.2) | MALF 前置认知过滤器 | **部分覆盖** —— v2.0 MALF 职责定义为"把价格序列构造成概率位姿"，但**从未**定义"前置过滤器"语义。`tachibana_front_filter` 是 MALF Snapshot 之上的新消费者，v2.0 角色表里**无对应条目** |
| Signal (2.4, 待建) | Tachibana Method/PM | **语义错位** —— v2.0 Signal 是 accept/reject/defer 裁决层；Tachibana Method/PM 是 front_filter pass 之后、独立于 PAS 的人工动作规划层，输出 `method_action / pm_action / execution_intent`，**不等价**于 v2.0 Signal 的 ProposedTrade |
| Backtest (2.6) | A 股制度适配层 | **部分覆盖** —— v2.0 将"A 股交易规则（涨跌停/T+1/停牌）"归 Backtest 独占（`01_Module_Roles:30`），但项目实际把 A 股制度适配层做成了**独立的前置审计层**（`ashare_intake_validator` + `institution-facts`），在 Signal/Backtest 之前执行 |

**v2.0 模块角色矩阵缺失 3 个角色**：
- `Front Filter`（MALF Snapshot 的第一消费者，认知资格过滤）
- `Tachibana Method/PM Adapter`（独立于 PAS/Signal 的立花法动作规划层）
- `A-Share Institution Audit Layer`（在 Backtest 之前的制度约束审计层）

### 4.3 协作规则容纳度

| 规则条文 | 容纳度 |
|---|---|
| F-1 (下游不写回上游) | ✅ 容纳 |
| F-2 (下游不重算上游) | ✅ 容纳 |
| PR-5 (概率不入决策) | ⚠️ 灰区 —— front_filter 的 `tachibana_applicability` 是"资格判定"，但 v2.0 未覆盖此层级 |
| 02 主链单向（`MALF→PAS→Signal→Backtest`） | ⚠️ 不完全容纳 —— front_filter 插在 `MALF→PAS` 之间，v2.0 主链图无此路径 |
| PR-4 (决策权独占 Signal) | ⚠️ 紧张 —— `eligible_for_tachibana_candidate=False` 是前置资格否决，v2.0 未明确这一决策层级 |

### 4.4 自检规则覆盖（**最严重缺口**）

`ashare_intake_validator.py` 的 6 条硬闸与 v2.0 自检体系的对应关系：

| 硬闸 | 代码位置 | 对应 v2.0 自检条目 |
|---|---|---|
| `institution_rule_definition_allowed=False` | `:164` | ❌ **无对应** —— v2.0 从未定义"制度规则定义权"维度 |
| `signal_generation_allowed=False` | `:165` | ⚠️ 部分对应 PR-4/PR-5，但 PR-4 说的是"概率不入决策"，未覆盖"谁允许触发 Signal 生成" |
| `backtest_execution_allowed=False` | `:166` | ❌ **无对应** —— v2.0 假设 Backtest 在 TDS 到达后自然执行，无前置闸门概念 |
| `malf_action_backflow_allowed=False` | `:371, 529, 555` | ✅ 对应 F-1，但语义更窄 |
| `method_pm_auto_generation_allowed=False` | `:371, 528, 554` | ❌ **无对应** —— v2.0 没有 Method/PM 层 |
| `candidate_table_update_allowed=False` | `:386 等多处` | ❌ **无对应** —— v2.0 假设 PAS candidate 状态自动推进 |

**结论**：6 条硬闸中只有 1 条能在 v2.0 自检框架找到上游依据。**代码层超前于定义层**。

### 4.5 修订点位（12 处）

| # | 文件:位置 | 修订建议 |
|---|---|---|
| 1 | `01_Module_Roles:9-32` | 独占职责矩阵新增 3 行：Front Filter / Tachibana Method-PM / A-Share Institution Audit |
| 2 | `01_Module_Roles:39-76` | 新增 2.9 Front Filter / 2.10 Method-PM / 2.11 Institution Audit 三节简介 |
| 3 | `02_Collaboration_Rules:36-39` | 主链修订为 `data → MALF → [Front Filter] → PAS → [Method/PM] → Signal → [Institution Audit] → Backtest` |
| 4 | `02_Collaboration_Rules:100-115` | 新增 Front Filter / Method-PM / Institution Audit 在事件链中的执行时点 |
| 5 | `03_Probability_Discipline:91-93` | 补充"资格否决"与"交易决策"的语义区分 |
| 6 | `03_Probability_Discipline:153-168` | 统一 reason_codes 表登记：`front_filter_blocked / method_pm_not_ready / institution_constraint_blocked / execution_feasibility_not_evaluated` |
| 7 | `04_Four_Behavior_Pattern:23-31` | 模块四行为对照表新增 3 行 |
| 8 | `04_Four_Behavior_Pattern:38-45` | 构造行为约束补充："构造行为不得包含执行语义字段" |
| 9 | `05_Conflict_Self_Check:10-19` | 7 问新增 Q8："我是不是把执行语义泄漏到了结构定义层？" |
| 10 | `05_Conflict_Self_Check:99-110` | 新增零容忍单测：MALF/PAS 输出含 `method_action` → schema fail；Front Filter 输出 `signal_generation_allowed=True` → validator fail |
| 11 | `MANIFEST:47-57` | 新增 F-6/F-7 系统铁律 |
| 12 | `MANIFEST:58-62` | 更新 covers_modules 声明 |

---

## 5. 总体建议（路线图）

### 5.1 立即可做（本 PR 不动）

- ✅ Signal / Data v2.0 保持原样
- ✅ Backtest v2.0 3 处文档澄清归入下一轮文档维护
- ⏳ System_Collaboration v2.0 需要单独一个 PR 做重大修订（不在当前 `codex/malf-tachibana-front-filter` PR 范围）

### 5.2 关键判断

**当前主线"MALF 作为立花法前置认知过滤器"的代码层落地是干净的**：
- Signal / Data / Backtest 三套 v2.0 通用定义都能容纳新链路
- 代码层硬闸（`ashare_intake_validator.py`）行为正确

**但定义层（System_Collaboration v2.0）已经落后于代码层**：
- 6 条硬闸只有 1 条能在 v2.0 自检框架找到对应
- 如果后续有人拿 v2.0 v2.0 当上线 checklist，**抓不出**当前代码层已经在执行的违规防护
- **这是一个文档债，不阻断当前主线，但建议在 v2.1 修订**

### 5.3 不做的事

- ❌ 本审计**不**修改任何 Definitive v2.0 文件 —— 修订需要单独评审流程，按你之前定的 "validated 目录是只读权威定义" 规则
- ❌ 不在当前 `codex/malf-tachibana-front-filter` PR 里塞 System_Collaboration v2.1 草案
- ❌ 不据此回过头去改 `ashare_intake_validator.py` 的硬闸 —— 它的方向是对的

---

## 6. 审计方法学（可复核）

本审计采用 4 个 Explore 子代理并行执行：
- Agent A: System_Collaboration v2.0（7 文件，结论：重大修订）
- Agent B: Backtest_Definitive v2.0（7 文件，结论：轻微修订）
- Agent C: Data_Definitive v2.0（6 文件，结论：无需修订）
- Agent D: Signal_Definitive v2.0（7 文件，结论：无需修订）

每个 Agent 独立读全部文件、独立给结论，不知道其他 Agent 的结果。报告由主代理汇总并现场抽检了关键引用（如 `ashare_intake_validator.py:164-166` 硬闸字段位置、`MANIFEST:58-62` covers_modules）。

---

**签字**: Claude (Opus 4.8) @ 2026-06-27
**配套验证**: 129 tests OK；本审计不改任何代码、不动 Definitive v2.0 原始定义文件
**下一步建议**: 进入第 3 优先剩余项 —— 用真实样本批量填实 `ASHARE-PENDING` 判定记录
