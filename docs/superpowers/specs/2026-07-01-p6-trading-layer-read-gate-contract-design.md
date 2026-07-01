# P6 Trading Layer Read Gate Contract 设计

**日期：** 2026-07-01
**状态：** 待评审草案
**范围：** P5 formal candidate table readiness audit 之后、真实 trading layer read 开放之前的只读 consumer contract 设计

## 1. 当前系统位置

当前系统位置是：

`candidate_table_trading_layer_readiness_audit_passed`

P5 已经证明 formal candidate table 的 `manifest.json` 与 `candidate-table.jsonl` 在结构上可进入未来 trading layer read gate review。

P5 pass 的含义是：

`ready_for_trading_layer_read_gate_review`

它不表示：

- trading layer 已经可以读取；
- institution rule definition 已经开放；
- signal generation 已经开放；
- backtest execution 已经开放；
- candidate table row 已经可以变成交易决策。

P6 从这个位置开始。

## 2. P6 目标

P6 定义 trading layer read gate / consumer contract。

这个 contract 回答一个窄问题：

> 未来 trading layer 若要读取 formal candidate table，它必须先看到哪些前置 artifact、审计哪些边界、在什么情况下 blocked，以及 pass 后仍然不能做什么？

P6 第一版仍是规格设计，不开放真实 trading layer read。

当前建议：P6 pass 仍保持 `trading_layer_read_allowed=False`，只推进到：

`ready_for_trading_layer_read_contract_review`

## 3. 设计决策

| 问题 | 决策 |
|---|---|
| 上游候选表证明 | 必须消费 P5 `candidate_table_trading_layer_readiness_audit_v0.1` pass report |
| Method/PM 前置 | 必须存在 `method_pm_bridge_gate` pass 或等价 Method/PM plan readiness |
| Backtest Input 前置 | 必须存在 `backtest_input_gate` pass 或等价 Backtest Input readiness |
| 制度约束输入 | 只能读取 `execution_constraint_snapshot` / `execution_feasibility_verdict` / outcome / policy archive 这类 audit-only artifact |
| P6 pass 含义 | consumer contract 已准备进入 review，不代表真实 trading layer read 已开放 |
| 硬闸 | `institution_rule_definition_allowed=False`、`trading_layer_read_allowed=False`、`signal_generation_allowed=False`、`backtest_execution_allowed=False` |

## 4. P6 入口候选

拟新增函数：

`audit_trading_layer_read_gate_contract_when_explicitly_requested`

命名边界：

- `audit`：只做审计，不做读取激活；
- `read_gate_contract`：定义 consumer contract，不生成交易；
- `explicitly_requested`：必须显式调用，不作为 P5 pass 的自动后续动作。

## 5. P6 可以读取什么

P6 可以读取以下 artifact：

1. P5 readiness report
   - `audit_id == "candidate_table_trading_layer_readiness_audit_v0.1"`
   - `candidate_table_trading_layer_readiness_audit_result == "pass"`
   - `candidate_table_trading_layer_readiness_status == "ready_for_trading_layer_read_gate_review"`

2. Formal candidate table manifest
   - `manifest_id == "candidate_table_formal_manifest_v0.1"`
   - `candidate_table_update_target == "formal_data_root"`
   - `trading_layer_read_allowed == False`

3. Method/PM gate or readiness artifact
   - `method_pm_bridge_gate.result == "pass"`
   - 或 `method_pm_readiness == "pass"` 的等价审计结果

4. Backtest Input gate or readiness artifact
   - `backtest_input_gate.result == "pass"`
   - 或 `backtest_input_readiness == "pass"` 的等价审计结果

5. Execution constraint / feasibility audit-only artifact
   - `execution_constraint_snapshot`
   - `execution_feasibility_verdict`
   - `execution_feasibility_outcome`
   - `execution_policy_archive`
   - `execution_policy_research_agenda`

P6 不应读取：

- raw TDX files；
- DuckDB market tables；
- MALF snapshot 原始文件；
- signal artifact；
- backtest execution result；
- order / fill / position artifact。

## 6. P6 审什么

P6 必须审计：

- P5 readiness report 是否 pass；
- P5 readiness report 是否仍保持所有下游硬闸 false；
- formal candidate table manifest 是否仍是 `formal_data_root` target；
- Method/PM 是否已经独立通过，不是由 MALF 或 candidate table 自动生成；
- Backtest Input gate 是否通过，且不强造 Signal `accept`；
- execution constraint / feasibility artifact 是否只是 execution facts / audit verdict，不是 institution rules；
- 输入 payload 是否含 forbidden fields；
- 输出 report 是否不回显 forbidden input field name；
- pass 是否仍不开放真实 trading layer read。

## 7. P6 阻断什么

出现以下任一情况时，P6 必须 blocked：

