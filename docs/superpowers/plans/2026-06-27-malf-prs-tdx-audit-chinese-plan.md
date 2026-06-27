# MALF 前置过滤器发布与本地数据接入中文执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把两个已完成的 GitHub draft PR 文案定稿，把本地 Tongdaxin / 离线数据审计的字段映射收口成可复核清单，并把最小接入原型稳定到 `symbol_master / trading_calendar / daily_bars / sector_membership` 四类主输出。

**Architecture:** 先冻结发布口径，再冻结数据边界，最后冻结原型输出。所有真实本地大文件都只读审计，不复制、不 stage、不 push。PR 发布只处理代码和文档，小型 fixture 继续保留在仓库内，真实 `.day` / `.txt` / `.duckdb` / `.7z` 只作为外部输入。

**Tech Stack:** PowerShell, Python 3.11, `unittest`, GitHub draft PR, 本地 Tongdaxin `tqcenter.py` / `PYMP` 模式。

---

## 当前事实

- `codex/malf-tachibana-front-filter` 已完成并推送。
- `codex/tdx-local-data-audit` 已完成并推送。
- 本地 `gh` 不可用，GitHub draft PR 目前不能走 CLI。
- 本地大目录边界必须保持只读：
  - `Z:\new_tdx64`
  - `Z:\tdx_offline_Data`
  - `Z:\malf-data`
- 真实行情文件和数据库文件绝不上传远端。

## Draft PR 文案

### PR 1

**标题**

`[codex] MALF Tachibana front filter gates`

**正文**

```markdown
## 做了什么

这次提交把 MALF 作为立花义正波段交易法的前置认知过滤器做实，补齐了结构资格、节奏意义、Method / PM 边界和接口边界的只读闸门。

## 为什么要做

核心目标不是改 A 股制度规则，而是先判断“什么结构条件下，立花法才值得进入讨论”。因此这部分只负责结构事实与前置过滤，不输出交易裁决，也不把执行语义回流污染 MALF。

## 影响

`rhythm_meaning`、`tachibana_applicability`、`qualification_rule_id` 这些字段现在有了更稳的边界定义；Data / Signal / Backtest 的角色也更清楚了。

## 验证

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests
```

## 边界

不包含 A 股制度改造，不包含真实本地大数据接入，不包含任何交易执行字段的回写。
```

### PR 2

**标题**

`[codex] Local Tongdaxin data audit scaffold`

**正文**

```markdown
## 做了什么

这次提交补上了本机 Tongdaxin / 离线目录 / 旧 DuckDB 的只读审计骨架，并把本地数据资产的主输出收口到 `symbol_master / trading_calendar / daily_bars / sector_membership`。

## 为什么要做

真实本地大数据不能直接进仓库，所以需要先有一个可重复执行的审计层，明确哪些是事实、哪些只是辅助信息、哪些绝对不能上传。

## 影响

现在可以用统一的审计入口检查 `Z:\new_tdx64`、`Z:\tdx_offline_Data`、`Z:\malf-data` 的形态，并把字段映射收成只读摘要，不复制原始 `.day` / `.txt` / `.duckdb` 文件。

## 验证

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests
```

## 边界

不写正式数据目录，不导出真实行情文件，不新增交易语义，不把本地大文件 stage 到 git。
```

## 字段映射清单

| 主输出 | 主要来源 | 说明 |
|---|---|---|
| `symbol_master` | `Z:\new_tdx64` 的本地 Python / `PYMP` 可用信息、`Z:\tdx_offline_Data\stock\*.txt`、旧 DuckDB 里的标的主数据 | 只记录标的主键、简称、市场归属、停复牌等基础事实。 |
| `trading_calendar` | 离线交易日文件、Tongdaxin 本地日历能力、历史交易日事实 | 只记录交易日与非交易日，不混入制度结论。 |
| `daily_bars` | `Z:\tdx_offline_Data\stock-day\*.day`、`Z:\tdx_offline_Data\stock\*.txt` | 只记录日线 OHLCV 与必要的原始来源引用。 |
| `sector_membership` | `Z:\tdx_offline_Data\stock\*.txt`、行业/板块成员表、旧 DuckDB 资产 | 只记录行业/板块成员关系，不写选股结论。 |
| `adjustment_metadata` | 复权相关 `.txt`、旧 DuckDB 的复权或事件痕迹 | 作为辅助事实，不算主输出。 |

## 最小接入原型扩展范围

### `src/data_sources/tdx_local/`

新增或稳定以下只读入口：

- `symbol_master`
- `trading_calendar`
- `daily_bars`
- `sector_membership`

要求：

- 只读，不落盘真实行情文件。
- 默认输出摘要、schema、统计信息。
- 对缺失路径返回可解释的 `blocked/report` 状态。

### `tests/test_tdx_local_audit.py`

补齐或维持以下测试：

- 真实大文件不会被纳入仓库输出。
- 缺少本地路径时返回明确阻断原因。
- 四类主输出都能从审计报告里稳定拿到。
- `adjustment_metadata` 只作为辅助事实存在。

### `docs/a-share/local-data-audit.md`

维持为人工可读总说明，强调：

- 哪些目录只读；
- 哪些文件类型绝不上传；
- 哪些是主输出；
- 哪些只是辅助事实。

## 执行顺序

1. 定稿两个 draft PR 的标题和正文。
2. 固化本地数据审计字段映射清单。
3. 复核 `src/data_sources/tdx_local/` 的四类主输出是否都齐。
4. 复核 `tests/test_tdx_local_audit.py` 是否覆盖边界。
5. 只在 GitHub 登录态可用时创建 draft PR。

## 验证命令

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests
git status --short --branch
```

## 完成判定

- 两个 draft PR 的标题和正文已定稿。
- 字段映射清单只保留四类主输出和一类辅助事实。
- Tongdaxin 最小接入原型只做只读审计，不碰真实大文件。
- 本地工作区与远端分支都保持可解释、可复核。
