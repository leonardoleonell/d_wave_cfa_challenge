from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


FORECAST_YEARS = list(range(2026, 2033))

ASSUMPTION_COLUMNS = [
    "revenue_growth",
    "gross_margin",
    "r_and_d_as_percent_revenue",
    "sga_as_percent_revenue",
    "capex_as_percent_revenue",
    "working_capital_as_percent_revenue",
    "tax_rate",
    "diluted_shares_growth",
]

REQUIRED_BASE_COLUMNS = [
    "fiscal_year",
    "revenue",
    "cash_and_equivalents",
    "shares_outstanding",
]

FORECAST_COLUMNS = [
    "fiscal_year",
    "revenue",
    "revenue_growth",
    "gross_profit",
    "gross_margin",
    "r_and_d",
    "r_and_d_as_percent_revenue",
    "sga",
    "sga_as_percent_revenue",
    "ebit",
    "tax_rate",
    "taxes",
    "nopat",
    "capex",
    "capex_as_percent_revenue",
    "working_capital_investment",
    "working_capital_as_percent_revenue",
    "free_cash_flow",
    "diluted_shares",
    "diluted_shares_growth",
    "cash_and_equivalents",
    "marketable_securities",
    "total_debt",
    "net_cash",
    "notes",
]


def find_project_root(start: Path) -> Path:
    """Find the project root from either the repo root or notebooks folder."""
    start = start.resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "data" / "processed" / "dwave_financials_clean.csv").exists():
            return candidate
    raise FileNotFoundError("Could not find data/processed/dwave_financials_clean.csv from the current path.")


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def load_historical(path: Path) -> pd.DataFrame:
    historical = pd.read_csv(path, na_values=["NA", "", "TO_BE_FILLED"])
    for column in historical.columns:
        if column != "notes":
            historical[column] = pd.to_numeric(historical[column], errors="coerce")
    return historical.sort_values("fiscal_year").reset_index(drop=True)


def load_assumptions(path: Path) -> pd.DataFrame:
    assumptions = pd.read_csv(path, na_values=["", "TO_BE_FILLED"])
    assumptions["fiscal_year"] = pd.to_numeric(assumptions["fiscal_year"], errors="coerce")
    for column in ASSUMPTION_COLUMNS:
        if column not in assumptions.columns:
            fail(f"Forecast assumptions file is missing required column: {column}")
        assumptions[column] = pd.to_numeric(assumptions[column], errors="coerce")
    return assumptions.sort_values("fiscal_year").reset_index(drop=True)


def validate_inputs(historical: pd.DataFrame, assumptions: pd.DataFrame) -> pd.Series:
    missing_base_columns = [column for column in REQUIRED_BASE_COLUMNS if column not in historical.columns]
    if missing_base_columns:
        fail(f"Historical financials are missing required columns: {missing_base_columns}")

    base_year = int(historical["fiscal_year"].max())
    base_row = historical.loc[historical["fiscal_year"] == base_year].iloc[0]

    missing_base_values = [
        column
        for column in REQUIRED_BASE_COLUMNS
        if pd.isna(base_row[column])
    ]
    if missing_base_values:
        fail(
            f"Latest historical fiscal year {base_year} has missing required values: "
            + ", ".join(missing_base_values)
        )

    assumption_years = assumptions["fiscal_year"].dropna().astype(int).tolist()
    if assumption_years != FORECAST_YEARS:
        fail(f"Forecast assumptions must contain fiscal years {FORECAST_YEARS}; found {assumption_years}.")

    missing_assumptions: list[str] = []
    for _, row in assumptions.iterrows():
        fiscal_year = int(row["fiscal_year"])
        for column in ASSUMPTION_COLUMNS:
            if pd.isna(row[column]):
                missing_assumptions.append(f"{fiscal_year}:{column}")
    if missing_assumptions:
        fail("Missing required forecast assumptions: " + ", ".join(missing_assumptions))

    return base_row


def calculate_net_cash(cash: float, marketable_securities: float | None, total_debt: float | None) -> float | None:
    if pd.isna(cash) or pd.isna(marketable_securities) or pd.isna(total_debt):
        return np.nan
    return cash + marketable_securities - total_debt


