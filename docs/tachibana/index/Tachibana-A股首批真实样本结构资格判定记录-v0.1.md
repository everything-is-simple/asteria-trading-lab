# Tachibana A 股首批真实样本结构资格判定记录 v0.1

**生成日期**: 2026-06-27
**生成方**: `ashare_intake_validator.py --audit-first-batch-front-filter-run` + `--audit-first-batch-record-drafts` + `--audit-first-batch-cognitive-pipeline`
**数据底座**: `Z:\asteria-trading-labs-data\ashare\` (从 DuckDB `market_meta` + `market_base_day` + TDX 离线日线生成)
**版本定位**: 这是整条认知链路第一次用真实 A 股数据"通电"留下的判定记录。它**承接**并**事实上取代** [Tachibana A 股结构资格判定记录 ASHARE-PENDING v0.1](./Tachibana-A股结构资格判定记录-ASHARE-PENDING-v0.1.md)——后者是"数据缺失时的阻断态样例"，本文件是"数据齐备后的真实样例"。

---

## 0. 边界声明（这是什么、不是什么）

- ✅ 本文件是 MALF 立花前置认知过滤器对 5 只真实 A 股样本窗口的判定记录
- ✅ 每条记录都附 `record_consistency / rhythm_sample_row_gate / candidate_table_gate` 三道闸门证据
- ✅ 数据来源、判定理由、边界警告完整可追溯
- ❌ 这**不是**交易信号——所有记录 `signal_generation_allowed=False`
- ❌ 这**不是**仓位决策——所有记录 `target_position` 等字段被 FORBIDDEN_FIELDS 阻断
- ❌ 这**不是**制度规则改造——所有记录 `institution_adaptation_allowed=False`
- ❌ MALF 快照是"研究映射型 ready snapshot"（preset），**不是**真正的 MALF v2.0 引擎产出。`evidence_level=[E1_malf_snapshot, E4_research_mapping]` 明确记录了这一点

---

## 1. 链路通电总结

### 1.1 整体管道状态（`audit_first_batch_cognitive_pipeline`）

| 链路环节 | 状态 |
|---|---|
| `readiness`（接入包契约） | ✅ pass |
| `front_filter_run`（前置过滤器批量） | ✅ pass |
| `record_drafts`（结构资格判定底稿） | ✅ pass |
| `sample_table_trial`（样本表试填） | ✅ pass |
| `method_pm_readiness`（Method/PM 计划草案） | ⛔ blocked |
| `backtest_input_readiness`（Backtest Input 快照） | ⛔ blocked |
| `institution_adaptation_allowed` | False（硬闸） |
| `current_blocking_layer` | `method_pm_readiness` |
| `next_action` | `action:method_pm_review` |

**这是设计意图的精确实现**：机器把所有**认知层**判定全做了（5 个样本中 4 个有明确结构判定，1 个保持 unknown），卡在 `method_pm_readiness` —— 因为这一步要求**人工提供 Method/PM 计划草案**（中心单/锁单/加码/认错），机器拒绝自动生成（`method_pm_auto_generation_allowed=False` 是硬闸）。

### 1.2 5 只样本一表

| ts_code | 简称 | 板块 | 窗口 | front_filter | candidate_stage | rhythm_meaning | tachibana_applicability | qualification_rule | next_action |
|---|---|---|---|---|---|---|---|---|---|
| `000001.SZ` | 平安银行 | main | 2026-03-24~04-03 | ✅ pass | **tachibana_candidate** | meaningful | **suitable** | `Q-ALIVE-CLEAN` | action:fill_qualification_record |
| `300750.SZ` | 宁德时代 | gem | 2026-03-24~04-03 | ✅ pass | **tachibana_candidate** | limited | conditional | `Q-PRESSURE-ADJUST` | action:fill_qualification_record |
| `600000.SH` | 浦发银行 | main | 2026-03-24~04-03 | ✅ pass | **tachibana_candidate** | limited | conditional | `Q-LOCK-WAIT` | action:fill_qualification_record |
| `002714.SZ` | 牧原股份 | main | 2026-03-24~04-03 | ❌ rejected | **rejected** | **not_meaningful** | unsuitable | `NM-NO-STRUCTURE` | action:research_audit_only |
| `601127.SH` | 赛力斯 | main | 2026-03-24~04-03 | ⛔ blocked | structure_candidate | unknown | unknown | `null` | action:keep_pending |

**覆盖结构**：meaningful / limited / not_meaningful / unknown 四谱**全覆盖**。

---

## 2. 三条 tachibana_candidate 详细判定记录

### 2.1 平安银行 000001.SZ（Q-ALIVE-CLEAN / meaningful / suitable）

```yaml
qualification_record_id: ASHARE-QUAL-000001.SZ-2026-03-24-2026-04-03-v0.1
ashare_sample_id: ASHARE-000001.SZ-2026-03-24-2026-04-03
ts_code: 000001.SZ
symbol_name: 平安银行
sample_window_start: 2026-03-24
sample_window_end: 2026-04-03
record_status: draft

