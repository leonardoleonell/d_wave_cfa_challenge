from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


# Simple valuation inputs
valuation_base_year = 2027

SCENARIOS = [
    {"scenario": "Bear", "ev_sales_multiple": 25.0},
    {"scenario": "Base", "ev_sales_multiple": 40.0},
    {"scenario": "Bull", "ev_sales_multiple": 60.0},
]

MULTIPLE_METHODOLOGY_NOTE = (
    "Capped multiples reflect that raw quantum peer EV/Sales multiples are distorted by extremely small revenue bases."
)

SHARES_PER_MILLION = 1_000_000


def find_project_root(start: Path) -> Path:
    """Find the project root from either the repo root or notebooks folder."""
    start = start.resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "data" / "processed" / "dwave_forecast.csv").exists():
            return candidate
    raise FileNotFoundError("Could not find data/processed/dwave_forecast.csv from the current path.")


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, na_values=["NA", "", "TO_BE_FILLED"])


def require_value(row: pd.Series, column: str, label: str) -> float:
    if column not in row.index or pd.isna(row[column]):
        raise SystemExit(f"ERROR: Missing required {label}: {column}")
    return float(row[column])


def choose_share_count(valuation_inputs: pd.Series) -> tuple[float, str, str]:
    diluted_shares = valuation_inputs.get("diluted_shares", np.nan)
    shares_outstanding = valuation_inputs.get("shares_outstanding", np.nan)

    if pd.notna(diluted_shares):
        return float(diluted_shares), "diluted_shares", "Diluted shares were available and used."
    if pd.notna(shares_outstanding):
        return (
            float(shares_outstanding),
            "shares_outstanding",
            "Diluted shares were missing, so shares outstanding were used. This is less conservative.",
        )
    raise SystemExit("ERROR: Both diluted_shares and shares_outstanding are missing.")


def get_peer_median_ev_sales_ltm(peer_statistics: pd.DataFrame) -> float:
    required_columns = {"multiple", "median"}
    missing_columns = required_columns - set(peer_statistics.columns)
    if missing_columns:
        raise SystemExit(f"ERROR: Peer multiples statistics file is missing columns: {sorted(missing_columns)}")

    rows = peer_statistics.loc[peer_statistics["multiple"].astype(str).str.lower().eq("ev_sales_ltm")]
    if rows.empty:
        raise SystemExit("ERROR: Peer multiples statistics file does not contain ev_sales_ltm row.")

    peer_median = pd.to_numeric(rows.iloc[0]["median"], errors="coerce")
    if pd.isna(peer_median):
        raise SystemExit("ERROR: Peer median EV/Sales LTM is missing.")
    return float(peer_median)


