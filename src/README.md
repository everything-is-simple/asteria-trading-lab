# src 占位

本目录预留给后续实现：

- 月表解析器
- 仓位状态转移规则
- 原始立花法回测引擎
- A 股适配版回测引擎

## 当前原型

- `original_tachibana/pm_state.py`：原始立花法最小 PM 状态机原型。
- `original_tachibana/performance.py`：基于 PM 回放生成权益曲线和正规绩效指标。
- `original_tachibana/major_trades.py`：按“一大笔交易”生成逐笔回测报告。
- `original_tachibana/audit_source_data.py`：审计 24 个 JSON 与 24 张源图的对应关系和账面一致性。
- `ashare_intake_validator.py`：只读复核 `Z:\asteria-trading-labs-data\ashare\` A 股最小接入包的路径、字段与禁用交易字段。
- `tachibana_front_filter.py`：只读运行 MALF-立花前置认知过滤器，输出 `rhythm_meaning / tachibana_applicability`，不输出交易或仓位字段。
- `data_sources/tdx_local/first_batch.py`：基于 Tongdaxin + DuckDB 主账本生成首批真实 A 股样本接入包，并复用现有只读 gate 做样本覆盖审计。
- `data_sources/tdx_local/institution_facts.py`：从本地 DuckDB `tradability_fact` 生成最小 A 股制度事实包，只用于把执行证据链路通到 `evidence_ready`。
- `tests/fixtures/ashare-intake-ready/`：非真实 A 股最小接入包 fixture，只用于验证 ready 接入包仍必须停在 `structure_candidate` 并进入前置过滤器。
- `tests/fixtures/front-filter/`：非真实 MALF snapshot fixture，只用于验证前置过滤器输出契约。
- 输出目标：`data/pioneer-1975-1976/backtest-v0.1/`。
- 单笔报告目标：`docs/backtest-spec/original-tachibana-major-trades/S001.md` 至 `S015.md`。

运行：

```powershell
$env:PYTHONPATH='src'; python -m original_tachibana.pm_state
$env:PYTHONPATH='src'; python -m original_tachibana.performance
$env:PYTHONPATH='src'; python -m original_tachibana.major_trades
$env:PYTHONPATH='src'; python -m original_tachibana.audit_source_data
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-readiness
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-front-filter-run
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-record-drafts
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-sample-table-trial
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-method-pm-readiness
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-backtest-input-readiness
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-cognitive-pipeline
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-method-pm-plan-draft path\to\method-pm-plan.json
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-method-pm-plan-merge path\to\method-pm-plan-dir
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-backtest-input-snapshots path\to\method-pm-plan-dir
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-institution-constraint-gate path\to\method-pm-plan-dir
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-institution-feasibility-records path\to\method-pm-plan-dir
$env:PYTHONPATH='src'; python -m data_sources.tdx_local.institution_facts --duckdb-root Z:\malf-data --data-root Z:\asteria-trading-labs-data --ts-code 000001.SZ --ts-code 300750.SZ --ts-code 600000.SH --window-start 2026-03-24 --window-end 2026-04-03
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-institution-fact-package
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-execution-constraint-snapshots path\to\method-pm-plan-dir --institution-fact-root Z:\asteria-trading-labs-data
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-execution-feasibility-gate path\to\method-pm-plan-dir --institution-fact-root Z:\asteria-trading-labs-data
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-execution-feasibility-verdicts path\to\method-pm-plan-dir --institution-fact-root Z:\asteria-trading-labs-data
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-execution-feasibility-verdict-merge path\to\execution-feasibility-verdict-dir --method-pm-plan-dir path\to\method-pm-plan-dir --institution-fact-root Z:\asteria-trading-labs-data
$env:PYTHONPATH='src'; python -m ashare_intake_validator --root tests\fixtures\ashare-intake-ready
$env:PYTHONPATH='src'; python -m tachibana_front_filter --snapshot tests\fixtures\front-filter\alive-wave-ready.json
$env:PYTHONPATH='src'; python -m tachibana_front_filter --snapshot tests\fixtures\front-filter\alive-wave-ready.json --record-draft --ashare-sample-id ASHARE-FIXTURE-001 --symbol-name "Ping An Bank"
$env:PYTHONPATH='src'; python -m tachibana_front_filter --audit-rule-catalog
$env:PYTHONPATH='src'; python -m tachibana_front_filter --audit-rhythm-samples
$env:PYTHONPATH='src'; python -m tachibana_front_filter --audit-method-pm-actions
$env:PYTHONPATH='src'; python -m tachibana_front_filter --audit-interface-boundary
$env:PYTHONPATH='src'; python -m tachibana_front_filter --audit-front-filter-system
@'
from data_sources.tdx_local import build_first_batch_sample_package, audit_first_batch_sample_coverage
build_report = build_first_batch_sample_package(
    data_root=r"Z:\asteria-trading-labs-data",
    tdx_root=r"Z:\new_tdx64",
    offline_root=r"Z:\tdx_offline_Data",
    duckdb_root=r"Z:\malf-data",
)
coverage = audit_first_batch_sample_coverage(r"Z:\asteria-trading-labs-data")
print(build_report["result"], coverage["covered_structure_targets"], coverage["trial_row_count"])
'@ | python -
```

注意：`data_sources/tdx_local/first_batch.py` 当前生成的是“研究映射型 ready snapshot”，用于把真实样本窗口推进到前置过滤器和样本表试填链路；它不是自动 MALF 引擎，也不生成交易信号或仓位。

## 前置过滤器机器闸门

`tachibana_front_filter.py --record-draft` 会输出一组只读 gate，用于确认“结构资格先行，A 股适配后行”：

- `record_consistency`：结构资格判定记录内部一致性，不允许 MALF 结果携带交易字段。
- `rhythm_sample_row_gate`：校验单行样本的 `rhythm_meaning -> tachibana_applicability` 映射。
- `candidate_table_gate`：判断样本是否能进入 A 股候选股票结构资格样本表。
- `method_pm_bridge_gate`：判断 Method / PM 层是否已独立给出动作解释与仓位节奏，不允许中心单、锁单、加码等回流污染 MALF。
- `interface_boundary_gate`：检查 Data / Signal / Backtest 是否越界写入结构裁决或交易裁决。
- `backtest_input_gate`：判断是否可生成 Tachibana Backtest Input。
- `cognitive_pipeline_gate`：总闸门；只有接入包契约、MALF 资格、结构资格、Method/PM、接口边界与回测输入全部通过，才允许进入 A 股制度约束审计。

`cognitive_pipeline_gate=pass` 只表示可以开始审计 T+1、涨跌停、停牌等制度约束，不表示这些制度规则已经成为方法定义。

资格理由码集中在 `get_qualification_rule_catalog()`，并由 `rhythm_sample_row_gate` 复核。任何 `qualification_rule_id` 都必须在目录中声明对应的 `rhythm_meaning`、`tachibana_applicability`、`pm_complexity`、`pm_required` 与候选阶段，避免理由码和结构资格样本表各说各话。

`audit_qualification_rule_catalog()` 会复核理由码目录本身。当前 `LIMITED_REQUIRED_RULES` 和 `NOT_MEANINGFUL_RULES` 内的理由码已经全部进入目录；后续新增理由码时必须先补目录定义，否则审计会回到 `blocked`。

最小代表样本集中在 `get_rhythm_sample_catalog()`，并由 `audit_rhythm_sample_catalog()` 批量复核。当前机器样本目录为每个已定义 `qualification_rule_id` 至少保留一条代表样本行，并检查 `covered_rule_ids / missing_rule_ids`；完整历史样本仍以 `docs/tachibana/index/MALF-立花结构资格样本表-v0.1.md` 为人工研究主表。

Method / PM 动作目录集中在 `get_method_action_catalog()` 与 `get_pm_action_catalog()`，并由 `audit_method_pm_action_catalog()` 复核。所有动作都声明 `malf_can_generate=false`：MALF 可以提供结构资格背景，但不能直接生成试仓、加码、中心单、锁单、解锁、清仓或持有动作。

Data / Signal / Backtest 接口边界集中在 `get_interface_boundary_catalog()`，并由 `audit_interface_boundary_catalog()` 复核。`data` 只保留事实，`signal` 不读取结构资格，`backtest` 只消费适配层输出，`tachibana_adapter` 只写结构资格而不写交易裁决。

`audit_front_filter_system()` 聚合以上四类审计，作为 MALF-立花前置认知过滤器的一键总审计。只有理由码目录、样本覆盖、Method/PM 动作边界和接口边界全部通过时，它才返回 `pass`。

`--record-draft` 输出会携带 `front_filter_system_audit`，`cognitive_pipeline_gate` 也要求该系统审计为 `pass`。因此，即使单条 MALF snapshot 通过，只要前置过滤器自身目录或边界失效，A 股制度约束审计仍会被阻断。

`ashare_intake_validator.py --audit-first-batch-readiness` 聚合 `audit_front_filter_system()` 与 A 股最小接入包验收，作为首批真实样本能否进入前置过滤器的只读准备度审计。它要求接入包至少具备可运行 MALF 的数据、ready MALF snapshot，以及 `candidate_stage_after=structure_candidate / next_action=action:run_front_filter` 的阶段摘要。输出中的 `front_filter_ready_candidate_count` 与 `front_filter_ready_candidates` 会列出下一步可运行前置过滤器的候选清单，包括 `symbol_name`、`malf_snapshot_ref`、相对数据根目录的 `malf_snapshot_file`、`ashare_sample_id_suggestion`、带 `<data_root>` 占位符的 `front_filter_command`，以及生成判定底稿草案的 `record_draft_command`。该审计通过只代表可以运行前置过滤器，不代表 `eligible_for_tachibana_candidate=true`，也不允许启动 T+1、涨跌停或停牌等制度约束。

`ashare_intake_validator.py --audit-first-batch-front-filter-run` 会先复用 readiness 审计，再对 `front_filter_ready_candidates` 批量运行 MALF-立花前置过滤器。它输出 `front_filter_results`，包括每个候选的 `front_filter_result / candidate_stage_after / rhythm_meaning / tachibana_applicability / qualification_rule_id / next_action`。该命令仍是只读批量过闸：`candidate_table_update_allowed=false` 且 `institution_adaptation_allowed=false`，因此它只生成“可进入判定底稿复核”的结构结果，不直接更新样本表，也不启动制度适配。

`ashare_intake_validator.py --audit-first-batch-record-drafts` 会基于批量前置过滤器结果，只为 `front_filter_result=pass / next_action=action:fill_qualification_record` 的候选生成结构资格判定底稿草案。输出中的 `record_drafts` 带有 `record_consistency / rhythm_sample_row_gate / candidate_table_gate / cognitive_pipeline_gate`，用于人工复核是否可试填样本表。该命令同样保持 `candidate_table_update_allowed=false` 与 `institution_adaptation_allowed=false`：底稿草案不是交易许可，也不是制度适配入口。

`ashare_intake_validator.py --audit-first-batch-sample-table-trial` 会把 `record_consistency=pass / candidate_table_gate=pass` 的底稿映射成 A 股结构资格样本表试填行草案。输出中的 `trial_rows` 只包含结构资格字段，不包含 `buy_signal / trade_accept / target_position / ashare_t1_action` 等交易或制度字段。该命令的 `candidate_table_write_mode=manual_review_only`，并继续保持 `candidate_table_update_allowed=false`：它是人工试填复核闸门，不是自动写表器。

`ashare_intake_validator.py --audit-first-batch-method-pm-readiness` 会检查试填行草案是否已经具备独立的 Method / PM 计划。它调用 `method_pm_bridge_gate`，但不自动生成 `method_action / pm_action`；缺口会进入 `method_pm_review_items`。该命令固定输出 `method_pm_auto_generation_allowed=false` 与 `malf_action_backflow_allowed=false`，用于防止中心单、锁单、加码、认错等交易动作回流污染 MALF。

`ashare_intake_validator.py --audit-first-batch-backtest-input-readiness` 会检查首批样本是否可以进入 Backtest Input 快照准备。它要求 Method / PM readiness 已通过；否则只输出 `backtest_input_blocked_items`，并保持 `backtest_input_snapshot_allowed=false` 与 `institution_adaptation_allowed=false`。该命令防止用结构资格样本直接绕过 Method / PM 进入回测或制度适配。

`ashare_intake_validator.py --audit-first-batch-cognitive-pipeline` 会汇总 readiness、front-filter、record-draft、sample-table trial、Method/PM readiness 与 Backtest Input readiness 的结果，输出 `current_blocking_layer / next_action / pipeline_summary / blocking_evidence`。它是一键总状态闸门；只有所有前置层通过后，才可能进入制度约束复核。当前任何阻断态都会保持 `institution_adaptation_allowed=false` 与 `structure_to_institution_transition_allowed=false`。

`ashare_intake_validator.py --audit-method-pm-plan-draft <json>` 会审计一条人工 Method / PM 计划草案。草案必须提供 `ashare_sample_id / ts_code / method_action / method_status / method_reason / pm_required / execution_intent / execution_event_type / method_evidence_ref`，当 `pm_required=true` 时还必须提供受控 `pm_action`。该命令复用 `method_pm_bridge_gate`，并额外要求 `method_evidence_ref`，同时固定 `method_pm_auto_generation_allowed=false / malf_action_backflow_allowed=false`。

`ashare_intake_validator.py --audit-first-batch-method-pm-plan-merge <dir>` 会读取目录内的人工 Method / PM 草案 JSON，按 `ashare_sample_id` 与首批 `method_pm_review_items` 合流。匹配且通过草案契约的样本会进入 `method_pm_plan_ready_items`，并让 `backtest_input_snapshot_allowed=true`；未匹配或草案不合格的样本继续停在 `action:method_pm_review`。该命令仍是只读合流，不写数据目录，也不允许制度适配。

`ashare_intake_validator.py --audit-first-batch-backtest-input-snapshots <dir>` 会在 Method / PM 计划合流通过后，生成只读 `TachibanaBacktestInputSnapshot` 草案。输出中的 `backtest_input_snapshots` 会携带结构资格字段、人工 Method / PM 计划、`candidate_table_gate / method_pm_bridge_gate / backtest_input_gate`，并保持 `institution_adaptation_allowed=false`。该快照不是 Signal，不包含 `signal_decision / trade_accept / target_position / ashare_t1_action`，也不启动 T+1、涨跌停或停牌规则。

`ashare_intake_validator.py --audit-first-batch-institution-constraint-gate <dir>` 会在 Backtest Input 快照草案通过后，审计是否允许进入 A 股制度约束复核。它只允许 `execution_feasibility_audit` 范围，固定 `institution_rule_definition_allowed=false / signal_generation_allowed=false`，并阻断已经混入 `ashare_t1_action / limit_up_strategy / trade_accept / signal_decision` 等字段的快照。

`ashare_intake_validator.py --audit-first-batch-institution-feasibility-records <dir>` 会在制度约束启动闸门通过后，生成只读 `AShareExecutionFeasibilityAudit` 底稿。当前没有真实制度事实输入时，记录必须停在 `executable_status=pending_constraint_evidence`，并输出 `next_action=action:collect_institution_constraint_evidence`。该命令不允许回测执行，不定义 A 股规则，也不把制度问题反写成结构资格判断。

`ashare_intake_validator.py --audit-institution-fact-package` 会验收 `ashare/institution-facts-v0.1/*.csv` 制度事实包。该包只允许记录交易日、停牌、涨跌停价、触及/收盘涨跌停状态、整手单位与来源引用；不得出现 `limit_up_strategy / trade_accept / target_position` 等策略、Signal 或仓位字段。通过只表示可以生成执行约束快照草案，不表示 A 股规则已经转正。

`data_sources.tdx_local.institution_facts` 会从本地 DuckDB `market_meta.tradability_fact` 按 `ts_code + window` 生成最小制度事实包。当前最小通电策略只使用可交易性事实：`limit_up_price / limit_down_price` 留空，`close_limit_status / touched_limit_status=unknown`，`board_lot_size=100`。它不计算完整涨跌停价，不引入 AkShare / Baostock，也不生成任何交易许可。

`ashare_intake_validator.py --audit-first-batch-execution-constraint-snapshots <dir> --institution-fact-root <root>` 会把已通过制度事实包验收的事实行，映射成只读 `AShareExecutionConstraintSnapshot` 草案。快照只引用 `constraint_ref / ts_code / trade_date / constraint_type / affected_execution_event / evidence_ref` 等事实字段，固定 `executable_status=not_evaluated`，因此不能直接驱动成交、PnL 或仓位调整。

`ashare_intake_validator.py --audit-first-batch-execution-feasibility-gate <dir> --institution-fact-root <root>` 会把已匹配约束快照的 `AShareExecutionFeasibilityAudit` 从 `pending_constraint_evidence` 升级为 `evidence_ready`。`evidence_ready` 只表示制度事实证据已经对齐，仍固定 `backtest_execution_allowed=false / signal_generation_allowed=false`，不得解释成 `trade_accept`、仓位许可或成交许可。

`ashare_intake_validator.py --audit-first-batch-execution-feasibility-verdicts <dir> --institution-fact-root <root>` 会在 `evidence_ready` 后生成只读 `AShareExecutionFeasibilityVerdict` 人工复核草案。草案只允许 `not_evaluated / evidence_ready / executable / constrained / blocked / carry_forward_required / blocked_by_fact_review` 这些执行事实状态，默认停在 `feasibility_status=not_evaluated`，并继续固定 `institution_rule_definition_allowed=false / signal_generation_allowed=false / backtest_execution_allowed=false`。该命令不得输出 `buy_signal / trade_accept / target_position / position_size / ashare_t1_action / limit_up_strategy`。

`ashare_intake_validator.py --audit-first-batch-execution-feasibility-verdict-merge <review-dir> --method-pm-plan-dir <plan-dir> --institution-fact-root <root>` 会把人工填写的执行可行性裁决 JSON 合流回只读 verdict 层。人工复核只允许填写 `not_evaluated / executable / constrained / blocked / carry_forward_required`，不得复写系统态 `evidence_ready / blocked_by_fact_review`，也不得混入 `buy_signal / trade_accept / target_position / position_size / ashare_t1_action / limit_up_strategy`。合流通过后，输出仍只表达“执行事实状态”，不会生成信号、仓位或成交许可。
