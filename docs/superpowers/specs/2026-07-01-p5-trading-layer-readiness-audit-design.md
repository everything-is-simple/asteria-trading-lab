# P5 Trading Layer Readiness Audit 设计

**日期：** 2026-07-01
**状态：** 已实现并测试通过，归档为 P5 设计依据
**范围：** formal candidate table 写入完成之后、任何 trading layer read 开放之前的只读 readiness audit

## 0. 归档说明

本规格已完成评审、实施计划、代码实现、导出与测试。

已实现入口：

`audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested`

当前归档结论：

- P5 pass 只表示 `ready_for_trading_layer_read_gate_review`。
- `trading_layer_read_allowed` 仍保持 `False`。
- `institution_rule_definition_allowed`、`signal_generation_allowed`、`backtest_execution_allowed` 仍保持 `False`。
- 本规格不再是待评审草案；后续工作已转入 P6 trading layer read gate / consumer contract。

## 1. 当前系统位置

当前系统位置是：

`formal_candidate_table_update_performed`

P4c 已经定义并实现 formal candidate table 写入边界。它消费 P4b staging candidate table manifest，并写入：

```text
<formal_data_root>/
  ashare/
    candidate-table-v0.1/
      manifest.json
      candidate-table.jsonl
```

P4c 证明了 formal candidate table 可以在显式人工确认、备份、回滚和所有下游硬闸关闭的前提下写入。

P5 从这个位置开始。

## 2. P5 目标

P5 定义 formal candidate table 的 trading layer readiness audit。

这个 audit 只回答一个窄问题：

> formal candidate table 在结构上是否已经准备好，进入未来的 trading layer read gate review？

P5 不开放 trading layer read。不定义制度规则。不生成 signal。不运行 backtest。

## 3. 设计决策

| 问题 | 决策 |
|---|---|
| 读取来源 | `<formal_data_root>/ashare/candidate-table-v0.1/` 下的 formal candidate table manifest 和 JSONL |
| 写入行为 | 只返回只读 audit report；P5 函数不写任何文件 |
| pass 含义 | candidate table 已准备进入下一步人工/规格评审，不代表可交易执行 |
| Trading layer 硬闸 | pass 和 blocked 结果中 `trading_layer_read_allowed` 都保持 `False` |
| Signal/backtest 硬闸 | `signal_generation_allowed=False` 和 `backtest_execution_allowed=False` 始终保持 |
| Institution rule 硬闸 | `institution_rule_definition_allowed=False` 始终保持 |

## 4. P5 入口

拟新增函数：

`audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested`

这个命名编码四条边界：

- 它是 audit，不是 activation；
- 它检查 trading layer readiness，不检查 signal readiness；
- 它消费 candidate table artifact，不消费 raw market data；
- 它只在调用方显式请求时运行。

## 5. 输入

函数接受：

- `formal_candidate_table_manifest_path`：指向 `<formal_data_root>/ashare/candidate-table-v0.1/manifest.json`
- 可选 `generated_at`

函数从 manifest 所在目录和 manifest 字段 `candidate_table_file` 推导 `candidate-table.jsonl`。

函数不应接受或读取：

- 通达信原始文件；
- DuckDB 市场表；
- MALF snapshot 文件；
- signal 文件；
- backtest 文件；
- order 或 position 文件。

## 6. P5 读取什么

P5 只读取两个 formal candidate table 文件：

```text
<formal_data_root>/ashare/candidate-table-v0.1/manifest.json
<formal_data_root>/ashare/candidate-table-v0.1/candidate-table.jsonl
```

manifest 是以下信息的权威来源：

- manifest identity；
- 期望 row count；
- candidate table 文件名；
- source staging manifest provenance；
- formal write result；
- 下游硬闸状态。

JSONL 文件是以下信息的权威来源：

- 实际 row count；
- row-level gate state；
- row identity uniqueness；
- forbidden field absence；
- formal candidate table target。

## 7. P5 审什么

manifest 必须证明：

- `manifest_id == "candidate_table_formal_manifest_v0.1"`
- `candidate_table_update_performed == True`
- `candidate_table_update_target == "formal_data_root"`
- `candidate_table_update_allowed == False`
- `trading_layer_read_allowed == False`
- `signal_generation_allowed == False`
- `backtest_execution_allowed == False`
- `candidate_table_file == "candidate-table.jsonl"`
- `candidate_table_row_count` 是正整数

每一行 JSONL row 必须证明：

- 该行是合法 JSON object；
- `candidate_table_row_id` 存在且唯一；
- `qualification_record_id` 存在；
- `ts_code` 存在；
- `candidate_table_update_performed == True`；
- `candidate_table_update_target == "formal_data_root"`；
- `candidate_table_update_allowed == False`；
- `trading_layer_read_allowed == False`；
- `signal_generation_allowed == False`；
- `backtest_execution_allowed == False`；
- 不包含任何 forbidden trading、signal、institution-rule 或 backtest 字段。

audit 还必须验证：

- JSONL 非空行数量等于 `candidate_table_row_count`；
- `candidate_table_row_id` 不重复；
- 没有 row 声称自己仍是 staging target；
- 没有 row 声称 candidate table update 本身打开了 trading read；
- report payload 不回显受污染输入 row 中的 forbidden field name。

## 8. P5 阻断什么

出现以下任一情况时，P5 返回 `result="blocked"`，且不写任何文件：

