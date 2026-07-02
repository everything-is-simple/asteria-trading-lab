# P7c 制度规则定义 contract review 设计

**日期：** 2026-07-01
**状态：** 已实现并通过全量测试，归档为 P7c 设计依据
**范围：** P7b 制度规则草案复核闸之后、未来正式制度规则定义开放 gate 之前的只读 contract review

## 0. Spec Review 结论

P7c 不定义正式 A 股制度规则。

P7c 只回答一个问题：

> P7b 已确认三类制度规则草案具备复核质量后，这些 reviewed draft 是否满足未来正式制度规则定义入口的消费契约？

P7c pass 只推进到：

`ready_for_explicit_institution_rule_definition_open_gate_review`

它不表示：

- `institution_rule_definition_allowed` 已开放；
- trading layer read 已开放；
- 可以生成 signal；
- 可以生成仓位、订单或交易决策；
- 可以运行 backtest；
- T+1、涨跌停、停复牌已经变成正式制度规则。

## 1. 当前系统位置

P7b 已完成，当前状态是：

`ready_for_institution_rule_definition_contract_review`

P7b 只证明三类草案输入具备进入 contract review 的复核质量。P7c 从这里继续，审未来正式制度规则定义入口能否安全消费这些 reviewed draft。

## 2. P7c 读取什么

P7c 第一版只读取调用方显式传入的内存 payload，不读真实市场根目录，不写文件。

必须输入：

1. P7b draft review gate report
   - `audit_id == "institution_rule_definition_draft_review_gate_audit_v0.1"`
   - `institution_rule_definition_draft_review_gate_result == "pass"`
   - `institution_rule_definition_draft_review_status == "ready_for_institution_rule_definition_contract_review"`

2. T+1 reviewed draft contract input
   - `rule_draft_input_type == "t1"`
   - `draft_input_only == True`
   - `draft_quality_status == "ready_for_review"`
   - `field_contract_status == "complete"`
   - `evidence_refs` 为非空 list
   - `boundary_review_status == "clean"`
   - `contract_review_status == "ready"`
   - `definition_contract_fields` 为非空 list
   - `consumer_entrypoint == "institution_rule_definition"`

3. 涨跌停 reviewed draft contract input
   - `rule_draft_input_type == "price_limit"`
   - 同上 contract review、字段契约、证据引用、边界要求

4. 停复牌 reviewed draft contract input
   - `rule_draft_input_type == "suspension_resume"`
   - 同上 contract review、字段契约、证据引用、边界要求

## 3. P7c 审什么

P7c 审计以下事项：

- P7b draft review gate report 是否通过。
- 三类 reviewed draft contract input 是否齐备。
- 三类 input 是否仍为 `draft_input_only=True`。
- 草案质量是否仍为 `ready_for_review`。
- 字段契约是否仍为 `complete`。
- 证据引用是否存在。
- 边界复核是否干净。
- contract review 状态是否为 `ready`。
- 未来正式制度规则定义入口消费字段是否声明完整。
- consumer entrypoint 是否仍限定为 `institution_rule_definition`。
- 输入与输出是否不含 forbidden fields。
- 所有 hard gates 是否保持关闭。

## 4. P7c 阻断什么

以下情况必须 blocked：

- 缺 P7b draft review gate report。
- P7b draft review gate report 未通过。
- 缺 T+1、涨跌停或停复牌任一 reviewed draft contract input。
- reviewed draft input 类型不匹配。
- input 未声明 `draft_input_only=True`。
- 草案质量不是 `ready_for_review`。
- 字段契约不是 `complete`。
- `evidence_refs` 缺失或为空。
- `boundary_review_status` 不是 `clean`。
- `contract_review_status` 不是 `ready`。
- `definition_contract_fields` 缺失或为空。
- `consumer_entrypoint` 不是 `institution_rule_definition`。
- 任一输入打开以下 hard gates：
  - `institution_rule_definition_allowed`
  - `trading_layer_read_allowed`
  - `signal_generation_allowed`
  - `backtest_execution_allowed`
- 任一输入含 forbidden fields。

## 5. P7c 输出什么

Pass report：

- `result == "pass"`
- `audit_id == "institution_rule_definition_contract_review_audit_v0.1"`
- `institution_rule_definition_contract_review_result == "pass"`
- `institution_rule_definition_contract_review_status == "ready_for_explicit_institution_rule_definition_open_gate_review"`
- `contract_reviewed_rule_draft_inputs == ["t1", "price_limit", "suspension_resume"]`
- `institution_rule_definition_allowed == False`
- `trading_layer_read_allowed == False`
- `signal_generation_allowed == False`
- `backtest_execution_allowed == False`
- `next_action == "action:review_explicit_institution_rule_definition_open_gate"`

Blocked report：

- `result == "blocked"`
- `audit_id == "institution_rule_definition_contract_review_audit_v0.1"`
- `institution_rule_definition_contract_review_result == "blocked"`
- `institution_rule_definition_contract_review_status == "blocked_before_explicit_institution_rule_definition_open_gate_review"`
- `issues` 给出稳定 issue code。
- 所有 hard gates 继续为 `False`。
- 不回显 forbidden field。

## 6. 推荐实现位置

继续放在：

`src/data_sources/tdx_local/first_batch.py`

新增入口：

`audit_institution_rule_definition_contract_review_when_explicitly_requested`

并从：

`src/data_sources/tdx_local/__init__.py`

导出。

## 7. TDD 要求

先写 RED 测试，再写生产代码。

至少覆盖：

1. pass：P7b gate pass，三类 contract input 的质量、字段契约、证据引用、边界、contract 字段齐备。
2. blocked：缺 P7b 或缺任一 reviewed draft contract input。
3. blocked：contract review 状态、definition contract fields 或 consumer entrypoint 不合格。
4. forbidden field：任一输入混入 signal / order / position / MALF override 字段时 blocked，输出不回显字段。
5. hard gates false：即使 pass，也不得打开 institution rule、trading layer read、signal、backtest。

## 8. 非目标

P7c 本轮不做：

- 不生成正式制度规则文件。
- 不开放 `institution_rule_definition_allowed`。
- 不把制度规则草案转成交易动作。
- 不生成 signal。
- 不生成 target position。
- 不运行 backtest。
- 不写真实数据根。
- 不修改真实市场文件。
