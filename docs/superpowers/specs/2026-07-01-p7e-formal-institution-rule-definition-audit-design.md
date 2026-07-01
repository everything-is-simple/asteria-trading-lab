# P7e 正式制度规则定义审计设计

**日期：** 2026-07-01
**状态：** 已实现并通过 focused / 全量测试，归档为 P7e 设计依据
**范围：** `P7d` 显式制度规则定义开放 gate 之后、任何 trading layer / signal / backtest gate 之前

## 0. Spec Review 结论

P7e 不是 signal，不是 backtest，也不是 trading layer read。

P7e 只回答一个问题：

> 在 `P7d` 已明确开放 `rule-definition-only` 入口之后，调用方给出的正式制度规则定义输入，是否已经以只读方式正确消费三类 contract-ready reviewed draft，并且在字段契约、边界与证据上满足正式制度规则定义审计要求？

P7e pass 只推进到：

`formal_institution_rule_definition_audited_for_rule_definition_only`

它表示：

- 当前 formal institution rule definition input 已通过审计；
- `institution_rule_definition_allowed == True` 继续只代表 rule-definition-only；
- `trading_layer_read_allowed == False`；
- `signal_generation_allowed == False`；
- `backtest_execution_allowed == False`；
- 不生成交易信号、不生成仓位、不生成订单、不运行 backtest；
- 不写正式制度规则文件，不写真实数据根。

## 1. 当前系统位置

P7d 已完成，当前系统位置是：

`institution_rule_definition_opened_for_rule_definition_only`

这意味着正式制度规则定义入口已经被显式打开，但只允许 rule-definition-only 工作继续向前。

P7e 从这里继续，审的是“正式制度规则定义本身”的输入质量，而不是下游交易消费。

## 2. P7e 读取什么

P7e 第一版只读取调用方显式传入的内存 payload，不读真实市场根目录，不写文件。

必须输入：

1. `P7d` explicit open gate report
   - `audit_id == "explicit_institution_rule_definition_open_gate_audit_v0.1"`
   - `explicit_institution_rule_definition_open_gate_result == "pass"`
   - `explicit_institution_rule_definition_open_gate_status == "institution_rule_definition_opened_for_rule_definition_only"`

2. `t1` contract-ready reviewed draft input
   - `rule_draft_input_type == "t1"`
   - `draft_input_only == True`
   - `contract_review_status == "ready"`
   - `definition_contract_fields` 为非空 list
   - `consumer_entrypoint == "institution_rule_definition"`

3. `price_limit` contract-ready reviewed draft input
   - `rule_draft_input_type == "price_limit"`
   - 同上 contract-ready 要求

4. `suspension_resume` contract-ready reviewed draft input
   - `rule_draft_input_type == "suspension_resume"`
   - 同上 contract-ready 要求

5. `formal institution rule definition input`
   - `artifact_id == "formal_institution_rule_definition_input_v0.1"`
   - `definition_scope == "institution_rule_definition_only"`
   - `definition_input_status == "ready_for_audit"`
   - `consumed_reviewed_draft_inputs == ["t1", "price_limit", "suspension_resume"]`
   - `field_contract_status == "complete"`
   - `boundary_review_status == "clean"`
   - `evidence_refs` 为非空 list
   - `formal_definition_fields` 为非空 list

## 3. P7e 审什么

P7e 审计以下事项：

- `P7d` 是否已通过，且只打开 `rule-definition-only`。
- 三类 contract-ready reviewed draft input 是否齐备。
- 三类 input 是否仍然保持 `draft_input_only=True`。
- 三类 input 是否仍指向 `institution_rule_definition` consumer entrypoint。
- formal institution rule definition input 是否存在。
- formal institution rule definition input 是否只限 `institution_rule_definition_only` 范围。
- formal institution rule definition input 是否明确覆盖 `t1 / price_limit / suspension_resume` 三类 reviewed draft。
- formal institution rule definition input 的字段契约是否完整。
- formal institution rule definition input 的边界复核是否 clean。
- formal institution rule definition input 的证据引用是否齐备。
- 输入与输出是否不含 forbidden fields。
- 所有 trading / signal / backtest 硬闸是否继续关闭。

