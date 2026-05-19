from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


METRIC_COLUMNS = [
    "fiscal_year",
    "revenue",
    "gross_profit",
    "r_and_d",
    "sga",
    "operating_income",
    "net_income",
    "cash_and_equivalents",
    "marketable_securities",
    "total_debt",
    "operating_cash_flow",
    "capex",
    "free_cash_flow",
    "shares_outstanding",
]

FINANCIAL_VALUE_COLUMNS = [
    column
    for column in METRIC_COLUMNS
    if column not in {"fiscal_year", "shares_outstanding"}
]

USD_MILLIONS_DIVISOR = 1_000_000

CAPEX_SOURCE_LINES = [
    "Purchase of property and equipment",
    "Purchase of software",
    "Expenditures for internal-use software",
]

DEBT_METHODOLOGY_NOTE = (
    "`total_debt` includes only financial debt items identified on the balance sheet, "
    "such as loans payable, notes/promissory notes payable, short-term debt, long-term debt, "
    "convertible debt, and finance lease liabilities if available. It excludes total liabilities, "
    "accounts payable, accrued expenses, deferred revenue, warrant liabilities, and operating lease liabilities."
)


@dataclass(frozen=True)
class Observation:
    value: float
    source_file: str
    sheet_name: str
    source_label: str
    source_priority: int


def find_project_root(start: Path) -> Path:
    """Find the project root from either the repo root or notebooks folder."""
    start = start.resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "data" / "raw").exists():
            return candidate
    raise FileNotFoundError("Could not find data/raw from the current path.")


def normalize_label(value: object) -> str:
    text = str(value).lower()
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fiscal_year_from_column(column: object) -> int | None:
    match = re.search(r"31/12/(\d{4})", str(column))
    if match:
        return int(match.group(1))
    return None


def workbook_priority(path: Path) -> int:
    match = re.search(r"(\d{4})", path.stem)
    if match:
        return int(match.group(1))
    return 0


def add_observation(
    observations: dict[tuple[int, str], list[Observation]],
    fiscal_year: int,
    metric: str,
    value: object,
    source_file: str,
    sheet_name: str,
    source_label: str,
    source_priority: int,
) -> None:
    numeric_value = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric_value):
        return
    observations[(fiscal_year, metric)].append(
        Observation(
            value=float(numeric_value),
            source_file=source_file,
            sheet_name=sheet_name,
            source_label=source_label,
            source_priority=source_priority,
        )
    )


def add_sheet_observations(
    observations: dict[tuple[int, str], list[Observation]],
    workbook_path: Path,
    sheet_name: str,
    sheet: pd.DataFrame,
) -> None:
    if sheet.empty or "Account Name" not in sheet.columns:
        return

    source_priority = workbook_priority(workbook_path)
    year_columns = {
        column: fiscal_year_from_column(column)
        for column in sheet.columns
        if fiscal_year_from_column(column) is not None
    }
    if not year_columns:
        return

    normalized_sheet_name = normalize_label(sheet_name)
    is_balance_sheet_parenthetical = (
        "balance sheets pa" in normalized_sheet_name
        or "balance sheet pa" in normalized_sheet_name
    )

    for _, row in sheet.iterrows():
        source_label = row["Account Name"]
        label = normalize_label(source_label)
        if not label or label == "-":
            continue

        metrics: list[str] = []
        sign = 1.0

        if "statements of oper" in normalized_sheet_name:
            if label == "revenue":
                metrics.append("revenue")
            elif label == "total gross profit":
                metrics.append("gross_profit")
            elif label == "research and development":
                metrics.append("r_and_d")
            elif label in {"general and administrative", "sales and marketing"}:
                metrics.append(f"component:{label}")
            elif label == "loss from operations":
                metrics.append("operating_income")
            elif label == "net loss":
                metrics.append("net_income")

        elif "balance sheets" in normalized_sheet_name:
            if label in {"cash", "cash and cash equivalents"}:
                metrics.append("cash_and_equivalents")
            elif label == "marketable investment securities":
                metrics.append("marketable_securities")
            elif not is_balance_sheet_parenthetical and label.startswith("loans payable net current"):
                metrics.append("component:debt")
            elif not is_balance_sheet_parenthetical and label.startswith("loans payable net noncurrent"):
                metrics.append("component:debt")
            elif not is_balance_sheet_parenthetical and label.startswith("loans payable net non current"):
                metrics.append("component:debt")
            elif not is_balance_sheet_parenthetical and label == "promissory notes related party":
                metrics.append("component:debt")
            elif label == "common stock outstanding in shares":
                metrics.append("shares_outstanding")

        elif "statements of cash" in normalized_sheet_name:
            if label == "net cash used in operating activities":
                metrics.append("operating_cash_flow")
            elif label in {
                "purchase of property and equipment",
                "purchase of software",
                "expenditures for internal use software",
            }:
                metrics.append("component:capex")
                sign = 1.0

        for metric in metrics:
            for column, fiscal_year in year_columns.items():
                numeric_value = pd.to_numeric(row[column], errors="coerce")
                if pd.isna(numeric_value):
                    continue
                add_observation(
                    observations,
                    fiscal_year,
                    metric,
                    numeric_value * sign,
                    workbook_path.name,
                    sheet_name,
                    str(source_label),
                    source_priority,
                )


