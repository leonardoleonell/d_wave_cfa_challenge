from __future__ import annotations

from pathlib import Path

import pandas as pd


EV_SALES_WEIGHT = 0.80
DCF_WEIGHT = 0.20
FINAL_SCENARIO = "Base"
REQUIRED_SCENARIOS = ["Bear", "Base", "Bull"]


def find_project_root(start: Path) -> Path:
    """Find the project root from either the repo root or notebooks folder."""
    start = start.resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "outputs" / "tables" / "ev_sales_valuation.csv").exists():
            return candidate
    raise FileNotFoundError("Could not find outputs/tables/ev_sales_valuation.csv from the current path.")


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"ERROR: Required input file does not exist: {path}")
    return pd.read_csv(path, na_values=["NA", "", "TO_BE_FILLED"])


def require_columns(df: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise SystemExit(f"ERROR: {label} is missing required columns: {missing}")


def prepare_method_table(df: pd.DataFrame, label: str) -> pd.DataFrame:
    require_columns(df, ["scenario", "target_price", "share_count_source", "note"], label)
    table = df.copy()
    table["scenario"] = table["scenario"].astype(str)
    table["target_price"] = pd.to_numeric(table["target_price"], errors="coerce")

    missing_scenarios = [scenario for scenario in REQUIRED_SCENARIOS if scenario not in set(table["scenario"])]
    if missing_scenarios:
        raise SystemExit(f"ERROR: {label} is missing required scenarios: {missing_scenarios}")

    required_rows = table[table["scenario"].isin(REQUIRED_SCENARIOS)]
    if required_rows["target_price"].isna().any():
        bad_rows = required_rows.loc[required_rows["target_price"].isna(), "scenario"].tolist()
        raise SystemExit(f"ERROR: {label} has missing target_price values for scenarios: {bad_rows}")

    return required_rows.set_index("scenario").loc[REQUIRED_SCENARIOS].reset_index()


def build_final_table(ev_sales: pd.DataFrame, dcf: pd.DataFrame) -> pd.DataFrame:
    ev_sales = prepare_method_table(ev_sales, "EV/Sales valuation file")
    dcf = prepare_method_table(dcf, "DCF valuation file")

    merged = ev_sales[["scenario", "target_price"]].rename(
        columns={"target_price": "ev_sales_target_price"}
    )
    merged = merged.merge(
        dcf[["scenario", "target_price"]].rename(columns={"target_price": "dcf_target_price"}),
        on="scenario",
        how="inner",
    )

    merged["ev_sales_weight"] = EV_SALES_WEIGHT
    merged["dcf_weight"] = DCF_WEIGHT
    merged["weighted_target_price"] = (
        merged["ev_sales_target_price"] * EV_SALES_WEIGHT
        + merged["dcf_target_price"] * DCF_WEIGHT
    )
    merged["is_final_target_price"] = merged["scenario"].eq(FINAL_SCENARIO)

    numeric_columns = merged.select_dtypes(include="number").columns
    merged[numeric_columns] = merged[numeric_columns].round(6)
    return merged


def get_base_value(table: pd.DataFrame, column: str) -> float:
    return float(table.loc[table["scenario"] == FINAL_SCENARIO, column].iloc[0])


def get_share_count_note(ev_sales: pd.DataFrame, dcf: pd.DataFrame) -> str:
    notes = []
    for table in [ev_sales, dcf]:
        if "note" in table.columns:
            notes.extend(table["note"].dropna().astype(str).tolist())
    less_conservative_notes = [note for note in notes if "less conservative" in note.lower()]
    if less_conservative_notes:
        return "Diluted shares were unavailable, so shares outstanding were used, which is less conservative."
    return "Share count source is based on the valuation input used by the underlying valuation scripts."


def get_raw_peer_median_note(ev_sales: pd.DataFrame) -> str:
    if "raw_peer_median_ev_sales_ltm" not in ev_sales.columns:
        return "Raw quantum peer EV/Sales median was not available in the EV/Sales valuation output."

    raw_median = pd.to_numeric(ev_sales["raw_peer_median_ev_sales_ltm"], errors="coerce").dropna()
    if raw_median.empty:
        return "Raw quantum peer EV/Sales median was not available in the EV/Sales valuation output."
    return f"Raw quantum peer EV/Sales median reference: {raw_median.iloc[0]:.3f}x."


def write_summary(
    summary_path: Path,
    ev_sales_path: Path,
    dcf_path: Path,
    final_table: pd.DataFrame,
    ev_sales: pd.DataFrame,
    dcf: pd.DataFrame,
    project_root: Path,
) -> None:
    ev_sales_base = get_base_value(final_table, "ev_sales_target_price")
    dcf_base = get_base_value(final_table, "dcf_target_price")
    final_target = get_base_value(final_table, "weighted_target_price")
    share_count_note = get_share_count_note(ev_sales, dcf)
    raw_peer_note = get_raw_peer_median_note(ev_sales)

    lines: list[str] = []
    lines.append("# Final Valuation Summary")
    lines.append("")
    lines.append(f"EV/Sales input: `{ev_sales_path.relative_to(project_root)}`")
    lines.append(f"DCF input: `{dcf_path.relative_to(project_root)}`")
    lines.append("")
    lines.append("No numbers were invented; the final valuation uses only the exported EV/Sales and DCF valuation files.")
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append("EV/Sales is the primary method because D-Wave is early-stage and current earnings/EBITDA are not representative.")
    lines.append("DCF is used only as a conservative cross-check because explicit FCF remains negative and the model is highly sensitive to terminal assumptions.")
    lines.append("The raw quantum peer EV/Sales median is not used directly because peer multiples are distorted by very small revenue bases.")
    lines.append("The final target price is based on an 80% EV/Sales and 20% DCF weighting.")
    lines.append(share_count_note)
    lines.append(raw_peer_note)
    lines.append("")
    lines.append("## Final Target Price")
    lines.append("")
    lines.append(f"- EV/Sales Base case target price: ${ev_sales_base:.2f}")
    lines.append(f"- DCF Base case target price: ${dcf_base:.2f}")
    lines.append(f"- Final weighted target price: ${final_target:.2f}")
    lines.append("")
    lines.append("## Scenario Summary")
    lines.append("")
    lines.append("```text")
    lines.append(final_table.to_string(index=False))
    lines.append("```")
    lines.append("")

    summary_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    project_root = find_project_root(Path.cwd())
    ev_sales_path = project_root / "outputs" / "tables" / "ev_sales_valuation.csv"
    dcf_path = project_root / "outputs" / "tables" / "dcf_valuation.csv"
    final_table_path = project_root / "outputs" / "tables" / "final_valuation_summary.csv"
    summary_path = project_root / "outputs" / "text" / "final_valuation_summary.md"

    final_table_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    ev_sales = load_csv(ev_sales_path)
    dcf = load_csv(dcf_path)
    final_table = build_final_table(ev_sales, dcf)

    final_table.to_csv(final_table_path, index=False)
    write_summary(
        summary_path=summary_path,
        ev_sales_path=ev_sales_path,
        dcf_path=dcf_path,
        final_table=final_table,
        ev_sales=ev_sales,
        dcf=dcf,
        project_root=project_root,
    )

    print(f"Saved final valuation table to: {final_table_path}")
    print(f"Saved final valuation summary to: {summary_path}")
    print("")
    print(final_table.to_string(index=False))


if __name__ == "__main__":
    main()
