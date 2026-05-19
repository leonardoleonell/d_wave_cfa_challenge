from __future__ import annotations

from pathlib import Path

import pandas as pd


PEER_SUMMARY_COLUMNS = [
    "ticker",
    "company",
    "category",
    "market_cap",
    "enterprise_value",
    "revenue_ltm",
    "ev_sales_ltm",
    "gross_margin",
    "revenue_growth",
    "ebitda_margin",
    "notes",
]

REQUIRED_PEER_FIELDS = ["ev_sales_ltm", "revenue_ltm", "enterprise_value"]


def find_project_root(start: Path) -> Path:
    """Find the project root from either the repo root or notebooks folder."""
    start = start.resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "data" / "processed" / "peer_multiples.csv").exists():
            return candidate
    raise FileNotFoundError("Could not find data/processed/peer_multiples.csv from the current path.")


def load_peer_data(path: Path) -> pd.DataFrame:
    peers = pd.read_csv(path, na_values=["NA", "", "TO_BE_FILLED"])
    numeric_columns = [
        "market_cap",
        "enterprise_value",
        "revenue_ltm",
        "ev_sales_ltm",
        "gross_margin",
        "revenue_growth",
        "ebitda_margin",
    ]
    for column in numeric_columns:
        if column in peers.columns:
            peers[column] = pd.to_numeric(peers[column], errors="coerce")
    return peers


def final_peer_mask(peers: pd.DataFrame) -> pd.Series:
    if "include_in_final_peer_group" not in peers.columns:
        raise ValueError("peer_multiples.csv is missing include_in_final_peer_group.")
    return peers["include_in_final_peer_group"].astype(str).str.upper().eq("TRUE")


def calculate_statistics(peer_group: pd.DataFrame) -> pd.DataFrame:
    multiple_columns = ["ev_sales_ltm"]
    for column in ["ev_sales_2025e", "ev_sales_2026e", "ev_sales_2027e"]:
        if column in peer_group.columns:
            multiple_columns.append(column)

    records = []
    for column in multiple_columns:
        series = pd.to_numeric(peer_group[column], errors="coerce").dropna()
        if series.empty:
            records.append(
                {
                    "multiple": column,
                    "count": 0,
                    "mean": pd.NA,
                    "median": pd.NA,
                    "p25": pd.NA,
                    "p75": pd.NA,
                    "minimum": pd.NA,
                    "maximum": pd.NA,
                }
            )
            continue

        records.append(
            {
                "multiple": column,
                "count": int(series.count()),
                "mean": series.mean(),
                "median": series.median(),
                "p25": series.quantile(0.25),
                "p75": series.quantile(0.75),
                "minimum": series.min(),
                "maximum": series.max(),
            }
        )

    statistics = pd.DataFrame(records)
    numeric_columns = ["mean", "median", "p25", "p75", "minimum", "maximum"]
    statistics[numeric_columns] = statistics[numeric_columns].round(3)
    return statistics


def flag_outliers(peer_group: pd.DataFrame) -> pd.DataFrame:
    peer_group = peer_group.copy()
    series = peer_group["ev_sales_ltm"].dropna()

    peer_group["ev_sales_ltm_outlier"] = False
    peer_group["ev_sales_ltm_outlier_note"] = ""

    if len(series) < 2:
        peer_group["ev_sales_ltm_outlier_note"] = "Not enough peers to calculate standard deviation."
        return peer_group

    median = series.median()
    std_dev = series.std(ddof=0)
    if pd.isna(std_dev) or std_dev == 0:
        peer_group["ev_sales_ltm_outlier_note"] = "Standard deviation is zero or unavailable."
        return peer_group

    distance = (peer_group["ev_sales_ltm"] - median).abs()
    outlier_mask = distance > (2 * std_dev)
    peer_group.loc[outlier_mask, "ev_sales_ltm_outlier"] = True
    peer_group.loc[outlier_mask, "ev_sales_ltm_outlier_note"] = (
        "EV/Sales LTM is more than 2 standard deviations from peer median."
    )
    return peer_group


