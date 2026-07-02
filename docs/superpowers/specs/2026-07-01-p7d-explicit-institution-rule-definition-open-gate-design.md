# P7d 显式制度规则定义开放 gate 设计

**日期：** 2026-07-01
**状态：** 已实现并通过全量测试，归档为 P7d 设计依据
**范围：** P7c 制度规则定义 contract review 之后、正式制度规则定义入口之前的显式开放闸

## 0. Spec Review 结论

P7d 不生成正式 A 股制度规则。

P7d 只回答一个问题：

> P7c 已确认三类 reviewed draft 满足未来制度规则定义入口消费契约后，调用方是否已经给出足够明确、可审计、只限制度规则定义的 open-gate 决策？

P7d pass 只推进到：

`institution_rule_definition_opened_for_rule_definition_only`

它表示：

- `institution_rule_definition_allowed == True`
- 只允许进入正式制度规则定义入口；
- 不允许 trading layer read；
- 不允许生成 signal；
- 不允许生成仓位、订单或交易决策；
- 不允许运行 backtest。

## 1. 当前系统位置

P7c 已完成，当前状态是：

`ready_for_explicit_institution_rule_definition_open_gate_review`

P7c 不自动打开 `institution_rule_definition_allowed`。P7d 从这里继续，审显式 open-gate 决策是否足够安全。

## 2. P7d 读取什么

P7d 第一版只读取调用方显式传入的内存 payload，不读真实市场根目录，不写文件。

必须输入：

1. P7c contract review report
   - `audit_id == "institution_rule_definition_contract_review_audit_v0.1"`
   - `institution_rule_definition_contract_review_result == "pass"`
   - `institution_rule_definition_contract_review_status == "ready_for_explicit_institution_rule_definition_open_gate_review"`

2. T+1 contract-ready reviewed draft input
   - `rule_draft_input_type == "t1"`
   - `draft_input_only == True`
   - `contract_review_status == "ready"`
   - `definition_contract_fields` 为非空 list
   - `consumer_entrypoint == "institution_rule_definition"`

3. 涨跌停 contract-ready reviewed draft input
   - `rule_draft_input_type == "price_limit"`
   - 同上 contract-ready 要求

4. 停复牌 contract-ready reviewed draft input
   - `rule_draft_input_type == "suspension_resume"`
   - 同上 contract-ready 要求

5. 显式 open-gate 决策
   - `gate_decision == "approve_institution_rule_definition_only"`
   - `gate_scope == "institution_rule_definition_only"`
   - `approved_by` 为非空字符串
   - `approval_evidence_refs` 为非空 list
   - `acknowledged_no_trading_layer_read == True`
   - `acknowledged_no_signal_generation == True`
   - `acknowledged_no_backtest_execution == True`

## 3. P7d 审什么

P7d 审计以下事项：

- P7c contract review report 是否通过。
- 三类 contract-ready reviewed draft input 是否齐备。
- 三类 input 是否仍为 `draft_input_only=True`。
- 三类 input 是否仍指向 `institution_rule_definition` consumer entrypoint。
- 显式 open-gate 决策是否存在。
- gate decision 是否只批准制度规则定义。
- gate scope 是否只限制度规则定义。
- 审批人与审批证据是否存在。
- 调用方是否确认不打开 trading layer read、signal、backtest。
- 输入与输出是否不含 forbidden fields。
- 除 `institution_rule_definition_allowed` 外，所有下游 hard gates 是否保持关闭。

## 4. P7d 阻断什么

以下情况必须 blocked：

- 缺 P7c contract review report。
- P7c contract review report 未通过。
- 缺 T+1、涨跌停或停复牌任一 contract-ready reviewed draft input。
- reviewed draft input 类型不匹配。
- input 未声明 `draft_input_only=True`。
- contract review 状态不是 `ready`。
- `definition_contract_fields` 缺失或为空。
- `consumer_entrypoint` 不是 `institution_rule_definition`。
- 缺显式 open-gate 决策。
- `gate_decision` 不是 `approve_institution_rule_definition_only`。
- `gate_scope` 不是 `institution_rule_definition_only`。
- 缺 `approved_by` 或 `approval_evidence_refs`。
- 未确认不打开 trading layer read、signal、backtest。
- 任一输入打开以下 hard gates：
  - `trading_layer_read_allowed`
  - `signal_generation_allowed`
  - `backtest_execution_allowed`
- 任一输入含 forbidden fields。

## 5. P7d 输出什么

Pass report：

- `result == "pass"`
- `audit_id == "explicit_institution_rule_definition_open_gate_audit_v0.1"`
- `explicit_institution_rule_definition_open_gate_result == "pass"`
- `explicit_institution_rule_definition_open_gate_status == "institution_rule_definition_opened_for_rule_definition_only"`
- `institution_rule_definition_allowed == True`
- `trading_layer_read_allowed == False`
- `signal_generation_allowed == False`
- `backtest_execution_allowed == False`
- `next_action == "action:define_formal_institution_rules_only"`

Blocked report：

- `result == "blocked"`
- `audit_id == "explicit_institution_rule_definition_open_gate_audit_v0.1"`
- `explicit_institution_rule_definition_open_gate_result == "blocked"`
- `explicit_institution_rule_definition_open_gate_status == "blocked_before_institution_rule_definition_open"`
- `institution_rule_definition_allowed == False`
- 所有 trading / signal / backtest gates 继续为 `False`。
- `issues` 给出稳定 issue code。
- 不回显 forbidden field。

## 6. 推荐实现位置

继续放在：

`src/data_sources/tdx_local/first_batch.py`

新增入口：

`audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested`

并从：

`src/data_sources/tdx_local/__init__.py`

导出。

## 7. TDD 要求

先写 RED 测试，再写生产代码。

至少覆盖：

1. pass：P7c pass、三类 contract-ready draft 齐备、显式 open-gate 决策齐备。
2. blocked：缺 P7c 或缺任一 contract-ready draft。
3. blocked：缺显式 open-gate 决策或决策范围不是 rule-definition-only。
4. forbidden field：任一输入混入 signal / order / position / MALF override 字段时 blocked，输出不回显字段。
5. hard gates：pass 时仅 `institution_rule_definition_allowed=True`，trading layer read、signal、backtest 仍为 `False`。

## 8. 非目标

P7d 本轮不做：

- 不生成正式制度规则文件。
- 不读取 trading layer。
- 不生成 signal。
- 不生成 target position。
- 不运行 backtest。
- 不写真实数据根。
- 不修改真实市场文件。