def choose_latest_observation(observations: list[Observation]) -> Observation | None:
    if not observations:
        return None
    return sorted(observations, key=lambda item: item.source_priority, reverse=True)[0]


def combine_latest_components(observations: list[Observation]) -> tuple[float | None, list[Observation]]:
    if not observations:
        return None, []

    by_source: dict[tuple[str, str, int], list[Observation]] = defaultdict(list)
    for observation in observations:
        key = (observation.source_file, observation.sheet_name, observation.source_priority)
        by_source[key].append(observation)

    latest_key = sorted(by_source, key=lambda key: key[2], reverse=True)[0]
    latest_observations = by_source[latest_key]
    value = sum(observation.value for observation in latest_observations)
    return value, latest_observations


def combine_latest_capex_components(observations: list[Observation]) -> tuple[float | None, float | None, list[Observation]]:
    if not observations:
        return None, None, []

    by_source: dict[tuple[str, str, int], list[Observation]] = defaultdict(list)
    for observation in observations:
        key = (observation.source_file, observation.sheet_name, observation.source_priority)
        by_source[key].append(observation)

    latest_key = sorted(by_source, key=lambda key: key[2], reverse=True)[0]
    latest_observations = by_source[latest_key]
    original_value = sum(observation.value for observation in latest_observations)
    cleaned_value = sum(abs(observation.value) for observation in latest_observations)
    return original_value, cleaned_value, latest_observations


def format_value(value: float | None) -> str:
    if value is None or pd.isna(value):
        return ""
    if float(value).is_integer():
        return str(int(value))
    return str(value)


def scale_financial_values_to_usd_millions(clean_df: pd.DataFrame) -> pd.DataFrame:
    scaled_df = clean_df.copy()
    for column in FINANCIAL_VALUE_COLUMNS:
        scaled_df[column] = scaled_df[column] / USD_MILLIONS_DIVISOR
    return scaled_df


def format_observation_value(metric: str, value: float) -> str:
    if metric == "shares_outstanding":
        display_value = value
    else:
        display_value = value / USD_MILLIONS_DIVISOR

    if float(display_value).is_integer():
        return str(int(display_value))
    return f"{display_value:.6g}"


def to_usd_millions(value: float | None) -> float | None:
    if value is None or pd.isna(value):
        return None
    return value / USD_MILLIONS_DIVISOR


def format_debt_line_items(debt_sources: list[Observation]) -> str:
    if not debt_sources:
        return ""
    return "; ".join(
        f"{str(source.source_label).encode('ascii', 'replace').decode()} "
        f"({format_observation_value('total_debt', source.value)})"
        for source in debt_sources
    )


