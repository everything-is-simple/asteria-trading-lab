# Tachibana A 股首批结构资格样本接入作业单 v0.1

## 版本定位

- 本文件是首批真实 A 股样本进入 `MALF -> Tachibana 前置过滤器 -> 结构资格样本表` 的作业入口。
- 它承接 [MALF-立花前置认知过滤器攻坚总控矩阵 v0.1](./MALF-立花前置认知过滤器攻坚总控矩阵-v0.1.md)、[Tachibana A 股最小接入包落盘准备清单 v0.1](./Tachibana-A股最小接入包落盘准备清单-v0.1.md)、[Tachibana A 股最小接入包复核流程 v0.1](./Tachibana-A股最小接入包复核流程-v0.1.md) 与 [Tachibana A 股结构资格判定记录模板 v0.1](./Tachibana-A股结构资格判定记录模板-v0.1.md)。
- 它不是选股公式，不下载数据，不生成交易信号，不定义 T+1、涨跌停、停牌、整手或撮合规则。
- 它只回答：第一批真实 A 股样本怎样从数据落盘推进到可复核结构资格判定。

## 作业目标

首批样本接入的目标不是证明立花法适合 A 股，也不是找出可交易股票，而是让第一批真实样本具备可复核证据链：

```text
真实数据落盘
  -> 最小接入包验收
  -> ready MALF snapshot
  -> 前置过滤器
  -> 结构资格判定记录
  -> A 股结构资格样本表试填
```

任何一步未通过，都保持较低阶段或进入 `research_audit`，不得人工跳到 `tachibana_candidate`。

## 首批样本选择口径

首批样本应小而可复核，优先服务结构资格判定，而不是覆盖全市场。

| 口径 | 要求 | 原因 |
|---|---|---|
| 样本数量 | 建议先用 `3-5` 只股票、每只 `1` 个观察窗口。 | 降低人工校验和 MALF 快照复核成本。 |
| 数据完整性 | 必须能提供元数据、申万行业标签、日线窗口和来源引用。 | 否则无法推进到 `structure_candidate`。 |
| 结构多样性 | 尽量覆盖干净推进、震荡等待、资料扰动或结构未知。 | 让 `meaningful / limited / unknown / not_meaningful` 有真实落点。 |
| 制度事件 | 可以包含停牌、除权或缺 bar 样本，但只能标为数据质量或结构证据风险。 | 不允许提前写制度规则。 |
| 禁止口径 | 不用行业热度、流动性排名、题材、涨跌幅或主观看好直接挑 `tachibana_candidate`。 | 防止选股逻辑替代结构资格。 |

若首批样本无法覆盖 `not_meaningful`，应如实记录为缺口，不得硬造反例。

## 作业目录

真实数据只放入正式数据目录：

```text
Z:\asteria-trading-labs-data\
  ashare\
    candidate-universe-v0.1.csv
    sw-industry-membership-v0.1.csv
    daily-window-v0.1\
      <ts_code>.csv
    malf-snapshots-v0.1\
      <ts_code>-<window>.json
```

仓库 `Z:\asteria-trading-lab` 只保存定义、模板、测试 fixture 和审计文档，不保存真实市场接入包。

## 执行顺序

### Step 0. 前置系统审计

在接入真实样本前，先确认前置过滤器自身没有目录或边界破损，并确认正式接入包是否已经达到首批样本准备状态：

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-readiness
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-cognitive-pipeline
```

通过条件：

| 字段 | 必须值 |
|---|---|
| `result` | `pass` |
| `front_filter_system_audit.result` | `pass` |
| `intake_contract.contract_check_result` | `pass / warn` |
| `first_batch_ready_for_front_filter` | `true` |
| `front_filter_ready_candidate_count` | 大于 `0` |
| `front_filter_ready_candidates` | 列出可运行前置过滤器的 `ts_code / symbol_name / candidate_stage_after / next_action / malf_snapshot_ref / malf_snapshot_file / ashare_sample_id_suggestion / front_filter_command / record_draft_command`。 |
| `institution_adaptation_allowed` | `false` |

若该审计失败，按 `issues` 判断是修复前置过滤器目录/边界、修复 A 股接入包，还是准备 ready MALF snapshot。该审计通过也只表示可以运行前置过滤器，不表示可以进入 A 股制度约束审计。

`--audit-first-batch-cognitive-pipeline` 是一键总状态闸门，用于汇总本作业单所有只读审计层。它不能替代单项审计，但可以直接回答当前卡在哪一层，以及下一步应执行哪个 `next_action`。

| readiness issue | 下一步 |
|---|---|
| `first_batch_requires_front_filter_system_audit_pass` | 修复前置过滤器理由码、样本目录、Method / PM 动作目录或接口边界。 |
| `first_batch_requires_intake_contract_pass_or_warn` | 修复最小接入包字段、路径、主键、值域或跨文件一致性。 |
| `first_batch_requires_eligible_for_malf_run` | 补齐行业标签和日线窗口，让样本至少可运行 MALF。 |
| `first_batch_requires_ready_malf_snapshot` | 生成或修复 ready MALF snapshot。 |
| `first_batch_requires_structure_candidate_with_run_front_filter_action` | 检查阶段摘要是否仍停在低阶段，不能直接升级。 |

### Step 1. 接入包落盘

按 [Tachibana A 股最小接入包落盘准备清单 v0.1](./Tachibana-A股最小接入包落盘准备清单-v0.1.md) 放入四类文件。

| 文件 | 首批最低要求 |
|---|---|
| `candidate-universe-v0.1.csv` | 每个 `ts_code` 唯一，`symbol_name / board_type / list_date / is_st / is_new_stock_window / source_ref` 可追溯。 |
| `sw-industry-membership-v0.1.csv` | 每个样本窗口内能找到有效行业标签。 |
| `daily-window-v0.1\<ts_code>.csv` | 日期升序、OHLC 合法、成交量与成交额非负，质量标记字段存在。 |
| `malf-snapshots-v0.1\<ts_code>-<window>.json` | 可先缺失；缺失时样本最多停在 `structure_candidate`，不能进入 `tachibana_candidate`。 |

### Step 2. 最小接入包验收

运行只读验收器：

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data
```

