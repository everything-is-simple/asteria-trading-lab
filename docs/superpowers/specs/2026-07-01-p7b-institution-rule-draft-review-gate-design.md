# P7b 制度规则草案复核闸设计

**日期：** 2026-07-01
**状态：** 已实现并通过全量测试，归档为 P7b 设计依据
**范围：** P7a 制度规则定义准备审计之后、P7c 制度规则定义 contract review 之前的只读草案复核闸

## 0. Spec Review 结论

P7b 不定义正式 A 股制度规则。

P7b 只回答一个问题：

> P7a 已确认三类制度材料可以作为草案输入后，这些草案输入是否已经具备进入制度规则定义 contract review 的复核质量？

P7b pass 只推进到：

`ready_for_institution_rule_definition_contract_review`

它不表示：

- `institution_rule_definition_allowed` 已开放；
- trading layer read 已开放；
- 可以生成 signal；
- 可以生成仓位、订单或交易决策；
- 可以运行 backtest；
- T+1、涨跌停、停复牌已经变成正式规则。

## 1. 当前系统位置

P7a 已完成，当前状态是：

`ready_for_institution_rule_definition_draft_review`

P7a 只证明三类制度材料可作为 `draft_input_only=True` 的规则草案输入。P7b 从这里继续，审草案是否适合进入 contract review。

## 2. P7b 读取什么

P7b 第一版只读取调用方显式传入的内存 payload，不读真实市场根目录，不写文件。

必须输入：

1. P7a readiness report
   - `audit_id == "institution_rule_definition_readiness_audit_v0.1"`
   - `institution_rule_definition_readiness_audit_result == "pass"`
   - `institution_rule_definition_readiness_status == "ready_for_institution_rule_definition_draft_review"`

2. T+1 草案输入材料
   - `rule_draft_input_type == "t1"`
   - `draft_input_only == True`
   - `draft_quality_status == "ready_for_review"`
   - `field_contract_status == "complete"`
   - `evidence_refs` 为非空 list
   - `boundary_review_status == "clean"`

3. 涨跌停草案输入材料
   - `rule_draft_input_type == "price_limit"`
   - 同上质量、字段契约、证据引用和边界要求

4. 停复牌草案输入材料
   - `rule_draft_input_type == "suspension_resume"`
   - 同上质量、字段契约、证据引用和边界要求

## 3. P7b 审什么

P7b 审计以下事项：

- P7a readiness report 是否通过。
- 三类 draft input 是否齐备。
- 三类 draft input 是否仍为 `draft_input_only=True`。
- 草案质量是否达到 `ready_for_review`。
- 字段契约是否完整。
- 证据引用是否存在。
- 边界复核是否干净。
- 输入与输出是否不含 forbidden fields。
- 所有 hard gates 是否保持关闭。

## 4. P7b 阻断什么

以下情况必须 blocked：

- 缺 P7a readiness report。
- P7a readiness report 未通过。
- 缺 T+1、涨跌停或停复牌任一草案输入。
- 草案输入类型不匹配。
- 草案输入未声明 `draft_input_only=True`。
- 草案质量不是 `ready_for_review`。
- 字段契约不是 `complete`。
- `evidence_refs` 缺失或为空。
- `boundary_review_status` 不是 `clean`。
- 任一输入打开以下 hard gates：
  - `institution_rule_definition_allowed`
  - `trading_layer_read_allowed`
  - `signal_generation_allowed`
  - `backtest_execution_allowed`
- 任一输入含 forbidden fields。

## 5. P7b 输出什么

Pass report：

- `result == "pass"`
- `audit_id == "institution_rule_definition_draft_review_gate_audit_v0.1"`
- `institution_rule_definition_draft_review_gate_result == "pass"`
- `institution_rule_definition_draft_review_status == "ready_for_institution_rule_definition_contract_review"`
- `reviewed_rule_draft_inputs == ["t1", "price_limit", "suspension_resume"]`
- `institution_rule_definition_allowed == False`
- `trading_layer_read_allowed == False`
- `signal_generation_allowed == False`
- `backtest_execution_allowed == False`
- `next_action == "action:write_p7c_institution_rule_definition_contract_review_spec"`

Blocked report：

- `result == "blocked"`
- `audit_id == "institution_rule_definition_draft_review_gate_audit_v0.1"`
- `institution_rule_definition_draft_review_gate_result == "blocked"`
- `institution_rule_definition_draft_review_status == "blocked_before_institution_rule_definition_contract_review"`
- `issues` 给出稳定 issue code。
- 所有 hard gates 继续为 `False`。
- 不回显 forbidden field。

## 6. 推荐实现位置

继续放在：

`src/data_sources/tdx_local/first_batch.py`

新增入口：

`audit_institution_rule_definition_draft_review_gate_when_explicitly_requested`

并从：

`src/data_sources/tdx_local/__init__.py`

导出。

## 7. TDD 要求

先写 RED 测试，再写生产代码。

至少覆盖：

1. pass：P7a readiness pass，三类草案输入质量、字段契约、证据引用、边界复核齐备。
2. blocked：缺 P7a 或缺任一草案输入。
3. blocked：草案质量、字段契约、证据引用或边界状态不合格。
4. forbidden field：任一输入混入 signal / order / position / MALF override 字段时 blocked，输出不回显字段。
5. hard gates false：即使 pass，也不得打开 institution rule、trading layer read、signal、backtest。

## 8. 非目标

P7b 本轮不做：

- 不生成正式制度规则文件。
- 不把草案输入转成交易动作。
- 不生成 signal。
- 不生成 target position。
- 不运行 backtest。
- 不写真实数据根。
- 不修改真实市场文件。
