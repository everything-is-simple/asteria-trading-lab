# Decision Traces

本目录记录 Asteria 的重大路线选择。目标不是保存模型的内部思考，而是保存可审计的外显决策链：识别任务、找证据、列候选路线、剪枝错误路线、保留最小正确路线、验证、记录经验。

## 何时记录

- 新 gate、新阶段或新里程碑启动前。
- 涉及真实数据根、制度规则、trading layer、signal、backtest 或仓位边界时。
- 文档、代码和路线图之间出现状态分歧时。
- 需要解释为什么不走某条看似可行但会扩大工程或越界的路线时。

## 文件命名

使用：

```text
YYYY-MM-DD-<short-topic>.md
```

示例：

```text
2026-07-01-p7d-rule-definition-open-gate.md
```

## 模板

```markdown
# <决策主题>

## Current State

- 证据：
- 当前 gate/status：

## Candidate Routes

1. 路线 A：
2. 路线 B：
3. 路线 C：

## Pruned Routes

- 剪枝路线：
- 剪枝理由：

## Selected Route

- 保留路线：
- 为什么这是最小正确路线：

## Hard Boundaries

- `institution_rule_definition_allowed`：
- `trading_layer_read_allowed`：
- `signal_generation_allowed`：
- `backtest_execution_allowed`：
- 真实数据根写入：

## Verification

- Focused：
- Full：
- 文档同步：
- Git 状态：

## Lessons

- 后续复用经验：
```

## 边界

- DecisionTrace 不是日报；日报放在 `docs/daily-status/`。
- DecisionTrace 不是 spec；规格仍放在 `docs/superpowers/specs/`。
- DecisionTrace 不是 plan；施工计划仍放在 `docs/superpowers/plans/`。
- DecisionTrace 不允许替代测试、代码验证或人工确认 gate。
