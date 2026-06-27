# Tachibana A 股结构资格判定记录模板 v0.1

## 版本定位

- 本文件承接 [Tachibana A 股候选股票结构资格样本表 v0.1](./Tachibana-A股候选股票结构资格样本表-v0.1.md)、[Tachibana A 股最小接入包复核流程 v0.1](./Tachibana-A股最小接入包复核流程-v0.1.md) 与 [MALF-立花结构资格横向判读矩阵 v0.1](./MALF-立花结构资格横向判读矩阵-v0.1.md)。
- 它是 A 股候选样本表每一行背后的判定底稿模板，不是新的选股公式，不是交易信号，不是 A 股制度规则。
- 它只回答：某只 A 股在某个日线观察窗口内，凭什么停在 `universe_candidate / structure_candidate / tachibana_candidate / rejected / unknown`。
- 本文件不定义 T+1、涨跌停、停牌、整手、融资融券或任何执行约束。
- 当前无数据状态下的阻断态样例见 [Tachibana A 股结构资格判定记录 ASHARE-PENDING v0.1](./Tachibana-A股结构资格判定记录-ASHARE-PENDING-v0.1.md)。
- 结构资格逐级升级检查见 [Tachibana A 股结构资格升级闸门检查清单 v0.1](./Tachibana-A股结构资格升级闸门检查清单-v0.1.md)。
- 结构资格理由码受控词表见 [Tachibana A 股结构资格理由码表 v0.1](./Tachibana-A股结构资格理由码表-v0.1.md)。
- `rhythm_meaning` 的判定准则见 [MALF-立花结构状态到仓位节奏意义判定准则 v0.1](./MALF-立花结构状态到仓位节奏意义判定准则-v0.1.md)。

## 使用时机

每当一个 A 股候选窗口完成最小接入包复核后，应先填写本记录，再决定是否更新 [Tachibana A 股候选股票结构资格样本表 v0.1](./Tachibana-A股候选股票结构资格样本表-v0.1.md)。

| 前置状态 | 是否填写本记录 | 说明 |
|---|---|---|
| `contract_check_result=fail` | 可填写阻断记录。 | 记录缺什么，但不生成真实结构资格。 |
| `contract_check_result=warn` | 必须填写。 | 记录警告项与是否阻断 MALF。 |
| `contract_check_result=pass` | 必须填写。 | 作为进入 MALF 快照与前置过滤器的证据链。 |

## 判定记录主键

| 字段 | 类型 | 必填 | 含义 |
|---|---|---:|---|
| `qualification_record_id` | string | 是 | 判定记录编号，建议格式 `ASHARE-QUAL-<ts_code>-<window>-v0.1`。 |
| `ashare_sample_id` | string | 是 | 对应候选样本表编号。 |
| `ts_code` | string | 是 | 股票代码。 |
| `symbol_name` | string | 是 | 股票简称。 |
| `sample_window_start` | date | 是 | 观察窗口起点。 |
| `sample_window_end` | date | 是 | 观察窗口终点。 |
| `record_status` | enum | 是 | `draft / reviewed / blocked / superseded`。 |

## 1. 接入包复核摘要

| 字段 | 类型 | 必填 | 来源 | 含义 |
|---|---|---:|---|---|
| `intake_package_status` | enum | 是 | 验收报告 | `missing / partial / ready / invalid`。 |
| `contract_check_result` | enum | 是 | 验收报告 | `pass / warn / fail`。 |
| `failed_contract_items` | list | 是 | 验收报告 | 缺失字段、重复主键、窗口不一致等。 |
| `eligible_for_malf_run` | boolean | 是 | 复核流程 | 是否可生成 MALF 快照。 |
| `data_quality_warning` | list | 否 | 复核流程 | 不阻断但需要携带的质量警告。 |

阻断原则：

| 条件 | 处理 |
|---|---|
| `contract_check_result=fail` | `candidate_stage` 只能为 `unknown` 或停在已满足的较低阶段。 |
| `eligible_for_malf_run=false` | 不得生成 `malf_snapshot_ref`，不得进入前置过滤器。 |
| `failed_contract_items` 影响窗口或 OHLC | 不得填 `structure_candidate`。 |

## 2. Data / Universe 事实

| 字段 | 类型 | 必填 | 来源 | 含义 |
|---|---|---:|---|---|
| `board_type` | enum | 是 | candidate universe | `main / gem / star / bse / unknown`。 |
| `list_date` | date/null | 是 | candidate universe | 上市日期。 |
| `is_st` | boolean/null | 是 | candidate universe | 是否 ST 或 *ST。 |
| `is_new_stock_window` | boolean/null | 是 | candidate universe | 是否处于新股特殊观察窗口。 |
| `source_ref_universe` | string | 是 | candidate universe | 元数据来源。 |

