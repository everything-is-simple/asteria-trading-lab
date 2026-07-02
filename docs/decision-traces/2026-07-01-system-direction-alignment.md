# 2026-07-01 系统方向校准

## Current State

- 当前分支：`Asteria-malf-pas/institution-facts-minimal-power`
- 最新已推送提交：`d0f257e Add auditable decision trace workflow`
- 当前 gate/status：`institution_rule_definition_opened_for_rule_definition_only`
- 证据：`docs/04_施工计划_当前进度版.md` 已记录 P7d 完成；`src/data_sources/tdx_local/first_batch.py` 的 P7d audit 成功路径只打开 `institution_rule_definition_allowed=True`；`tests/test_tdx_local_first_batch.py` 覆盖 P7d pass、blocked、bad decision、forbidden field 和 opens only rule definition gate。

## Candidate Routes

1. 直接进入 signal/backtest。
2. 继续扩大工具系统，新增 hook、automation 或 MCP 编排。
3. 先校准 P7d 后的文档、代码、治理语义，再进入正式制度规则定义 spec。

## Pruned Routes

- 直接进入 signal/backtest：剪枝。P7d 只开放 rule-definition-only，`trading_layer_read_allowed`、`signal_generation_allowed`、`backtest_execution_allowed` 仍为 `False`。
- 继续扩大工具系统：剪枝。当前真正缺口是状态口径一致性，不是缺工具；新增自动化会扩大治理面。

## Selected Route

- 保留路线：先完成系统方向校准，修正陈旧文档口径，确认代码、测试、文档、治理一致。
- 为什么这是最小正确路线：它不改变代码行为，不触碰真实数据根，只把 P7d 之后的 gate 语义固定为可审计事实，为下一步正式制度规则定义 spec 清路。

## Hard Boundaries

- `institution_rule_definition_allowed`：P7d 后可为 `True`，但仅限 `rule-definition-only`。
- `trading_layer_read_allowed`：必须保持 `False`。
- `signal_generation_allowed`：必须保持 `False`。
- `backtest_execution_allowed`：必须保持 `False`。
- 真实数据根写入：本次不写入 `Z:\asteria-trading-labs-data`、`Z:\malf-data`、`Z:\new_tdx64` 或 `Z:\tdx_offline_Data`。

## Verification

- Skill validation：`asteria-decision-gate`、`asteria-daily-status-review`、`asteria-doc-reality-audit` 均通过官方 `quick_validate.py`。
- Focused：`python -B -m unittest tests.test_tdx_local_first_batch -v`，80 tests OK。
- Full：`python -B -m unittest discover -s tests -v`，271 tests OK。
- 文档同步：`AGENTS.md`、`docs/06_Roadmap_TodoList_后续路线图与待办.md`、`docs/daily-status/2026-07-01-下一步工作计划.md` 与本 DecisionTrace 对齐。
- Git 状态：本次只产生文档治理改动。

## Lessons

- P7d 之后不能再把 `institution_rule_definition_allowed` 归入“必须保持 false”的硬闸；它已经成为 rule-definition-only 的开放信号。
- 下一步仍不是 P8 signal/backtest，而是正式制度规则定义 spec、plan 和 TDD。
