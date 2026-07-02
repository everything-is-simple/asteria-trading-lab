# 正式制度规则定义写入前审计实施计划

> **代理执行说明：** 必须使用子技能 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务执行本计划。步骤使用复选框（`- [ ]`）语法追踪进度。

**目标：** 构建 P8 到写入确认之间的审计 gate，不写入任何文件，不打开 trading layer read、signal generation 或 backtest execution。

**架构：** 在 P8 包准备之后增加一个显式内存审计入口。实现步骤为：先为 P8 包报告补充链路身份字段，再新增 `audit_formal_institution_rule_definition_write_when_explicitly_requested`，用于校验包身份、请求范围、blocked 状态、禁止字段和硬闸。

**技术栈：** Python 标准库、`unittest`、现有 `data_sources.tdx_local` 审计帮助函数。

---

### 任务 1：新增写入审计 RED 测试

**文件：**
- 新建：`tests/test_tdx_local_rule_definition_write_audit.py`
- 修改：`tests/tdx_local_first_batch_support.py`
- 修改：`tests/test_tdx_local_first_batch.py`

- [ ] **步骤 1：在测试支持文件中导入新入口**

在 `tests/tdx_local_first_batch_support.py` 的 `data_sources.tdx_local` 导入块中加入 `audit_formal_institution_rule_definition_write_when_explicitly_requested`。

- [ ] **步骤 2：新增写入前 P9 辅助载荷**

在 `tests/tdx_local_first_batch_support.py` 中新增辅助方法：

```python
def _p8_prepared_package_report(self, root: Path) -> dict[str, object]:
    inputs = self._p8_formal_rule_definition_persistence_package_inputs(root)
    report = prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested(
        **inputs,
        generated_at="2026-07-01T16:10:00+08:00",
    )
    self.assertEqual(report["result"], "pass")
    return report

def _formal_rule_definition_write_audit_request(self, package_report: dict[str, object]) -> dict[str, object]:
    return {
        "write_audit_requested": True,
        "write_audit_scope": "formal_institution_rule_definition",
        "target_kind": "formal_rule_definition_file",
        "target_package_id": package_report["package_id"],
        "target_package_version": package_report["package_version"],
        "real_data_root_write_confirmed": False,
        "manual_confirmation_required": True,
        "no_trading_no_signal_no_backtest_acknowledged": True,
    }
```

- [ ] **步骤 3：新建通过和硬闸测试**

新建 `tests/test_tdx_local_rule_definition_write_audit.py`，内容如下：

```python
from __future__ import annotations

from tests.tdx_local_first_batch_support import *


class TdxLocalRuleDefinitionWriteAuditTest(TdxLocalFirstBatchSupport):
    def test_audit_formal_institution_rule_definition_write_when_explicitly_requested_passes_valid_package_and_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package_report = self._p8_prepared_package_report(Path(tmp))
            request = self._formal_rule_definition_write_audit_request(package_report)

            report = audit_formal_institution_rule_definition_write_when_explicitly_requested(
                formal_rule_definition_persistence_package_report=package_report,
                formal_rule_definition_write_audit_request=request,
                generated_at="2026-07-02T09:00:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["audit_id"], "formal_institution_rule_definition_write_audit_v0.1")
        self.assertEqual(report["formal_institution_rule_definition_write_audit_result"], "pass")
        self.assertEqual(
            report["formal_institution_rule_definition_write_audit_status"],
            "ready_for_formal_institution_rule_definition_explicit_write_confirmation_gate",
        )
        self.assertFalse(report["formal_institution_rule_definition_write_allowed"])
        self.assertFalse(report["formal_institution_rule_definition_persistence_performed"])
        self.assertEqual(report["source_package_id"], package_report["package_id"])
        self.assertEqual(report["source_package_version"], package_report["package_version"])
        self.assertTrue(report["institution_rule_definition_allowed"])
        self.assertEqual(report["institution_rule_definition_scope"], "rule-definition-only")
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(
            report["next_gate"],
            "gate:formal_institution_rule_definition_explicit_write_confirmation",
        )
        self.assertEqual(report["package_staleness_policy"], "not_enforced_v0.1")
        self.assertEqual(
            report["write_audit_idempotency_policy"],
            "same_package_identity_is_idempotent_v0.1",
        )
        payload = json.dumps(report, ensure_ascii=False)
        self.assertFalse(any(field in payload for field in P7_FORBIDDEN_FIELDS))

    def test_audit_formal_institution_rule_definition_write_when_explicitly_requested_keeps_downstream_hard_gates_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package_report = self._p8_prepared_package_report(Path(tmp))
            request = self._formal_rule_definition_write_audit_request(package_report)

            report = audit_formal_institution_rule_definition_write_when_explicitly_requested(
                formal_rule_definition_persistence_package_report=package_report,
                formal_rule_definition_write_audit_request=request,
                generated_at="2026-07-02T09:10:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertFalse(report["formal_institution_rule_definition_write_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
```