验收结果解释：

| 结果 | 处理 |
|---|---|
| `contract_check_result=fail` | 不进入 MALF；按 `failed_contract_items` 修复数据。 |
| `contract_check_result=warn` | 可继续人工复核，但警告必须进入判定记录。 |
| `contract_check_result=pass` | 可进入 MALF 快照复核或生成。 |

注意：即使 `contract_check_result=pass`，`eligible_for_tachibana_candidate` 仍应为 `false`，因为结构适用性必须由前置过滤器裁决。

### Step 3. MALF 快照准备

每个待判定窗口必须形成 MALF snapshot。快照必须至少满足：

| 字段 | 要求 |
|---|---|
| `malf_snapshot_ref` | 非空，可追溯。 |
| `ts_code` | 与日线文件和文件名一致。 |
| `window_start / window_end` | 落在日线窗口内。 |
| `source_daily_file` | 指向对应 `daily-window-v0.1\<ts_code>.csv`。 |
| `malf_background` | 使用受控结构背景：`alive_wave / pullback / range / break_birth / stagnation / transition / unknown`。 |
| `wave_range_break_fields` | 保留结构证据字段。 |
| `snapshot_quality_status` | 只有 `ready` 才能进入前置过滤器升级。 |

若快照缺失、非 ready 或结构背景为 `unknown`，样本保持 `structure_candidate / unknown`，进入补证或研究审计。

### Step 4. 前置过滤器判定

若 Step 0 已通过，可先按 readiness 清单批量运行首批前置过滤器：

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-front-filter-run
```

批量输出仍然是只读审计结果，不直接升级样本表：

| 字段 | 必须值或含义 |
|---|---|
| `result` | `pass` 才表示首批 ready 候选已完成前置过滤器批量判定。 |
| `front_filter_run_count` | 本轮实际运行前置过滤器的候选数量。 |
| `front_filter_results` | 每个候选的 `ts_code / symbol_name / ashare_sample_id_suggestion / malf_snapshot_ref / malf_snapshot_file / front_filter_result / candidate_stage_after / rhythm_meaning / tachibana_applicability / qualification_rule_id / next_action`。 |
| `candidate_table_update_allowed` | 固定为 `false`；样本表必须等判定底稿复核后再试填。 |
| `institution_adaptation_allowed` | 固定为 `false`；制度约束仍后置。 |

若批量审计返回 `blocked`，先处理 readiness 的 `next_action`，不得跳过前置过滤器直接生成判定底稿。

对每个 ready MALF snapshot 运行：

```powershell
$env:PYTHONPATH='src'; python -m tachibana_front_filter --snapshot Z:\asteria-trading-labs-data\ashare\malf-snapshots-v0.1\<ts_code>-<window>.json
```

输出只允许作为结构资格证据，不得解释成交易动作。

| 输出 | 后续 |
|---|---|
| `rhythm_meaning=meaningful` 且 `tachibana_applicability=suitable` | 可进入判定记录草案。 |
| `rhythm_meaning=limited` 且 `tachibana_applicability=conditional` | 可进入判定记录草案，但必须保留边界警告。 |
| `rhythm_meaning=not_meaningful` 或 `tachibana_applicability=unsuitable` | 记录为反例或研究审计，不进入 Method / PM。 |
| `rhythm_meaning=unknown` 或 `tachibana_applicability=unknown` | 补证或 rerun MALF，不升级。 |

### Step 5. 判定底稿草案

若 Step 4 的批量前置过滤器已通过，可先批量生成只读判定底稿草案：

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-record-drafts
```

该批量入口只为 `front_filter_result=pass / next_action=action:fill_qualification_record` 的候选生成 `record_drafts`，并携带 `record_consistency / rhythm_sample_row_gate / candidate_table_gate / cognitive_pipeline_gate`。它仍然不写样本表：

