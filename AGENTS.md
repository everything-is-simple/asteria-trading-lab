# Repository Guidelines

## 项目结构与模块组织

- `src/original_tachibana/`：原始立花交易回放引擎、报告生成器、逐笔交易段回放。
- `src/tachibana_front_filter.py`：MALF 到立花法的前置认知过滤器。
- `src/ashare_intake_validator.py`：A 股只读审计链路总协调器。
- `src/data_sources/tdx_local/`：通达信与 DuckDB 本地读取、首批样本构建、制度事实包导出。
- `tests/`：`unittest` 测试与 `tests/fixtures/` 合成样本。
- `docs/`：研究、审计、方案与施工文档；真实市场大文件不入库。

## 构建、测试与开发命令

运行 Python 入口前先设置模块路径：

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
python -m tachibana_front_filter --audit-front-filter-system
python -m ashare_intake_validator --help
python -m data_sources.tdx_local.institution_facts --duckdb-root Z:\malf-data --data-root Z:\asteria-trading-labs-data --ts-code 000001.SZ --ts-code 300750.SZ --ts-code 600000.SH --window-start 2026-03-24 --window-end 2026-04-03
```

做管道定点修改时，优先跑：

```powershell
python -m unittest tests.test_ashare_intake_validator -v
```

## 编码风格与命名约定

- 语言为 Python，使用 4 空格缩进。
- 优先标准库与现有辅助函数，避免引入新依赖。
- 函数、变量、文件名统一使用 `snake_case`。
- 新增审计阶段时，沿用 `ashare_intake_validator.py` 中的 `audit_*` 命名。
- 除受控导出命令外，模块应保持只读，不得偷偷写回数据。
- 不得把交易信号、仓位字段混入 MALF 或制度审计层。

## 可审计决策链

- 新 gate、新阶段、路线选择、制度审计或数据写入边界决策时，使用 `asteria-decision-gate`，先记录 `DecisionTrace`：当前证据、候选路线、剪枝理由、保留路线、硬边界与验证方式。
- 开工、收工、日报、阶段总结、当前进度和下一步判断时，使用 `asteria-daily-status-review`，必须从最近会话、记忆摘要、git、`docs/04_施工计划_当前进度版.md`、`docs/06_Roadmap_TodoList_后续路线图与待办.md` 和 `docs/daily-status/` 取证。
- 创建或修订 PRD、TRD、Design、README、AGENTS、CLAUDE、施工计划、路线图和 handoff 文档时，使用 `asteria-doc-reality-audit`，区分 `implemented`、`verified`、`design-only`、`research-only`、`not-started`、`blocked`。
- 重大路线选择的 DecisionTrace 存放到 `docs/decision-traces/`；不要用 hook 或 automation 代替决策记录。

## 测试规范

- 测试框架：标准库 `unittest`。
- 测试文件命名：`test_*.py`。
- 新增审计阶段时，至少补三类测试：`pass`、`blocked`、禁用字段校验。
- P7d 之后，`institution_rule_definition_allowed=True` 只表示制度规则定义入口开放为 `rule-definition-only`。
- 下游硬闸默认必须保持 `false`：
  - `trading_layer_read_allowed`
  - `signal_generation_allowed`
  - `backtest_execution_allowed`

## 提交与 Pull Request 规范

- 提交信息沿用当前仓库风格，使用祈使句，例如：
  - `Add execution policy archive layer`
  - `Make institution fact export replace target files atomically`
- 每个提交尽量只做一件事：一个功能层、一组测试、或一轮文档修订。
- PR 说明应写清：
  - 改动影响的管道阶段
  - 已运行的测试命令
  - 触碰了哪些外部数据根目录
  - 是否涉及真实市场文件读写
- 若改了 CLI，附上命令示例与关键输出摘要。

## 安全与数据说明

- 真实数据位于仓库外，主要包括：
  - `Z:\asteria-trading-labs-data`
  - `Z:\malf-data`
  - `Z:\new_tdx64`
  - `Z:\tdx_offline_Data`
- 不要提交 DuckDB、通达信二进制文件、凭据、或真实市场导出数据。
