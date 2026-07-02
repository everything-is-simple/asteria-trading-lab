# Price Limit Fact Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不越过制度审计边界的前提下，为 `institution_facts` 最小制度事实包补上可推导的 `limit_up_price / limit_down_price`，同时保持 `close_limit_status / touched_limit_status` 仍为显式事实优先、缺失即 `unknown`。

**Architecture:** 沿用 `src/data_sources/tdx_local/institution_facts.py` 当前“DuckDB tradability 行 -> CSV 制度事实包”的单文件构建路径，在读出 `tradability_fact` 后补一层只读价格边界富化。价格边界只依赖本地已有事实来源：`tradability_fact`、`first_batch` 同口径的 `board_type / is_st / is_new_stock_window` 判断，以及从本地日线读取得到的 `prev_close`。不改 `ashare_intake_validator.py` 的审计语义，不开放规则定义、signal 或 backtest。

**Tech Stack:** PowerShell, Python 3.11, 标准库 `decimal` / `unittest`, 现有 `data_sources.tdx_local` 读取器与只读 CSV 导出链路。

---

## 子项目边界

这个计划只做一件事：

- 让 `data_sources.tdx_local.institution_facts` 在“可明确推导”的情况下输出非空 `limit_up_price / limit_down_price`。

明确不在本计划范围：

- 不推导 `close_limit_status / touched_limit_status`；
- 不定义完整涨跌停制度规则引擎；
- 不修改 `src/ashare_intake_validator.py` 的下游判断逻辑；
- 不启动 `PAS`、signal、backtest、仓位或交易许可语义。

## 文件结构

### 需要修改

- `src/data_sources/tdx_local/institution_facts.py`
  - 增加价格边界推导 helper；
  - 增加按 `ts_code + trade_date` 读取 `prev_close` 的本地日线 helper；
  - 增加 `board_type / is_st / is_new_stock_window` 判定 helper；
  - 把 `limit_price_policy` 从当前最小通电口径改成“derived_bounds_explicit_status_only”。
- `tests/test_tdx_local_institution_facts.py`
  - 新增 3 组红绿测试：可推导、保持 `unknown`、特殊例外留空；
  - 保留现有 CLI 与 stale file 行为测试。
- `src/README.md`
  - 更新 `institution_facts` 当前策略说明与命令说明。

### 当前不改

- `src/ashare_intake_validator.py`
- `tests/test_ashare_intake_validator.py`
- `src/data_sources/tdx_local/first_batch.py`

原因：本子项目只补制度事实包，不改变样本接入与后续审计层结构。

## 输出契约

完成后，单条制度事实行的最小目标如下：

```python
{
    "ts_code": "300750.SZ",
    "trade_date": "2026-03-24",
    "is_trading_day": "true",
    "is_suspended": "false",
    "limit_up_price": "237.60",
    "limit_down_price": "158.40",
    "close_limit_status": "unknown",
    "touched_limit_status": "unknown",
    "board_lot_size": "100",
    "source_ref": "market_meta.duckdb:market_meta.tradability_fact:sz300750:2026-03-24:hash-3",
}
```

报告层的最小契约调整：

```python
{
    "result": "pass",
    "limit_price_policy": "derived_bounds_explicit_status_only",
    "institution_rule_definition_allowed": False,
    "signal_generation_allowed": False,
    "backtest_execution_allowed": False,
}
```

## 关键实现口径

### 价格边界推导口径

- `main`: `+10% / -10%`
- `gem`: `+20% / -20%`
- `star`: `+20% / -20%`
- `bse`: `+30% / -30%`
- `is_st=true`: 一律覆盖为 `+5% / -5%`

### 特殊窗口口径

- `is_new_stock_window=true` 时，本次不强推价格边界；
- 直接保留 `limit_up_price="" / limit_down_price=""`；
- `close_limit_status / touched_limit_status` 继续保持 `unknown`。

### `prev_close` 口径

- `prev_close` 不是来自 DuckDB `tradability_fact`；
- 使用 `read_daily_bars(offline_root, ts_code)` 读取本地原始日线；
- 在目标 `trade_date` 的前一个可见 bar 上取 `close` 作为 `prev_close`；
- 若前一个 bar 缺失，则本行价格边界继续留空。

### 数值格式口径

- 使用 `Decimal` 计算，不用二进制浮点直接乘；
- 最终输出保留两位小数；
- 使用 `ROUND_HALF_UP`，避免测试里出现浮点尾差。

## Task 1: 先写制度事实补强的失败测试

