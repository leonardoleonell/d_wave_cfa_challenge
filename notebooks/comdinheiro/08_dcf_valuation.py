from __future__ import annotations

from pathlib import Path

import pandas as pd


DCF_CASES = [
    {"scenario": "Bear", "wacc": 0.20, "terminal_growth": 0.02, "terminal_fcf_margin": 0.05},
    {"scenario": "Base", "wacc": 0.17, "terminal_growth": 0.03, "terminal_fcf_margin": 0.10},
    {"scenario": "Bull", "wacc": 0.14, "terminal_growth": 0.04, "terminal_fcf_margin": 0.15},
]

LATEST_HISTORICAL_YEAR = 2025
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


def require_columns(df: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise SystemExit(f"ERROR: {label} is missing required columns: {missing}")


def require_value(row: pd.Series, column: str, label: str) -> float:
    if column not in row.index or pd.isna(row[column]):
        raise SystemExit(f"ERROR: Missing required {label}: {column}")
    return float(row[column])


def choose_share_count(valuation_inputs: pd.Series) -> tuple[float, str, str]:
    diluted_shares = valuation_inputs.get("diluted_shares", pd.NA)
    shares_outstanding = valuation_inputs.get("shares_outstanding", pd.NA)

    if pd.notna(diluted_shares):
        return float(diluted_shares), "diluted_shares", "Diluted shares were available and used."
    if pd.notna(shares_outstanding):
        return (
            float(shares_outstanding),
            "shares_outstanding",
            "Diluted shares were missing, so shares outstanding were used. This is less conservative.",
        )
    raise SystemExit("ERROR: Both diluted_shares and shares_outstanding are missing.")


def select_valuation_inputs(valuation_inputs: pd.DataFrame) -> pd.Series:
    require_columns(valuation_inputs, ["latest_fiscal_year", "net_cash"], "Valuation input file")
    valuation_inputs = valuation_inputs.copy()
    for column in ["latest_fiscal_year", "net_cash", "diluted_shares", "shares_outstanding"]:
        if column in valuation_inputs.columns:
            valuation_inputs[column] = pd.to_numeric(valuation_inputs[column], errors="coerce")

    matching_rows = valuation_inputs[valuation_inputs["latest_fiscal_year"] == LATEST_HISTORICAL_YEAR]
    if matching_rows.empty:
        raise SystemExit(f"ERROR: Valuation input file does not include {LATEST_HISTORICAL_YEAR} net cash.")
    return matching_rows.iloc[0]


def prepare_inputs(forecast: pd.DataFrame, valuation_inputs: pd.Series) -> tuple[pd.DataFrame, float, float, str, str]:
    require_columns(forecast, ["fiscal_year", "revenue", "free_cash_flow"], "Forecast file")

    forecast = forecast.copy()
    for column in ["fiscal_year", "revenue", "free_cash_flow"]:
        forecast[column] = pd.to_numeric(forecast[column], errors="coerce")

    forecast = forecast.sort_values("fiscal_year").reset_index(drop=True)
    if forecast.empty:
        raise SystemExit("ERROR: Forecast file has no rows.")

    missing_rows = forecast[forecast[["fiscal_year", "revenue", "free_cash_flow"]].isna().any(axis=1)]
    if not missing_rows.empty:
        years = ", ".join(str(int(year)) for year in missing_rows["fiscal_year"].dropna())
        raise SystemExit(f"ERROR: Forecast has missing required revenue or free_cash_flow values for years: {years}")

    net_cash = require_value(valuation_inputs, "net_cash", "2025 net cash")
    share_count, share_count_source, share_count_note = choose_share_count(valuation_inputs)
    return forecast, net_cash, share_count, share_count_source, share_count_note


def calculate_dcf_case(
    forecast: pd.DataFrame,
    net_cash: float,
    share_count: float,
    share_count_source: str,
    share_count_note: str,
    scenario: str,
    wacc: float,
    terminal_growth: float,
    terminal_fcf_margin: float,
) -> dict[str, float | str]:
    if wacc <= terminal_growth:
        raise SystemExit(f"ERROR: WACC must be greater than terminal growth for {scenario} case.")

    start_year = int(forecast["fiscal_year"].min())
    last_year = int(forecast["fiscal_year"].max())
    terminal_year_revenue = float(forecast.loc[forecast["fiscal_year"] == last_year, "revenue"].iloc[0])

    pv_explicit_fcf = 0.0
    for _, row in forecast.iterrows():
        year = int(row["fiscal_year"])
        period = year - start_year + 1
        pv_explicit_fcf += float(row["free_cash_flow"]) / ((1 + wacc) ** period)

    terminal_fcf = terminal_year_revenue * terminal_fcf_margin
    terminal_value = terminal_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
    terminal_discount_period = last_year - start_year + 1
    pv_terminal_value = terminal_value / ((1 + wacc) ** terminal_discount_period)
    enterprise_value = pv_explicit_fcf + pv_terminal_value
    equity_value = enterprise_value + net_cash
    share_count_millions = share_count / SHARES_PER_MILLION
    target_price = equity_value / share_count_millions
    positive_pv_components = sum(value for value in [pv_explicit_fcf, pv_terminal_value] if value > 0)
    terminal_value_share_of_positive_pv = (
        pv_terminal_value / positive_pv_components if positive_pv_components else pd.NA
    )

    return {
        "scenario": scenario,
        "forecast_start_year": start_year,
        "forecast_end_year": last_year,
        "wacc": wacc,
        "terminal_growth": terminal_growth,
        "terminal_fcf_margin": terminal_fcf_margin,
        "terminal_year_revenue": terminal_year_revenue,
        "terminal_fcf": terminal_fcf,
        "terminal_value": terminal_value,
        "pv_explicit_fcf": pv_explicit_fcf,
        "pv_terminal_value": pv_terminal_value,
        "terminal_value_share_of_positive_pv_components": terminal_value_share_of_positive_pv,
        "enterprise_value": enterprise_value,
        "net_cash": net_cash,
        "equity_value": equity_value,
        "share_count_used": share_count,
        "share_count_used_millions": share_count_millions,
        "share_count_source": share_count_source,
        "target_price": target_price,
        "note": share_count_note,
    }


def build_dcf_valuation(
    forecast: pd.DataFrame,
    net_cash: float,
    share_count: float,
    share_count_source: str,
    share_count_note: str,
) -> pd.DataFrame:
    rows = [
        calculate_dcf_case(
            forecast=forecast,
            net_cash=net_cash,
            share_count=share_count,
            share_count_source=share_count_source,
            share_count_note=share_count_note,
            **case,
        )
        for case in DCF_CASES
    ]
    valuation = pd.DataFrame(rows)
    numeric_columns = valuation.select_dtypes(include="number").columns
    valuation[numeric_columns] = valuation[numeric_columns].round(6)
    return valuation


def build_sensitivity(forecast: pd.DataFrame, net_cash: float, share_count: float) -> pd.DataFrame:
    wacc_values = [value / 100 for value in range(14, 23)]
    terminal_fcf_margin_values = [value / 100 for value in range(5, 21, 1)]

    rows: list[dict[str, float]] = []
    for wacc in wacc_values:
        row: dict[str, float] = {"wacc": wacc}
        for margin in terminal_fcf_margin_values:
            dcf_case = calculate_dcf_case(
                forecast=forecast,
                net_cash=net_cash,
                share_count=share_count,
                share_count_source="sensitivity",
                share_count_note="",
                scenario="Sensitivity",
                wacc=wacc,
                terminal_growth=0.03,
                terminal_fcf_margin=margin,
            )
            row[f"terminal_fcf_margin_{int(margin * 100)}pct"] = dcf_case["target_price"]
        rows.append(row)

    sensitivity = pd.DataFrame(rows)
    return sensitivity.round(6)


def write_summary(
    summary_path: Path,
    forecast_path: Path,
    valuation_inputs_path: Path,
    valuation: pd.DataFrame,
    sensitivity: pd.DataFrame,
    share_count_note: str,
) -> None:
    base = valuation.loc[valuation["scenario"] == "Base"].iloc[0]

    lines: list[str] = []
    lines.append("# DCF Valuation Summary")
    lines.append("")
    lines.append(f"Forecast input: `{forecast_path}`")
    lines.append(f"Valuation input: `{valuation_inputs_path}`")
    lines.append("")
    lines.append("All financial values are in USD millions, except share count and target price.")
    lines.append(f"Net cash is sourced from the {LATEST_HISTORICAL_YEAR} valuation input row.")
    lines.append("")
    lines.append("DCF is used as a secondary cross-check, not the primary valuation method.")
    lines.append("D-Wave's current free cash flow is negative, so the DCF is highly sensitive to terminal assumptions.")
    lines.append("Most of the DCF value likely comes from terminal value.")
    lines.append("EV/Sales remains the primary method because current earnings and EBITDA are not representative of normalized profitability.")
    lines.append("")
    lines.append(f"Share count note: {share_count_note}")
    lines.append("")
    lines.append("## Base Case Snapshot")
    lines.append("")
    lines.append(f"- WACC: {base['wacc']:.0%}")
    lines.append(f"- Terminal growth: {base['terminal_growth']:.0%}")
    lines.append(f"- Terminal FCF margin: {base['terminal_fcf_margin']:.0%}")
    lines.append(f"- PV explicit FCF: {base['pv_explicit_fcf']:.3f}")
    lines.append(f"- PV terminal value: {base['pv_terminal_value']:.3f}")
    lines.append(f"- Enterprise value: {base['enterprise_value']:.3f}")
    lines.append(f"- Equity value: {base['equity_value']:.3f}")
    lines.append(f"- Target price: ${base['target_price']:.2f}")
    lines.append(f"- Terminal value share of positive PV components: {base['terminal_value_share_of_positive_pv_components']:.1%}")
    lines.append("")
    lines.append(
        "Because explicit forecast FCF is negative, the present value of terminal value is the positive operating value component before adding net cash."
    )
    lines.append("")
    lines.append("## Scenario Valuation")
    lines.append("")
    lines.append("```text")
    lines.append(valuation.to_string(index=False))
    lines.append("```")
    lines.append("")
    lines.append("## Base Case Sensitivity")
    lines.append("")
    lines.append("The sensitivity table uses WACC from 14% to 22% and terminal FCF margin from 5% to 20%, with base-case terminal growth of 3%.")
    lines.append("")
    lines.append("```text")
    lines.append(sensitivity.to_string(index=False))
    lines.append("```")
    lines.append("")

    summary_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    project_root = find_project_root(Path.cwd())
    forecast_path = project_root / "data" / "processed" / "dwave_forecast.csv"
    valuation_inputs_path = project_root / "data" / "processed" / "valuation_inputs.csv"
    dcf_output_path = project_root / "outputs" / "tables" / "dcf_valuation.csv"
    sensitivity_output_path = project_root / "outputs" / "tables" / "dcf_sensitivity.csv"
    summary_path = project_root / "outputs" / "text" / "dcf_valuation_summary.md"

    dcf_output_path.parent.mkdir(parents=True, exist_ok=True)
    sensitivity_output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    forecast = load_csv(forecast_path)
    valuation_inputs = select_valuation_inputs(load_csv(valuation_inputs_path))

    forecast, net_cash, share_count, share_count_source, share_count_note = prepare_inputs(forecast, valuation_inputs)
    valuation = build_dcf_valuation(forecast, net_cash, share_count, share_count_source, share_count_note)
    sensitivity = build_sensitivity(forecast, net_cash, share_count)

    valuation.to_csv(dcf_output_path, index=False, na_rep="NA")
    sensitivity.to_csv(sensitivity_output_path, index=False, na_rep="NA")
    write_summary(
        summary_path=summary_path,
        forecast_path=forecast_path.relative_to(project_root),
        valuation_inputs_path=valuation_inputs_path.relative_to(project_root),
        valuation=valuation,
        sensitivity=sensitivity,
        share_count_note=share_count_note,
    )

    print(f"Saved DCF valuation to: {dcf_output_path}")
    print(f"Saved DCF sensitivity to: {sensitivity_output_path}")
    print(f"Saved DCF summary to: {summary_path}")
    print("")
    print(valuation.to_string(index=False))
    print("")
    print(sensitivity.to_string(index=False))


if __name__ == "__main__":
    main()
