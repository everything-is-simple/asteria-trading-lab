# 2026-07-01 Formal Rule Definition Next Gate DecisionTrace

| Field | Content |
|---|---|
| `current_state` | `docs/04_施工计划_当前进度版.md` 与 `docs/06_Roadmap_TodoList_后续路线图与待办.md` 一致证明当前系统位置为 `institution_rule_definition_opened_for_rule_definition_only`。代码与测试证据位于 `src/data_sources/tdx_local/first_batch.py`、`src/data_sources/tdx_local/__init__.py`、`tests/test_tdx_local_first_batch.py` 的 P7d 实现与覆盖。 |
| `candidate_routes` | `route_a`: 直接进入 `signal/backtest`；`route_b`: 先新增 formal rule definition 审计层，继续只读消费 `P7d` 与三类 contract-ready reviewed draft；`route_c`: 先新增一个汇总 package 层，再做 formal rule definition 审计。 |
| `pruned_routes` | `route_a` 被剪枝：违反 `AGENTS.md` 与当前硬边界，提前触碰 `trading_layer_read / signal_generation / backtest_execution`。`route_c` 被剪枝：比当前目标多引入一个新 artifact 层，范围扩大，且没有用户要求先做 package。 |
| `selected_route` | 选择 `route_b`：新增最小 `formal institution rule definition audit`，读取 `P7d open gate report`、`t1 / price_limit / suspension_resume` 三类 contract-ready reviewed draft，以及待审的 `formal institution rule definition input`，只输出 formal rule definition 审计结果。 |
| `hard_boundaries` | 不打开 `trading_layer_read_allowed`；不打开 `signal_generation_allowed`；不打开 `backtest_execution_allowed`；不输出交易信号、仓位、订单、PnL 语义；不写真实数据根；不把制度规则语义回流到 MALF 或制度前置审计层。 |
| `verification` | 先写并观察 `pass / blocked / forbidden-field / hard-gate` RED 测试失败，再实现最小函数并导出；跑 `python -B -m unittest tests.test_tdx_local_first_batch -v`、`python -B -m unittest discover -s tests -v` 与 `git diff --check`；最后再更新 `docs/04`、`docs/06`、`docs/daily-status/2026-07-01-下一步工作计划.md`。 |
