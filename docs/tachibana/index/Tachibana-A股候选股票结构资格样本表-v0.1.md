# Tachibana A 股候选股票结构资格样本表 v0.1

## 版本定位

- 本文件承接 [MALF-立花结构资格样本表 v0.1](./MALF-立花结构资格样本表-v0.1.md)、[MALF-立花结构资格横向判读矩阵 v0.1](./MALF-立花结构资格横向判读矩阵-v0.1.md) 与 [Tachibana Backtest Input 适配层草案 v0.1](./Tachibana-Backtest-Input-适配层草案-v0.1.md)。
- 它是 A 股适配前的结构资格样本表，不是 A 股交易规则，不是选股公式，不是买卖信号。
- 本文件不定义 T+1、涨跌停、停牌、整手、融资融券或执行约束。
- 它只回答：A 股个股在什么数据与结构证据下，才值得进入 Tachibana Method / PM 讨论。
- 当前数据接入状态见 [Tachibana A 股候选股票数据接入审计 v0.1](./Tachibana-A股候选股票数据接入审计-v0.1.md)。
- 最小接入包字段契约见 [Tachibana A 股最小接入包字段契约 v0.1](./Tachibana-A股最小接入包字段契约-v0.1.md)。
- 当前最小接入包验收结果见 [Tachibana A 股最小接入包验收报告 v0.1](./Tachibana-A股最小接入包验收报告-v0.1.md)。
- 数据到位后的复核顺序见 [Tachibana A 股最小接入包复核流程 v0.1](./Tachibana-A股最小接入包复核流程-v0.1.md)。
- 单个候选窗口的判定底稿见 [Tachibana A 股结构资格判定记录模板 v0.1](./Tachibana-A股结构资格判定记录模板-v0.1.md)。
- 当前待填队列的阻断态判定记录见 [Tachibana A 股结构资格判定记录 ASHARE-PENDING v0.1](./Tachibana-A股结构资格判定记录-ASHARE-PENDING-v0.1.md)。
- 结构资格逐级升级检查见 [Tachibana A 股结构资格升级闸门检查清单 v0.1](./Tachibana-A股结构资格升级闸门检查清单-v0.1.md)。
- 结构资格理由码受控词表见 [Tachibana A 股结构资格理由码表 v0.1](./Tachibana-A股结构资格理由码表-v0.1.md)。
- `结构状态 -> 仓位节奏意义` 的中间裁决见 [MALF-立花结构状态到仓位节奏意义判定准则 v0.1](./MALF-立花结构状态到仓位节奏意义判定准则-v0.1.md)。

## 为什么需要这张表

A 股适配不能直接从“股票池”跳到“立花法可用”。必须先分清三层候选：

| 层级 | 含义 | 能否进入 Method / PM |
|---|---|---|
| `universe_candidate` | Data 层可识别的 A 股普通标的，具备基础元数据。 | 否。 |
| `structure_candidate` | 已具备可运行 MALF 的日线样本、行业标签和基本可复核窗口。 | 否。 |
| `tachibana_candidate` | MALF / 前置过滤器输出 `suitable` 或 `conditional`，且保留边界警告。 | 可以。 |

因此，本表的首要职责不是挑股票，而是防止以下误读：

- 行业清楚，不等于适合立花法。
- 流动性足够，不等于适合立花法。
- 波动大，不等于适合立花法。
- MALF 结构可讨论，不等于应该交易。

## 字段契约

### 1. Data 与 Universe 字段

| 字段 | 类型 | 必填 | 来源 | 含义 |
|---|---|---:|---|---|
| `ashare_sample_id` | string | 是 | 本表 | A 股结构资格样本编号。 |
| `ts_code` | string | 是 | Data | 股票代码。 |
| `symbol_name` | string | 是 | Data | 股票简称。 |
| `sample_window_start` | date | 是 | Data | 结构观察窗口起点。 |
| `sample_window_end` | date | 是 | Data | 结构观察窗口终点。 |
| `board_type` | enum | 是 | Data | `main / gem / star / bse / unknown`。 |
| `is_st` | boolean | 是 | Data | 是否 ST 或 *ST。 |
| `is_new_stock_window` | boolean | 是 | Data | 是否处于新股特殊窗口。 |
| `sw_l1_name` | string/null | 是 | 申万分类 | 申万一级行业。 |
| `sw_l2_name` | string/null | 否 | 申万分类 | 申万二级行业。 |
| `data_quality_status` | enum | 是 | Data | `ready / incomplete / source_missing / disputed`。 |