- P5 readiness report 缺失；
- P5 readiness report 不是 pass；
- P5 readiness report 的 hard gate 任一为 true；
- formal candidate table manifest 缺失或不是 formal target；
- 缺 Method/PM plan 或 `method_pm_bridge_gate` 未 pass；
- 缺 Backtest Input gate 或 `backtest_input_gate` 未 pass；
- execution constraint / feasibility artifact 缺失或不是 audit-only；
- execution facts 被写成 institution rules；
- 输入中出现 forbidden fields；
- 输入把 `tachibana_applicability`、`rhythm_meaning`、`structure_suitable` 改写成交易裁决；
- 输入包含 signal、order、position、execution strategy 或 backtest result 语义。

建议 issue code：

- `trading_layer_read_gate_requires_p5_readiness_pass`
- `trading_layer_read_gate_requires_formal_candidate_table`
- `trading_layer_read_gate_requires_method_pm_gate_pass`
- `trading_layer_read_gate_requires_backtest_input_gate_pass`
- `trading_layer_read_gate_requires_execution_constraint_audit_only`
- `trading_layer_read_gate_forbidden_output_field_present`
- `trading_layer_read_gate_downstream_gate_open`
- `trading_layer_read_gate_signal_semantics_forbidden`
- `trading_layer_read_gate_backtest_execution_forbidden`

## 8. P6 输出什么

pass report 应包含：

- `result = "pass"`
- `audit_id = "trading_layer_read_gate_contract_audit_v0.1"`
- `trading_layer_read_gate_contract_audit_result = "pass"`
- `trading_layer_read_gate_contract_status = "ready_for_trading_layer_read_contract_review"`
- `candidate_table_trading_layer_readiness_audit_result = "pass"`
- `method_pm_gate_result = "pass"`
- `backtest_input_gate_result = "pass"`
- `execution_constraint_audit_only = True`
- `institution_rule_definition_allowed = False`
- `trading_layer_read_allowed = False`
- `signal_generation_allowed = False`
- `backtest_execution_allowed = False`
- `next_action = "action:review_trading_layer_read_gate_contract"`

blocked report 应包含：

- `result = "blocked"`
- `audit_id = "trading_layer_read_gate_contract_audit_v0.1"`
- `trading_layer_read_gate_contract_audit_result = "blocked"`
- `trading_layer_read_gate_contract_status = "blocked_before_trading_layer_read_contract_review"`
- `issues`
- `institution_rule_definition_allowed = False`
- `trading_layer_read_allowed = False`
- `signal_generation_allowed = False`
- `backtest_execution_allowed = False`
- `next_action = "action:repair_trading_layer_read_gate_contract_inputs"`

blocked report 不得回显 forbidden input field name。

## 9. 非目标

P6 不得：

- 打开真实 `trading_layer_read_allowed`；
- 生成 `TradeDecisionSnapshot`；
- 生成 Signal `accept / reject / defer`；
- 生成 buy / sell signal；
- 生成仓位或目标仓位；
- 生成 order / fill / execution result；
- 定义 T+1、涨跌停、停复牌正式规则；
- 运行 backtest；
- 用执行约束反向改写 MALF、`rhythm_meaning`、`tachibana_applicability` 或 `structure_suitable`。

## 10. 测试要求

未来实施计划至少应新增：

1. pass case
   - P5 readiness pass；
   - Method/PM gate pass；
   - Backtest Input gate pass；
   - execution constraint artifact audit-only；
   - downstream gates 全部 false。

2. blocked case
   - 缺 P5 readiness report；
   - 缺 Method/PM plan；
   - 缺 Backtest Input gate；
   - execution constraint artifact 不合格。

3. forbidden field case
   - 输入混入 `buy_signal` / `trade_accept` / `target_position` / `position_size`；
   - report blocked；
   - report 不回显 forbidden field name。

4. does-not-open-trading-layer case
   - 即使 pass，仍断言：
     - `institution_rule_definition_allowed == False`
     - `trading_layer_read_allowed == False`
     - `signal_generation_allowed == False`
     - `backtest_execution_allowed == False`

推荐 focused 命令：

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_tdx_local_first_batch -v
```

如果实现触碰 A 股总审计链，追加：

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_ashare_intake_validator -v
```

全量验证：

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests
git diff --check
```

## 11. 实现位置候选

第一版实现建议优先放在：

`src/data_sources/tdx_local/first_batch.py`

原因：

- P5 readiness audit 已在该文件；
- formal candidate table 后续 gate 与 P5 相邻；
- 可复用 existing forbidden-field helper 与 JSON helper；
- 测试可继续使用临时目录，不触碰真实数据根。

公共函数应从：

`src/data_sources/tdx_local/__init__.py`

导出。

如果后续需要把 Method/PM、Backtest Input、execution policy research agenda 串成更高层总审计视图，再考虑在：

`src/ashare_intake_validator.py`

新增独立总协调入口。

## 12. 完成定义

P6 规格完成条件：

- 本设计文档通过 review；
- 明确 P6 第一版仍不开放真实 trading layer read；
- 明确读取来源、审计对象、阻断条件、输出契约；
- 明确 P6 与 P7 制度规则定义、P8 signal/backtest 的边界；
- 明确测试要求和实现候选位置。

P6 实现完成条件另行由 implementation plan 定义。
