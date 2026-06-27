from __future__ import annotations

from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_sources.tdx_local import (
    build_minimal_read_report,
    inspect_duckdb_assets,
    probe_pytdx_reader,
    read_daily_bars,
    read_sector_membership,
    read_symbol_master,
    read_trading_calendar,
)


FORBIDDEN_FIELDS = {
    "buy_signal",
    "trade_accept",
    "target_position",
    "ashare_t1_action",
    "limit_up_strategy",
}


def write_day_record(path: Path, date: int = 20260106) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # TDX day record: date, open, high, low, close, amount, volume, reserved.
    path.write_bytes(struct.pack("<IIIIIfII", date, 1020, 1080, 1010, 1070, 1177000.0, 110000, 0))


def write_text_bars(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "000001 Ping An Bank 日线 前复权",
                "日期\t开盘\t最高\t最低\t收盘\t成交量\t成交额",
                "2026/01/05\t10.00\t10.50\t9.80\t10.20\t100000\t1020000.00",
                "2026/01/06\t10.20\t10.80\t10.10\t10.70\t110000\t1177000.00",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


class TdxLocalReadersTest(unittest.TestCase):
    def test_read_symbol_master_prefers_duckdb_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            duckdb_root = root / "duckdb"
            duckdb_root.mkdir()
            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
            con.execute(
                """
                create table instrument_master (
                    symbol varchar,
                    asset_type varchar,
                    exchange varchar,
                    name varchar,
                    list_dt date,
                    delist_dt date,
                    source_run_id varchar,
                    schema_version varchar,
                    rule_version varchar,
                    source_manifest_hash varchar
                )
                """
            )
            con.execute(
                """
                insert into instrument_master values
                ('000001.SZ', 'equity', 'SZ', 'Ping An Bank', '1991-04-03', null, 'run-1', 'v1', 'r1', 'hash-1')
                """
            )
            con.close()

            rows = read_symbol_master(root / "tdx", root / "offline", duckdb_root=duckdb_root)

        self.assertEqual(rows, [
            {
                "ts_code": "000001.SZ",
                "market": "SZ",
                "symbol_name": "Ping An Bank",
                "list_date": "1991-04-03",
                "delist_date": None,
                "source_type": "duckdb_instrument_master",
                "source_path": "market_meta.duckdb:market_meta.instrument_master",
                "source_ref": "market_meta.duckdb:market_meta.instrument_master",
            }
        ])

    def test_read_daily_bars_parses_raw_day_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            offline_root = Path(tmp)
            write_day_record(offline_root / "raw" / "sz" / "lday" / "sz000001.day")

            rows = read_daily_bars(offline_root, "000001.SZ")

        self.assertEqual(rows, [
            {
                "ts_code": "000001.SZ",
                "trade_date": "2026-01-06",
                "open": 10.2,
                "high": 10.8,
                "low": 10.1,
                "close": 10.7,
                "volume": 110000,
                "amount": 1177000.0,
                "source_ref": "raw/sz/lday/sz000001.day",
            }
        ])
        self.assertTrue(FORBIDDEN_FIELDS.isdisjoint(rows[0]))

    def test_read_daily_bars_parses_adjusted_text_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            offline_root = Path(tmp)
            write_text_bars(offline_root / "stock" / "Forward-Adjusted" / "SZ#000001.txt")

            rows = read_daily_bars(offline_root, "000001.SZ", adjustment="forward_adjusted", limit=1)

        self.assertEqual(rows[0]["ts_code"], "000001.SZ")
        self.assertEqual(rows[0]["trade_date"], "2026-01-05")
        self.assertEqual(rows[0]["open"], 10.0)
        self.assertEqual(rows[0]["close"], 10.2)
        self.assertEqual(rows[0]["volume"], 100000)
        self.assertEqual(rows[0]["amount"], 1020000.0)
        self.assertEqual(rows[0]["source_ref"], "stock/Forward-Adjusted/SZ#000001.txt")
        self.assertTrue(FORBIDDEN_FIELDS.isdisjoint(rows[0]))

    def test_read_symbol_master_uses_file_names_without_requiring_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tdx_root = root / "tdx"
            offline_root = root / "offline"
            write_day_record(tdx_root / "vipdoc" / "sh" / "lday" / "sh600000.day")
            write_text_bars(offline_root / "stock" / "Non-Adjusted" / "SZ#000001.txt")

            rows = read_symbol_master(tdx_root, offline_root, duckdb_root=root / "missing-duckdb")

        self.assertEqual(
            {(row["ts_code"], row["market"], row["symbol_name"]) for row in rows},
            {("600000.SH", "SH", None), ("000001.SZ", "SZ", None)},
        )
        for row in rows:
            self.assertTrue(FORBIDDEN_FIELDS.isdisjoint(row))

    def test_read_trading_calendar_extracts_dates_from_local_bars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            offline_root = Path(tmp)
            write_day_record(offline_root / "raw" / "sz" / "lday" / "sz000001.day", date=20260106)
            write_text_bars(offline_root / "stock" / "Forward-Adjusted" / "SZ#000001.txt")

            rows = read_trading_calendar(Path(tmp) / "tdx", offline_root, duckdb_root=Path(tmp) / "missing-duckdb")

        self.assertEqual(
            {row["trade_date"] for row in rows},
            {"2026-01-05", "2026-01-06"},
        )
        for row in rows:
            self.assertIn(row["market"], {"SZ"})
            self.assertTrue(FORBIDDEN_FIELDS.isdisjoint(row))

    def test_read_sector_membership_blocks_when_source_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = read_sector_membership(Path(tmp), duckdb_root=Path(tmp) / "missing-duckdb", limit_files=10)

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["reason"], "sector_membership_source_missing")
        self.assertEqual(report["sector_membership"], [])
        self.assertFalse(report["sector_membership_inferred_from_index_bars"])

    def test_build_minimal_read_report_summarizes_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tdx_root = root / "tdx"
            offline_root = root / "offline"
            duckdb_root = root / "duckdb"
            duckdb_root.mkdir()
            write_day_record(offline_root / "raw" / "sz" / "lday" / "sz000001.day")
            write_text_bars(offline_root / "stock" / "Forward-Adjusted" / "SZ#000001.txt")

            report = build_minimal_read_report(tdx_root, offline_root, duckdb_root)

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["symbol_master"]["result"], "pass")
        self.assertEqual(report["trading_calendar"]["result"], "pass")
        self.assertEqual(report["daily_bars"]["result"], "pass")
        self.assertEqual(report["sector_membership"]["result"], "blocked")
        self.assertIn("duckdb_introspection", report)
        self.assertIn("pytdx_reader_probe", report)
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["raw_market_file_export_allowed"])

    def test_read_trading_calendar_prefers_duckdb_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            duckdb_root = root / "duckdb"
            duckdb_root.mkdir()
            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
            con.execute(
                """
                create table trade_calendar (
                    exchange varchar,
                    trade_dt date,
                    is_open boolean,
                    source_run_id varchar,
                    schema_version varchar,
                    rule_version varchar,
                    source_manifest_hash varchar
                )
                """
            )
            con.execute(
                """
                insert into trade_calendar values
                ('SZ', '2026-01-06', true, 'run-1', 'v1', 'r1', 'hash-1')
                """
            )
            con.close()

            rows = read_trading_calendar(root / "tdx", root / "offline", duckdb_root=duckdb_root)

        self.assertEqual(rows, [
            {
                "trade_date": "2026-01-06",
                "market": "SZ",
                "is_trading_day": True,
                "source_ref": "market_meta.duckdb:market_meta.trade_calendar",
            }
        ])

    def test_read_sector_membership_prefers_duckdb_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            duckdb_root = root / "duckdb"
            duckdb_root.mkdir()
            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
            con.execute(
                """
                create table industry_block_relation (
                    symbol varchar,
                    asset_type varchar,
                    relation_type varchar,
                    relation_code varchar,
                    relation_name varchar,
                    effective_from date,
                    effective_to date,
                    source_run_id varchar,
                    schema_version varchar,
                    rule_version varchar,
                    source_manifest_hash varchar
                )
                """
            )
            con.execute(
                """
                insert into industry_block_relation values
                ('000001.SZ', 'equity', 'sw_l1', '801780', 'Bank', '2020-01-01', null, 'run-1', 'v1', 'r1', 'hash-1')
                """
            )
            con.close()

            report = read_sector_membership(root / "offline", duckdb_root=duckdb_root, limit_files=10)

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["selected_source"], "duckdb_industry_block_relation")
        self.assertEqual(report["sector_membership"], [
            {
                "ts_code": "000001.SZ",
                "sector_code": "801780",
                "sector_name": "Bank",
                "valid_from": "2020-01-01",
                "valid_to": None,
                "source_ref": "market_meta.duckdb:market_meta.industry_block_relation",
            }
        ])

    def test_inspect_duckdb_assets_lists_tables_and_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            duckdb_root = root / "duckdb"
            duckdb_root.mkdir()
            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
            con.execute("create table instrument_master (symbol varchar, name varchar)")
            con.execute("insert into instrument_master values ('000001.SZ', 'Ping An Bank')")
            con.close()

            report = inspect_duckdb_assets(duckdb_root)

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["databases"][0]["database_name"], "market_meta.duckdb")
        self.assertEqual(report["databases"][0]["tables"][0]["table_name"], "instrument_master")
        self.assertEqual(report["databases"][0]["tables"][0]["columns"][0]["column_name"], "symbol")
        self.assertNotIn("rows", report["databases"][0]["tables"][0])

    def test_probe_pytdx_reader_reports_availability_without_bulk_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "vipdoc" / "sh" / "lday").mkdir(parents=True)

            report = probe_pytdx_reader(root)

        self.assertTrue(report["pytdx_reader_available"])
        self.assertTrue(report["daily_bar_reader_available"])
        self.assertTrue(report["block_reader_available"])
        self.assertTrue(report["vipdoc_detected"])
        self.assertFalse(report["bulk_read_performed"])


if __name__ == "__main__":
    unittest.main()