**Files:**
- Modify: `tests/test_tdx_local_institution_facts.py`
- Modify: `src/data_sources/tdx_local/institution_facts.py`

- [ ] **Step 1: 写“可推导价格边界”失败测试**

```python
def test_build_minimal_institution_fact_package_derives_price_bounds_for_known_board(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        duckdb_root = root / "duckdb"
        data_root = root / "data"
        offline_root = root / "offline"
        duckdb_root.mkdir()

        import duckdb

        con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
        con.execute(
            """
            create table tradability_fact (
                symbol varchar,
                asset_type varchar,
                trade_dt date,
                tradability_status varchar,
                blocked_reason varchar,
                source_role varchar,
                source_run_id varchar,
                schema_version varchar,
                rule_version varchar,
                source_manifest_hash varchar
            )
            """
        )
        con.execute(
            """
            insert into tradability_fact values
            ('sz300750', 'stock', '2026-03-24', 'tradable', null, 'tdx_direct', 'run-1', 'v1', 'r1', 'hash-3')
            """
        )
        con.close()

        day_dir = offline_root / "raw" / "sz" / "lday"
        day_dir.mkdir(parents=True)
        _write_day_file(
            day_dir / "sz300750.day",
            [
                (20260321, 19800, 19900, 19700, 19800, 1000.0, 100000),
                (20260324, 20000, 21000, 19500, 20500, 1200.0, 120000),
            ],
        )

        report = build_minimal_institution_fact_package(
            duckdb_root=duckdb_root,
            data_root=data_root,
            ts_codes=["300750.SZ"],
            window_start="2026-03-24",
            window_end="2026-03-24",
            offline_root=offline_root,
        )

        rows = _read_csv(data_root / "ashare" / "institution-facts-v0.1" / "300750.SZ.csv")

    self.assertEqual(report["result"], "pass")
    self.assertEqual(report["limit_price_policy"], "derived_bounds_explicit_status_only")
    self.assertEqual(rows[0]["limit_up_price"], "237.60")
    self.assertEqual(rows[0]["limit_down_price"], "158.40")
    self.assertEqual(rows[0]["close_limit_status"], "unknown")
    self.assertEqual(rows[0]["touched_limit_status"], "unknown")
```

- [ ] **Step 2: 写“新股窗口继续留空”失败测试**

```python
def test_build_minimal_institution_fact_package_keeps_bounds_empty_for_new_stock_window(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        duckdb_root = root / "duckdb"
        data_root = root / "data"
        offline_root = root / "offline"
        duckdb_root.mkdir()

        import duckdb

        con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
        con.execute(
            """
            create table tradability_fact (
                symbol varchar,
                asset_type varchar,
                trade_dt date,
                tradability_status varchar,
                blocked_reason varchar,
                source_role varchar,
                source_run_id varchar,
                schema_version varchar,
                rule_version varchar,
                source_manifest_hash varchar
            )
            """
        )
        con.execute(
            """
            insert into tradability_fact values
            ('sz301001', 'stock', '2026-03-24', 'tradable', null, 'tdx_direct', 'run-1', 'v1', 'r1', 'hash-9')
            """
        )
        con.close()

        day_dir = offline_root / "raw" / "sz" / "lday"
        day_dir.mkdir(parents=True)
        _write_day_file(
            day_dir / "sz301001.day",
            [
                (20260321, 1000, 1100, 900, 1000, 100.0, 10000),
                (20260324, 1010, 1200, 1000, 1150, 120.0, 12000),
            ],
        )

        report = build_minimal_institution_fact_package(
            duckdb_root=duckdb_root,
            data_root=data_root,
            ts_codes=["301001.SZ"],
            window_start="2026-03-24",
            window_end="2026-03-24",
            offline_root=offline_root,
        )

        rows = _read_csv(data_root / "ashare" / "institution-facts-v0.1" / "301001.SZ.csv")

    self.assertEqual(report["result"], "pass")
    self.assertEqual(rows[0]["limit_up_price"], "")
    self.assertEqual(rows[0]["limit_down_price"], "")
    self.assertEqual(rows[0]["close_limit_status"], "unknown")
    self.assertEqual(rows[0]["touched_limit_status"], "unknown")
```

- [ ] **Step 3: 写“缺少 prev_close 时仍保持留空”失败测试**

