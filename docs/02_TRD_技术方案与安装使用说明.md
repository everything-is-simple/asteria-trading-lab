# 02_TRD — 技术方案与安装使用说明

**版本**: v0.2  
**日期**: 2026-06-28

## 1. 技术栈

- Python 3.14
- `unittest`
- DuckDB
- 本地 Tongdaxin `.day` / `.txt` 数据
- 可选校验源：`baostock`、`pytdx`

当前仓库无 `requirements.txt`。最小依赖安装：

```powershell
pip install duckdb
```

可选：

```powershell
pip install baostock
pip install pytdx
```

## 2. 本地目录约定

- 项目仓库：`Z:\asteria-trading-lab`
- 正式数据：`Z:\asteria-trading-labs-data`
- Definitive 定义：`Z:\asteria-trading-labs-Definitive-validated`
- DuckDB 主账本：`Z:\malf-data`
- Tongdaxin：`Z:\new_tdx64`
- Tongdaxin 离线：`Z:\tdx_offline_Data`

## 3. 当前代码结构

- `src/original_tachibana/`：原始立花回测与报告生成
- `src/tachibana_front_filter.py`：MALF-立花前置认知过滤器
- `src/ashare_intake_validator.py`：A 股审计链路总协调器
- `src/data_sources/tdx_local/`：本地 TDX / DuckDB 只读接入
- `tests/`：当前 7 个测试文件，全量 161 tests

## 4. 关键命令

### 4.1 全量测试

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
```

### 4.2 前置过滤器

```powershell
$env:PYTHONPATH='src'
python -m tachibana_front_filter --audit-front-filter-system
```

### 4.3 A 股审计链路帮助

```powershell
$env:PYTHONPATH='src'
python -m ashare_intake_validator --help
```

### 4.4 制度事实包生成

```powershell
$env:PYTHONPATH='src'
python -m data_sources.tdx_local.institution_facts --duckdb-root Z:\malf-data --data-root Z:\asteria-trading-labs-data --ts-code 000001.SZ --ts-code 300750.SZ --ts-code 600000.SH --window-start 2026-03-24 --window-end 2026-04-03
```

### 4.5 当前活跃链路验证

```powershell
$env:PYTHONPATH='src'
python -m ashare_intake_validator --root Z:\asteria-trading-labs-data --audit-first-batch-execution-policy-research-prep Z:\asteria-trading-lab\docs\tachibana\execution-policy-reviews\first-batch-v0.1 --method-pm-plan-dir Z:\asteria-trading-lab\docs\tachibana\method-pm-plans\first-batch-v0.1 --institution-fact-root Z:\asteria-trading-labs-data
```

## 5. 当前已完成部分

- TDX `.day` / `.txt` 读取
- DuckDB 只读接入
- 首批真实样本接入包
- 最小制度事实包
- 前置过滤器
- `execution_policy_research_prep` 前全部审计链路

## 6. 重要边界

- `first_batch.py`、`audit.py` 目前以函数入口为主，不应写成“完整终端工具”
- 制度事实包当前是“最小通电”版本：
  - `limit_up_price` / `limit_down_price` 为空
  - `close_limit_status` / `touched_limit_status` 为 `unknown`
- 当前系统不生成交易信号，不生成仓位，不允许回测成交