candidate_stage_before: structure_candidate
candidate_stage_after: tachibana_candidate

malf_snapshot_ref: MALF-SNAP-000001.SZ-2026-03-24-2026-04-03-RMAP-v0.1
snapshot_quality_status: ready
malf_background: alive_wave
wave_range_break_fields_ref: front_filter_report.wave_range_break_fields
malf_evidence_ref:
  - docs/a-share/first-batch-real-samples.md#000001sz

qualification_rule_id: Q-ALIVE-CLEAN
rhythm_meaning: meaningful
meaning_reason:
  - structure_clean_alive_wave
  - rhythm_meaning_meaningful
rule_match_reason:
  - matched_q_alive_clean
rule_match_confidence: high

tachibana_applicability: suitable
applicability_reason:
  - structure_clean_alive_wave
  - rhythm_meaning_meaningful

boundary_warning:
  - do_not_infer_position_size_from_malf
  - do_not_convert_rhythm_meaning_to_signal_accept
  - do_not_generate_trade_from_rhythm_meaning_only

evidence_level:
  - E1_malf_snapshot
  - E4_research_mapping

pm_complexity: none
pm_required: false
institution_constraint_need: none
interface_layer: tachibana_adapter
next_action: action:fill_candidate_table

front_filter_result: pass
record_consistency: { result: pass, issues: [] }
rhythm_sample_row_gate: { result: pass, next_action: action:fill_candidate_table }
candidate_table_gate: { result: pass, allowed_candidate_stage: tachibana_candidate }
```

**裁决**：在该观察窗口内，平安银行的日线结构被研究映射快照判为 `alive_wave`，匹配 `Q-ALIVE-CLEAN` 规则。结构资格**可以**升级到 `tachibana_candidate`。`rhythm_meaning=meaningful` 表示立花式仓位节奏在此结构下有意义。**仍不允许**自动生成 signal、不允许推断仓位、不允许进入 A 股制度规则改造。

### 2.2 宁德时代 300750.SZ（Q-PRESSURE-ADJUST / limited / conditional）

```yaml
qualification_record_id: ASHARE-QUAL-300750.SZ-2026-03-24-2026-04-03-v0.1
ashare_sample_id: ASHARE-300750.SZ-2026-03-24-2026-04-03
ts_code: 300750.SZ
symbol_name: 宁德时代
candidate_stage_after: tachibana_candidate

malf_snapshot_ref: MALF-SNAP-300750.SZ-2026-03-24-2026-04-03-RMAP-v0.1
malf_background: pullback
qualification_rule_id: Q-PRESSURE-ADJUST

rhythm_meaning: limited
tachibana_applicability: conditional
pm_complexity: conditional
pm_required: true

boundary_warning:
  - pm_required_high_volatility_pullback
  - do_not_treat_limited_as_suitable
  - do_not_infer_position_size_from_malf

evidence_level: [E1_malf_snapshot, E4_research_mapping]
next_action: action:fill_candidate_table
front_filter_result: pass
```

**裁决**：高波动回撤样本，结构上可讨论但**必须**配合 Method/PM 复杂度判断；不可直接当 suitable 用。

### 2.3 浦发银行 600000.SH（Q-LOCK-WAIT / limited / conditional）

```yaml
qualification_record_id: ASHARE-QUAL-600000.SH-2026-03-24-2026-04-03-v0.1
ashare_sample_id: ASHARE-600000.SH-2026-03-24-2026-04-03
ts_code: 600000.SH
symbol_name: 浦发银行
candidate_stage_after: tachibana_candidate

malf_background: range
qualification_rule_id: Q-LOCK-WAIT

rhythm_meaning: limited
tachibana_applicability: conditional

boundary_warning:
  - range_state_wait_for_break
  - do_not_treat_limited_as_suitable

next_action: action:fill_candidate_table
front_filter_result: pass
```

**裁决**：区间等待型样本（`range` 背景 + `no_trade_wait=true`）；结构上保留为 `Q-LOCK-WAIT` 资格，但不允许在区间内启动 Method/PM。

---

## 3. 一条 rejected 真实判定（not_meaningful 反例）

### 3.1 牧原股份 002714.SZ（NM-NO-STRUCTURE / not_meaningful / unsuitable）

```yaml
qualification_record_id: ASHARE-QUAL-002714.SZ-2026-03-24-2026-04-03-v0.1
ts_code: 002714.SZ
symbol_name: 牧原股份
candidate_stage_after: rejected
front_filter_result: rejected

malf_background: no_structure
qualification_rule_id: NM-NO-STRUCTURE

rhythm_meaning: not_meaningful
tachibana_applicability: unsuitable

applicability_reason:
  - noise_dominated_no_structure
  - rhythm_meaning_not_meaningful

boundary_warning:
  - do_not_force_method_pm_on_no_structure
  - do_not_treat_volatility_as_structure

