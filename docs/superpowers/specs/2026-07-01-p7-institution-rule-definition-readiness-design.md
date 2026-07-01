# P7a 制度规则定义准备审计设计

**日期：** 2026-07-01
**状态：** 已实现并通过全量测试，归档为 P7a 设计依据
**范围：** P6 trading layer read gate contract 之后、正式制度规则定义之前的只读准备度审计

## 0. Spec Review 结论

P7a 本轮不定义正式 A 股制度规则，也不代表完整 P7 已完成。

本规格只建立一道准备度审计闸，回答一个窄问题：

> 当前已有材料是否足够进入「制度规则草案复核」？

P7a pass 只推进到：

`ready_for_institution_rule_definition_draft_review`

它不表示：

- `institution_rule_definition_allowed` 已开放；
- trading layer read 已开放；
- 可以生成 signal；
- 可以生成仓位、订单或交易决策；
- 可以运行 backtest；
- T+1、涨跌停、停复牌已经变成正式规则。

## 1. 当前系统位置

当前系统已经完成 P6，并已通过 P7 准备度审计：

`ready_for_institution_rule_definition_draft_review`

P6 已明确 consumer contract 可审哪些只读输入，但仍保持：

- `institution_rule_definition_allowed=False`
- `trading_layer_read_allowed=False`
- `signal_generation_allowed=False`
- `backtest_execution_allowed=False`

P7a 从这个位置开始，只审查制度规则草案输入是否齐备。

## 2. P7a 读取什么

P7a 第一版只读取调用方显式传入的内存 payload，不读真实市场根目录，不写文件。

必须输入：

1. P6 contract report
   - `audit_id == "trading_layer_read_gate_contract_audit_v0.1"`
   - `trading_layer_read_gate_contract_audit_result == "pass"`
   - `trading_layer_read_gate_contract_status == "ready_for_trading_layer_read_contract_review"`

2. T+1 草案输入材料
   - `rule_draft_input_type == "t1"`
   - `draft_input_only == True`
   - `result == "pass"` 或 `readiness == "pass"`

3. 涨跌停草案输入材料
   - `rule_draft_input_type == "price_limit"`
   - `draft_input_only == True`
   - `result == "pass"` 或 `readiness == "pass"`

4. 停复牌草案输入材料
   - `rule_draft_input_type == "suspension_resume"`
   - `draft_input_only == True`
   - `result == "pass"` 或 `readiness == "pass"`

这些材料只能作为制度规则草案输入，不能携带交易动作、信号、仓位、回测结果或 MALF 覆盖字段。

## 3. P7a 审什么

P7a 审计以下事项：

- P6 contract report 是否通过。
- P6 与所有草案输入材料是否仍保持 hard gates 关闭。
- T+1、涨跌停、停复牌三类材料是否齐备。
- 三类材料是否明确 `draft_input_only=True`。
- 三类材料是否仍是研究 / 审计输入，而不是正式规则。
- 输入与输出是否不含 forbidden fields。
- 制度事实是否没有回流覆盖 MALF 层字段。

## 4. P7a 阻断什么

以下情况必须 blocked：

- 缺 P6 contract report。
- P6 contract report 未通过。
- 缺 T+1、涨跌停或停复牌任一材料。
- 草案输入材料类型不匹配。
- 草案输入未声明 `draft_input_only=True`。
- 任一输入打开以下 hard gates：
  - `institution_rule_definition_allowed`
  - `trading_layer_read_allowed`
  - `signal_generation_allowed`
  - `backtest_execution_allowed`
- 任一输入含 forbidden fields：
  - `buy_signal`
  - `sell_signal`
  - `trade_accept`
  - `trade_reject`
  - `trade_defer`
  - `signal_decision`
  - `target_position`
  - `position_size`
  - `ashare_t1_action`
  - `limit_up_strategy`
  - `limit_down_strategy`
  - `industry_hot_score`
  - `liquidity_rank_as_applicability`
  - `rhythm_meaning_override`
  - `tachibana_applicability_override`

## 5. P7a 输出什么

Pass report：

- `result == "pass"`
- `audit_id == "institution_rule_definition_readiness_audit_v0.1"`
- `institution_rule_definition_readiness_audit_result == "pass"`
- `institution_rule_definition_readiness_status == "ready_for_institution_rule_definition_draft_review"`
- `required_rule_draft_inputs == ["t1", "price_limit", "suspension_resume"]`
- `institution_rule_definition_allowed == False`
- `trading_layer_read_allowed == False`
- `signal_generation_allowed == False`
- `backtest_execution_allowed == False`
- `next_action == "action:review_institution_rule_definition_drafts"`

Blocked report：

- `result == "blocked"`
- `audit_id == "institution_rule_definition_readiness_audit_v0.1"`
- `institution_rule_definition_readiness_audit_result == "blocked"`
- `institution_rule_definition_readiness_status == "blocked_before_institution_rule_definition_draft_review"`
- `issues` 给出稳定 issue code。
- 所有 hard gates 继续为 `False`。
- 不回显 forbidden field。

## 6. 推荐实现位置

继续放在：

`src/data_sources/tdx_local/first_batch.py`

原因：

- P5/P6 已在这里形成 candidate table 之后、trading layer / institution rule 之前的审计闸链路。
- P7a 仍是只读 audit，不需要进入真实 trading layer，也不需要触碰 `ashare_intake_validator.py` 的 CLI 管线。
- 测试可继续放在 `tests/test_tdx_local_first_batch.py`。

新增入口：

`audit_institution_rule_definition_readiness_when_explicitly_requested`

并从：

`src/data_sources/tdx_local/__init__.py`

导出。

## 7. TDD 要求

先写 RED 测试，再写生产代码。

至少覆盖：

1. pass：P6 contract pass，三类草案输入齐备，所有 hard gates false。
2. blocked：缺 P6 或缺任一草案输入。
3. forbidden field：任一输入混入 signal / order / position / MALF override 字段时 blocked，输出不回显字段。
4. hard gates false：即使 pass，也不得打开 institution rule、trading layer read、signal、backtest。

## 8. 非目标

P7a 本轮不做：

- 不生成正式制度规则文件。
- 不把 `t1`、`price_limit`、`suspension_resume` 转成交易动作。
- 不生成 signal。
- 不生成 target position。
- 不运行 backtest。
- 不写真实数据根。
- 不修改真实市场文件。

## 9. 后续 P7 工作

完整 P7 尚未完成。P7a 完成后，后续至少还需要：

- P7b：制度规则草案复核闸，审查三类 draft input 的质量、字段契约、证据引用与边界完整性。
- P7c：制度规则定义 contract review，定义未来正式 institution rule definition 入口可读取什么、审什么、阻断什么、输出什么。

P7b/P7c 仍不得自动打开 `institution_rule_definition_allowed`，更不得打开 trading layer read、signal generation 或 backtest execution。