- [ ] **步骤 4：新增身份拦截和请求测试**

新增测试，覆盖以下情况：P8 报告缺失、P8 报告失败、`report_id` 缺失、`package_id` 缺失、`package_version` 缺失、目标包不匹配、目标版本不匹配、写入确认过早，以及确认字段缺失。

- [ ] **步骤 5：新增禁止字段和非布尔 write_allowed 测试**

新增测试，拦截以下情况：

```python
package_report["formal_institution_rule_definition_write_allowed"] = True
package_report["formal_institution_rule_definition_write_allowed"] = "true"
package_report["position_size"] = 1.0
```

禁止字段场景下，`position_size` 不得出现在序列化输出中。

- [ ] **步骤 6：新增幂等性测试**

使用相同的包和请求连续调用新审计两次，断言两次通过报告的源包身份、状态和策略字段完全一致。

- [ ] **步骤 7：注册拆分测试模块**

在 `tests/test_tdx_local_first_batch.py` 的 `SPLIT_TEST_MODULES` 中加入 `tests.test_tdx_local_rule_definition_write_audit`。

- [ ] **步骤 8：执行 RED 验证**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_tdx_local_rule_definition_write_audit -v
```

预期：失败，原因是 `audit_formal_institution_rule_definition_write_when_explicitly_requested` 尚未实现/导出，或 P8 尚未提供所需的身份字段。

### 任务 2：强化 P8 包身份字段

**文件：**
- 修改：`src/data_sources/tdx_local/rule_definition_gates.py`
- 修改：`tests/test_tdx_local_rule_definition_persistence_package.py`

- [ ] **步骤 1：新增 P8 身份断言**

扩展现有 P8 通过测试，要求包含以下字段：

```python
self.assertEqual(report["report_id"], "formal_institution_rule_definition_persistence_package_report_v0.1")
self.assertEqual(report["package_id"], "formal_institution_rule_definition_persistence_package_v0.1")
self.assertEqual(report["package_version"], "v0.1")
```

- [ ] **步骤 2：实现 P8 身份字段**

在 P8 通过报告中加入上述三个字段，不得改变现有 P8 状态或硬闸行为。

- [ ] **步骤 3：执行 P8 专项验证**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_tdx_local_rule_definition_persistence_package -v
```

预期：实现后通过。

### 任务 3：实现写入审计 Gate

**文件：**
- 修改：`src/data_sources/tdx_local/rule_definition_gates.py`
- 修改：`src/data_sources/tdx_local/first_batch_rule_definition_helpers.py`
- 修改：`src/data_sources/tdx_local/__init__.py`

- [ ] **步骤 1：新增拦截报告辅助函数**

新增 `_formal_institution_rule_definition_write_audit_blocked_report(generated_at, issues)`，使用以下拦截状态：

`blocked_before_formal_institution_rule_definition_explicit_write_confirmation_gate`

必须设置：