| 字段 | 必须值或含义 |
|---|---|
| `result` | `pass` 表示已生成可人工复核的底稿草案集合。 |
| `record_draft_count` | 本轮生成的底稿草案数量。 |
| `record_drafts` | 每条草案的样本编号、MALF 结构结果、资格理由码、边界警告和各级 gate。 |
| `candidate_table_update_allowed` | 固定为 `false`；试填样本表必须由人工复核后执行。 |
| `institution_adaptation_allowed` | 固定为 `false`；制度适配仍后置。 |

对通过前置过滤器的样本生成只读草案：

```powershell
$env:PYTHONPATH='src'; python -m tachibana_front_filter --snapshot Z:\asteria-trading-labs-data\ashare\malf-snapshots-v0.1\<ts_code>-<window>.json --record-draft --ashare-sample-id <ASHARE-SAMPLE-ID> --symbol-name "<symbol_name>"
```

草案必须检查：

| 门禁 | 必须值 |
|---|---|
| `record_consistency.result` | `pass` |
| `rhythm_sample_row_gate.result` | `pass` |
| `candidate_table_gate.result` | `pass` 才允许试填样本表。 |
| `front_filter_system_audit.result` | `pass` |
| `cognitive_pipeline_gate.result` | 不要求此时通过；它用于判断是否允许进入 A 股制度约束审计。 |

若 `candidate_table_gate=blocked`，样本只能保留在底稿或研究备注，不得写入 `tachibana_candidate`。

### Step 6. 样本表试填

试填前先运行只读样本表试填复核闸门：

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-sample-table-trial
```

该命令只把 `record_consistency=pass / candidate_table_gate=pass` 的底稿映射成 `trial_rows`，不写入样本表：

| 字段 | 必须值或含义 |
|---|---|
| `result` | `pass` 表示已形成可人工复核的试填行草案。 |
| `trial_row_count` | 可试填复核的样本行数量。 |
| `trial_rows` | 从底稿映射出的结构资格字段集合。 |
| `candidate_table_write_mode` | 固定为 `manual_review_only`。 |
| `candidate_table_update_allowed` | 固定为 `false`；本命令不自动写表。 |
| `institution_adaptation_allowed` | 固定为 `false`；制度适配仍后置。 |

只有通过 Step 5 的样本，才允许把汇总字段写入 [Tachibana A 股候选股票结构资格样本表 v0.1](./Tachibana-A股候选股票结构资格样本表-v0.1.md)。

最小写入字段：

| 字段 | 来源 |
|---|---|
| `ashare_sample_id / ts_code / symbol_name / sample_window` | 接入包与判定底稿。 |
| `board_type / sw_l1_name` | Data / 行业事实。 |
| `candidate_stage` | 判定底稿。 |
| `malf_snapshot_ref / malf_background` | MALF snapshot。 |
| `rhythm_meaning / tachibana_applicability / qualification_rule_id` | 前置过滤器。 |
| `boundary_warning / evidence_level / next_action` | 判定底稿。 |

样本表不得直接吸收未经过底稿和门禁的原始 MALF 输出。

### Step 7. 制度改造保持后置

进入制度约束前，先审计结构资格样本是否已经具备独立 Method / PM 计划：

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-method-pm-readiness
```

该命令只检查 Method / PM 分层准备度，不生成动作、不生成仓位、不写 A 股规则：

| 字段 | 必须值或含义 |
|---|---|
| `method_pm_ready_count` | 已通过 `method_pm_bridge_gate` 的样本数量。 |
| `method_pm_review_required_count` | 需要人工 Method / PM 复核的样本数量。 |
| `method_pm_review_items` | 每个待复核样本的缺失字段、阻断理由和下一步。 |
| `method_pm_auto_generation_allowed` | 固定为 `false`；不得由 MALF 自动生成 Method / PM 动作。 |
| `malf_action_backflow_allowed` | 固定为 `false`；不得让中心单、锁单、加码、认错等回流污染 MALF。 |
| `institution_adaptation_allowed` | 固定为 `false`，直到 Backtest Input 和总闸门通过。 |

人工补 Method / PM 计划时，先把草案写成 JSON，然后运行：

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-method-pm-plan-draft <method-pm-plan.json>
```

草案最小字段：

| 字段 | 要求 |
|---|---|
| `ashare_sample_id / ts_code` | 指向已通过结构资格链路的样本。 |
| `method_action` | 必须来自 Method 受控动作表。 |
| `method_status` | `observed / inferred / hypothesis`。 |
| `method_reason` | 非空列表，必须是 Method 层理由，不得写 MALF 自动裁决。 |
| `pm_required` | 显式 `true / false`。 |
| `pm_action` | 当 `pm_required=true` 时必填，且来自 PM 受控动作表。 |
| `execution_intent / execution_event_type` | 声明是观察回放、假设回放还是审计；可执行回放必须有事件类型。 |
| `method_evidence_ref` | 非空列表，指向人工计划证据。 |

该草案审计允许 Method / PM 人工计划进入 `method_pm_bridge_gate`，但仍禁止 `center_position_from_malf / target_position_from_malf / lock_confirmed_by_malf / buy_signal / trade_accept` 等字段。

若有多条人工计划草案，可放入一个目录后批量合流：

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-method-pm-plan-merge <method-pm-plan-dir>
```