## 4. P7e 阻断什么

以下情况必须 blocked：

- 缺 `P7d` open gate report。
- `P7d` open gate report 未通过。
- `P7d` status 不是 `institution_rule_definition_opened_for_rule_definition_only`。
- 缺任一 contract-ready reviewed draft input。
- reviewed draft input 类型不匹配。
- reviewed draft input 未声明 `draft_input_only=True`。
- reviewed draft input 的 `contract_review_status` 不是 `ready`。
- reviewed draft input 缺 `definition_contract_fields`。
- reviewed draft input 的 `consumer_entrypoint` 不是 `institution_rule_definition`。
- 缺 formal institution rule definition input。
- `definition_scope` 不是 `institution_rule_definition_only`。
- `definition_input_status` 不是 `ready_for_audit`。
- `consumed_reviewed_draft_inputs` 缺少 `t1 / price_limit / suspension_resume` 任一项。
- `field_contract_status` 不是 `complete`。
- `boundary_review_status` 不是 `clean`。
- `evidence_refs` 缺失或为空。
- `formal_definition_fields` 缺失或为空。
- 任一输入打开以下 hard gates：
  - `trading_layer_read_allowed`
  - `signal_generation_allowed`
  - `backtest_execution_allowed`
- 任一输入含 forbidden fields。

## 5. P7e 输出什么

Pass report：

- `result == "pass"`
- `audit_id == "formal_institution_rule_definition_audit_v0.1"`
- `formal_institution_rule_definition_result == "pass"`
- `formal_institution_rule_definition_status == "formal_institution_rule_definition_audited_for_rule_definition_only"`
- `p7d_open_gate_result == "pass"`
- `consumed_reviewed_draft_inputs == ["t1", "price_limit", "suspension_resume"]`
- `formal_institution_rule_definition_field_contract_status == "complete"`
- `formal_institution_rule_definition_boundary_status == "clean"`
- `formal_institution_rule_definition_evidence_status == "ready"`
- `institution_rule_definition_allowed == True`
- `trading_layer_read_allowed == False`
- `signal_generation_allowed == False`
- `backtest_execution_allowed == False`
- `next_action == "action:prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested"`

Blocked report：

- `result == "blocked"`
- `audit_id == "formal_institution_rule_definition_audit_v0.1"`
- `formal_institution_rule_definition_result == "blocked"`
- `formal_institution_rule_definition_status == "blocked_before_formal_institution_rule_definition_audit_pass"`
- `institution_rule_definition_allowed == False`
- 所有 trading / signal / backtest gates 继续为 `False`
- `issues` 给出稳定 issue code
- 不回显 forbidden field

## 6. 推荐实现位置

继续放在：

`src/data_sources/tdx_local/first_batch.py`

新增入口：

`audit_formal_institution_rule_definition_when_explicitly_requested`

并从：

`src/data_sources/tdx_local/__init__.py`

导出。

## 7. TDD 要求

先写 RED 测试，再写生产代码。

至少覆盖：

1. `pass`：`P7d` pass、三类 contract-ready reviewed draft 齐备、formal institution rule definition input 齐备。
2. `blocked`：缺 `P7d` 或缺任一 reviewed draft，或 formal institution rule definition input 不完整。
3. `forbidden field`：任一输入混入 signal / order / position / MALF override 字段时 blocked，输出不回显字段。
4. `hard gate`：pass 时只能保持 `institution_rule_definition_allowed=True`；`trading_layer_read_allowed / signal_generation_allowed / backtest_execution_allowed` 仍为 `False`。

## 8. 非目标

P7e 本轮不做：

- 不生成正式制度规则文件。
- 不读取 trading layer。
- 不生成 signal。
- 不生成 target position。
- 不运行 backtest。
- 不写真实数据根。
- 不修改真实市场文件。