```python
"formal_institution_rule_definition_write_audit_result": "blocked"
"formal_institution_rule_definition_write_allowed": False
"formal_institution_rule_definition_persistence_performed": False
"institution_rule_definition_allowed": False
"trading_layer_read_allowed": False
"signal_generation_allowed": False
"backtest_execution_allowed": False
```

- [ ] **步骤 2：新增 P8 包校验器**

校验 `audit_id`、`report_id`、`package_id`、`package_version`、P8 通过状态、包已准备、持久化未执行、write allowed 缺失或为 false、包状态字段、rule-definition-only gate 以及下游硬闸。

问题代码：

```python
formal_institution_rule_definition_write_audit_requires_p8_package_pass
formal_institution_rule_definition_write_audit_requires_report_id
formal_institution_rule_definition_write_audit_requires_package_identity
formal_institution_rule_definition_write_audit_requires_write_not_already_allowed
formal_institution_rule_definition_write_audit_downstream_gate_open
```

- [ ] **步骤 3：新增请求校验器**

校验请求对象、scope、target kind、`target_package_id` 匹配、`target_package_version` 匹配、禁止过早确认真实数据根目录、手动确认要求，以及不交易/不信号/不回测的确认字段。

问题代码：

```python
formal_institution_rule_definition_write_audit_requires_request
formal_institution_rule_definition_write_audit_requires_rule_definition_scope
formal_institution_rule_definition_write_audit_requires_formal_rule_file_target
formal_institution_rule_definition_write_audit_package_identity_mismatch
formal_institution_rule_definition_write_audit_rejects_early_real_data_root_confirmation
formal_institution_rule_definition_write_audit_requires_manual_confirmation_gate
formal_institution_rule_definition_write_audit_requires_no_downstream_acknowledgement
```

- [ ] **步骤 4：新增公开函数**

新增：

```python
def audit_formal_institution_rule_definition_write_when_explicitly_requested(
    formal_rule_definition_persistence_package_report: dict[str, Any] | None,
    formal_rule_definition_write_audit_request: dict[str, Any] | None,
    generated_at: str | None = None,
) -> dict[str, Any]:
```

返回与规格完全对齐的通过报告，包含 `next_gate`、过期策略和幂等策略。

- [ ] **步骤 5：导出公开函数**

在 `src/data_sources/tdx_local/__init__.py` 中添加导入和 `__all__` 条目。

### 任务 4：验证

**文件：**
- 无计划修改。

- [ ] **步骤 1：执行新专项测试**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_tdx_local_rule_definition_write_audit -v
```

- [ ] **步骤 2：执行聚合专项 gate 测试**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_tdx_local_first_batch -v
```

- [ ] **步骤 3：执行源文件大小契约检查**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_source_file_size_contract -v
```

- [ ] **步骤 4：执行全量测试**

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests
```

- [ ] **步骤 5：执行 diff 空白字符检查**

```powershell
git diff --check
```

### 任务 5：文档收尾

**文件：**
- 仅在绿灯后修改：`docs/04_施工计划_当前进度版.md`
- 仅在绿灯后修改：`docs/06_Roadmap_TodoList_后续路线图与待办.md`
- 仅在绿灯后新建：`docs/daily-status/2026-07-02-项目阶段总结.md`

- [ ] 仅在测试通过后记录写入审计已实现/验证。
- [ ] 说明通过意味着 `ready_for_formal_institution_rule_definition_explicit_write_confirmation_gate`。
- [ ] 说明尚未写入任何正式规则文件。
- [ ] 说明 `formal_institution_rule_definition_write_allowed=False`。
- [ ] 说明 trading layer 读取、信号生成和回测执行仍处于关闭状态。

### 自检

- 规格覆盖：计划涵盖下一 gate 命名、write_allowed 为 false 的语义、包身份、report_id、过期策略、幂等策略、非布尔 write_allowed 拦截、禁止字段、硬闸和非目标。
- 占位符扫描：不存在任何 TBD/TODO 占位符。
- 类型一致性：函数名、报告键、状态值和问题代码均与写入审计规格一致。