该命令按 `ashare_sample_id` 匹配 `method_pm_review_items`。匹配且通过草案契约的样本可进入 Backtest Input 快照准备；未匹配或草案不合格的样本继续停在 `action:method_pm_review`。

然后审计是否可以进入 Backtest Input 快照准备：

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-backtest-input-readiness
```

该命令不得绕过 Method / PM：

| 字段 | 必须值或含义 |
|---|---|
| `backtest_input_ready_count` | 可进入 Backtest Input 快照准备的样本数量。 |
| `backtest_input_blocked_count` | 因 Method / PM 或其他前置条件未满足而阻断的样本数量。 |
| `backtest_input_blocked_items` | 每个阻断样本的 blocker、下一步和边界警告。 |
| `backtest_input_snapshot_allowed` | 只有前置条件通过时才可为 `true`。 |
| `institution_adaptation_allowed` | 固定为 `false`，直到总闸门明确允许。 |

若 Method / PM 计划合流已通过，可生成只读 Backtest Input 快照草案：

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-backtest-input-snapshots <method-pm-plan-dir>
```

该命令只生成 `TachibanaBacktestInputSnapshot` 草案，不写正式数据目录、不生成 Signal、不启动 A 股制度规则：

| 字段 | 必须值或含义 |
|---|---|
| `backtest_input_snapshot_count` | 生成的快照草案数量。 |
| `backtest_input_snapshots` | 每条草案携带结构资格字段、人工 Method / PM 计划、`candidate_table_gate / method_pm_bridge_gate / backtest_input_gate`。 |
| `backtest_input_gate_result` | 必须为 `pass` 才能作为可执行型 Backtest Input 草案。 |
| `backtest_input_snapshot_allowed` | 只有所有草案通过 `backtest_input_gate` 时才为 `true`。 |
| `institution_adaptation_allowed` | 固定为 `false`；快照草案之后才讨论制度约束闸门。 |

快照草案不得包含 `signal_decision / trade_accept / target_position / ashare_t1_action`。若这些字段出现，说明 Backtest Input 已被 Signal 或制度规则污染，应退回 Method / PM 草案或接口边界审计。

快照草案通过后，再运行制度约束启动闸门：

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-institution-constraint-gate <method-pm-plan-dir>
```

该命令只回答“能不能开始审计执行可行性”，不定义 T+1、涨跌停、停牌、撮合或仓位缩放规则：

| 字段 | 必须值或含义 |
|---|---|
| `institution_constraint_audit_allowed` | 是否允许进入制度约束审计。 |
| `institution_rule_definition_allowed` | 固定为 `false`；本闸门不让制度规则转正。 |
| `signal_generation_allowed` | 固定为 `false`；制度约束不得生成 Signal。 |
| `allowed_constraint_scope` | 通过时只能是 `execution_feasibility_audit`。 |
| `boundary_warning` | 必须提醒不得在本闸门定义 T+1/涨跌停规则，也不得用制度结果改写结构资格。 |

若该闸门返回 `blocked`，只能按 `next_action` 清洗 Backtest Input 或回到前置层；不得因为制度问题倒逼修改 MALF、Method、PM 或 Signal。

制度约束启动闸门通过后，先生成只读执行可行性审计底稿：

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-institution-feasibility-records <method-pm-plan-dir>
```

在没有真实制度事实输入前，该底稿必须保持 `pending_constraint_evidence`，不得直接判断可成交、不可成交或应调整仓位：

| 字段 | 必须值或含义 |
|---|---|
| `record_type` | `AShareExecutionFeasibilityAudit`。 |
| `planned_event` | 来自 Backtest Input 的计划执行事件。 |
| `executable_status` | 当前固定为 `pending_constraint_evidence`。 |
| `blocked_reason` | 当前包含 `institution_constraint_evidence_not_loaded`。 |
| `carry_forward_required` | `true`，表示需要补制度事实后再判断执行可行性。 |
| `constraint_snapshot_ref` | 当前为 `null`，等待真实约束快照引用。 |

该底稿不能包含 `signal_decision / trade_accept / target_position / structure_suitable / rhythm_meaning`。这些字段一旦出现，说明制度审计层开始侵入 Signal 或结构资格，应退回清洗。

即使样本进入 `tachibana_candidate`，也只表示可以进入 Method / PM 讨论。只有满足以下条件，才允许启动 A 股制度约束审计：

| 条件 | 说明 |
|---|---|
| `method_pm_bridge_gate.result=pass` | Method / PM 已形成独立动作和仓位语义。 |
| `backtest_input_gate.result=pass` | 已具备可回测输入。 |
| `institution_constraint_need=execution_feasibility` | 确认讨论的是执行可行性，不是结构资格。 |
| `cognitive_pipeline_gate.result=pass` | 总闸门允许进入制度约束审计。 |