def build_forecast(base_row: pd.Series, assumptions: pd.DataFrame) -> pd.DataFrame:
    prior_revenue = float(base_row["revenue"])
    prior_cash = float(base_row["cash_and_equivalents"])
    prior_shares = float(base_row["shares_outstanding"])

    records: list[dict[str, float | int | str | None]] = []

    for _, assumption in assumptions.iterrows():
        fiscal_year = int(assumption["fiscal_year"])

        revenue = prior_revenue * (1 + assumption["revenue_growth"])
        gross_profit = revenue * assumption["gross_margin"]
        r_and_d = revenue * assumption["r_and_d_as_percent_revenue"]
        sga = revenue * assumption["sga_as_percent_revenue"]
        ebit = gross_profit - r_and_d - sga
        taxes = ebit * assumption["tax_rate"] if ebit > 0 else 0.0
        nopat = ebit - taxes
        capex = revenue * assumption["capex_as_percent_revenue"]
        working_capital_investment = revenue * assumption["working_capital_as_percent_revenue"]
        free_cash_flow = nopat - capex - working_capital_investment
        diluted_shares = prior_shares * (1 + assumption["diluted_shares_growth"])
        cash_and_equivalents = prior_cash + free_cash_flow

        # No forecast assumptions are provided for marketable securities or total debt.
        marketable_securities = np.nan
        total_debt = np.nan
        net_cash = calculate_net_cash(cash_and_equivalents, marketable_securities, total_debt)

        records.append(
            {
                "fiscal_year": fiscal_year,
                "revenue": revenue,
                "revenue_growth": assumption["revenue_growth"],
                "gross_profit": gross_profit,
                "gross_margin": assumption["gross_margin"],
                "r_and_d": r_and_d,
                "r_and_d_as_percent_revenue": assumption["r_and_d_as_percent_revenue"],
                "sga": sga,
                "sga_as_percent_revenue": assumption["sga_as_percent_revenue"],
                "ebit": ebit,
                "tax_rate": assumption["tax_rate"],
                "taxes": taxes,
                "nopat": nopat,
                "capex": capex,
                "capex_as_percent_revenue": assumption["capex_as_percent_revenue"],
                "working_capital_investment": working_capital_investment,
                "working_capital_as_percent_revenue": assumption["working_capital_as_percent_revenue"],
                "free_cash_flow": free_cash_flow,
                "diluted_shares": diluted_shares,
                "diluted_shares_growth": assumption["diluted_shares_growth"],
                "cash_and_equivalents": cash_and_equivalents,
                "marketable_securities": marketable_securities,
                "total_debt": total_debt,
                "net_cash": net_cash,
                "notes": assumption.get("notes", ""),
            }
        )

        prior_revenue = revenue
        prior_cash = cash_and_equivalents
        prior_shares = diluted_shares

    forecast = pd.DataFrame(records, columns=FORECAST_COLUMNS)
    numeric_columns = [column for column in forecast.columns if column not in {"fiscal_year", "notes"}]
    forecast[numeric_columns] = forecast[numeric_columns].round(3)
    return forecast


def write_summary(
    summary_path: Path,
    base_row: pd.Series,
    forecast: pd.DataFrame,
    assumptions_path: Path,
    historical_path: Path,
) -> None:
    base_year = int(base_row["fiscal_year"])
    final_year = int(forecast["fiscal_year"].max())
    final_row = forecast.loc[forecast["fiscal_year"] == final_year].iloc[0]

    lines: list[str] = []
    lines.append("# D-Wave Forecast Summary")
    lines.append("")
    lines.append(f"Historical input: `{historical_path}`")
    lines.append(f"Assumptions input: `{assumptions_path}`")
    lines.append("")
    lines.append("All financial values are in USD millions, except share count.")
    lines.append(f"The latest historical fiscal year used as the base year is fiscal {base_year}.")
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append("- Revenue is projected from prior-year revenue using `revenue_growth`.")
    lines.append("- Gross profit is projected using `gross_margin`.")
    lines.append("- R&D and SG&A are projected as percentages of revenue.")
    lines.append("- EBIT equals gross profit minus R&D minus SG&A.")
    lines.append("- Taxes are calculated only when EBIT is positive.")
    lines.append("- NOPAT equals EBIT minus taxes.")
    lines.append("- Capex and working capital investment are projected as percentages of revenue.")
    lines.append("- Free cash flow equals NOPAT minus capex minus working capital investment.")
    lines.append("- Diluted shares are projected using `diluted_shares_growth`.")
    lines.append("- Cash balance equals prior-year cash plus free cash flow.")
    lines.append("- Net cash is left blank because no forecast assumptions were provided for marketable securities or total debt.")
    lines.append("")
    lines.append("## Forecast Snapshot")
    lines.append("")
    lines.append(
        f"By fiscal {final_year}, forecast revenue is {final_row['revenue']:.1f}, "
        f"EBIT is {final_row['ebit']:.1f}, free cash flow is {final_row['free_cash_flow']:.1f}, "
        f"and cash and equivalents are {final_row['cash_and_equivalents']:.1f}."
    )
    lines.append("")
    lines.append("## Forecast Table")
    lines.append("")
    lines.append("```text")
    lines.append(forecast.to_string(index=False, na_rep="NA"))
    lines.append("```")
    lines.append("")

    summary_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    project_root = find_project_root(Path.cwd())
    historical_path = project_root / "data" / "processed" / "dwave_financials_clean.csv"
    assumptions_path = project_root / "data" / "processed" / "dwave_forecast_assumptions.csv"
    forecast_path = project_root / "data" / "processed" / "dwave_forecast.csv"
    table_path = project_root / "outputs" / "tables" / "dwave_forecast_summary.csv"
    summary_path = project_root / "outputs" / "text" / "forecast_summary.md"

    forecast_path.parent.mkdir(parents=True, exist_ok=True)
    table_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    historical = load_historical(historical_path)
    assumptions = load_assumptions(assumptions_path)
    base_row = validate_inputs(historical, assumptions)
    forecast = build_forecast(base_row, assumptions)

    forecast.to_csv(forecast_path, index=False, na_rep="NA")
    forecast.to_csv(table_path, index=False, na_rep="NA")
    write_summary(
        summary_path=summary_path,
        base_row=base_row,
        forecast=forecast,
        assumptions_path=assumptions_path.relative_to(project_root),
        historical_path=historical_path.relative_to(project_root),
    )

    print(f"Base fiscal year: {int(base_row['fiscal_year'])}")
    print(f"Saved forecast to: {forecast_path}")
    print(f"Saved forecast summary table to: {table_path}")
    print(f"Saved written forecast summary to: {summary_path}")
    print("")
    print(forecast.to_string(index=False, na_rep="NA"))


if __name__ == "__main__":
    main()
