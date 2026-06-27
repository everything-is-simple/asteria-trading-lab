# Tachibana A 股结构资格判定记录 ASHARE-PENDING v0.1

## 版本定位

- 本文件承接 [Tachibana A 股结构资格判定记录模板 v0.1](./Tachibana-A股结构资格判定记录模板-v0.1.md)、[Tachibana A 股最小接入包验收报告 v0.1](./Tachibana-A股最小接入包验收报告-v0.1.md) 与 [Tachibana A 股候选股票结构资格样本表 v0.1](./Tachibana-A股候选股票结构资格样本表-v0.1.md)。
- 它是当前无数据状态下的阻断态判定记录样例，不是真实个股样本，不生成 A 股候选结论。
- 本文件不定义 T+1、涨跌停、停牌、整手、融资融券或任何执行规则。
- 它只回答：正式数据目录为空时，`ASHARE-PENDING-001/002/003` 应如何被明确挡在结构资格闸门外。
- 逐级升级闸门检查见 [Tachibana A 股结构资格升级闸门检查清单 v0.1](./Tachibana-A股结构资格升级闸门检查清单-v0.1.md)。
- 本文件中的阻断理由码承接 [Tachibana A 股结构资格理由码表 v0.1](./Tachibana-A股结构资格理由码表-v0.1.md)。

## 当前文件系统证据

| 证据项 | 当前值 |
|---|---|
| 正式数据目录 | `Z:\asteria-trading-labs-data` |
| 当前文件数 | `0` |
| `candidate-universe-v0.1.csv` | 缺失 |
| `sw-industry-membership-v0.1.csv` | 缺失 |
| `daily-window-v0.1\` | 缺失 |
| `malf-snapshots-v0.1\` | 缺失 |

因此，本文件中的三条记录全部是 `blocked`，不得被解释为真实 A 股结构资格样本。

## 阻断记录总表

| qualification_record_id | ashare_sample_id | contract_check_result | eligible_for_malf_run | candidate_stage_after | tachibana_applicability | next_action |
|---|---|---:|---:|---|---|---|
| `ASHARE-QUAL-PENDING-001-v0.1` | `ASHARE-PENDING-001` | `fail` | `false` | `unknown` | `unknown` | `repair_data` |
| `ASHARE-QUAL-PENDING-002-v0.1` | `ASHARE-PENDING-002` | `fail` | `false` | `unknown` | `unknown` | `repair_data` |
| `ASHARE-QUAL-PENDING-003-v0.1` | `ASHARE-PENDING-003` | `fail` | `false` | `unknown` | `unknown` | `repair_data` |

## ASHARE-PENDING-001

```yaml
qualification_record_id: ASHARE-QUAL-PENDING-001-v0.1
ashare_sample_id: ASHARE-PENDING-001
ts_code: TBD
symbol_name: TBD
sample_window_start: null
sample_window_end: null
record_status: blocked

intake_package_status: missing
contract_check_result: fail
failed_contract_items:
  - missing_candidate_universe
  - missing_sw_industry_membership
  - missing_daily_window
  - missing_malf_snapshot
eligible_for_malf_run: false
data_quality_warning: []

board_type: unknown
list_date: null
is_st: null
is_new_stock_window: null
source_ref_universe: missing

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
rule_match_reason:
  - blocked_by_missing_candidate_universe
  - blocked_by_missing_malf_snapshot
rule_match_confidence: blocked
boundary_warning:
  - do_not_upgrade_without_malf_snapshot
  - do_not_use_manual_stock_pick_as_structure_qualification

candidate_stage_before: universe_candidate
candidate_stage_after: unknown
tachibana_applicability: unknown
applicability_reason:
  - no_stock_metadata
  - no_industry_label
  - no_daily_window
  - no_ready_malf_snapshot
evidence_level:
  - source_missing