def build_valuation(
    forecast: pd.DataFrame,
    valuation_inputs: pd.Series,
    peer_statistics: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    base_rows = forecast.loc[forecast["fiscal_year"] == valuation_base_year]
    if base_rows.empty:
        raise SystemExit(f"ERROR: Forecast does not contain valuation base year {valuation_base_year}.")

    base_row = base_rows.iloc[0]
    base_year_revenue = require_value(base_row, "revenue", "forecast revenue")
    net_cash = require_value(valuation_inputs, "net_cash", "net cash")
    share_count, share_count_source, share_count_note = choose_share_count(valuation_inputs)
    peer_median_ev_sales_ltm = get_peer_median_ev_sales_ltm(peer_statistics)
    share_count_millions = share_count / SHARES_PER_MILLION

    valuation_rows = []
    for scenario in SCENARIOS:
        ev_sales_multiple = scenario["ev_sales_multiple"]
        enterprise_value = base_year_revenue * ev_sales_multiple
        equity_value = enterprise_value + net_cash
        target_price = equity_value / share_count_millions
        valuation_rows.append(
            {
                "scenario": scenario["scenario"],
                "valuation_base_year": valuation_base_year,
                "base_year_revenue": base_year_revenue,
                "raw_peer_median_ev_sales_ltm": peer_median_ev_sales_ltm,
                "ev_sales_multiple": ev_sales_multiple,
                "multiple_methodology": MULTIPLE_METHODOLOGY_NOTE,
                "enterprise_value": enterprise_value,
                "net_cash": net_cash,
                "equity_value": equity_value,
                "share_count_used": share_count,
                "share_count_used_millions": share_count_millions,
                "share_count_source": share_count_source,
                "target_price": target_price,
                "note": share_count_note,
            }
        )

    valuation_table = pd.DataFrame(valuation_rows)

    multiples = [float(value) for value in range(20, 81, 5)]
    revenue_cases = {
        "revenue_down_20pct": base_year_revenue * 0.80,
        "revenue_base": base_year_revenue,
        "revenue_up_20pct": base_year_revenue * 1.20,
    }
    sensitivity_rows: list[dict[str, float | str]] = []
    for multiple in multiples:
        row: dict[str, float | str] = {"ev_sales_multiple": multiple}
        for case_name, revenue_case in revenue_cases.items():
            case_enterprise_value = revenue_case * multiple
            case_equity_value = case_enterprise_value + net_cash
            row[f"{case_name}_target_price"] = case_equity_value / share_count_millions
        sensitivity_rows.append(row)

    sensitivity_table = pd.DataFrame(sensitivity_rows)

    numeric_columns = valuation_table.select_dtypes(include="number").columns
    valuation_table[numeric_columns] = valuation_table[numeric_columns].round(6)
    sensitivity_table = sensitivity_table.round(6)

    return valuation_table, sensitivity_table, share_count_note


def write_summary(
    summary_path: Path,
    valuation_table: pd.DataFrame,
    sensitivity_table: pd.DataFrame,
    forecast_path: Path,
    valuation_inputs_path: Path,
    peer_statistics_path: Path,
    share_count_note: str,
) -> None:
    row = valuation_table.iloc[0]

    lines: list[str] = []
    lines.append("# EV/Sales Valuation Summary")
    lines.append("")
    lines.append(f"Forecast input: `{forecast_path}`")
    lines.append(f"Valuation input: `{valuation_inputs_path}`")
    lines.append(f"Peer statistics input: `{peer_statistics_path}`")
    lines.append("")
    lines.append("All financial values are in USD millions, except share count and target price.")
    lines.append("D-Wave is valued through forward revenue because current earnings and EBITDA are not representative of normalized profitability.")
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append(f"- Valuation base year: {int(row['valuation_base_year'])}")
    lines.append(f"- Base year revenue: {row['base_year_revenue']:.3f}")
    lines.append(f"- Raw quantum peer median EV/Sales LTM: {row['raw_peer_median_ev_sales_ltm']:.3f}x")
    lines.append("- Raw quantum peer EV/Sales multiples are shown as a market reference.")
    lines.append("- The raw median is not used directly due to distortion from small revenue bases.")
    lines.append("- Scenario multiples are capped to reduce the effect of those distortions.")
    lines.append("- Base case multiple: 40.0x EV/Sales.")
    lines.append(f"- Multiple methodology: {row['multiple_methodology']}")
    lines.append("")
    lines.append(f"Share count note: {share_count_note}")
    lines.append("")
    lines.append("## Scenario Valuation")
    lines.append("")
    lines.append("```text")
    lines.append(valuation_table.to_string(index=False))
    lines.append("```")
    lines.append("")
    lines.append("## Formula")
    lines.append("")
    lines.append("`enterprise_value = base_year_revenue * ev_sales_multiple`")
    lines.append("")
    lines.append("`equity_value = enterprise_value + net_cash`")
    lines.append("")
    lines.append("`target_price = equity_value / diluted_shares_or_share_count_used_in_millions`")
    lines.append("")
    lines.append("## Sensitivity")
    lines.append("")
    lines.append("The sensitivity table uses EV/Sales multiples from 20.0x to 80.0x and revenue cases from -20% to +20% around 2027E revenue.")
    lines.append("")
    lines.append("```text")
    lines.append(sensitivity_table.to_string(index=False))
    lines.append("```")
    lines.append("")

    summary_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    project_root = find_project_root(Path.cwd())
    forecast_path = project_root / "data" / "processed" / "dwave_forecast.csv"
    valuation_inputs_path = project_root / "data" / "processed" / "valuation_inputs.csv"
    peer_statistics_path = project_root / "outputs" / "tables" / "peer_multiples_statistics.csv"
    valuation_output_path = project_root / "outputs" / "tables" / "ev_sales_valuation.csv"
    sensitivity_output_path = project_root / "outputs" / "tables" / "ev_sales_sensitivity.csv"
    summary_path = project_root / "outputs" / "text" / "ev_sales_valuation_summary.md"

    valuation_output_path.parent.mkdir(parents=True, exist_ok=True)
    sensitivity_output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    forecast = load_csv(forecast_path)
    valuation_inputs = load_csv(valuation_inputs_path).iloc[0]
    peer_statistics = load_csv(peer_statistics_path)

    forecast["fiscal_year"] = pd.to_numeric(forecast["fiscal_year"], errors="coerce")
    for column in ["revenue"]:
        forecast[column] = pd.to_numeric(forecast[column], errors="coerce")
    for column in ["net_cash", "diluted_shares", "shares_outstanding"]:
        if column in valuation_inputs.index:
            valuation_inputs[column] = pd.to_numeric(valuation_inputs[column], errors="coerce")

    valuation_table, sensitivity_table, share_count_note = build_valuation(
        forecast,
        valuation_inputs,
        peer_statistics,
    )

    valuation_table.to_csv(valuation_output_path, index=False, na_rep="NA")
    sensitivity_table.to_csv(sensitivity_output_path, index=False, na_rep="NA")
    write_summary(
        summary_path=summary_path,
        valuation_table=valuation_table,
        sensitivity_table=sensitivity_table,
        forecast_path=forecast_path.relative_to(project_root),
        valuation_inputs_path=valuation_inputs_path.relative_to(project_root),
        peer_statistics_path=peer_statistics_path.relative_to(project_root),
        share_count_note=share_count_note,
    )

    print(f"Saved valuation table to: {valuation_output_path}")
    print(f"Saved sensitivity table to: {sensitivity_output_path}")
    print(f"Saved valuation summary to: {summary_path}")
    print("")
    print(valuation_table.to_string(index=False))
    print("")
    print(sensitivity_table.to_string(index=False))


if __name__ == "__main__":
    main()