def build_summary_text(
    source_path: Path,
    peer_group: pd.DataFrame,
    statistics: pd.DataFrame,
    missing_flags: list[str],
) -> str:
    included_tickers = ", ".join(peer_group["ticker"].tolist())
    outliers = peer_group.loc[peer_group["ev_sales_ltm_outlier"], "ticker"].tolist()

    lines: list[str] = []
    lines.append("# Peer Analysis Summary")
    lines.append("")
    lines.append(f"Source file: `{source_path}`")
    lines.append("")
    lines.append("Financial values are in USD millions where applicable.")
    lines.append(f"Final peer group: {included_tickers}")
    lines.append("")
    lines.append("## EV/Sales LTM Statistics")
    lines.append("")
    lines.append("```text")
    lines.append(statistics.to_string(index=False, na_rep="NA"))
    lines.append("```")
    lines.append("")
    lines.append("## Missing Data Flags")
    if missing_flags:
        lines.extend(f"- {flag}" for flag in missing_flags)
    else:
        lines.append("- No final peer group companies are missing EV/Sales LTM, revenue, or enterprise value.")
    lines.append("")
    lines.append("## Outlier Flags")
    if outliers:
        lines.extend(f"- {ticker}: EV/Sales LTM is more than 2 standard deviations from peer median." for ticker in outliers)
    else:
        lines.append("- No EV/Sales LTM outliers were flagged using the 2 standard deviation rule.")
    lines.append("")
    lines.append("## Peer Summary Table")
    lines.append("")
    lines.append("```text")
    lines.append(peer_group[PEER_SUMMARY_COLUMNS + ["ev_sales_ltm_outlier"]].to_string(index=False, na_rep="NA"))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    project_root = find_project_root(Path.cwd())
    source_path = project_root / "data" / "processed" / "peer_multiples.csv"
    peer_summary_path = project_root / "outputs" / "tables" / "peer_group_summary.csv"
    statistics_path = project_root / "outputs" / "tables" / "peer_multiples_statistics.csv"
    text_summary_path = project_root / "outputs" / "text" / "peer_analysis_summary.md"

    peer_summary_path.parent.mkdir(parents=True, exist_ok=True)
    statistics_path.parent.mkdir(parents=True, exist_ok=True)
    text_summary_path.parent.mkdir(parents=True, exist_ok=True)

    peers = load_peer_data(source_path)
    peer_group = peers.loc[final_peer_mask(peers)].copy()
    if peer_group.empty:
        raise SystemExit("ERROR: No rows marked TRUE in include_in_final_peer_group.")

    missing_flags: list[str] = []
    for _, row in peer_group.iterrows():
        missing_fields = [
            field
            for field in REQUIRED_PEER_FIELDS
            if field not in row.index or pd.isna(row[field])
        ]
        if missing_fields:
            missing_flags.append(f"{row['ticker']} is missing: {', '.join(missing_fields)}")

    peer_group = flag_outliers(peer_group)
    statistics = calculate_statistics(peer_group)

    peer_summary = peer_group[PEER_SUMMARY_COLUMNS + ["ev_sales_ltm_outlier", "ev_sales_ltm_outlier_note"]].copy()
    peer_summary.to_csv(peer_summary_path, index=False, na_rep="NA")
    statistics.to_csv(statistics_path, index=False, na_rep="NA")

    summary_text = build_summary_text(
        source_path=source_path.relative_to(project_root),
        peer_group=peer_group,
        statistics=statistics,
        missing_flags=missing_flags,
    )
    text_summary_path.write_text(summary_text, encoding="utf-8")

    print(f"Saved peer group summary to: {peer_summary_path}")
    print(f"Saved peer multiples statistics to: {statistics_path}")
    print(f"Saved peer analysis summary to: {text_summary_path}")
    print("")
    print(peer_summary.to_string(index=False, na_rep="NA"))
    print("")
    print(statistics.to_string(index=False, na_rep="NA"))


if __name__ == "__main__":
    main()