```python
def test_build_minimal_institution_fact_package_keeps_bounds_empty_without_prev_close(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        duckdb_root = root / "duckdb"
        data_root = root / "data"
        offline_root = root / "offline"
        duckdb_root.mkdir()

        import duckdb

        con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
        con.execute(
            """
            create table tradability_fact (
                symbol varchar,
                asset_type varchar,
                trade_dt date,
                tradability_status varchar,
                blocked_reason varchar,
                source_role varchar,
                source_run_id varchar,
                schema_version varchar,
                rule_version varchar,
                source_manifest_hash varchar
            )
            """
        )
        con.execute(
            """
            insert into tradability_fact values
            ('sh600000', 'stock', '2026-03-24', 'tradable', null, 'tdx_direct', 'run-1', 'v1', 'r1', 'hash-6')
            """
        )
        con.close()

        day_dir = offline_root / "raw" / "sh" / "lday"
        day_dir.mkdir(parents=True)
        _write_day_file(
            day_dir / "sh600000.day",
            [
                (20260324, 1000, 1020, 990, 1010, 100.0, 10000),
            ],
        )

        report = build_minimal_institution_fact_package(
            duckdb_root=duckdb_root,
            data_root=data_root,
            ts_codes=["600000.SH"],
            window_start="2026-03-24",
            window_end="2026-03-24",
            offline_root=offline_root,
        )

        rows = _read_csv(data_root / "ashare" / "institution-facts-v0.1" / "600000.SH.csv")

    self.assertEqual(report["result"], "pass")
    self.assertEqual(rows[0]["limit_up_price"], "")
    self.assertEqual(rows[0]["limit_down_price"], "")
```