在此之前，T+1、涨跌停、停牌等内容只能保持候选约束，不得转正。

## 首批作业验收表

| 阶段 | 机器证据 | 人工复核 | 允许升级 |
|---|---|---|---|
| 数据落盘 | 四类路径存在。 | 来源、窗口、禁止字段确认。 | `universe_candidate` |
| 接入包验收 | `ashare_intake_validator` 输出 `pass/warn`。 | `failed_contract_items` 无结构阻断。 | `structure_candidate` |
| MALF 快照 | `snapshot_quality_status=ready`。 | 结构背景和证据引用可追溯。 | 运行前置过滤器 |
| 前置过滤器 | `front_filter_result=pass`。 | `boundary_warning` 没被删改。 | 生成判定底稿 |
| 判定底稿 | `candidate_table_gate=pass`。 | 理由码、证据等级和边界警告可复核。 | 试填样本表 |
| Method / PM | `method_pm_bridge_gate=pass`。 | 动作和仓位语义不回写 MALF。 | Backtest Input |
| Backtest Input | `backtest_input_gate=pass`。 | 适配层快照不是 Signal，不含制度规则。 | 制度约束闸门 |
| 制度约束 | `cognitive_pipeline_gate=pass`。 | 确认为执行可行性问题。 | 启动制度审计 |

## readiness 输出字段

`--audit-first-batch-readiness` 的输出应作为首批样本接入的操作索引：

| 字段 | 含义 |
|---|---|
| `front_filter_ready_candidate_count` | 当前已经可以进入前置过滤器的候选数量。 |
| `front_filter_ready_candidates` | 每个候选的 `ts_code`、`symbol_name`、`candidate_stage_after`、`next_action`、`malf_snapshot_ref`、`malf_snapshot_file`、建议样本编号、前置过滤器建议命令与判定底稿草案建议命令。 |
| `first_batch_ready_for_front_filter` | 是否允许按该清单运行 `tachibana_front_filter --snapshot ...`。 |
| `institution_adaptation_allowed` | 固定为 `false`，提醒制度约束仍后置。 |

该清单只定位下一步要处理的 MALF snapshot，不等于结构适用性结论，也不等于候选样本表更新许可。`front_filter_command` 与 `record_draft_command` 使用 `<data_root>` 占位符；真实执行时替换为正式数据根目录。`ashare_sample_id_suggestion` 由 `ts_code / window_start / window_end` 生成，用于判定底稿草案，例如：

```powershell
$env:PYTHONPATH='src'; python -m tachibana_front_filter --snapshot Z:\asteria-trading-labs-data\ashare\malf-snapshots-v0.1\<ts_code>-<window>.json
$env:PYTHONPATH='src'; python -m tachibana_front_filter --snapshot Z:\asteria-trading-labs-data\ashare\malf-snapshots-v0.1\<ts_code>-<window>.json --record-draft --ashare-sample-id <ashare_sample_id_suggestion> --symbol-name "<symbol_name>"
```

`record_draft_command` 只生成结构资格判定底稿草案。草案仍必须通过 `record_consistency / rhythm_sample_row_gate / candidate_table_gate`，才允许试填 A 股结构资格样本表。

## batch front-filter 输出字段

`--audit-first-batch-front-filter-run` 的输出应作为首批样本从 `structure_candidate` 进入“判定底稿复核”的批量过闸记录：

| 字段 | 含义 |
|---|---|
| `front_filter_run_count` | 本轮根据 readiness 清单完成前置过滤器判定的候选数量。 |
| `front_filter_results` | 每个候选的结构资格结果、理由码、建议下一步和建议样本编号。 |
| `candidate_table_update_allowed` | 固定为 `false`，说明批量过闸不直接写样本表。 |
| `institution_adaptation_allowed` | 固定为 `false`，说明仍未进入 T+1、涨跌停、停牌等制度适配。 |

该输出可以告诉我们哪些样本值得生成 `record-draft`，但不能替代判定底稿、Method / PM 动作解释或 Backtest Input。若单个候选的 `next_action=action:fill_qualification_record`，下一步才是生成结构资格判定底稿草案；若为补证、研究审计或不适用，则按前置过滤器结果保留原阶段。

## batch record-drafts 输出字段

`--audit-first-batch-record-drafts` 的输出应作为首批样本进入人工底稿复核的集合，不是样本表写入动作：

| 字段 | 含义 |
|---|---|
| `record_draft_count` | 本轮可复核底稿草案数量。 |
| `record_drafts` | 每条草案包含 `ashare_sample_id / ts_code / symbol_name / rhythm_meaning / tachibana_applicability / qualification_rule_id / boundary_warning` 与各级 gate。 |
| `candidate_table_update_allowed` | 固定为 `false`，提醒样本表仍需人工复核后试填。 |
| `institution_adaptation_allowed` | 固定为 `false`，提醒制度约束仍未启动。 |

