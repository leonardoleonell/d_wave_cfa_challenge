from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = [
    "revenue",
    "gross_profit",
    "cash_and_equivalents",
    "total_debt",
    "operating_cash_flow",
    "capex",
    "free_cash_flow",
]


def find_project_root(start: Path) -> Path:
    """Find the project root from either the repo root or notebooks folder."""
    start = start.resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "data" / "processed" / "dwave_financials_clean.csv").exists():
            return candidate
    raise FileNotFoundError("Could not find data/processed/dwave_financials_clean.csv from the current path.")


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.replace({0: np.nan})
    return numerator / denominator


def format_numeric_table(df: pd.DataFrame) -> str:
    return df.to_string(index=False, na_rep="NA")


def add_flag(flags: list[str], fiscal_year: object, message: str) -> None:
    flags.append(f"- Fiscal {fiscal_year}: {message}")


def validate_financials(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    flags: list[str] = []
    presence_notes: list[str] = []

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        presence_notes.append(f"Missing required columns: {', '.join(missing_columns)}")
    else:
        presence_notes.append("All required validation columns exist.")

    for column in REQUIRED_COLUMNS:
        if column in df.columns:
            non_missing_count = df[column].notna().sum()
            if non_missing_count == 0:
                presence_notes.append(f"`{column}` exists but has no non-missing values.")
            else:
                presence_notes.append(f"`{column}` present with {non_missing_count} non-missing values.")

    metric_df = df.copy()
    for column in metric_df.columns:
        if column != "fiscal_year":
            metric_df[column] = pd.to_numeric(metric_df[column], errors="coerce")

    metric_df = metric_df.sort_values("fiscal_year").reset_index(drop=True)

    metric_df["gross_margin"] = safe_divide(metric_df["gross_profit"], metric_df["revenue"])
    metric_df["operating_margin"] = safe_divide(metric_df["operating_income"], metric_df["revenue"])
    metric_df["net_margin"] = safe_divide(metric_df["net_income"], metric_df["revenue"])
    metric_df["revenue_growth"] = metric_df["revenue"].pct_change(fill_method=None)
    metric_df["cash_burn"] = np.where(metric_df["free_cash_flow"] < 0, -metric_df["free_cash_flow"], 0)
    metric_df["cash_runway_years"] = np.where(
        metric_df["cash_burn"] > 0,
        metric_df["cash_and_equivalents"] / metric_df["cash_burn"],
        np.nan,
    )

    fiscal_years = metric_df["fiscal_year"].dropna().astype(int).sort_values().tolist()
    if fiscal_years:
        expected_years = list(range(min(fiscal_years), max(fiscal_years) + 1))
        missing_years = sorted(set(expected_years) - set(fiscal_years))
        if missing_years:
            flags.append(f"- Missing fiscal years: {', '.join(str(year) for year in missing_years)}")
    else:
        flags.append("- Missing fiscal years: no fiscal_year values found.")

    for _, row in metric_df.iterrows():
        fiscal_year = row.get("fiscal_year", "unknown")

        if pd.isna(row.get("revenue")):
            add_flag(flags, fiscal_year, "revenue is missing.")
        elif row["revenue"] == 0:
            add_flag(flags, fiscal_year, "revenue is equal to zero.")

        gross_margin = row.get("gross_margin")
        if pd.notna(gross_margin) and (gross_margin > 1 or gross_margin < -1):
            add_flag(flags, fiscal_year, f"gross margin is outside +/-100%: {gross_margin:.2%}.")

        cash = row.get("cash_and_equivalents")
        if pd.notna(cash) and cash < 0:
            add_flag(flags, fiscal_year, f"cash_and_equivalents is negative: {cash:,.0f}.")

        capex = row.get("capex")
        operating_cash_flow = row.get("operating_cash_flow")
        free_cash_flow = row.get("free_cash_flow")
        if pd.notna(capex) and capex > 0 and pd.notna(operating_cash_flow) and pd.notna(free_cash_flow):
            expected_free_cash_flow = operating_cash_flow - capex
            if not np.isclose(free_cash_flow, expected_free_cash_flow, rtol=0, atol=1):
                add_flag(
                    flags,
                    fiscal_year,
                    "free_cash_flow does not equal operating_cash_flow - capex "
                    f"when capex is positive. Expected {expected_free_cash_flow:,.0f}, found {free_cash_flow:,.0f}.",
                )

    return metric_df, presence_notes, flags


def build_report(
    source_path: Path,
    validation_df: pd.DataFrame,
    presence_notes: list[str],
    flags: list[str],
) -> str:
    lines: list[str] = []
    lines.append("# Financials Validation Report")
    lines.append("")
    lines.append(f"Source file: `{source_path}`")
    lines.append("")
    lines.append("## Required Field Presence")
    lines.extend(f"- {note}" for note in presence_notes)
    lines.append("")
    lines.append("## Validation Flags")
    if flags:
        lines.extend(flags)
    else:
        lines.append("- No suspicious values flagged.")
    lines.append("")
    lines.append("## Calculated Metrics")
    lines.append("")
    lines.append("```text")
    lines.append(format_numeric_table(validation_df))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    project_root = find_project_root(Path.cwd())
    source_path = project_root / "data" / "processed" / "dwave_financials_clean.csv"
    report_path = project_root / "outputs" / "text" / "financials_validation_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(source_path, na_values=["NA", ""])

    print("Full cleaned financials table:")
    print(format_numeric_table(df))

    validation_df, presence_notes, flags = validate_financials(df)

    print("\nCalculated validation metrics:")
    print(format_numeric_table(validation_df))

    print("\nRequired field presence:")
    for note in presence_notes:
        print(f"- {note}")

    print("\nValidation flags:")
    if flags:
        for flag in flags:
            print(flag)
    else:
        print("- No suspicious values flagged.")

    report = build_report(source_path.relative_to(project_root), validation_df, presence_notes, flags)
    report_path.write_text(report, encoding="utf-8")
    print(f"\nSaved validation report to: {report_path}")


if __name__ == "__main__":
    main()
