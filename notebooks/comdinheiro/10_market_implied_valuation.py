from __future__ import annotations

from pathlib import Path

import pandas as pd


CURRENT_SHARE_PRICE = 22.35
DEFAULT_SHARES_OUTSTANDING_MILLIONS = 370.03
FORECAST_REVENUE_YEAR = 2027
BASE_CASE_EV_SALES_MULTIPLE = 40.0
BULL_CASE_EV_SALES_MULTIPLE = 60.0
SHARES_PER_MILLION = 1_000_000


def find_project_root(start: Path) -> Path:
    """Find the project root from either the repo root or notebooks folder."""
    start = start.resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "data" / "processed" / "dwave_forecast.csv").exists():
            return candidate
    raise FileNotFoundError("Could not find data/processed/dwave_forecast.csv from the current path.")


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"ERROR: Required input file does not exist: {path}")
    return pd.read_csv(path, na_values=["NA", "", "TO_BE_FILLED"])


def require_columns(df: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise SystemExit(f"ERROR: {label} is missing required columns: {missing}")


def get_numeric_value(row: pd.Series, column: str, label: str) -> float:
    if column not in row.index or pd.isna(row[column]):
        raise SystemExit(f"ERROR: Missing required {label}: {column}")
    return float(row[column])


def get_2027_revenue(forecast: pd.DataFrame) -> float:
    require_columns(forecast, ["fiscal_year", "revenue"], "Forecast file")
    forecast = forecast.copy()
    forecast["fiscal_year"] = pd.to_numeric(forecast["fiscal_year"], errors="coerce")
    forecast["revenue"] = pd.to_numeric(forecast["revenue"], errors="coerce")

    revenue_rows = forecast[forecast["fiscal_year"] == FORECAST_REVENUE_YEAR]
    if revenue_rows.empty:
        raise SystemExit(f"ERROR: Forecast file does not include fiscal year {FORECAST_REVENUE_YEAR}.")

    revenue = revenue_rows["revenue"].iloc[0]
    if pd.isna(revenue):
        raise SystemExit(f"ERROR: Forecast revenue is missing for fiscal year {FORECAST_REVENUE_YEAR}.")
    return float(revenue)


def get_valuation_inputs(valuation_inputs: pd.DataFrame) -> tuple[float, float, str]:
    require_columns(valuation_inputs, ["net_cash"], "Valuation input file")
    inputs = valuation_inputs.copy()
    for column in ["latest_fiscal_year", "net_cash", "shares_outstanding"]:
        if column in inputs.columns:
            inputs[column] = pd.to_numeric(inputs[column], errors="coerce")

    latest_row = inputs.sort_values("latest_fiscal_year").iloc[-1] if "latest_fiscal_year" in inputs.columns else inputs.iloc[-1]
    net_cash = get_numeric_value(latest_row, "net_cash", "net cash")

    shares_outstanding = latest_row.get("shares_outstanding", pd.NA)
    if pd.notna(shares_outstanding):
        shares_outstanding_millions = float(shares_outstanding) / SHARES_PER_MILLION
        share_count_source = "valuation_inputs.csv shares_outstanding"
    else:
        shares_outstanding_millions = DEFAULT_SHARES_OUTSTANDING_MILLIONS
        share_count_source = "default 370.03 million shares"

    return net_cash, shares_outstanding_millions, share_count_source


def get_base_case_ev_sales_target_price(ev_sales_valuation: pd.DataFrame) -> float | None:
    if "scenario" not in ev_sales_valuation.columns or "target_price" not in ev_sales_valuation.columns:
        return None
    table = ev_sales_valuation.copy()
    table["target_price"] = pd.to_numeric(table["target_price"], errors="coerce")
    base_rows = table[table["scenario"].astype(str).str.lower() == "base"]
    if base_rows.empty or pd.isna(base_rows["target_price"].iloc[0]):
        return None
    return float(base_rows["target_price"].iloc[0])


def build_market_implied_table(
    revenue_2027: float,
    net_cash: float,
    shares_outstanding_millions: float,
    share_count_source: str,
    base_case_target_price: float | None,
) -> pd.DataFrame:
    current_market_cap = CURRENT_SHARE_PRICE * shares_outstanding_millions
    implied_enterprise_value = current_market_cap - net_cash
    implied_ev_sales_2027 = implied_enterprise_value / revenue_2027
    revenue_required_at_40x = implied_enterprise_value / BASE_CASE_EV_SALES_MULTIPLE
    revenue_required_at_60x = implied_enterprise_value / BULL_CASE_EV_SALES_MULTIPLE

    target_price_premium_to_base = pd.NA
    if base_case_target_price is not None and base_case_target_price != 0:
        target_price_premium_to_base = CURRENT_SHARE_PRICE / base_case_target_price - 1

    results = pd.DataFrame(
        [
            {
                "current_share_price": CURRENT_SHARE_PRICE,
                "shares_outstanding_millions": shares_outstanding_millions,
                "share_count_source": share_count_source,
                "current_market_cap": current_market_cap,
                "net_cash": net_cash,
                "implied_enterprise_value": implied_enterprise_value,
                "forecast_year": FORECAST_REVENUE_YEAR,
                "forecast_revenue": revenue_2027,
                "implied_ev_sales_2027": implied_ev_sales_2027,
                "revenue_required_at_40x_ev_sales": revenue_required_at_40x,
                "revenue_required_at_60x_ev_sales": revenue_required_at_60x,
                "base_case_ev_sales_target_price": base_case_target_price if base_case_target_price is not None else pd.NA,
                "current_price_premium_to_base_case_target_price": target_price_premium_to_base,
            }
        ]
    )

    numeric_columns = results.select_dtypes(include="number").columns
    results[numeric_columns] = results[numeric_columns].round(6)
    return results


def write_summary(
    summary_path: Path,
    forecast_path: Path,
    valuation_inputs_path: Path,
    ev_sales_path: Path,
    results: pd.DataFrame,
    project_root: Path,
) -> None:
    row = results.iloc[0]
    lines: list[str] = []
    lines.append("# Market-Implied Valuation Summary")
    lines.append("")
    lines.append(f"Forecast input: `{forecast_path.relative_to(project_root)}`")
    lines.append(f"Valuation input: `{valuation_inputs_path.relative_to(project_root)}`")
    lines.append(f"EV/Sales valuation input: `{ev_sales_path.relative_to(project_root)}`")
    lines.append("")
    lines.append("All financial values are in USD millions, except share price and EV/Sales multiples.")
    lines.append("")
    lines.append("## Market-Implied View")
    lines.append("")
    lines.append(f"- Current share price used: ${row['current_share_price']:.2f}")
    lines.append(f"- Shares outstanding used: {row['shares_outstanding_millions']:.2f} million")
    lines.append(f"- Share count source: {row['share_count_source']}")
    lines.append(f"- Current market capitalization: {row['current_market_cap']:.3f}")
    lines.append(f"- Net cash: {row['net_cash']:.3f}")
    lines.append(f"- Implied enterprise value: {row['implied_enterprise_value']:.3f}")
    lines.append(f"- 2027E revenue: {row['forecast_revenue']:.3f}")
    lines.append(f"- Implied EV/Sales on 2027E revenue: {row['implied_ev_sales_2027']:.2f}x")
    lines.append(f"- Revenue required at 40.0x EV/Sales: {row['revenue_required_at_40x_ev_sales']:.3f}")
    lines.append(f"- Revenue required at 60.0x EV/Sales: {row['revenue_required_at_60x_ev_sales']:.3f}")
    lines.append("")
    lines.append(
        "The current market price implies a much higher revenue base or a much higher EV/Sales multiple than the base case."
    )
    lines.append(
        "At the current share price, the implied EV/Sales multiple on 2027E revenue is materially above the capped 40.0x base-case EV/Sales multiple used in the valuation."
    )
    lines.append("")
    lines.append("## Output Table")
    lines.append("")
    lines.append("```text")
    lines.append(results.to_string(index=False))
    lines.append("```")
    lines.append("")

    summary_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    project_root = find_project_root(Path.cwd())
    forecast_path = project_root / "data" / "processed" / "dwave_forecast.csv"
    valuation_inputs_path = project_root / "data" / "processed" / "valuation_inputs.csv"
    ev_sales_path = project_root / "outputs" / "tables" / "ev_sales_valuation.csv"
    output_path = project_root / "outputs" / "tables" / "market_implied_valuation.csv"
    summary_path = project_root / "outputs" / "text" / "market_implied_valuation_summary.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    forecast = load_csv(forecast_path)
    valuation_inputs = load_csv(valuation_inputs_path)
    ev_sales_valuation = load_csv(ev_sales_path)

    revenue_2027 = get_2027_revenue(forecast)
    net_cash, shares_outstanding_millions, share_count_source = get_valuation_inputs(valuation_inputs)
    base_case_target_price = get_base_case_ev_sales_target_price(ev_sales_valuation)

    results = build_market_implied_table(
        revenue_2027=revenue_2027,
        net_cash=net_cash,
        shares_outstanding_millions=shares_outstanding_millions,
        share_count_source=share_count_source,
        base_case_target_price=base_case_target_price,
    )

    results.to_csv(output_path, index=False, na_rep="NA")
    write_summary(
        summary_path=summary_path,
        forecast_path=forecast_path,
        valuation_inputs_path=valuation_inputs_path,
        ev_sales_path=ev_sales_path,
        results=results,
        project_root=project_root,
    )

    print(f"Saved market-implied valuation table to: {output_path}")
    print(f"Saved market-implied valuation summary to: {summary_path}")
    print("")
    print(results.to_string(index=False))


if __name__ == "__main__":
    main()