底稿草案中的 `candidate_table_gate=pass` 只表示“可进入样本表试填复核”，不是自动写入许可；`cognitive_pipeline_gate=blocked` 在此阶段是正常结果，因为 Method / PM 动作解释和 Backtest Input 尚未完成。

## sample-table trial 输出字段

`--audit-first-batch-sample-table-trial` 的输出应作为人工试填 A 股结构资格样本表前的只读复核清单：

| 字段 | 含义 |
|---|---|
| `trial_row_count` | 可进入人工试填复核的结构资格样本行数量。 |
| `trial_rows` | 每行只包含 `ashare_sample_id / ts_code / symbol_name / sample_window_start / sample_window_end / candidate_stage / malf_snapshot_ref / malf_background / rhythm_meaning / tachibana_applicability / qualification_rule_id / boundary_warning / evidence_level / next_action` 等结构资格字段。 |
| `candidate_table_write_mode` | 固定为 `manual_review_only`，说明必须人工复核后试填。 |
| `candidate_table_update_allowed` | 固定为 `false`，说明该命令不写样本表。 |
| `institution_adaptation_allowed` | 固定为 `false`，说明仍未进入制度适配。 |

`trial_rows` 不能包含 `buy_signal / trade_accept / target_position / ashare_t1_action`。如果这些字段出现，应视为接口边界污染，回到底稿或前置过滤器修正。

## Method/PM readiness 输出字段

`--audit-first-batch-method-pm-readiness` 的输出应作为首批样本进入 Method / PM 人工计划复核的只读索引：

| 字段 | 含义 |
|---|---|
| `method_pm_ready_count` | 已具备独立 Method / PM 计划、可进入 Backtest Input 的样本数量。 |
| `method_pm_review_required_count` | 仍需补 Method 动作、Method 状态、Method 理由、执行意图或 PM 动作的样本数量。 |
| `method_pm_review_items` | 每条待复核项保留结构资格背景、缺失字段、阻断理由和 `action:method_pm_review`。 |
| `method_pm_auto_generation_allowed` | 固定为 `false`，防止由 MALF 或样本表自动生成动作。 |
| `malf_action_backflow_allowed` | 固定为 `false`，防止 Method / PM 动作回流修改 MALF。 |

若该审计返回 `blocked`，说明下一步是补独立 Method / PM 计划，而不是修改 MALF 定义或提前讨论 T+1、涨跌停、停牌。

## Method/PM plan draft 输出字段

`--audit-method-pm-plan-draft <json>` 的输出应作为人工 Method / PM 草案进入 Backtest Input 前的单条契约审计：

| 字段 | 含义 |
|---|---|
| `method_pm_bridge_gate` | 底层 Method / PM 桥接门结果。 |
| `required_fields_checked` | 草案必须提供或显式说明的字段清单。 |
| `method_pm_auto_generation_allowed` | 固定为 `false`，说明动作不得由 MALF 自动生成。 |
| `malf_action_backflow_allowed` | 固定为 `false`，说明 Method / PM 动作不得回写 MALF。 |
| `next_action` | `pass` 时进入 `action:build_backtest_input_snapshot`，否则回到 `action:method_pm_review`。 |

通过该单条草案审计后，仍需重新运行 `--audit-first-batch-method-pm-readiness` 与 `--audit-first-batch-backtest-input-readiness`，确认批量链路状态已经更新。

## Method/PM plan merge 输出字段

`--audit-first-batch-method-pm-plan-merge <dir>` 的输出应作为多条人工计划草案合流后的只读状态：

| 字段 | 含义 |
|---|---|
| `method_pm_plan_ready_count` | 与待复核样本匹配且草案契约通过的数量。 |
| `method_pm_plan_blocked_count` | 匹配到了草案但草案契约未通过的数量。 |
| `unmatched_review_count` | 仍没有匹配人工计划草案的待复核样本数量。 |
| `method_pm_plan_ready_items` | 可进入 Backtest Input 快照准备的 Method / PM 计划索引。 |
| `backtest_input_snapshot_allowed` | 是否允许进入 Backtest Input 快照准备。 |
| `institution_adaptation_allowed` | 固定为 `false`，说明即使合流成功也还未进入制度适配。 |

该合流命令不写入正式数据目录，不修改结构资格样本表，不生成 Method / PM 动作；它只校验人工草案是否足以让链路继续。

## Backtest Input snapshot draft 输出字段

`--audit-first-batch-backtest-input-snapshots <dir>` 的输出应作为首批样本进入制度约束闸门前的只读 Backtest Input 草案集合：