### 2. 结构资格字段

| 字段 | 类型 | 必填 | 来源 | 含义 |
|---|---|---:|---|---|
| `candidate_stage` | enum | 是 | 本表 | `universe_candidate / structure_candidate / tachibana_candidate / rejected / unknown`。 |
| `malf_snapshot_ref` | string/null | 条件必填 | MALF | A 股日线结构快照引用。没有快照时不得升为 `tachibana_candidate`。 |
| `malf_background` | enum/list | 条件必填 | MALF / 前置过滤器 | `alive_wave / pullback / range / break_birth / stagnation / transition / unknown`。 |
| `qualification_rule_id` | enum/null | 条件必填 | 横向矩阵 | 如 `Q-ALIVE-CLEAN`、`Q-LOCK-CANDIDATE`。 |
| `secondary_rule_ids` | list | 否 | 横向矩阵 | 复杂结构的辅规则。 |
| `rhythm_meaning` | enum | 条件必填 | 意义判定准则 | `meaningful / limited / not_meaningful / unknown`；先于 `tachibana_applicability`。 |
| `tachibana_applicability` | enum | 是 | 前置过滤器 | `suitable / conditional / unsuitable / unknown`。 |
| `applicability_reason` | string/list | 条件必填 | 前置过滤器 | 为什么值得或不值得进入 Method / PM。 |
| `boundary_warning` | list | 是 | 横向矩阵 | 防止越界解释。 |
| `evidence_level` | enum/list | 是 | 本表 / MALF | `E1_malf_snapshot / E2_ashare_daily_fact / E3_industry_classification / E4_research_mapping`。 |

### 3. 禁止提前写入的字段

| 禁止字段 | 原因 |
|---|---|
| `buy_signal` | 本表不是 Signal。 |
| `trade_accept` | 结构资格不是交易裁决。 |
| `target_position` | MALF 和候选池都不输出目标仓位。 |
| `ashare_t1_action` | 本表不处理 T+1。 |
| `limit_up_strategy / limit_down_strategy` | 本表不处理涨跌停执行规则。 |
| `industry_hot_score` | 行业热度不能替代结构资格。 |
| `tachibana_candidate_by_liquidity_only` | 流动性不能单独升级结构资格。 |

## 升级规则

| 升级 | 必要条件 | 不足时处理 |
|---|---|---|
| `universe_candidate -> structure_candidate` | `data_quality_status=ready`，行业标签可追溯，观察窗口日线数据完整。 | 保持 `universe_candidate` 或 `unknown`。 |
| `structure_candidate -> tachibana_candidate` | 有 `malf_snapshot_ref`，`rhythm_meaning=meaningful/limited`，且前置过滤器输出 `suitable / conditional`。 | 保持 `structure_candidate`。 |
| `tachibana_candidate -> Backtest Input` | 已有 `qualification_rule_id`、`boundary_warning`、`evidence_level`，且 Method / PM 可承接。 | 只保留研究记录。 |
| 任意阶段 -> `rejected` | 结构资格明确不适合，或资料质量无法修复。 | 记录原因，不进入 Method / PM。 |

### 更新前机器门禁

候选样本表不得直接吸收前置过滤器原始输出。进入本表前，必须先形成结构资格判定记录草案，并通过两个机器检查：

| 机器检查 | 通过条件 | 失败处理 |
|---|---|---|
| `record_consistency` | `result=pass`，底稿内部无阶段、适用性、理由码或禁止字段矛盾。 | 回到判定底稿修正，不更新样本表。 |
| `candidate_table_gate` | `result=pass`，且 `next_action=action:fill_candidate_table`。 | 保持 `structure_candidate / rejected / research_audit_only`，不得写成 `tachibana_candidate`。 |

`candidate_table_gate=pass` 不代表可以交易，只代表可以把结构资格汇总字段写入本表。`buy_signal / trade_accept / target_position / ashare_t1_action` 仍然禁止出现。

## 样本表 v0.1

