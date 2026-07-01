# P8 正式制度规则定义持久化包设计

**日期：** 2026-07-01
**状态：** implemented / verified，已通过 focused / 全量测试，归档为 P8 设计依据
**范围：** `P7e` 正式制度规则定义审计之后、任何真实制度规则文件写入 / trading layer / signal / backtest gate 之前

## 0. DecisionTrace

| Field | Evidence |
|---|---|
| `current_state` | `docs/04_施工计划_当前进度版.md` 与 `docs/06_Roadmap_TodoList_后续路线图与待办.md` 均记录当前基线为 `formal_institution_rule_definition_audited_for_rule_definition_only`；最近提交 `031b618 Add formal institution rule definition gate`；`git status --short` 当前为空。 |
| `candidate_routes` | 1. P8 persistence/package 准备审计；2. 真实制度规则文件写入 gate；3. trading layer / signal / backtest 下一层门。 |
| `pruned_routes` | 路线 2 被剪枝：真实写入需要独立人工确认和写入前审计；路线 3 被剪枝：`trading_layer_read_allowed`、`signal_generation_allowed`、`backtest_execution_allowed` 仍必须关闭。 |
| `selected_route` | 只做 P8：准备正式制度规则定义持久化包，不写文件，不开放下游交易语义。 |
| `hard_boundaries` | 不读取 trading layer；不生成 signal、position、order、PnL、backtest 输入；不写 `Z:\asteria-trading-labs-data` 或任何真实市场根；不把 Method/PM、Signal、回测字段混入制度审计层。 |
| `verification` | 先写 pass / blocked / forbidden-field / hard-gate 测试；再实现 `prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested`；运行 `tests.test_tdx_local_first_batch`、全量 `unittest discover` 与 `git diff --check`。 |

## 1. P8 目的

P8 不定义交易信号，不写正式制度规则文件，也不执行持久化。

P8 只回答一个问题：

> P7e 已经通过的正式制度规则定义输入，是否可以被封装成一个只读的、可审计的 persistence package，为后续独立写入 gate 做准备？

P8 pass 只推进到：

`formal_institution_rule_definition_persistence_package_prepared`

它表示：

- 已准备正式制度规则定义持久化包；
- `institution_rule_definition_allowed == True` 仍只代表 rule-definition-only；
- `formal_institution_rule_definition_persistence_performed == False`；
- `trading_layer_read_allowed == False`；
- `signal_generation_allowed == False`；
- `backtest_execution_allowed == False`；
- 不写正式制度规则文件，不写真实数据根。

## 2. P8 读取什么

P8 第一版只读取调用方显式传入的内存 payload，不读真实市场根目录，不写文件。

必须输入：

1. `P7e` formal institution rule definition audit report
   - `audit_id == "formal_institution_rule_definition_audit_v0.1"`
   - `formal_institution_rule_definition_result == "pass"`
   - `formal_institution_rule_definition_status == "formal_institution_rule_definition_audited_for_rule_definition_only"`
   - `institution_rule_definition_allowed == True`
   - `trading_layer_read_allowed == False`
   - `signal_generation_allowed == False`
   - `backtest_execution_allowed == False`

2. `formal institution rule definition payload`
   - `artifact_id == "formal_institution_rule_definition_input_v0.1"`
   - `definition_scope == "institution_rule_definition_only"`
   - `definition_input_status == "ready_for_audit"`
   - `consumed_reviewed_draft_inputs == ["t1", "price_limit", "suspension_resume"]`
   - `field_contract_status == "complete"`
   - `boundary_review_status == "clean"`
   - `evidence_refs` 为非空 list
   - `formal_definition_fields` 为非空 list
   - `institution_rule_definition_allowed == True`
   - 下游 hard gates 均为 `False`

## 3. P8 审什么

P8 审计以下事项：

- `P7e` 是否已通过。
- `P7e` 是否只表示 rule-definition-only。
- formal definition payload 是否存在。
- formal definition payload 是否仍限于 `institution_rule_definition_only`。
- formal definition payload 是否覆盖 `t1 / price_limit / suspension_resume` 三类 reviewed draft。
- 字段契约是否 complete。
- 边界复核是否 clean。
- 证据引用是否齐备。
- formal definition fields 是否非空。
- 输入与输出是否不含 forbidden fields。
- `trading_layer_read_allowed / signal_generation_allowed / backtest_execution_allowed` 是否继续关闭。