next_action: action:research_audit_only
```

**裁决**：噪声主导窗口，**不构成可讨论的波段结构**。明确登记为 `NM-NO-STRUCTURE` 反例，进入 [MALF-立花not_meaningful反例登记表 v0.1](./MALF-立花not_meaningful反例登记表-v0.1.md)。**禁止**在此样本上启动 Method/PM。

---

## 4. 一条 blocked 真实样本（unknown 保持诚实）

### 4.1 赛力斯 601127.SH（unknown / unknown）

```yaml
qualification_record_id: ASHARE-QUAL-601127.SH-2026-03-24-2026-04-03-v0.1
ts_code: 601127.SH
symbol_name: 赛力斯
candidate_stage_after: structure_candidate
front_filter_result: blocked

malf_background: unknown
qualification_rule_id: null

rhythm_meaning: unknown
tachibana_applicability: unknown

next_action: action:keep_pending
```

**裁决**：研究待定样本。结构背景 `unknown`，前置过滤器**禁止**人工经验升级为 suitable/conditional（v2.0 MALF 铁律：`malf_background=unknown` 不得人工改写）。保持 `structure_candidate`，进入研究队列。

---

## 5. 关键不变量验证

| 不变量 | 验证结果 |
|---|---|
| `record_consistency=pass`（3 条 tachibana_candidate 全部） | ✅ |
| `rhythm_sample_row_gate=pass`（3 条） | ✅ |
| `candidate_table_gate=pass`（3 条） | ✅ |
| `signal_generation_allowed=False`（全部 5 条） | ✅ |
| `backtest_execution_allowed=False`（全部 5 条） | ✅ |
| `institution_adaptation_allowed=False`（全部 5 条） | ✅ |
| `method_pm_auto_generation_allowed=False`（卡在 method_pm_readiness） | ✅ |
| `target_position / buy_signal / trade_accept` 等 FORBIDDEN_FIELDS 不出现 | ✅ |
| `evidence_level` 同时包含 `E1_malf_snapshot` 和 `E4_research_mapping`（明确这是研究映射快照） | ✅ |

---

## 6. 链路停在哪、为什么

**当前停在 `method_pm_readiness=blocked`**：

```
readiness → front_filter_run → record_drafts → sample_table_trial → [STOP] method_pm_readiness
                                                                            ↓
                                                          需要人工提供 Method/PM 计划草案
                                                          （中心单/锁单/加码/认错）
```

**这是设计意图**。Method/PM 是立花法的"动作规划"层（独立于 MALF 结构事实层）。机器不能也不应该自动生成这些动作。下游的 `backtest_input_readiness / institution_adaptation` 都要等人工 Method/PM 计划合流后才能解锁。

**这一停点正好印证了三层分工**：
- ✅ MALF（结构事实）：机器全做完
- ⏳ Tachibana Method/PM（交易动作）：等待人工
- ⏳ A 股制度审计（执行约束）：等 Method/PM 合流后才启动

---

## 7. 复跑指令

```powershell
$env:PYTHONPATH='src'
python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-readiness
python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-front-filter-run
python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-record-drafts
python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-sample-table-trial
python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-cognitive-pipeline
```

**预期输出**：与本文件 §1.1 / §1.2 一致。

---

## 8. 与 ASHARE-PENDING 文件的关系

| 文件 | 定位 | 状态 |
|---|---|---|
| `Tachibana-A股结构资格判定记录-ASHARE-PENDING-v0.1.md` | 正式数据目录**为空**时的阻断态样例 | 历史文档，保留作为"缺数据时正确行为"的回归基线 |
| **本文件** | 正式数据目录**齐备**后的真实判定记录 | **当前主基线** |

ASHARE-PENDING 没有被"填实"——它本就是"空数据状态"的样例，不该被填。本文件是它的并列后继。

---

## 9. 下一步（不在本记录范围）

1. **人工 Method/PM 计划草案** —— 针对 3 条 tachibana_candidate 各编写一份独立的中心单/锁单/加码/认错动作计划（按 `audit_method_pm_plan_draft_contract` 字段契约），让 `method_pm_readiness` 升级到 pass
2. **跨源复权口径对齐验证** —— 把 [本地数据资产接入审计 v0.1](../data/本地数据资产接入审计-v0.1.md) §2.4 的 Baostock/DuckDB 复权差异在这 5 只股票上扩展校验
3. **GBK 解码** —— `readers.py` 给 DuckDB 中文字段加 GBK→UTF-8 转换（本批数据 GPT 已经手工处理过中文名，下次自动化）

---

**签字**: Claude (Opus 4.8) @ 2026-06-27
**配套验证**:
- 129 tests OK（含 `test_tdx_local_first_batch.py` / `test_ashare_intake_validator.py` 全套）
- 整条链路 `cognitive_pipeline` 在真实数据上跑通到 `method_pm_readiness` 边界
- A 股制度适配硬闸 `institution_adaptation_allowed=False` 在所有 5 条记录上保持
