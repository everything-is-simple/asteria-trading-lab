from .audit import audit_local_data_assets
from .first_batch import (
    audit_first_batch_sample_coverage,
    build_first_batch_sample_package,
    build_default_add_on_price_limit_shortlist_malf_research_prep,
    build_shortlist_malf_research_prep,
    build_shortlist_sample_package,
    default_add_on_price_limit_shortlist_sample_entries,
)
from .readers import (
    build_minimal_read_report,
    inspect_duckdb_assets,
    probe_pytdx_reader,
    read_daily_bars,
    read_intraday_range,
    read_sector_membership,
    read_symbol_master,
    read_trading_calendar,
)
from .price_limit_sample_pool import (
    screen_pullback_add_price_limit_candidates,
    screen_pullback_add_price_limit_candidates_with_intraday,
    shortlist_core_malf_snapshot_candidates,
    shortlist_formal_pressure_adjust_review_candidates,
    shortlist_pullback_add_pressure_adjust_candidates,
)

__all__ = [
    "audit_local_data_assets",
    "audit_first_batch_sample_coverage",
    "build_first_batch_sample_package",
    "build_default_add_on_price_limit_shortlist_malf_research_prep",
    "build_shortlist_malf_research_prep",
    "build_shortlist_sample_package",
    "default_add_on_price_limit_shortlist_sample_entries",
    "build_minimal_institution_fact_package",
    "build_minimal_read_report",
    "inspect_duckdb_assets",
    "probe_pytdx_reader",
    "read_daily_bars",
    "read_intraday_range",
    "screen_pullback_add_price_limit_candidates",
    "screen_pullback_add_price_limit_candidates_with_intraday",
    "shortlist_core_malf_snapshot_candidates",
    "shortlist_formal_pressure_adjust_review_candidates",
    "shortlist_pullback_add_pressure_adjust_candidates",
    "read_sector_membership",
    "read_symbol_master",
    "read_trading_calendar",
]


def __getattr__(name: str):
    if name == "build_minimal_institution_fact_package":
        from .institution_facts import build_minimal_institution_fact_package

        return build_minimal_institution_fact_package
    raise AttributeError(name)