| 字段 | 含义 |
|---|---|
| `backtest_input_snapshot_count` | 本轮生成的 Backtest Input 快照草案数量。 |
| `backtest_input_snapshots` | 每条草案包含 `adapter_version / snapshot_granularity / mode / sample_id / ts_code / malf_snapshot_ref / rhythm_meaning / qualification_rule_id / method_action / pm_required / execution_intent` 等适配层字段。 |
| `candidate_table_gate` | 证明该样本来自已通过结构资格样本表门禁的试填行。 |
| `method_pm_bridge_gate` | 证明动作与仓位语义来自独立 Method / PM 计划，而不是 MALF 回流。 |
| `backtest_input_gate` | 证明快照草案具备 Backtest Input 条件。 |
| `backtest_input_snapshot_allowed` | 是否允许把该草案交给后续制度约束闸门审计。 |
| `institution_adaptation_allowed` | 固定为 `false`；本命令不处理 T+1、涨跌停、停牌或整手约束。 |

该输出是 “结构资格 -> Method/PM -> Backtest Input” 的适配层证据，不是 `TradeDecisionSnapshot`。它不能携带 `signal_decision / trade_accept / target_position / ashare_t1_action`，也不能把 `rhythm_meaning=meaningful` 改写成买入许可。

## institution constraint gate 输出字段

`--audit-first-batch-institution-constraint-gate <dir>` 的输出应作为 A 股制度约束复核前的最后一道启动闸门：

| 字段 | 含义 |
|---|---|
| `institution_gate_count` | 本轮通过制度约束启动闸门的样本数量。 |
| `institution_gate_items` | 每条通过项的 `ashare_sample_id / ts_code / malf_snapshot_ref / qualification_rule_id / gate_status / allowed_constraint_scope`。 |
| `institution_gate_blocked_items` | 被阻断项及其 `issues / next_action`。 |
| `institution_constraint_audit_allowed` | 是否允许进入 A 股制度约束审计。 |
| `institution_rule_definition_allowed` | 固定为 `false`；该命令不定义 T+1、涨跌停、停牌规则。 |
| `signal_generation_allowed` | 固定为 `false`；该命令不输出 Signal。 |

该闸门通过，只表示可以开始调查执行可行性问题，如计划动作是否会被 T+1、涨跌停、停牌或整手约束影响。它不代表任何制度规则已经转正，也不允许把执行失败反写为结构失败。

## institution feasibility records 输出字段

`--audit-first-batch-institution-feasibility-records <dir>` 的输出应作为收集真实制度约束证据前的只读审计底稿：

| 字段 | 含义 |
|---|---|
| `institution_feasibility_record_count` | 本轮生成的执行可行性审计底稿数量。 |
| `institution_feasibility_records` | 每条记录包含 `record_type / ashare_sample_id / ts_code / planned_event / executable_status / blocked_reason / carry_forward_required / constraint_snapshot_ref`。 |
| `institution_rule_definition_allowed` | 固定为 `false`；记录底稿不定义制度规则。 |
| `signal_generation_allowed` | 固定为 `false`；记录底稿不生成 Signal。 |
| `backtest_execution_allowed` | 固定为 `false`；没有真实制度事实前不得进入成交和 PnL。 |

当前 v0.1 的默认状态是 `pending_constraint_evidence`。这不是阻止继续研究，而是把下一步明确成“收集制度事实”，例如交易日历、停牌、涨跌停距离、整手和成交可行性证据；只有证据进入约束快照后，才讨论最小执行规则字段。

## institution fact package 输出字段

制度事实先进入 `ashare/institution-facts-v0.1/*.csv`，再由审计层决定能否生成约束快照草案：

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-institution-fact-package
```

最小字段：

| 字段 | 含义 |
|---|---|
| `ts_code / trade_date` | 股票与交易日锚点。 |
| `is_trading_day` | 当日是否为交易日。 |
| `is_suspended` | 当日是否停牌或无法正常交易。 |
| `limit_up_price / limit_down_price` | 当日涨跌停价事实，可为空但字段必须存在。 |
| `close_limit_status` | `none / limit_up / limit_down / near_limit_up / near_limit_down / unknown`。 |
| `touched_limit_status` | `none / touched_up / touched_down / both / unknown`。 |
| `board_lot_size` | 最小交易单位事实，如 `100`。 |
| `source_ref` | 交易所、数据源或人工复核引用。 |

该事实包不得包含 `limit_up_strategy / limit_down_strategy / trade_accept / target_position / signal_decision`。验收通过只表示可以进入 `action:build_execution_constraint_snapshots`，不表示制度规则转正，也不允许用这些事实改写结构资格。

## execution constraint snapshots 输出字段

制度事实包验收通过后，可以生成只读执行约束快照草案：

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-execution-constraint-snapshots <method-pm-plan-dir> --institution-fact-root Z:\asteria-trading-labs-data
```

该快照只把制度事实与计划执行事件相连，不判断能否成交：

| 字段 | 含义 |
|---|---|
| `record_type` | `AShareExecutionConstraintSnapshot`。 |
| `constraint_ref` | 约束快照引用，如 `ASHARE-CONSTRAINT-<ts_code>-<trade_date>-v0.1`。 |
| `ts_code / trade_date` | 制度事实锚点。 |
| `constraint_type` | `trading_calendar / price_limit / board_lot`，停牌时追加 `suspension`。 |
| `affected_execution_event` | 被该事实快照引用的计划执行事件。 |
| `evidence_ref` | 制度事实来源引用。 |
| `executable_status` | 固定为 `not_evaluated`；本快照不裁决可成交性。 |
| `boundary_warning` | 必须提醒不得从约束快照推断买卖、仓位或结构资格。 |