def create_log(
    log_path: Path,
    files: list[Path],
    clean_df: pd.DataFrame,
    selected_sources: dict[tuple[int, str], list[Observation]],
    raw_observations: dict[tuple[int, str], list[Observation]],
    capex_reconciliation: pd.DataFrame,
    debt_reconciliation: pd.DataFrame,
) -> None:
    lines: list[str] = []
    lines.append("# D-Wave 10-K Cleaning Log")
    lines.append("")
    lines.append("## Raw Files Read")
    for path in files:
        lines.append(f"- `{path.name}` ({path.stat().st_size:,} bytes)")

    lines.append("")
    lines.append("## Output")
    lines.append("- `data/processed/dwave_financials_clean.csv`")
    lines.append("- Units: USD millions for all financial statement values.")
    lines.append("- `shares_outstanding` remains actual shares, not millions.")

    lines.append("")
    lines.append("## Definitions")
    lines.append("- `sga` = `General and administrative` + `Sales and marketing`, when both are available in the selected filing.")
    lines.append("- `capex` = `Purchase of property and equipment` + software/internal-use software purchases, when available.")
    lines.append("- Original capex cash flow lines used: " + "; ".join(f"`{line}`" for line in CAPEX_SOURCE_LINES) + ".")
    lines.append("- Capex sign convention: source cash outflow values are preserved in `original_capex_value`; cleaned `capex` is reported as a positive cash outflow. If a source capex value is negative, the cleaned output uses its absolute value.")
    lines.append("- `free_cash_flow` = `operating_cash_flow` - `capex`, only when both fields are available.")
    lines.append(f"- Debt methodology: {DEBT_METHODOLOGY_NOTE}")
    lines.append("- If both current and non-current financial debt exist, they are summed.")
    lines.append("- `net_cash` in the debt reconciliation equals cash and equivalents plus marketable securities minus total debt, only when all three values are available.")
    lines.append("- Duplicate fiscal years are resolved by using the newest workbook year.")
    lines.append("- Duplicate/conflict values shown below are also in USD millions, except share counts.")

    lines.append("")
    lines.append("## Capex Reconciliation")
    lines.append("")
    lines.append("```text")
    lines.append(capex_reconciliation.to_string(index=False, na_rep="NA"))
    lines.append("```")

    lines.append("")
    lines.append("## Debt Reconciliation")
    lines.append("")
    lines.append("- Saved to `outputs/tables/debt_reconciliation.csv`.")
    lines.append("")
    lines.append("```text")
    lines.append(debt_reconciliation.to_string(index=False, na_rep="NA"))
    lines.append("```")

    lines.append("")
    lines.append("## Selected Sources")
    for fiscal_year in clean_df["fiscal_year"].tolist():
        lines.append(f"### Fiscal {fiscal_year}")
        for metric in METRIC_COLUMNS[1:]:
            selected = selected_sources.get((fiscal_year, metric), [])
            if not selected:
                lines.append(f"- `{metric}`: missing")
                continue
            source_parts = [
                f"`{obs.source_file}` / `{obs.sheet_name}` / `{obs.source_label}`"
                for obs in selected
            ]
            lines.append(f"- `{metric}`: " + "; ".join(source_parts))

    lines.append("")
    lines.append("## Duplicate Or Conflicting Observations")
    duplicate_found = False
    for (fiscal_year, metric), observations in sorted(raw_observations.items()):
        if len(observations) <= 1:
            continue
        duplicate_found = True
        values = sorted({format_observation_value(metric, observation.value) for observation in observations})
        lines.append(f"- Fiscal {fiscal_year}, `{metric}`: {len(observations)} observations, values={values}")
        for observation in sorted(observations, key=lambda item: item.source_priority, reverse=True):
            lines.append(
                f"  - `{observation.source_file}` / `{observation.sheet_name}` / "
                f"`{observation.source_label}` = {format_observation_value(metric, observation.value)}"
            )
    if not duplicate_found:
        lines.append("- None found.")

    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    project_root = find_project_root(Path.cwd())
    raw_dir = project_root / "data" / "raw"
    filings_dir = raw_dir / "filings"
    output_path = project_root / "data" / "processed" / "dwave_financials_clean.csv"
    debt_reconciliation_path = project_root / "outputs" / "tables" / "debt_reconciliation.csv"
    log_path = project_root / "outputs" / "text" / "cleaning_log.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    debt_reconciliation_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    files = sorted(
        path
        for path in filings_dir.glob("dwave_10k_*.xlsx")
        if path.is_file() and path.stat().st_size > 0
    )
    if not files:
        raise FileNotFoundError("No non-empty D-Wave 10-K Excel files found in data/raw/filings.")

    observations: dict[tuple[int, str], list[Observation]] = defaultdict(list)

    for workbook_path in files:
        workbook = pd.ExcelFile(workbook_path)
        for sheet_name in workbook.sheet_names:
            sheet = pd.read_excel(workbook, sheet_name=sheet_name)
            add_sheet_observations(observations, workbook_path, sheet_name, sheet)

    fiscal_years = sorted({fiscal_year for fiscal_year, _ in observations.keys()})
    records: list[dict[str, float | int | None]] = []
    selected_sources: dict[tuple[int, str], list[Observation]] = {}
    capex_reconciliation_records: list[dict[str, float | int | None]] = []
    debt_reconciliation_records: list[dict[str, float | int | str | None]] = []

    for fiscal_year in fiscal_years:
        record: dict[str, float | int | None] = {"fiscal_year": fiscal_year}

        for metric in [
            "revenue",
            "gross_profit",
            "r_and_d",
            "operating_income",
            "net_income",
            "cash_and_equivalents",
            "marketable_securities",
            "operating_cash_flow",
            "shares_outstanding",
        ]:
            selected = choose_latest_observation(observations.get((fiscal_year, metric), []))
            record[metric] = selected.value if selected else None
            if selected:
                selected_sources[(fiscal_year, metric)] = [selected]

        sga_value, sga_sources = combine_latest_components(
            observations.get((fiscal_year, "component:general and administrative"), [])
            + observations.get((fiscal_year, "component:sales and marketing"), [])
        )
        record["sga"] = sga_value
        if sga_sources:
            selected_sources[(fiscal_year, "sga")] = sga_sources

        total_debt, debt_sources = combine_latest_components(observations.get((fiscal_year, "component:debt"), []))
        record["total_debt"] = total_debt
        if debt_sources:
            selected_sources[(fiscal_year, "total_debt")] = debt_sources

        original_capex_value, capex, capex_sources = combine_latest_capex_components(
            observations.get((fiscal_year, "component:capex"), [])
        )
        record["capex"] = capex
        if capex_sources:
            selected_sources[(fiscal_year, "capex")] = capex_sources

        if record.get("operating_cash_flow") is not None and record.get("capex") is not None:
            record["free_cash_flow"] = record["operating_cash_flow"] - record["capex"]
        else:
            record["free_cash_flow"] = None

        if record["free_cash_flow"] is not None:
            selected_sources[(fiscal_year, "free_cash_flow")] = (
                selected_sources.get((fiscal_year, "operating_cash_flow"), [])
                + selected_sources.get((fiscal_year, "capex"), [])
            )

        cash = record.get("cash_and_equivalents")
        marketable_securities = record.get("marketable_securities")
        if cash is not None and marketable_securities is not None and total_debt is not None:
            net_cash = cash + marketable_securities - total_debt
        else:
            net_cash = None

        debt_reconciliation_records.append(
            {
                "fiscal_year": fiscal_year,
                "original_debt_line_items": format_debt_line_items(debt_sources),
                "cleaned_total_debt": to_usd_millions(total_debt),
                "cash_and_equivalents": to_usd_millions(cash),
                "marketable_securities": to_usd_millions(marketable_securities),
                "net_cash": to_usd_millions(net_cash),
            }
        )

        capex_reconciliation_records.append(
            {
                "fiscal_year": fiscal_year,
                "original_capex_value": original_capex_value,
                "cleaned_capex": record.get("capex"),
                "operating_cash_flow": record.get("operating_cash_flow"),
                "free_cash_flow": record.get("free_cash_flow"),
            }
        )

        records.append(record)

    clean_df = pd.DataFrame(records, columns=METRIC_COLUMNS)
    clean_df = clean_df.sort_values("fiscal_year").reset_index(drop=True)
    clean_df = scale_financial_values_to_usd_millions(clean_df)
    capex_reconciliation = pd.DataFrame(capex_reconciliation_records)
    for column in ["original_capex_value", "cleaned_capex", "operating_cash_flow", "free_cash_flow"]:
        capex_reconciliation[column] = capex_reconciliation[column] / USD_MILLIONS_DIVISOR
    debt_reconciliation = pd.DataFrame(debt_reconciliation_records)
    clean_df.to_csv(output_path, index=False, na_rep="NA")
    debt_reconciliation.to_csv(debt_reconciliation_path, index=False, na_rep="NA")

    create_log(log_path, files, clean_df, selected_sources, observations, capex_reconciliation, debt_reconciliation)

    print(f"Saved cleaned financials to: {output_path}")
    print(f"Saved debt reconciliation to: {debt_reconciliation_path}")
    print(f"Saved cleaning log to: {log_path}")
    display_df = clean_df.map(format_value) if hasattr(clean_df, "map") else clean_df.applymap(format_value)
    print(display_df.to_string(index=False))
    print("\nCapex reconciliation (USD millions):")
    print(capex_reconciliation.to_string(index=False, na_rep="NA"))
    print("\nDebt reconciliation (USD millions except original_debt_line_items):")
    print(debt_reconciliation.to_string(index=False, na_rep="NA"))


if __name__ == "__main__":
    main()