这些字段只说明样本是否可识别，不得直接生成 `tachibana_applicability`。

## 3. 行业与日线窗口事实

| 字段 | 类型 | 必填 | 来源 | 含义 |
|---|---|---:|---|---|
| `sw_l1_name` | string/null | 是 | 申万标签 | 申万一级行业。 |
| `sw_l2_name` | string/null | 否 | 申万标签 | 申万二级行业。 |
| `industry_valid_for_window` | boolean | 是 | 复核流程 | 行业标签是否覆盖观察窗口。 |
| `daily_window_ref` | string/null | 是 | 日线窗口 | 日线文件引用。 |
| `daily_window_quality` | enum | 是 | 复核流程 | `ready / incomplete / source_missing / disputed`。 |
| `bar_count` | number/null | 否 | 日线窗口 | 观察窗口内有效 bar 数。 |
| `quality_event_flags` | list | 否 | 日线窗口 | `suspension_flag / corporate_action_flag / missing_bar_flag` 等。 |

行业只作为样本分层；日线窗口只作为 MALF 输入。二者都不是交易判断。

## 4. MALF 快照事实

| 字段 | 类型 | 必填 | 来源 | 含义 |
|---|---|---:|---|---|
| `malf_snapshot_ref` | string/null | 条件必填 | MALF 快照 | MALF 结构快照引用。 |
| `snapshot_quality_status` | enum/null | 条件必填 | MALF 快照 | `ready / incomplete / source_missing / disputed`。 |
| `malf_version` | string/null | 条件必填 | MALF 快照 | MALF 定义或实现版本。 |
| `malf_background` | enum/list | 条件必填 | MALF 快照 | `alive_wave / pullback / range / break_birth / stagnation / transition / unknown`。 |
| `wave_range_break_fields_ref` | string/null | 条件必填 | MALF 快照 | 波段、区间、突破证据字段引用。 |
| `malf_evidence_ref` | list | 条件必填 | MALF 快照 | 支撑证据引用。 |

阻断原则：

| 条件 | 处理 |
|---|---|
| `malf_snapshot_ref=null` | 不能进入 `tachibana_candidate`。 |
| `snapshot_quality_status!=ready` | 不能进入 `tachibana_candidate`。 |
| `malf_background=unknown` | 前置过滤器不得人工升级为 `suitable / conditional`。 |

## 5. 横向矩阵判读

| 字段 | 类型 | 必填 | 来源 | 含义 |
|---|---|---:|---|---|
| `qualification_rule_id` | enum/null | 条件必填 | 横向矩阵 | 如 `Q-ALIVE-CLEAN`、`Q-LOCK-CANDIDATE`。 |
| `secondary_rule_ids` | list | 否 | 横向矩阵 | 同时触发的辅规则。 |
| `rhythm_meaning` | enum | 条件必填 | 意义判定准则 | `meaningful / limited / not_meaningful / unknown`。 |
| `meaning_reason` | list | 条件必填 | 理由码表 / 本记录 | 为什么该结构状态下仓位节奏有意义、有限、无意义或未知。 |
| `rule_match_reason` | string/list | 条件必填 | 本记录 | 为什么匹配该规则。 |
| `rule_match_confidence` | enum | 是 | 本记录 | `high / medium / low / blocked`。 |
| `boundary_warning` | list | 是 | 横向矩阵 | 必须携带的边界警告。 |

判读纪律：

| 情况 | 处理 |
|---|---|
| 同时匹配多个规则 | 选一个主 `qualification_rule_id`，其余写入 `secondary_rule_ids`。 |
| 匹配到 PM 复杂规则 | `tachibana_applicability` 原则上不得高于 `conditional`。 |
| 匹配到 `Q-SOURCE-DISRUPTED` | 默认 `tachibana_applicability=unknown`。 |

## 6. 前置过滤器裁决

| 字段 | 类型 | 必填 | 来源 | 含义 |
|---|---|---:|---|---|
| `candidate_stage_before` | enum | 是 | 候选样本表 | 当前阶段。 |
| `candidate_stage_after` | enum | 是 | 本记录 | 本次复核后的阶段。 |
| `tachibana_applicability` | enum | 是 | 前置过滤器 | `suitable / conditional / unsuitable / unknown`。 |
| `applicability_reason` | string/list | 条件必填 | 前置过滤器 | 裁决理由。 |
| `evidence_level` | enum/list | 是 | 本记录 / MALF | `E1_malf_snapshot / E2_ashare_daily_fact / E3_industry_classification / E4_research_mapping`。 |
| `next_action` | enum | 是 | 本记录 | `fill_candidate_table / keep_pending / repair_data / rerun_malf / research_audit_only`。 |