约束快照不得包含 `trade_accept / signal_decision / target_position / ashare_t1_action / limit_up_strategy`。它只是后续执行可行性审计的事实引用，不是策略、信号或回测成交输入。

## execution feasibility gate 输出字段

约束快照草案通过复核后，可以把执行可行性审计底稿升级到证据就绪状态：

```powershell
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-execution-feasibility-gate <method-pm-plan-dir> --institution-fact-root Z:\asteria-trading-labs-data
```

该 gate 只更新审计状态，不生成交易裁决：

| 字段 | 含义 |
|---|---|
| `execution_feasibility_gate_count` | 本轮进入证据就绪状态的审计记录数量。 |
| `execution_feasibility_gate_items` | 每条记录保留 `planned_event / constraint_snapshot_ref / executable_status / blocked_reason`。 |
| `executable_status` | 通过时为 `evidence_ready`，表示制度事实已经对齐。 |
| `backtest_execution_allowed` | 固定为 `false`；证据就绪还不能进入成交和 PnL。 |
| `signal_generation_allowed` | 固定为 `false`；不得生成 Signal。 |

`evidence_ready` 不是 `trade_accept`，也不是仓位许可。下一步必须由人工或后续最小执行可行性规则审计，判断计划动作在制度事实下如何记录；在此之前，仍不得把制度事实变成买卖信号或回测成交。

## Backtest Input readiness 输出字段

`--audit-first-batch-backtest-input-readiness` 的输出应作为 Backtest Input 快照准备前的只读闸门：

| 字段 | 含义 |
|---|---|
| `backtest_input_ready_count` | 已满足 Backtest Input 前置条件的样本数量。 |
| `backtest_input_ready_items` | 可进入 `action:build_backtest_input_snapshot` 的样本索引。 |
| `backtest_input_blocked_count` | 被挡在 Backtest Input 前的样本数量。 |
| `backtest_input_blocked_items` | 每条阻断项说明是否因 `method_pm_not_ready` 等原因停留。 |
| `backtest_input_snapshot_allowed` | 是否允许生成 Backtest Input 快照。 |

若该审计因为 `method_pm_not_ready` 返回 `blocked`，只能回到 `action:method_pm_review`。不得从 `trial_rows` 或结构资格样本表直接生成回测输入，也不得进入 A 股制度约束。

## cognitive pipeline 输出字段

`--audit-first-batch-cognitive-pipeline` 的输出应作为首批认知管线的总闸门状态：

| 字段 | 含义 |
|---|---|
| `current_blocking_layer` | 当前最早阻断层，如 `readiness / method_pm_readiness / backtest_input_readiness`。 |
| `next_action` | 当前应执行的下一步动作。 |
| `pipeline_summary` | `readiness -> front_filter_run -> record_drafts -> sample_table_trial -> method_pm_readiness -> backtest_input_readiness` 的逐层结果。 |
| `blocking_evidence` | 当前阻断相关证据，如 Method / PM 待复核数量、Backtest Input 阻断数量、是否允许快照。 |
| `institution_adaptation_allowed` | 固定在总闸门明确通过前为 `false`。 |
| `structure_to_institution_transition_allowed` | 总闸门是否允许从结构资格链路进入制度约束链路。 |

如果 `current_blocking_layer=method_pm_readiness`，说明结构资格链路已经能走到样本表试填复核，但仍需补独立 Method / PM 计划；如果 `current_blocking_layer=readiness`，说明正式接入包或 ready MALF snapshot 尚未具备。

## 禁止越界清单

| 禁止事项 | 正确处理 |
|---|---|
| 用行业、流动性、题材或涨跌幅直接升级样本。 | 只能作为 Data / Universe 事实。 |
| 用制度问题解释结构资格。 | 制度只在 Backtest Input 之后作为执行约束。 |
| 在接入包或样本表写 `buy_signal / trade_accept / target_position`。 | 这些字段属于 Signal、PM 或执行层，不属于结构资格。 |
| 把 `suitable` 当作可以买。 | `suitable` 只表示可进入 Method / PM 讨论。 |
| 把 `unsuitable` 当作看空。 | `unsuitable` 只表示不适合立花式仓位节奏。 |
| 因缺少 `not_meaningful` 反例而人工制造。 | 等真实样本出现后登记。 |

## 当前裁决

- 原五步计划继续成立，下一步是首批真实样本接入，不是规则修补。
- 首批作业的成功标准是生成可复核的 A 股结构资格判定底稿，而不是生成 A 股交易规则。
- 正式数据目录当前为空时，本作业单只作为下一轮落盘与复核入口，不产生真实个股结论。
- 只有样本通过前置过滤器、Method / PM 和 Backtest Input 后，才可能进入 A 股制度约束审计。