- manifest 文件不存在；
- manifest 无法解析为 JSON；
- manifest id 不是 `candidate_table_formal_manifest_v0.1`；
- manifest 指向的 candidate table JSONL 文件不存在；
- manifest 指向 manifest 目录之外的路径；
- `candidate_table_row_count` 缺失、为零、为负数，或不是整数；
- JSONL 文件为空；
- 任意 JSONL 行格式错误；
- 任意 JSONL 行不是 object；
- 实际 row count 与 manifest row count 不一致；
- `candidate_table_row_id` 重复；
- 必需 row identity 字段缺失；
- manifest 或 row 含 forbidden output fields；
- 任一下游硬闸已经为 `True`；
- 任意 row 仍标记为 `candidate_table_update_target == "staging"`；
- 任意 row 含 signal、order、position、execution、strategy 或 backtest 语义。

blocked 结果应使用稳定 issue code，包括：

- `candidate_table_formal_manifest_missing`
- `candidate_table_formal_manifest_invalid`
- `candidate_table_formal_jsonl_missing`
- `candidate_table_formal_jsonl_invalid`
- `candidate_table_formal_row_count_mismatch`
- `candidate_table_formal_duplicate_row_id`
- `candidate_table_formal_required_field_missing`
- `candidate_table_trading_readiness_forbidden_output_field_present`
- `candidate_table_trading_readiness_downstream_gate_open`
- `candidate_table_trading_readiness_not_formal_target`

## 9. P5 输出什么

pass 时，report 应包含：

- `result = "pass"`
- `audit_id = "candidate_table_trading_layer_readiness_audit_v0.1"`
- `candidate_table_trading_layer_readiness_audit_result = "pass"`
- `candidate_table_trading_layer_readiness_checked = True`
- `candidate_table_trading_layer_readiness_status = "ready_for_trading_layer_read_gate_review"`
- `formal_candidate_table_manifest_path`
- `formal_candidate_table_path`
- `candidate_table_row_count`
- `candidate_table_update_performed = True`
- `candidate_table_update_target = "formal_data_root"`
- `candidate_table_update_allowed = False`
- `institution_rule_definition_allowed = False`
- `trading_layer_read_allowed = False`
- `signal_generation_allowed = False`
- `backtest_execution_allowed = False`
- `next_action = "action:write_p5_implementation_plan_for_trading_layer_readiness_audit"`

blocked 时，report 应包含：

- `result = "blocked"`
- `audit_id = "candidate_table_trading_layer_readiness_audit_v0.1"`
- `candidate_table_trading_layer_readiness_audit_result = "blocked"`
- `candidate_table_trading_layer_readiness_checked = False`
- `candidate_table_trading_layer_readiness_status = "blocked_before_trading_layer_read_gate_review"`
- `issues`
- `candidate_table_update_allowed = False`
- `institution_rule_definition_allowed = False`
- `trading_layer_read_allowed = False`
- `signal_generation_allowed = False`
- `backtest_execution_allowed = False`
- `next_action = "action:repair_formal_candidate_table_before_trading_layer_readiness_audit"`

blocked report 不得回显受污染 row 里的 forbidden input field name。

## 10. 非目标

P5 不得：

- 打开 `trading_layer_read_allowed`；
- 生成 `TradeDecisionSnapshot`；
- 生成 buy 或 sell signal；
- 计算 target position；
- 应用 T+1 执行规则；
- 定义涨跌停执行策略；
- 把 liquidity ranking 或 industry heat 作为 applicability；
- 读取 raw market files；
- 写 formal candidate table 文件；
- 写 trading layer artifacts；
- 写 signal artifacts；
- 写 backtest artifacts。

## 11. 测试要求

实施计划应从 `tests/test_tdx_local_first_batch.py` 的测试开始。

至少新增以下测试：

1. pass case：
   - 通过现有 P4a/P4b/P4c helper 构造 formal candidate table；
   - 运行 P5 audit；
   - 断言 `result == "pass"`；
   - 断言 `candidate_table_trading_layer_readiness_status == "ready_for_trading_layer_read_gate_review"`；
   - 断言所有硬闸保持 false。

2. blocked manifest case：
   - 让 P5 指向缺失或错误 manifest；
   - 断言 `result == "blocked"`；
   - 断言 issue code 稳定；
   - 断言不创建任何输出目录或文件。

3. forbidden field case：
   - 向 `candidate-table.jsonl` 注入 forbidden field；
   - 运行 P5 audit；
   - 断言 `result == "blocked"`；
   - 断言 report 不回显 forbidden field name；
   - 断言所有硬闸保持 false。

4. does-not-open-trading-layer case：
   - 使用有效 formal candidate table；
   - 断言 pass 仍返回 `trading_layer_read_allowed == False`；
   - 断言 `signal_generation_allowed == False`；
   - 断言 `backtest_execution_allowed == False`；
   - 断言 `institution_rule_definition_allowed == False`。

聚焦命令：

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_tdx_local_first_batch -v
```

全量验证：

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests
git diff --check
```

## 12. 实现位置

实现应放在 P4c formal candidate table writer 附近：

`src/data_sources/tdx_local/first_batch.py`

公共函数应从这里导出：

`src/data_sources/tdx_local/__init__.py`

P5 audit 应复用 `first_batch.py` 中已有的 forbidden-field 词表和 JSON helper 风格。

## 13. 完成定义

P5 完成条件：

- 已有书面 implementation plan；
- 测试覆盖 pass、blocked、forbidden fields，以及 trading layer gate 保持关闭；
- `audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested` 已实现并导出；
- focused first-batch tests 通过；
- full `unittest discover` 通过；
- 测试不触碰 formal data root 或外部 market root；
- 系统位置可以推进到：

`candidate_table_trading_layer_readiness_audit_passed`

即使推进到该位置，所有下游硬闸仍保持关闭，直到未来独立里程碑显式打开。
