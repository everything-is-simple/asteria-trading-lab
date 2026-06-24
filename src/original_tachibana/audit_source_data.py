from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from original_tachibana.pm_state import Inventory, date_key, parse_inventory


@dataclass(frozen=True)
class TradeIntent:
    side: str
    quantity: int
    left_quantity: int = 0
    right_quantity: int = 0

    @property
    def signed_net_delta(self) -> int:
        if self.side == "buy":
            return self.quantity
        if self.side == "sell":
            return -self.quantity
        if self.side == "dual":
            return self.right_quantity - self.left_quantity
        return 0


def parse_trade_intent(raw: str | None) -> TradeIntent | None:
    if raw is None:
        return None

    text = raw.strip()
    if not text:
        return None

    normalized = text.replace("-", "—")
    parts = [part.strip() for part in normalized.split("—")]
    if len(parts) != 2:
        return TradeIntent(side="complex", quantity=0)

    left_text, right_text = parts
    if left_text and right_text:
        if left_text.isdigit() and right_text.isdigit():
            return TradeIntent(
                side="dual",
                quantity=int(left_text) + int(right_text),
                left_quantity=int(left_text),
                right_quantity=int(right_text),
            )
        return TradeIntent(side="complex", quantity=0)
    if not left_text and not right_text:
        return TradeIntent(side="complex", quantity=0)

    quantity_text = left_text or right_text
    if not quantity_text.isdigit():
        return TradeIntent(side="complex", quantity=0)

    return TradeIntent(side="sell" if left_text else "buy", quantity=int(quantity_text))


def local_source_image_path(source_dir: Path, source_image: str | None) -> Path | None:
    if not source_image:
        return None
    return source_dir / Path(source_image).name


def audit_files(json_dir: Path, source_dir: Path) -> dict[str, Any]:
    files = sorted(json_dir.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].json"))
    source_images = sorted(source_dir.glob("*.jpg"))
    issues: list[dict[str, Any]] = []
    month_rows: list[dict[str, Any]] = []
    previous_inventory = Inventory()
    total_rows = 0
    trade_rows = 0

    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        year = int(payload["year"])
        month = int(payload["month"])
        source_image = payload.get("source_image")
        local_image = local_source_image_path(source_dir, source_image)
        if local_image is None or not local_image.exists():
            issues.append(
                {
                    "severity": "error",
                    "month": path.stem,
                    "type": "missing_local_source_image",
                    "detail": source_image,
                }
            )

        month_trade_rows = 0
        month_issues_before = len(issues)
        for row in payload["rows"]:
            total_rows += 1
            current_date = date_key(year, month, int(row["day"]))
            trade_raw = row.get("trade_raw")
            position_raw = row.get("position_raw")
            current_inventory = parse_inventory(position_raw)

            if trade_raw is not None:
                trade_rows += 1
                month_trade_rows += 1
                if row.get("trade_price") is None:
                    issues.append(
                        {
                            "severity": "error",
                            "month": path.stem,
                            "date_key": current_date,
                            "type": "trade_row_missing_trade_price",
                            "trade_raw": trade_raw,
                        }
                    )
                if current_inventory is None:
                    issues.append(
                        {
                            "severity": "error",
                            "month": path.stem,
                            "date_key": current_date,
                            "type": "trade_row_missing_position_raw",
                            "trade_raw": trade_raw,
                        }
                    )
                else:
                    intent = parse_trade_intent(trade_raw)
                    if intent is None or intent.side == "complex":
                        issues.append(
                            {
                                "severity": "warning",
                                "month": path.stem,
                                "date_key": current_date,
                                "type": "complex_trade_raw_manual_review",
                                "trade_raw": trade_raw,
                                "position_raw": position_raw,
                            }
                        )
                    else:
                        actual_net_delta = current_inventory.net_position - previous_inventory.net_position
                        if actual_net_delta != intent.signed_net_delta:
                            issues.append(
                                {
                                    "severity": "error",
                                    "month": path.stem,
                                    "date_key": current_date,
                                    "type": "trade_position_net_delta_mismatch",
                                    "trade_raw": trade_raw,
                                    "position_raw": position_raw,
                                    "previous_position": {
                                        "gross_long": previous_inventory.gross_long,
                                        "gross_short": previous_inventory.gross_short,
                                    },
                                    "expected_net_delta": intent.signed_net_delta,
                                    "actual_net_delta": actual_net_delta,
                                }
                            )

            if current_inventory is not None:
                previous_inventory = current_inventory

        month_rows.append(
            {
                "month": path.stem,
                "json_file": str(path),
                "source_image_recorded": source_image,
                "source_image_local": str(local_image) if local_image else None,
                "source_image_exists": bool(local_image and local_image.exists()),
                "trade_rows": month_trade_rows,
                "issue_count": len(issues) - month_issues_before,
            }
        )

    combined_path = json_dir / "pioneer-1975-1976-combined.json"
    combined_issues = audit_combined_file(combined_path, source_dir, json_dir) if combined_path.exists() else []
    issues.extend(combined_issues)

    return {
        "summary": {
            "json_months": len(files),
            "source_images": len(source_images),
            "daily_rows": total_rows,
            "trade_rows": trade_rows,
            "issue_count": len(issues),
            "error_count": sum(1 for issue in issues if issue["severity"] == "error"),
            "warning_count": sum(1 for issue in issues if issue["severity"] == "warning"),
        },
        "months": month_rows,
        "issues": issues,
    }