裁决规则：

| 裁决 | 必要条件 | 后续 |
|---|---|---|
| `suitable` | `rhythm_meaning=meaningful`，快照 ready、结构清楚、`Q-ALIVE-CLEAN` 或等价干净规则。 | 可进入 Method / PM。 |
| `conditional` | `rhythm_meaning=limited`，快照 ready，但需要边界警告或 PM 承接。 | 可进入 Method / PM，但必须携带限制。 |
| `unsuitable` | `rhythm_meaning=not_meaningful`，结构明确不适合立花仓位节奏。 | 不进入 Method / PM。 |
| `unknown` | `rhythm_meaning=unknown`，数据、快照或结构证据不足。 | 补证或研究审计。 |

## 7. 禁止字段

本记录不得出现以下字段：

| 禁止字段 | 原因 |
|---|---|
| `buy_signal` | 结构资格不是买卖信号。 |
| `trade_accept / trade_reject / trade_defer` | 这些属于 Signal 裁决，不属于前置过滤器。 |
| `target_position` | 目标仓位属于 PM 或执行层，不属于结构资格。 |
| `position_size_from_malf` | MALF 不输出手数。 |
| `ashare_t1_action` | T+1 是制度执行约束，后置处理。 |
| `limit_up_strategy / limit_down_strategy` | 涨跌停策略不是结构资格。 |
| `industry_hot_score` | 行业热度不能替代结构证据。 |

## YAML 模板

```yaml
qualification_record_id: ASHARE-QUAL-TBD-TBD-v0.1
ashare_sample_id: ASHARE-PENDING-TBD
ts_code: TBD
symbol_name: TBD
sample_window_start: YYYY-MM-DD
sample_window_end: YYYY-MM-DD
record_status: draft

intake_package_status: missing
contract_check_result: fail
failed_contract_items:
  - TBD
eligible_for_malf_run: false
data_quality_warning: []

board_type: unknown
list_date: null
is_st: null
is_new_stock_window: null
source_ref_universe: TBD

sw_l1_name: null
sw_l2_name: null
industry_valid_for_window: false
daily_window_ref: null
daily_window_quality: source_missing
bar_count: null
quality_event_flags: []

malf_snapshot_ref: null
snapshot_quality_status: source_missing
malf_version: null
malf_background: unknown
wave_range_break_fields_ref: null
malf_evidence_ref: []

qualification_rule_id: null
secondary_rule_ids: []
rhythm_meaning: unknown
meaning_reason:
  - no_ready_malf_snapshot
rule_match_reason:
  - blocked_by_missing_malf_snapshot
rule_match_confidence: blocked
boundary_warning:
  - do_not_upgrade_without_malf_snapshot

candidate_stage_before: unknown
candidate_stage_after: unknown
tachibana_applicability: unknown
applicability_reason:
  - no_ready_malf_snapshot
evidence_level:
  - source_missing
next_action: repair_data
```

## 当前结论

- 本模板把“结构状态 -> 仓位节奏意义”的判断拆成可复核底稿，而不是让候选样本表直接承载全部证据。
- 当前正式数据目录仍无 A 股接入包，因此模板只作为下一轮真实样本的填写标准，不生成真实个股结论。
- 当前 `ASHARE-PENDING-001/002/003` 的阻断态底稿已单独记录在 [Tachibana A 股结构资格判定记录 ASHARE-PENDING v0.1](./Tachibana-A股结构资格判定记录-ASHARE-PENDING-v0.1.md)。
- 真实样本填写本模板时，必须同步检查 [Tachibana A 股结构资格升级闸门检查清单 v0.1](./Tachibana-A股结构资格升级闸门检查清单-v0.1.md)，不得跳级。
- `failed_contract_items / rule_match_reason / applicability_reason / boundary_warning / next_action` 应优先使用 [Tachibana A 股结构资格理由码表 v0.1](./Tachibana-A股结构资格理由码表-v0.1.md)。
- `rhythm_meaning` 必须先于 `tachibana_applicability` 写入；前者回答节奏意义，后者回答是否进入 Method / PM。
- 只有完成本记录并得到 `tachibana_applicability=suitable/conditional` 的样本，才允许进入 Method / PM 与 Backtest Input；仍不进入 A 股制度规则改造。
