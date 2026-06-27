from __future__ import annotations

BLOCKED_PATTERNS = ["*.day", "*.txt", "*.duckdb", "*.7z"]
BLOCKED_LOCATIONS = ["Z:\\new_tdx64", "Z:\\tdx_offline_Data", "Z:\\malf-data"]
SOURCE_PRIORITY = ["local_tdx_pymp", "offline_tdx_files", "legacy_duckdb"]

FIELD_MAPPING = {
    "symbol_master": {
        "source_files": ["stock/<ts_code>.txt", "stock/summary.txt"],
        "target_fields": ["ts_code", "symbol_name", "board_type", "list_date", "source_ref"],
    },
    "trading_calendar": {
        "source_files": ["stock-day/<ts_code>.day", "raw/calendar.txt"],
        "target_fields": ["trade_date", "is_trading_day", "source_ref"],
    },
    "daily_bars": {
        "source_files": ["stock-day/<ts_code>.day", "stock/<ts_code>.txt"],
        "target_fields": ["ts_code", "trade_date", "open", "high", "low", "close", "volume", "amount"],
    },
    "sector_membership": {
        "source_files": ["stock/*.txt", "block/*.txt", "index/*.txt"],
        "target_fields": ["ts_code", "sw_l1_name", "sw_l2_name", "valid_from", "valid_to", "source_ref"],
    },
}

SUPPORTING_FACTS = {
    "adjustment_metadata": {
        "source_files": ["raw/*.txt", "market_meta.duckdb"],
        "target_fields": ["adj_ref", "corporate_action_flag", "source_ref"],
    }
}

