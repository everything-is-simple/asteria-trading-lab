# 首批真实样本链路审计

本页记录当前首批真实 A 股样本窗口，在正式数据目录上的首轮运行结果。

## 运行对象

- 正式数据目录：`Z:\asteria-trading-labs-data`
- 本地 Tongdaxin：`Z:\new_tdx64`
- 本地离线日线：`Z:\tdx_offline_Data`
- 本地 DuckDB：`Z:\malf-data`

## 落盘结果

已生成：

- `5` 条 `candidate-universe` 元数据
- `5` 条行业标签记录
- `5` 个 `daily-window-v0.1/<ts_code>.csv`
- `5` 个研究映射型 `ready snapshot`
- `1` 份 `first-batch-sample-manifest-v0.1.json`

## Gate 结果

| 审计层 | 结果 | 关键数字 | 备注 |
|---|---|---|---|
| `audit_first_batch_readiness` | `pass` | `front_filter_ready_candidate_count=5` | 首批真实样本都已达到 `structure_candidate -> action:run_front_filter`。 |
| `audit_first_batch_front_filter_run` | `pass` | `front_filter_run_count=5` | 已形成 `meaningful / limited / unknown / not_meaningful` 四类真实结果。 |
| `audit_first_batch_record_drafts` | `pass` | `record_draft_count=3` | 仅 `pass + fill_qualification_record` 的样本进入底稿草案。 |
| `audit_first_batch_sample_table_trial` | `pass` | `trial_row_count=3` | 当前形成 `3` 条真实 `trial_rows`。 |

## 每个样本停在哪一层

| ts_code | symbol_name | 预期结构目标 | front_filter_result | rhythm_meaning | tachibana_applicability | candidate_stage_after | next_action | 是否形成 trial_row |
|---|---|---|---|---|---|---|---|---|
| `000001.SZ` | `平安银行` | `meaningful` | `pass` | `meaningful` | `suitable` | `tachibana_candidate` | `action:fill_qualification_record` | 是 |
| `300750.SZ` | `宁德时代` | `limited` | `pass` | `limited` | `conditional` | `tachibana_candidate` | `action:fill_qualification_record` | 是 |
| `600000.SH` | `浦发银行` | `limited` | `pass` | `limited` | `conditional` | `tachibana_candidate` | `action:fill_qualification_record` | 是 |
| `601127.SH` | `赛力斯` | `unknown` | `blocked` | `unknown` | `unknown` | `structure_candidate` | `action:keep_pending` | 否 |
| `002714.SZ` | `牧原股份` | `not_meaningful` | `rejected` | `not_meaningful` | `unsuitable` | `rejected` | `action:research_audit_only` | 否 |

## 覆盖结论

当前 `expected_structure_targets` 与 `covered_structure_targets` 一致：

- `meaningful`
- `limited`
- `unknown`
- `not_meaningful`

因此，这一批样本已经完成“四类尽量覆盖”的首轮目标；当前 `missing_structure_targets=[]`。

## 当前还不能说成“完成”的地方

- 这批 `ready snapshot` 是 **研究映射型 ready snapshot**，不是自动 MALF 计算引擎输出。
- 当前样本链路已真实跑到 `trial_rows`，但 `cognitive_pipeline_gate` 仍然因为缺少独立 Method / PM 计划而保持阻断，这符合本轮“停在样本表试填”的边界。
- 当前行业标签已改为按样本窗口做重叠匹配；若窗口内没有可重叠的行业事实，样本会被阻断而不是借用未来标签。

## 本轮结论

本轮已经做到：

- 用真实本地 Tongdaxin + DuckDB 数据落下首批正式接入包；
- 用真实窗口生成 `5` 个 ready 候选；
- 用前置过滤器跑出四类结构覆盖；
- 形成 `3` 条真实 `trial_rows`；
- 且全链路仍未越界到 `buy_signal / trade_accept / target_position / ashare_t1_action / limit_up_strategy`。

下一步最自然的是：

1. 人工复核这 `3` 条 `trial_rows`；
2. 补时间对齐的行业标签来源；
3. 再决定是先补自动 MALF snapshot，还是先回接 Method / PM。