当前仓库尚未纳入申万个股分类原始表，也未生成 A 股 MALF 快照；正式数据目录当前也没有可用文件。数据接入审计见 [Tachibana A 股候选股票数据接入审计 v0.1](./Tachibana-A股候选股票数据接入审计-v0.1.md)，字段验收口径见 [Tachibana A 股最小接入包字段契约 v0.1](./Tachibana-A股最小接入包字段契约-v0.1.md)，当前验收报告见 [Tachibana A 股最小接入包验收报告 v0.1](./Tachibana-A股最小接入包验收报告-v0.1.md)，阻断态底稿见 [Tachibana A 股结构资格判定记录 ASHARE-PENDING v0.1](./Tachibana-A股结构资格判定记录-ASHARE-PENDING-v0.1.md)。因此 v0.1 只建立待填样本队列，不编造个股结论。

| ashare_sample_id | ts_code | symbol_name | sample_window | board_type | sw_l1_name | candidate_stage | malf_snapshot_ref | tachibana_applicability | qualification_rule_id | boundary_warning | evidence_level | next_action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ASHARE-PENDING-001` | `TBD` | `TBD` | `TBD` | `unknown` | `null` | `universe_candidate` | `null` | `unknown` | `null` | `do_not_upgrade_without_malf_snapshot` | `E3_industry_classification_pending` | 导入申万个股分类与日线数据后再判。 |
| `ASHARE-PENDING-002` | `TBD` | `TBD` | `TBD` | `unknown` | `null` | `structure_candidate` | `null` | `unknown` | `null` | `do_not_treat_liquidity_as_structure` | `E2_ashare_daily_fact_pending` | 先跑 MALF 快照，不进入 Method / PM。 |
| `ASHARE-PENDING-003` | `TBD` | `TBD` | `TBD` | `unknown` | `null` | `unknown` | `null` | `unknown` | `null` | `do_not_mix_board_constraints_with_structure_qualification` | `source_missing` | 补齐 board、ST、新股窗口与行业标签。 |

## 与历史样本的映射

| A 股候选状态 | 可参考的历史资格样本 | 说明 |
|---|---|---|
| 干净有向推进 | `Q-ALIVE-CLEAN`：`1975-01`、`1975-04`、`1975-11`、`1976-10` | 可作为优先正样本，但 A 股标的必须先有 MALF 快照。 |
| 推进但 PM 复杂 | `Q-ALIVE-PM-MIXED`：`1975-06-A`、`1976-12-A/B` | 可进入 Tachibana，但需要 PM 承接中心单/加码。 |
| 震荡或无交易 | `Q-NO-TRADE`：`1975-08`、`1975-09`、`1976-12-C` | 不得仅凭无交易或低波动判为 range。 |
| 资料/制度扰动 | `Q-SOURCE-DISRUPTED`：`1976-09` | A 股停牌、除权、交易制度扰动应优先保持 `unknown`，但本表暂不定义制度规则。 |

## 当前结论

- A 股候选股票必须先经过 [Tachibana A 股结构资格升级闸门检查清单 v0.1](./Tachibana-A股结构资格升级闸门检查清单-v0.1.md) 的 `unknown -> universe_candidate -> structure_candidate -> tachibana_candidate` 逐级闸门。
- v0.1 不输出任何 A 股股票的 `suitable / conditional` 结论，因为当前缺少真实 A 股 MALF 快照和申万个股分类表。
- 行业、板块、流动性只提供 Data / Universe 事实，不能直接升级为立花适用资格。
- 只有 `tachibana_candidate` 才能进入 Method / PM 与 Backtest Input；`unknown` 与 `rejected` 只保留研究记录。

## 下一步

- 按 [Tachibana A 股最小接入包字段契约 v0.1](./Tachibana-A股最小接入包字段契约-v0.1.md) 导入一小批 A 股候选股票元数据、申万行业标签和日线窗口，并按 [Tachibana A 股最小接入包复核流程 v0.1](./Tachibana-A股最小接入包复核流程-v0.1.md) 更新 [Tachibana A 股最小接入包验收报告 v0.1](./Tachibana-A股最小接入包验收报告-v0.1.md) 的 `contract_check_result`。
- 对候选窗口跑 MALF 快照，生成 `malf_snapshot_ref`。
- 先按 [MALF-立花结构状态到仓位节奏意义判定准则 v0.1](./MALF-立花结构状态到仓位节奏意义判定准则-v0.1.md) 判定 `rhythm_meaning`，再按 [Tachibana A 股结构资格判定记录模板 v0.1](./Tachibana-A股结构资格判定记录模板-v0.1.md) 填写单窗口判定底稿，并用本表字段填入第一批真实 A 股结构资格样本。
- 在完成结构资格样本后，才进入 T+1、涨跌停、停牌等制度约束定义。