next_action: repair_data
```

裁决：`ASHARE-PENDING-001` 当前不能作为真实 `universe_candidate`，因为缺少股票元数据；更不能进入 `structure_candidate` 或 `tachibana_candidate`。

## ASHARE-PENDING-002

```yaml
qualification_record_id: ASHARE-QUAL-PENDING-002-v0.1
ashare_sample_id: ASHARE-PENDING-002
ts_code: TBD
symbol_name: TBD
sample_window_start: null
sample_window_end: null
record_status: blocked

intake_package_status: missing
contract_check_result: fail
failed_contract_items:
  - missing_daily_window
  - missing_malf_snapshot
eligible_for_malf_run: false
data_quality_warning: []

board_type: unknown
list_date: null
is_st: null
is_new_stock_window: null
source_ref_universe: missing

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
rule_match_reason:
  - blocked_by_missing_daily_window
  - blocked_by_missing_malf_snapshot
rule_match_confidence: blocked
boundary_warning:
  - do_not_treat_liquidity_as_structure
  - do_not_upgrade_without_malf_snapshot

candidate_stage_before: structure_candidate
candidate_stage_after: unknown
tachibana_applicability: unknown
applicability_reason:
  - no_daily_window
  - no_ready_malf_snapshot
evidence_level:
  - source_missing
next_action: repair_data
```

裁决：`ASHARE-PENDING-002` 的“structure_candidate”只能保留为待填占位，不是事实状态。缺少日线窗口时，不能声称已具备可运行 MALF。

## ASHARE-PENDING-003

```yaml
qualification_record_id: ASHARE-QUAL-PENDING-003-v0.1
ashare_sample_id: ASHARE-PENDING-003
ts_code: TBD
symbol_name: TBD
sample_window_start: null
sample_window_end: null
record_status: blocked

intake_package_status: missing
contract_check_result: fail
failed_contract_items:
  - missing_board_type
  - missing_st_flag
  - missing_new_stock_window
  - missing_industry_label
eligible_for_malf_run: false
data_quality_warning: []

board_type: unknown
list_date: null
is_st: null
is_new_stock_window: null
source_ref_universe: missing

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
rule_match_reason:
  - blocked_by_missing_universe_fields
  - blocked_by_missing_industry_label
rule_match_confidence: blocked
boundary_warning:
  - do_not_mix_board_constraints_with_structure_qualification
  - do_not_use_industry_hot_score_as_structure_evidence

candidate_stage_before: unknown
candidate_stage_after: unknown
tachibana_applicability: unknown
applicability_reason:
  - no_board_type
  - no_st_flag
  - no_new_stock_window
  - no_industry_label
evidence_level:
  - source_missing
next_action: repair_data
```

裁决：`ASHARE-PENDING-003` 当前停在 `unknown`。板块、ST、新股窗口和行业标签只能帮助 Data / Universe 识别，不能替代 MALF 快照或前置过滤器。

## 汇总裁决

| 问题 | 裁决 |
|---|---|
| 是否生成真实 A 股结构资格样本？ | 否。三条记录均为阻断态。 |
| 是否允许进入 MALF 快照生成？ | 否。缺少日线窗口。 |
| 是否允许进入前置过滤器？ | 否。缺少 `snapshot_quality_status=ready` 的 MALF 快照。 |
| 是否允许进入 Method / PM？ | 否。`tachibana_applicability=unknown`。 |
| 是否允许进入 A 股制度规则改造？ | 否。本轮仍停在结构资格数据阻断。 |

## 当前结论

- `ASHARE-PENDING-001/002/003` 只是待填队列，不是真实候选样本。
- 当前阻断原因是数据接入缺失，不是 MALF、Tachibana Method 或 PM 的方法失败。
- 三条 pending 记录在 [Tachibana A 股结构资格升级闸门检查清单 v0.1](./Tachibana-A股结构资格升级闸门检查清单-v0.1.md) 中均被判为不得升级。
- 三条 pending 记录使用的 `missing_* / blocked_by_* / no_* / do_not_*` 理由码已由 [Tachibana A 股结构资格理由码表 v0.1](./Tachibana-A股结构资格理由码表-v0.1.md) 承接。
- 下一步仍应补齐最小接入包，重新生成验收报告，再按判定记录模板填写真实单窗口底稿。
