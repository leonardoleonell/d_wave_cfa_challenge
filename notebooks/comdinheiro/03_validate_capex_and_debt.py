from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


DISPLAY_COLUMNS = [
    "fiscal_year",
    "operating_cash_flow",
    "capex",
    "free_cash_flow",
    "cash_and_equivalents",
    "marketable_securities",
    "total_debt",
    "net_cash",
]


def find_project_root(start: Path) -> Path:
    """Find the project root from either the repo root or notebooks folder."""
    start = start.resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "data" / "processed" / "dwave_financials_clean.csv").exists():
            return candidate
    raise FileNotFoundError("Could not find data/processed/dwave_financials_clean.csv from the current path.")


def format_table(df: pd.DataFrame) -> str:
    return df.to_string(index=False, na_rep="NA")


def add_result(results: list[dict[str, str]], check: str, status: str, detail: str) -> None:
    results.append({"check": check, "status": status, "detail": detail})


def validate(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    results: list[dict[str, str]] = []
    data = df.copy()

    numeric_columns = [column for column in data.columns if column != "fiscal_year"]
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    required_columns = [
        "fiscal_year",
        "operating_cash_flow",
        "capex",
        "free_cash_flow",
        "cash_and_equivalents",
        "marketable_securities",
        "total_debt",
    ]
    missing_columns = [column for column in required_columns if column not in data.columns]
    if missing_columns:
        add_result(
            results,
            "Required columns",
            "FAIL",
            "Missing required columns: " + ", ".join(missing_columns),
        )
        for column in missing_columns:
            data[column] = np.nan
    else:
        add_result(results, "Required columns", "PASS", "All required columns are present.")

    data["net_cash"] = data["cash_and_equivalents"] + data["marketable_securities"] - data["total_debt"]
    validation_table = data[DISPLAY_COLUMNS].sort_values("fiscal_year").reset_index(drop=True)

    capex_available = validation_table["capex"].notna()
    if not capex_available.any():
        add_result(results, "Capex positive", "WARN", "No capex values are available to validate.")
    else:
        bad_capex = validation_table[capex_available & (validation_table["capex"] < 0)]
        if bad_capex.empty:
            add_result(results, "Capex positive", "PASS", "All available cleaned capex values are non-negative.")
        else:
            years = ", ".join(str(int(year)) for year in bad_capex["fiscal_year"])
            add_result(results, "Capex positive", "FAIL", f"Negative cleaned capex found for fiscal years: {years}.")

    fcf_inputs_available = validation_table[["operating_cash_flow", "capex", "free_cash_flow"]].notna().all(axis=1)
    if not fcf_inputs_available.any():
        add_result(results, "Free cash flow formula", "WARN", "No complete OCF/capex/FCF rows are available.")
    else:
        expected_fcf = validation_table["operating_cash_flow"] - validation_table["capex"]
        fcf_mismatch = validation_table[
            fcf_inputs_available
            & ~np.isclose(validation_table["free_cash_flow"], expected_fcf, rtol=0, atol=0.001)
        ]
        if fcf_mismatch.empty:
            add_result(
                results,
                "Free cash flow formula",
                "PASS",
                "All complete rows satisfy free_cash_flow = operating_cash_flow - capex.",
            )
        else:
            years = ", ".join(str(int(year)) for year in fcf_mismatch["fiscal_year"])
            add_result(results, "Free cash flow formula", "FAIL", f"Formula mismatch for fiscal years: {years}.")

    if "total_liabilities" not in data.columns:
        add_result(
            results,
            "Debt not equal total liabilities",
            "N/A",
            "total_liabilities is not present in the cleaned CSV, so this check is not applicable.",
        )
    else:
        total_liabilities = pd.to_numeric(data["total_liabilities"], errors="coerce")
        comparable = data["total_debt"].notna() & total_liabilities.notna()
        if not comparable.any():
            add_result(
                results,
                "Debt not equal total liabilities",
                "WARN",
                "total_debt and total_liabilities have no comparable non-missing rows.",
            )
        else:
            equal_rows = data[comparable & np.isclose(data["total_debt"], total_liabilities, rtol=0, atol=0.001)]
            if equal_rows.empty:
                add_result(
                    results,
                    "Debt not equal total liabilities",
                    "PASS",
                    "total_debt differs from total_liabilities for all comparable rows.",
                )
            else:
                years = ", ".join(str(int(year)) for year in equal_rows["fiscal_year"])
                add_result(
                    results,
                    "Debt not equal total liabilities",
                    "FAIL",
                    f"total_debt equals total_liabilities for fiscal years: {years}.",
                )

    net_cash_inputs_available = validation_table[
        ["cash_and_equivalents", "marketable_securities", "total_debt", "net_cash"]
    ].notna().all(axis=1)
    if not net_cash_inputs_available.any():
        add_result(results, "Net cash formula", "WARN", "No complete cash/securities/debt rows are available.")
    else:
        expected_net_cash = (
            validation_table["cash_and_equivalents"]
            + validation_table["marketable_securities"]
            - validation_table["total_debt"]
        )
        net_cash_mismatch = validation_table[
            net_cash_inputs_available
            & ~np.isclose(validation_table["net_cash"], expected_net_cash, rtol=0, atol=0.001)
        ]
        if net_cash_mismatch.empty:
            add_result(
                results,
                "Net cash formula",
                "PASS",
                "All complete rows satisfy net_cash = cash_and_equivalents + marketable_securities - total_debt.",
            )
        else:
            years = ", ".join(str(int(year)) for year in net_cash_mismatch["fiscal_year"])
            add_result(results, "Net cash formula", "FAIL", f"Formula mismatch for fiscal years: {years}.")

    return validation_table, results


def build_report(source_path: Path, validation_table: pd.DataFrame, results: list[dict[str, str]]) -> str:
    results_df = pd.DataFrame(results)

    lines: list[str] = []
    lines.append("# Capex And Debt Validation Report")
    lines.append("")
    lines.append(f"Source file: `{source_path}`")
    lines.append("")
    lines.append("## Validation Results")
    lines.append("")
    lines.append("```text")
    lines.append(format_table(results_df))
    lines.append("```")
    lines.append("")
    lines.append("## Validation Table")
    lines.append("")
    lines.append("```text")
    lines.append(format_table(validation_table))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    project_root = find_project_root(Path.cwd())
    source_path = project_root / "data" / "processed" / "dwave_financials_clean.csv"
    report_path = project_root / "outputs" / "text" / "capex_debt_validation_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(source_path, na_values=["NA", ""])
    validation_table, results = validate(df)

    print("Capex and debt validation table:")
    print(format_table(validation_table))

    print("\nValidation results:")
    print(format_table(pd.DataFrame(results)))

    report = build_report(source_path.relative_to(project_root), validation_table, results)
    report_path.write_text(report, encoding="utf-8")
    print(f"\nSaved validation report to: {report_path}")


if __name__ == "__main__":
    main()