## 4. P8 阻断什么

以下情况必须 blocked：

- 缺 `P7e` audit report。
- `P7e` audit report 未通过。
- `P7e` status 不是 `formal_institution_rule_definition_audited_for_rule_definition_only`。
- `P7e` 未保持 `institution_rule_definition_allowed == True`。
- 缺 formal definition payload。
- formal definition payload 的 `artifact_id` 不正确。
- formal definition payload 的 `definition_scope` 不是 `institution_rule_definition_only`。
- formal definition payload 的 `definition_input_status` 不是 `ready_for_audit`。
- formal definition payload 的 `consumed_reviewed_draft_inputs` 缺任一 `t1 / price_limit / suspension_resume`。
- formal definition payload 的 `field_contract_status` 不是 `complete`。
- formal definition payload 的 `boundary_review_status` 不是 `clean`。
- formal definition payload 缺 `evidence_refs` 或为空。
- formal definition payload 缺 `formal_definition_fields` 或为空。
- 任一输入打开以下 hard gates：
  - `trading_layer_read_allowed`
  - `signal_generation_allowed`
  - `backtest_execution_allowed`
- 任一输入含 forbidden fields。

## 5. P8 输出什么

Pass report：

- `result == "pass"`
- `audit_id == "formal_institution_rule_definition_persistence_package_v0.1"`
- `formal_institution_rule_definition_persistence_package_result == "pass"`
- `formal_institution_rule_definition_persistence_package_status == "formal_institution_rule_definition_persistence_package_prepared"`
- `formal_institution_rule_definition_persistence_package_prepared == True`
- `formal_institution_rule_definition_persistence_performed == False`
- `source_formal_institution_rule_definition_result == "pass"`
- `packaged_rule_definition_inputs == ["t1", "price_limit", "suspension_resume"]`
- `package_field_contract_status == "complete"`
- `package_boundary_status == "clean"`
- `package_evidence_status == "ready"`
- `institution_rule_definition_allowed == True`
- `trading_layer_read_allowed == False`
- `signal_generation_allowed == False`
- `backtest_execution_allowed == False`
- `next_action == "action:audit_formal_institution_rule_definition_write_when_explicitly_requested"`

Blocked report：

- `result == "blocked"`
- `audit_id == "formal_institution_rule_definition_persistence_package_v0.1"`
- `formal_institution_rule_definition_persistence_package_result == "blocked"`
- `formal_institution_rule_definition_persistence_package_status == "blocked_before_formal_institution_rule_definition_persistence_package_prepared"`
- `formal_institution_rule_definition_persistence_package_prepared == False`
- `formal_institution_rule_definition_persistence_performed == False`
- `institution_rule_definition_allowed == False`
- 所有 trading / signal / backtest gates 继续为 `False`
- `issues` 给出稳定 issue code
- 不回显 forbidden field

## 6. 推荐实现位置

继续放在：

`src/data_sources/tdx_local/first_batch.py`

新增入口：

`prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested`

并从：

`src/data_sources/tdx_local/__init__.py`

导出。

## 7. TDD 要求

先写 RED 测试，再写生产代码。

至少覆盖：

1. `pass`：`P7e` pass、formal definition payload 完整，输出 package prepared report。
2. `blocked`：缺 `P7e`、`P7e` failed、缺 formal definition payload、payload 字段契约不完整。
3. `forbidden field`：任一输入混入 signal / order / position / backtest 字段时 blocked，输出不回显字段。
4. `hard gate`：pass 时只能保持 `institution_rule_definition_allowed=True`；`trading_layer_read_allowed / signal_generation_allowed / backtest_execution_allowed` 仍为 `False`。

## 8. 非目标

P8 本轮不做：

- 不写正式制度规则文件。
- 不读取 trading layer。
- 不生成 signal。
- 不生成 target position。
- 不生成 order。
- 不生成 PnL。
- 不运行 backtest。
- 不写真实数据根。
- 不修改真实市场文件。