- [ ] **Step 4: 跑新增测试，确认先失败**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_tdx_local_institution_facts.TdxLocalInstitutionFactsTest.test_build_minimal_institution_fact_package_derives_price_bounds_for_known_board -v
python -m unittest tests.test_tdx_local_institution_facts.TdxLocalInstitutionFactsTest.test_build_minimal_institution_fact_package_keeps_bounds_empty_for_new_stock_window -v
python -m unittest tests.test_tdx_local_institution_facts.TdxLocalInstitutionFactsTest.test_build_minimal_institution_fact_package_keeps_bounds_empty_without_prev_close -v
```

Expected:

```text
TypeError: build_minimal_institution_fact_package() got an unexpected keyword argument 'offline_root'
```

- [ ] **Step 5: Commit 测试基线**

```powershell
git add tests/test_tdx_local_institution_facts.py
git commit -m "Add failing tests for price limit fact enrichment"
```

## Task 2: 为 institution_facts 加最小实现

**Files:**
- Modify: `src/data_sources/tdx_local/institution_facts.py`
- Test: `tests/test_tdx_local_institution_facts.py`

- [ ] **Step 1: 扩展函数签名并保留向后兼容**

```python
def build_minimal_institution_fact_package(
    duckdb_root: str | Path,
    data_root: str | Path,
    ts_codes: list[str],
    window_start: str,
    window_end: str,
    offline_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(data_root)
    output_dir = root / "ashare" / "institution-facts-v0.1"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows_by_code = _read_tradability_rows(
        Path(duckdb_root),
        ts_codes,
        window_start,
        window_end,
        Path(offline_root) if offline_root is not None else None,
    )
```

- [ ] **Step 2: 增加价格边界 helper**

```python
from decimal import Decimal, ROUND_HALF_UP


def _derive_limit_prices(
    ts_code: str,
    trade_date: str,
    prev_close: str,
) -> tuple[str, str]:
    if not prev_close:
        return "", ""
    if _is_new_stock_window(ts_code, trade_date):
        return "", ""

    ratio = _limit_ratio(ts_code)
    if ratio is None:
        return "", ""

    prev_close_decimal = Decimal(prev_close)
    limit_up = (prev_close_decimal * (Decimal("1") + ratio)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    limit_down = (prev_close_decimal * (Decimal("1") - ratio)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{limit_up:.2f}", f"{limit_down:.2f}"
```

- [ ] **Step 3: 沿用 first_batch 同口径写 board / ST / new stock helpers**

```python
def _load_symbol_metadata(duckdb_root: Path, ts_codes: list[str]) -> dict[str, dict[str, Any]]:
    db_path = duckdb_root / "market_meta.duckdb"
    if not db_path.exists():
        return {}
    try:
        con = duckdb.connect(str(db_path), read_only=True)
    except Exception:
        return {}

    table_ref = _resolve_duckdb_table_ref(con, "instrument_master")
    if table_ref is None:
        con.close()
        return {}

    symbol_to_ts = {_ts_code_to_duckdb_symbol(ts_code): ts_code for ts_code in ts_codes}
    placeholders = ", ".join(["?"] * len(symbol_to_ts))
    rows = con.execute(
        f"""
        select symbol, exchange, name, list_dt
        from {table_ref}
        where symbol in ({placeholders})
        """,
        [*symbol_to_ts.keys()],
    ).fetchall()
    con.close()

    metadata: dict[str, dict[str, Any]] = {}
    for symbol, exchange, name, list_dt in rows:
        ts_code = symbol_to_ts.get(str(symbol))
        if ts_code is None:
            continue
        metadata[ts_code] = {
            "board_type": _board_type(ts_code),
            "is_st": _is_st_name(str(name or "")),
            "list_date": str(list_dt) if list_dt is not None else "",
        }
    return metadata


def _board_type(ts_code: str) -> str:
    code, suffix = ts_code.split(".", 1)
    suffix = suffix.upper()
    if suffix == "BJ":
        return "bse"
    if suffix == "SH" and code.startswith("688"):
        return "star"
    if suffix == "SZ" and code.startswith(("300", "301")):
        return "gem"
    return "main"


def _is_st_name(symbol_name: str) -> bool:
    uppercase_name = symbol_name.upper()
    return "ST" in uppercase_name or "*ST" in uppercase_name


def _is_new_stock_window(list_date: str, trade_date: str) -> bool:
    if not list_date or not trade_date:
        return False
    try:
        list_dt = datetime.fromisoformat(list_date)
        trade_dt = datetime.fromisoformat(trade_date)
    except ValueError:
        return False
    return (trade_dt - list_dt).days <= 365
```

- [ ] **Step 4: 增加 prev_close 读取 helper**

```python
def _prev_close_by_trade_date(
    offline_root: Path | None,
    ts_code: str,
) -> dict[str, str]:
    if offline_root is None:
        return {}
    daily_rows = read_daily_bars(offline_root, ts_code)
    if not daily_rows:
        return {}

    result: dict[str, str] = {}
    previous_close = ""
    for row in daily_rows:
        trade_date = str(row.get("trade_date", ""))
        if trade_date:
            result[trade_date] = previous_close
        close_value = row.get("close")
        previous_close = "" if close_value in (None, "") else str(close_value)
    return result
```

- [ ] **Step 5: 在 `_read_tradability_rows(...)` 中接入富化逻辑**

```python
prev_close_map = _prev_close_by_trade_date(offline_root, ts_code)
symbol_metadata = metadata_by_code.get(ts_code, {})

limit_up_price, limit_down_price = _derive_limit_prices(
    ts_code=ts_code,
    trade_date=trade_date,
    prev_close=prev_close_map.get(trade_date, ""),
    board_type=str(symbol_metadata.get("board_type", _board_type(ts_code))),
    is_st=bool(symbol_metadata.get("is_st", False)),
    is_new_stock_window=bool(symbol_metadata.get("is_new_stock_window", False)),
)
```

Target row shape:

```python
{
    "ts_code": ts_code,
    "trade_date": trade_date,
    "is_trading_day": "true",
    "is_suspended": "true" if _is_suspended(tradability_status, blocked_reason) else "false",
    "limit_up_price": limit_up_price,
    "limit_down_price": limit_down_price,
    "close_limit_status": "unknown",
    "touched_limit_status": "unknown",
    "board_lot_size": "100",
    "source_ref": source_ref,
}
```

- [ ] **Step 6: 更新报告口径**

```python
"limit_price_policy": "derived_bounds_explicit_status_only",
```

- [ ] **Step 7: 跑 institution_facts 定向测试，确认通过**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_tdx_local_institution_facts -v
```

Expected:

```text
OK
```

- [ ] **Step 8: Commit 最小实现**

```powershell
git add src/data_sources/tdx_local/institution_facts.py tests/test_tdx_local_institution_facts.py
git commit -m "Enrich institution facts with derived price bounds"
```

## Task 3: 更新 README 口径并验证 CLI

**Files:**
- Modify: `src/README.md`
- Test: `tests/test_tdx_local_institution_facts.py`

- [ ] **Step 1: 更新 `src/README.md` 的制度事实说明**

Replace:

```markdown
`data_sources.tdx_local.institution_facts` 会从本地 DuckDB `market_meta.tradability_fact` 按 `ts_code + window` 生成最小制度事实包。当前最小通电策略只使用可交易性事实：`limit_up_price / limit_down_price` 留空，`close_limit_status / touched_limit_status=unknown`，`board_lot_size=100`。它不计算完整涨跌停价，不引入 AkShare / Baostock，也不生成任何交易许可。
```

With:

```markdown
`data_sources.tdx_local.institution_facts` 会从本地 DuckDB `market_meta.tradability_fact` 按 `ts_code + window` 生成最小制度事实包。当前策略会在本地日线可提供 `prev_close` 且板块口径明确时，推导 `limit_up_price / limit_down_price`；`close_limit_status / touched_limit_status` 仍保持显式事实优先，缺失即 `unknown`，`board_lot_size=100`。它不定义完整涨跌停规则，不引入 AkShare / Baostock，也不生成任何交易许可。
```

- [ ] **Step 2: 为 CLI 增加带 `offline_root` 的 smoke test**

```python
def test_cli_builds_minimal_institution_fact_package_with_derived_bounds(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        duckdb_root = root / "duckdb"
        data_root = root / "data"
        offline_root = root / "offline"
        duckdb_root.mkdir()

        import duckdb

        con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
        con.execute(
            """
            create table tradability_fact (
                symbol varchar,
                asset_type varchar,
                trade_dt date,
                tradability_status varchar,
                blocked_reason varchar,
                source_role varchar,
                source_run_id varchar,
                schema_version varchar,
                rule_version varchar,
                source_manifest_hash varchar
            )
            """
        )
        con.execute(
            """
            insert into tradability_fact values
            ('sz300750', 'stock', '2026-03-24', 'tradable', null, 'tdx_direct', 'run-1', 'v1', 'r1', 'hash-3')
            """
        )
        con.close()

        day_dir = offline_root / "raw" / "sz" / "lday"
        day_dir.mkdir(parents=True)
        _write_day_file(
            day_dir / "sz300750.day",
            [
                (20260321, 19800, 19900, 19700, 19800, 1000.0, 100000),
                (20260324, 20000, 21000, 19500, 20500, 1200.0, 120000),
            ],
        )

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "data_sources.tdx_local.institution_facts",
                "--duckdb-root",
                str(duckdb_root),
                "--data-root",
                str(data_root),
                "--offline-root",
                str(offline_root),
                "--ts-code",
                "300750.SZ",
                "--window-start",
                "2026-03-24",
                "--window-end",
                "2026-03-24",
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

    self.assertEqual(completed.returncode, 0, completed.stderr)
    report = json.loads(completed.stdout)
    self.assertEqual(report["limit_price_policy"], "derived_bounds_explicit_status_only")
```

- [ ] **Step 3: 增加 CLI 参数**

```python
parser.add_argument("--offline-root")
```

Pass-through:

```python
report = build_minimal_institution_fact_package(
    duckdb_root=args.duckdb_root,
    data_root=args.data_root,
    ts_codes=args.ts_code,
    window_start=args.window_start,
    window_end=args.window_end,
    offline_root=args.offline_root,
)
```

- [ ] **Step 4: 跑 README 相关与 CLI 测试**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_tdx_local_institution_facts.TdxLocalInstitutionFactsTest.test_cli_builds_minimal_institution_fact_package_with_derived_bounds -v
python -m unittest tests.test_tdx_local_institution_facts -v
git status --short
```

Expected:

```text
OK
M src/README.md
M src/data_sources/tdx_local/institution_facts.py
M tests/test_tdx_local_institution_facts.py
```

- [ ] **Step 5: Commit 文档与 CLI 收口**

```powershell
git add src/README.md src/data_sources/tdx_local/institution_facts.py tests/test_tdx_local_institution_facts.py
git commit -m "Document derived price limit facts"
```

## 总验证

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_tdx_local_institution_facts -v
python -m unittest tests.test_ashare_intake_validator -v
python -m unittest discover -s tests
```

Expected:

```text
OK
```

## 完成判定

- `institution_facts` 在可明确推导时输出非空 `limit_up_price / limit_down_price`；
- `close_limit_status / touched_limit_status` 继续保持 `unknown`；
- 缺少 `prev_close` 或处于 `new_stock_window` 时不硬推错误边界；
- 三道硬闸仍保持 `False`；
- CLI、单测、README 口径一致。

## 自检备注

- 本计划故意不把 `ashare_intake_validator.py` 拉进来，避免把“事实补强”和“下游解释”混成一个子项目；
- `PAS` 不在本计划中，也不应在实现时被顺手恢复；
- 执行时如果发现 DuckDB 的 `instrument_master` 无法稳定提供 `list_date / name`，允许退回到“只依据 `ts_code` 判定 board_type，`is_st / is_new_stock_window` 缺失则保守留空”的实现，但必须同步修改测试与 README，使行为和文档一致。
