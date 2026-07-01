from __future__ import annotations

from .candidate_table_gates import *
from .first_batch_constants import *
from .first_batch_reviews import *
from .first_batch_sample_packages import *
from .first_batch_shortlist import *
from .qualification_record_gates import *
from .rule_definition_gates import *
from .trading_readiness_gates import *


def review_add_on_price_limit_post_label_intraday_reopen(
    tdx_root,
    rescreen_report,
    generated_at=None,
):
    from .first_batch_shortlist import review_add_on_price_limit_post_label_intraday_reopen as _review

    original_reader = _review.__globals__["read_intraday_range"]
    _review.__globals__["read_intraday_range"] = read_intraday_range
    try:
        return _review(tdx_root=tdx_root, rescreen_report=rescreen_report, generated_at=generated_at)
    finally:
        _review.__globals__["read_intraday_range"] = original_reader