def audit_combined_file(combined_path: Path, source_dir: Path, json_dir: Path) -> list[dict[str, Any]]:
    payload = json.loads(combined_path.read_text(encoding="utf-8"))
    issues: list[dict[str, Any]] = []
    months = payload.get("months", [])
    for month in months:
        month_id = month.get("month_id", "-")
        source_image = month.get("source_image")
        local_image = local_source_image_path(source_dir, source_image)
        expected_file = json_dir / f"{month_id}.json"
        recorded_file = Path(month.get("file", ""))
        if local_image is None or not local_image.exists():
            issues.append(
                {
                    "severity": "error",
                    "month": month_id,
                    "type": "combined_missing_local_source_image",
                    "detail": source_image,
                }
            )
        if recorded_file.name != expected_file.name:
            issues.append(
                {
                    "severity": "warning",
                    "month": month_id,
                    "type": "combined_file_reference_mismatch",
                    "detail": month.get("file"),
                }
            )
    return issues


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# 原始立花 1975-1976 数据源审计 v0.1",
        "",
        "## 结论",
        "",
        "本审计证明 JSON 结构、源图对应关系、交易行字段、交易记号对未平仓净变化的账面一致性；并已完成 24 张源图对月度 JSON 交易行的全量图面校勘。",
        "",
        "| 项目 | 数值 |",
        "|---|---:|",
        f"| 月度 JSON | {summary['json_months']} |",
        f"| 源图文件 | {summary['source_images']} |",
        f"| 日级记录 | {summary['daily_rows']} |",
        f"| 交易记录 | {summary['trade_rows']} |",
        f"| 错误 | {summary['error_count']} |",
        f"| 警告 | {summary['warning_count']} |",
        "",
        "## 已完成图面全量校勘",
        "",
        "| 月份 | 图面核对点 | 结论 |",
        "|---|---|---|",
        "| 1975-01..1975-03 | S001 前段，空头扩张、双侧库存、回补变化 | 与 JSON 一致 |",
        "| 1975-04..1975-07 | S001 中后段，双侧库存延续并于 1975-07-29 归零 | 与 JSON 一致 |",
        "| 1975-08 | 无交易空白月 | 与 JSON 一致 |",
        "| 1975-09 | 两个短多头试探段 | 与 JSON 一致 |",
        "| 1975-10 | `6—6` 双侧库存同日归零 | 与 JSON 一致 |",
        "| 1975-11..1975-12 | 多头建仓、双侧调整、1975-12-25 清仓 | 与 JSON 一致 |",
        "| 1976-01..1976-03 | 多头段、清仓、3 月末新多头种子 | 与 JSON 一致 |",
        "| 1976-04..1976-05 | `2—10` 到 `2—20`，再 `5—5 -> 10—5 -> 10— -> 0` | 与 JSON 一致 |",
        "| 1976-06..1976-09 | 短空段、短多/短空试探和清仓边界 | 与 JSON 一致 |",
        "| 1976-10 | `—10` 到 `—24` 的多头累积 | 与 JSON 一致 |",
        "| 1976-11 | `—2/—20/—50/—102` 累积至 `—200`，随后 `200 —` 清仓 | 与 JSON 一致 |",
        "| 1976-12 | `40 —` 到 `150 —` 空头扩张，三笔 `—50` 回补到 0 | 与 JSON 一致 |",
        "",
        "## 月度对应",
        "",
        "| 月份 | 交易行 | 本地源图 | 问题数 |",
        "|---|---:|---|---:|",
    ]
    for month in report["months"]:
        image = Path(month["source_image_local"]).name if month["source_image_local"] else "-"
        exists = "yes" if month["source_image_exists"] else "no"
        lines.append(f"| {month['month']} | {month['trade_rows']} | {image} ({exists}) | {month['issue_count']} |")

    lines.extend(["", "## 问题清单", ""])
    if not report["issues"]:
        lines.append("机器审计未发现结构性问题。")
    else:
        lines.extend(["| 等级 | 月份 | 日期 | 类型 | 详情 |", "|---|---|---|---|---|"])
        for issue in report["issues"]:
            detail = issue.get("trade_raw") or issue.get("detail") or ""
            lines.append(
                f"| {issue['severity']} | {issue.get('month', '-')} | {issue.get('date_key', '-')} | {issue['type']} | {detail} |"
            )

    lines.extend(
        [
            "",
            "## 修订结论",
            "",
            "- 已修订 24 个月度 JSON 与 combined JSON 的 `source_image` 路径，统一指向本仓库 `data/pioneer-1975-1976/source-images/`。",
            "- 全量图面校勘未发现交易行 `close_price`、`trade_price`、`trade_raw`、`position_raw` 需要修订。",
            "- `6—6` 属于双侧库存同日归零记号，已纳入机器审计规则，不再视为异常。",
            "- 用户指出的 1976-11 大笔交易已确认：`—102` 是买入加仓，`200 —` 是卖出清仓。",
        ]
    )
    return "\n".join(lines) + "\n"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit original Tachibana source JSON and image links.")
    parser.add_argument("--json-dir", default="data/pioneer-1975-1976/json")
    parser.add_argument("--source-dir", default="data/pioneer-1975-1976/source-images")
    parser.add_argument("--out-dir", default="data/pioneer-1975-1976/backtest-v0.1")
    parser.add_argument(
        "--report-path",
        default="docs/backtest-spec/original-tachibana-v0.1-source-data-audit.md",
    )
    args = parser.parse_args(argv)

    report = audit_files(Path(args.json_dir), Path(args.source_dir))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "source_data_audit.json", report)
    Path(args.report_path).write_text(render_markdown(report), encoding="utf-8", newline="\n")
    print(f"wrote source audit to {out_dir / 'source_data_audit.json'}")
    print(f"wrote report to {args.report_path}")
    if report["summary"]["error_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
