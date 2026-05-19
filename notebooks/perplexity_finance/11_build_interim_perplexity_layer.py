from __future__ import annotations

import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from notebooks.utils.inspection_workbooks import (  # noqa: E402
    CsvSheetSpec,
    InspectionWorkbookConfig,
    build_inspection_workbook_from_csvs,
)


MANIFEST_RELATIVE_PATH = Path("data/raw/perplexity/2026-05-15_batch01/manifest.csv")
INTERIM_DIR_RELATIVE_PATH = Path("data/interim/perplexity")
SUMMARY_RELATIVE_PATH = Path("outputs/text/perplexity_finance/qbts_interim_perplexity_build_summary.md")
INSPECTION_DIR_RELATIVE_PATH = Path("outputs/inspection")
INSPECTION_WORKBOOK_RELATIVE_PATH = INSPECTION_DIR_RELATIVE_PATH / "qbts_interim_perplexity_inspection.xlsx"
INSPECTION_GUIDE_RELATIVE_PATH = Path("outputs/text/inspection_guide.md")
FORMATTING_CHECK_RELATIVE_PATH = Path("outputs/text/interim_formatting_check.md")

INSPECTION_SHEETS = [
    ("line_item_mapping", "qbts_line_item_mapping.csv"),
    ("annual_long_standardized", "qbts_annual_long_standardized.csv"),
    ("quarterly_long_standardized", "qbts_quarterly_long_standardized.csv"),
    ("annual_wide_standardized", "qbts_annual_wide_standardized.csv"),
    ("quarterly_wide_standardized", "qbts_quarterly_wide_standardized.csv"),
]

MAPPING_COLUMNS = [
    "original_line_item",
    "canonical_metric",
    "statement_or_tab",
    "category",
    "use_in_core_financials",
    "notes",
]

ANNUAL_LONG_COLUMNS = [
    "fiscal_year",
    "period",
    "period_type",
    "statement_or_tab",
    "original_line_item",
    "canonical_metric",
    "value_usd_millions",
    "unit_scale",
    "source_file",
    "source_platform",
    "retrieval_date",
    "notes",
]

QUARTERLY_LONG_COLUMNS = [
    "fiscal_year",
    "fiscal_quarter",
    "period",
    "period_type",
    "statement_or_tab",
    "original_line_item",
    "canonical_metric",
    "value_usd_millions",
    "unit_scale",
    "source_file",
    "source_platform",
    "retrieval_date",
    "notes",
]

CORE_GAAP_TABS = {"Income Statement", "Balance Sheet", "Cash Flow"}

TAB_CATEGORY = {
    "Income Statement": "gaap_income_statement",
    "Balance Sheet": "gaap_balance_sheet",
    "Cash Flow": "gaap_cash_flow",
    "Adjusted": "adjusted_non_gaap",
    "Ratios": "ratio_or_market_metric",
    "Key Stats": "contextual_market_metric",
    "Segments & KPIs": "segment_or_operating_kpi",
}

SECTION_HEADERS = {
    "Assets",
    "Liabilities",
    "Equity",
    "Operating Activities",
    "Investing Activities",
    "Financing Activities",
    "Margins",
    "Valuation",
    "Trailing Valuation",
    "Other",
    "Capital Efficiency",
    "Financial Health",
    "Per Share",
    "Common Size",
    "Growth",
    "Revenue by Geography",
    "Key Performance Indicators",
}

CORE_USD_METRICS = {
    "revenue",
    "cost_of_revenue",
    "gross_profit",
    "r_and_d",
    "sga",
    "operating_income",
    "depreciation_and_amortization",
    "interest_income",
    "interest_expense",
    "pretax_income",
    "tax_expense",
    "net_income",
    "cash_and_equivalents",
    "marketable_securities",
    "total_current_assets",
    "total_assets",
    "accounts_payable",
    "accrued_expenses",
    "deferred_revenue",
    "short_term_debt",
    "long_term_debt",
    "total_current_liabilities",
    "total_liabilities",
    "stockholders_equity",
    "operating_cash_flow",
    "capex",
    "stock_based_compensation",
}

NON_USD_CANONICAL_METRICS = {
    "eps_basic",
    "eps_diluted",
    "shares_outstanding",
    "weighted_average_basic_shares",
    "weighted_average_diluted_shares",
}

RAW_TO_CANONICAL_BY_TAB = {
    "Income Statement": {
        "Total Revenues": "revenue",
        "Cost of Sales": "cost_of_revenue",
        "Gross Profit": "gross_profit",
        "Selling, General & Administrative Expenses": "sga",
        "Research & Development Expenses": "r_and_d",
        "Operating Profit": "operating_income",
        "Interest and Investment Income": "interest_income",
        "Interest Expense": "interest_expense",
        "Income Before Provision for Income Taxes": "pretax_income",
        "Provision for Income Taxes": "tax_expense",
        "Consolidated Net Income": "net_income",
        "Basic EPS": "eps_basic",
        "Diluted EPS": "eps_diluted",
        "Basic Weighted Average Shares Outstanding": "weighted_average_basic_shares",
        "Diluted Weighted Average Shares Outstanding": "weighted_average_diluted_shares",
    },
    "Balance Sheet": {
        "Cash and Cash Equivalents": "cash_and_equivalents",
        "Short-Term Investments": "marketable_securities",
        "Total Current Assets": "total_current_assets",
        "Total Assets": "total_assets",
        "Accounts Payable": "accounts_payable",
        "Accrued Expenses": "accrued_expenses",
        "Short-Term Debt": "short_term_debt",
        "Unearned Revenue": "deferred_revenue",
        "Total Current Liabilities": "total_current_liabilities",
        "Long-Term Debt": "long_term_debt",
        "Total Liabilities": "total_liabilities",
        "Total Shareholders' Equity": "stockholders_equity",
    },
    "Cash Flow": {
        "Net Income": "net_income",
        "Depreciation & Amortization": "depreciation_and_amortization",
        "Share-Based Compensation Expense": "stock_based_compensation",
        "Cash from Operating Activities": "operating_cash_flow",
        "Capital Expenditure": "capex",
    },
    "Adjusted": {
        "Adjusted Revenue": "revenue",
        "Adjusted Gross Profit": "gross_profit",
        "Adjusted EBITDA": "ebitda",
        "Adjusted Net Income": "net_income",
        "Adjusted Free Cash Flow (FCF)": "free_cash_flow",
        "Adjusted Capital Expenditures": "capex",
    },
    "Key Stats": {
        "Revenue": "revenue",
        "Gross Profit": "gross_profit",
        "EBITDA": "ebitda",
        "Net Income": "net_income",
        "Diluted EPS": "eps_diluted",
        "Operating Cash Flow": "operating_cash_flow",
        "CapEx": "capex",
        "Free Cash Flow": "free_cash_flow",
    },
    "Ratios": {
        "Total Shares Outstanding": "shares_outstanding",
        "Free Cash Flow": "free_cash_flow",
        "EBITDA": "ebitda",
        "Total Debt": "total_debt",
        "Basic EPS": "eps_basic",
        "Diluted EPS": "eps_diluted",
        "Weighted Avg. Shares Outstanding": "weighted_average_basic_shares",
        "Weighted Avg. Shares Outstanding Diluted": "weighted_average_diluted_shares",
    },
    "Segments & KPIs": {
        "Revenue": "revenue",
    },
}

PREFERRED_CORE_SOURCE_BY_METRIC = {
    "net_income": ("Income Statement", "Consolidated Net Income"),
}


@dataclass(frozen=True)
class MappingDecision:
    canonical_metric: str
    category: str
    use_in_core_financials: bool
    notes: str


def find_project_root(start: Path) -> Path:
    start = start.resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "data" / "raw" / "perplexity").exists():
            return candidate
    raise FileNotFoundError("Could not find the project root containing data/raw/perplexity.")


def normalize_original_line_item(value: object) -> str:
    return str(value).strip()


def is_missing_raw_value(value: object) -> bool:
    if pd.isna(value):
        return True
    text = str(value).strip()
    return text in {"", "-", "—"}


def parse_numeric_value(value: object) -> float | None:
    if is_missing_raw_value(value):
        return None

    text = str(value).strip()
    text = text.replace("$", "").replace(",", "").replace("%", "")
    text = text.replace("(", "-").replace(")", "")
    text = text.replace("−", "-")
    try:
        return float(text)
    except ValueError:
        return None


def convert_to_usd_millions(value: float, unit_scale: str) -> tuple[float, str]:
    if unit_scale == "usd_millions":
        return value, "No conversion; source already exported in USD millions."
    if unit_scale == "usd_thousands":
        return value / 1_000, "Converted from USD thousands to USD millions."
    if unit_scale == "usd":
        return value / 1_000_000, "Converted from raw USD to USD millions."
    if unit_scale == "usd_billions":
        return value * 1_000, "Converted from USD billions to USD millions."
    return value, f"No conversion applied; unrecognized unit_scale `{unit_scale}`."


def date_column_to_period(date_text: str, period_type: str) -> tuple[int, int | None, str]:
    period_end = pd.to_datetime(date_text)
    fiscal_year = int(period_end.year)
    if period_type == "annual":
        return fiscal_year, None, str(fiscal_year)
    fiscal_quarter = int(((period_end.month - 1) // 3) + 1)
    return fiscal_year, fiscal_quarter, f"{fiscal_year}Q{fiscal_quarter}"


def build_mapping_decision(statement_or_tab: str, original_line_item: str) -> MappingDecision:
    category = TAB_CATEGORY.get(statement_or_tab, "unknown")
    canonical_metric = RAW_TO_CANONICAL_BY_TAB.get(statement_or_tab, {}).get(
        original_line_item,
        "UNMAPPED",
    )

    if original_line_item in SECTION_HEADERS:
        return MappingDecision(
            canonical_metric="UNMAPPED",
            category=category,
            use_in_core_financials=False,
            notes="Section header or grouping row; retained in mapping, not a standardized metric.",
        )

    if canonical_metric == "UNMAPPED":
        return MappingDecision(
            canonical_metric="UNMAPPED",
            category=category,
            use_in_core_financials=False,
            notes="No confident mapping to the requested canonical metric set.",
        )

    if statement_or_tab not in CORE_GAAP_TABS:
        return MappingDecision(
            canonical_metric=canonical_metric,
            category=category,
            use_in_core_financials=False,
            notes="Mapped for reference, but excluded from the core GAAP layer because it comes from a non-core tab.",
        )

    if canonical_metric in NON_USD_CANONICAL_METRICS:
        return MappingDecision(
            canonical_metric=canonical_metric,
            category=category,
            use_in_core_financials=False,
            notes="Mapped but excluded from the core USD-millions layer because the metric is not USD-denominated.",
        )

    preferred_source = PREFERRED_CORE_SOURCE_BY_METRIC.get(canonical_metric)
    if preferred_source and preferred_source != (statement_or_tab, original_line_item):
        return MappingDecision(
            canonical_metric=canonical_metric,
            category=category,
            use_in_core_financials=False,
            notes=(
                "Mapped but excluded from the core layer because another GAAP source line "
                "is preferred for this canonical metric."
            ),
        )

    if canonical_metric in CORE_USD_METRICS:
        return MappingDecision(
            canonical_metric=canonical_metric,
            category=category,
            use_in_core_financials=True,
            notes="Core GAAP USD-denominated financial-statement metric.",
        )

    return MappingDecision(
        canonical_metric=canonical_metric,
        category=category,
        use_in_core_financials=False,
        notes="Mapped, but not yet eligible for the core USD-millions layer.",
    )


def build_mapping_table(manifest: pd.DataFrame, batch_dir: Path) -> pd.DataFrame:
    mapping_rows: dict[tuple[str, str], dict[str, object]] = {}

    for _, manifest_row in manifest.iterrows():
        path = batch_dir / manifest_row["file_name"]
        raw_df = pd.read_csv(path)
        statement_or_tab = manifest_row["data_tab"]

        for original_line_item in raw_df.iloc[:, 0].dropna():
            original_line_item = normalize_original_line_item(original_line_item)
            key = (statement_or_tab, original_line_item)
            if key in mapping_rows:
                continue
            decision = build_mapping_decision(statement_or_tab, original_line_item)
            mapping_rows[key] = {
                "original_line_item": original_line_item,
                "canonical_metric": decision.canonical_metric,
                "statement_or_tab": statement_or_tab,
                "category": decision.category,
                "use_in_core_financials": decision.use_in_core_financials,
                "notes": decision.notes,
            }

    mapping_df = pd.DataFrame(mapping_rows.values(), columns=MAPPING_COLUMNS)
    return mapping_df.sort_values(["statement_or_tab", "original_line_item"]).reset_index(drop=True)


def build_long_tables(
    manifest: pd.DataFrame,
    batch_dir: Path,
    mapping_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, set[str]], dict[str, set[str]], dict[str, int]]:
    mapping_lookup = {
        (row.statement_or_tab, row.original_line_item): row
        for row in mapping_df.itertuples(index=False)
    }

    annual_rows: list[dict[str, object]] = []
    quarterly_rows: list[dict[str, object]] = []
    annual_coverage: dict[str, set[str]] = defaultdict(set)
    quarterly_coverage: dict[str, set[str]] = defaultdict(set)
    conversion_counts: dict[str, int] = defaultdict(int)

    for _, manifest_row in manifest.iterrows():
        path = batch_dir / manifest_row["file_name"]
        raw_df = pd.read_csv(path)
        statement_or_tab = manifest_row["data_tab"]
        period_type = manifest_row["period"]
        retrieval_date = str(manifest_row["retrieved_at"])[:10]
        source_file = manifest_row["file_name"]
        source_platform = manifest_row["source_platform"]
        unit_scale = manifest_row["unit_scale"]

        date_columns = [column for column in raw_df.columns[1:] if re.match(r"\d{1,2}/\d{1,2}/\d{4}", str(column))]

        for date_column in date_columns:
            fiscal_year, fiscal_quarter, period = date_column_to_period(date_column, period_type)
            if period_type == "annual":
                annual_coverage[statement_or_tab].add(period)
            else:
                quarterly_coverage[statement_or_tab].add(period)

        for _, raw_row in raw_df.iterrows():
            original_line_item = normalize_original_line_item(raw_row.iloc[0])
            mapping_row = mapping_lookup[(statement_or_tab, original_line_item)]

            for date_column in date_columns:
                parsed_value = parse_numeric_value(raw_row[date_column])
                if parsed_value is None:
                    continue

                standardized_value, conversion_note = convert_to_usd_millions(parsed_value, unit_scale)
                conversion_counts[conversion_note] += 1

                if mapping_row.canonical_metric == "capex":
                    standardized_value = abs(standardized_value)

                fiscal_year, fiscal_quarter, period = date_column_to_period(date_column, period_type)
                row_notes = mapping_row.notes
                if (
                    mapping_row.canonical_metric in NON_USD_CANONICAL_METRICS
                    or "%" in str(raw_row[date_column])
                    or statement_or_tab in {"Ratios", "Adjusted", "Segments & KPIs", "Key Stats"}
                ):
                    row_notes = (
                        f"{row_notes} "
                        "Retained as a source-display numeric value; review unit semantics before final processing."
                    ).strip()

                base_row = {
                    "fiscal_year": fiscal_year,
                    "period": period,
                    "period_type": period_type,
                    "statement_or_tab": statement_or_tab,
                    "original_line_item": original_line_item,
                    "canonical_metric": mapping_row.canonical_metric,
                    "value_usd_millions": standardized_value,
                    "unit_scale": unit_scale,
                    "source_file": source_file,
                    "source_platform": source_platform,
                    "retrieval_date": retrieval_date,
                    "notes": row_notes,
                }

                if period_type == "annual":
                    annual_rows.append(base_row)
                else:
                    quarterly_rows.append(
                        {
                            "fiscal_year": fiscal_year,
                            "fiscal_quarter": fiscal_quarter,
                            "period": period,
                            "period_type": period_type,
                            "statement_or_tab": statement_or_tab,
                            "original_line_item": original_line_item,
                            "canonical_metric": mapping_row.canonical_metric,
                            "value_usd_millions": standardized_value,
                            "unit_scale": unit_scale,
                            "source_file": source_file,
                            "source_platform": source_platform,
                            "retrieval_date": retrieval_date,
                            "notes": row_notes,
                        }
                    )

    annual_long_df = pd.DataFrame(annual_rows, columns=ANNUAL_LONG_COLUMNS)
    quarterly_long_df = pd.DataFrame(quarterly_rows, columns=QUARTERLY_LONG_COLUMNS)

    if not annual_long_df.empty:
        annual_long_df["fiscal_year"] = annual_long_df["fiscal_year"].astype("int64")
        annual_long_df["period"] = annual_long_df["period"].astype("string")
        annual_long_df = annual_long_df.sort_values(
            ["fiscal_year", "statement_or_tab", "canonical_metric", "original_line_item"]
        ).reset_index(drop=True)
    if not quarterly_long_df.empty:
        quarterly_long_df["fiscal_year"] = quarterly_long_df["fiscal_year"].astype("int64")
        quarterly_long_df["fiscal_quarter"] = quarterly_long_df["fiscal_quarter"].astype("int64")
        quarterly_long_df["period"] = quarterly_long_df["period"].astype("string")
        quarterly_long_df = quarterly_long_df.sort_values(
            ["fiscal_year", "fiscal_quarter", "statement_or_tab", "canonical_metric", "original_line_item"]
        ).reset_index(drop=True)

    return annual_long_df, quarterly_long_df, annual_coverage, quarterly_coverage, conversion_counts


def build_wide_table(long_df: pd.DataFrame, mapping_df: pd.DataFrame, period_type: str) -> pd.DataFrame:
    core_mapping_df = mapping_df[mapping_df["use_in_core_financials"] == True].copy()  # noqa: E712
    core_metrics = core_mapping_df["canonical_metric"].drop_duplicates()

    core_df = long_df.merge(
        core_mapping_df[
            [
                "statement_or_tab",
                "original_line_item",
                "canonical_metric",
            ]
        ],
        on=["statement_or_tab", "original_line_item", "canonical_metric"],
        how="inner",
    )
    if core_df.empty:
        if period_type == "annual":
            return pd.DataFrame(columns=["fiscal_year"])
        return pd.DataFrame(columns=["fiscal_year", "fiscal_quarter", "period"])

    if period_type == "annual":
        index_columns = ["fiscal_year"]
    else:
        index_columns = ["fiscal_year", "fiscal_quarter", "period"]

    duplicate_check = (
        core_df.groupby(index_columns + ["canonical_metric"], dropna=False)
        .size()
        .reset_index(name="row_count")
    )
    duplicates = duplicate_check[duplicate_check["row_count"] > 1]
    if not duplicates.empty:
        raise ValueError(
            "Duplicate core metric observations found while building the wide table:\n"
            + duplicates.to_string(index=False)
        )

    wide_df = (
        core_df.pivot(index=index_columns, columns="canonical_metric", values="value_usd_millions")
        .reset_index()
        .sort_values(index_columns)
    )
    wide_df.columns.name = None
    ordered_metric_columns = [metric for metric in core_metrics if metric in wide_df.columns]
    wide_df = wide_df[index_columns + ordered_metric_columns]
    wide_df["fiscal_year"] = wide_df["fiscal_year"].astype("int64")
    if "fiscal_quarter" in wide_df.columns:
        wide_df["fiscal_quarter"] = wide_df["fiscal_quarter"].astype("int64")
    if "period" in wide_df.columns:
        wide_df["period"] = wide_df["period"].astype("string")
    return wide_df


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_None._"
    text_df = df.fillna("").astype(str)
    headers = list(text_df.columns)
    rows = text_df.values.tolist()
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def format_coverage_table(coverage: dict[str, set[str]]) -> pd.DataFrame:
    rows = []
    for tab, periods in sorted(coverage.items()):
        ordered_periods = sorted(periods, key=lambda value: (int(value[:4]), value))
        rows.append(
            {
                "statement_or_tab": tab,
                "first_period": ordered_periods[0],
                "last_period": ordered_periods[-1],
                "period_count": len(ordered_periods),
            }
        )
    return pd.DataFrame(rows)


def build_summary(
    manifest: pd.DataFrame,
    mapping_df: pd.DataFrame,
    annual_long_df: pd.DataFrame,
    quarterly_long_df: pd.DataFrame,
    annual_coverage: dict[str, set[str]],
    quarterly_coverage: dict[str, set[str]],
    conversion_counts: dict[str, int],
) -> str:
    files_read_df = manifest[["file_name", "data_tab", "period", "period_covered", "unit_scale"]].copy()
    annual_coverage_df = format_coverage_table(annual_coverage)
    quarterly_coverage_df = format_coverage_table(quarterly_coverage)

    mapped_metrics = sorted(
        metric for metric in mapping_df["canonical_metric"].drop_duplicates() if metric != "UNMAPPED"
    )
    unmapped_df = (
        mapping_df[mapping_df["canonical_metric"] == "UNMAPPED"]
        .groupby("statement_or_tab", as_index=False)
        .agg(unmapped_line_items=("original_line_item", lambda values: ", ".join(sorted(values))))
    )
    core_metrics = sorted(
        mapping_df.loc[
            mapping_df["use_in_core_financials"] == True,  # noqa: E712
            "canonical_metric",
        ].drop_duplicates()
    )
    conversion_df = pd.DataFrame(
        [{"unit_logic": key, "value_count": value} for key, value in conversion_counts.items()]
    ).sort_values("unit_logic")

    suspicious_points = [
        "Quarterly coverage differs across tabs; no assumption of a common starting quarter is safe.",
        "Annual adjusted metrics begin in 2021 rather than 2020.",
        "Quarterly cash-flow history begins in 2021Q4, later than several other quarterly tabs.",
        "Ratios, adjusted metrics, key stats, and segment/KPI tabs contain non-USD measures mixed with USD-denominated rows even though the export display scale is `usd_millions`.",
        "No raw GAAP statement line item explicitly provides free cash flow; it is therefore not recalculated in this interim build.",
        "No raw GAAP statement line item explicitly provides total debt; short-term and long-term debt remain separate at this stage.",
        "Capex is exported as a cash outflow in the cash-flow statements and is standardized to a positive number here.",
    ]

    lines = [
        "# QBTS interim Perplexity build summary",
        "",
        "## Purpose",
        "",
        "This run builds the **interim** Perplexity layer from the raw batch exports. It standardizes labels, periods, values, and provenance while deliberately stopping short of creating the final processed historical dataset.",
        "",
        "## Files read",
        "",
        markdown_table(files_read_df),
        "",
        "## Annual coverage by tab",
        "",
        markdown_table(annual_coverage_df),
        "",
        "## Quarterly coverage by tab",
        "",
        markdown_table(quarterly_coverage_df),
        "",
        "## Metrics mapped successfully",
        "",
        f"Mapped canonical metrics ({len(mapped_metrics)}): "
        + ", ".join(f"`{metric}`" for metric in mapped_metrics),
        "",
        "Core GAAP USD-denominated metrics admitted to the wide interim tables "
        f"({len(core_metrics)}): "
        + ", ".join(f"`{metric}`" for metric in core_metrics),
        "",
        "## Metrics left unmapped",
        "",
        markdown_table(unmapped_df),
        "",
        "## Unit logic and conversions",
        "",
        markdown_table(conversion_df),
        "",
        "- Currency symbols, commas, percent signs, and accounting-style parentheses are stripped during parsing.",
        "- All source files in the present batch are marked `usd_millions` in the manifest, so no scale conversion was required for USD-denominated statement values.",
        "- Non-USD rows such as EPS, share counts, margins, ratios, and operating KPIs are retained as source-display numeric values, but they are excluded from the core GAAP wide tables until a later unit-aware processing step.",
        "- `fiscal_year`, `fiscal_quarter`, and `period` are identifiers / period labels, not financial values. They are kept separate from USD-millions metric formatting in the inspection layer.",
        "",
        "## Missing or suspicious fields",
        "",
    ]
    lines.extend(f"- {item}" for item in suspicious_points)
    lines.extend(
        [
            "",
            "## Output counts",
            "",
            f"- Annual standardized rows: {len(annual_long_df):,}",
            f"- Quarterly standardized rows: {len(quarterly_long_df):,}",
            f"- Mapping rows: {len(mapping_df):,}",
            "",
            "## Why this is still interim",
            "",
            "This layer preserves and standardizes the raw exports, but it does **not** yet reconcile annual versus quarterly values, resolve all unmapped rows, derive free cash flow, combine financial debt into total debt, or choose the final canonical historical series for modeling. Those decisions belong in the validation and final processed-data stages, not in raw standardization.",
            "",
        ]
    )
    return "\n".join(lines)


def build_inspection_guide(inspection_workbook_path: Path, included_sheets: list[str]) -> str:
    sheet_list = "\n".join(f"- `{sheet}`" for sheet in included_sheets)
    return "\n".join(
        [
            "# Inspection guide",
            "",
            "## Purpose",
            "",
            "CSV files remain the machine-readable outputs. Excel workbooks in `outputs/inspection/` are companion files for manual review only; they do not replace or alter the CSVs.",
            "The workbook is generated through the shared utility at `notebooks/utils/inspection_workbooks.py`, so the same inspection pattern can be reused by future validation, forecast, and valuation scripts.",
            "",
            "## Interim Perplexity workbook",
            "",
            f"- Workbook: `{inspection_workbook_path.as_posix()}`",
            "- Use it to review mappings, standardized long tables, and standardized wide tables without manually applying Excel formatting each time.",
            "",
            "Included sheets:",
            "",
            sheet_list,
            "",
            "## Formatting conventions",
            "",
            "- Header row is frozen and filtered on every sheet.",
            "- Column widths are adjusted for readability, with a maximum width cap so notes do not dominate the sheet.",
            "- `fiscal_year` is displayed as a year label with no thousands separator or decimals.",
            "- `fiscal_quarter` and `period` are displayed as text labels.",
            "- USD-millions fields use a currency-style number format for easier review.",
            "- Margin/rate/yield rows use percentage-style display where applicable.",
            "- Blank or missing cells are highlighted in light yellow.",
            "- Rows with `canonical_metric = UNMAPPED` are highlighted in light red.",
            "",
            "## Recommended review order",
            "",
            "1. `line_item_mapping` — confirm mappings and inspect `UNMAPPED` rows first.",
            "2. `annual_wide_standardized` — review the core annual GAAP history quickly.",
            "3. `quarterly_wide_standardized` — inspect quarterly coverage and recent trends.",
            "4. `annual_long_standardized` and `quarterly_long_standardized` — use these for provenance-level review.",
            "",
            "## Important caution",
            "",
            "The inspection workbook is a readability layer. Make edits in the source code or upstream CSV-generation logic, not inside the workbook, so the data pipeline stays reproducible.",
            "",
        ]
    )


def build_interim_formatting_check(
    annual_long_df: pd.DataFrame,
    quarterly_long_df: pd.DataFrame,
    annual_wide_df: pd.DataFrame,
    quarterly_wide_df: pd.DataFrame,
    raw_files_unchanged: bool,
) -> str:
    annual_year_sample = annual_long_df["fiscal_year"].dropna().iloc[0]
    annual_period_sample = str(annual_long_df["period"].dropna().iloc[0])
    quarterly_period_sample = str(quarterly_long_df["period"].dropna().iloc[0])
    value_dtype = str(annual_long_df["value_usd_millions"].dtype)
    wide_financial_columns = [
        column
        for column in annual_wide_df.columns
        if column not in {"fiscal_year", "fiscal_quarter", "period"}
    ]

    return "\n".join(
        [
            "# Interim formatting check",
            "",
            "## Result",
            "",
            "- `fiscal_year` remains an integer label in the generated CSV layer.",
            f"- Sample `fiscal_year`: `{annual_year_sample}` (expected display: `2020`, not `2.020,00`).",
            f"- Sample annual `period`: `{annual_period_sample}`.",
            f"- Sample quarterly `period`: `{quarterly_period_sample}`.",
            f"- `value_usd_millions` dtype: `{value_dtype}`; it remains numeric.",
            "- Core financial metric columns remain USD-millions numeric values.",
            f"- Example financial metric columns: {', '.join(f'`{column}`' for column in wide_financial_columns[:10])}.",
            f"- Raw files modified by this build: `{'no' if raw_files_unchanged else 'yes'}`.",
            "",
            "## Interpretation",
            "",
            "- `fiscal_year`, `fiscal_quarter`, and `period` are identifiers / labels, not financial measures.",
            "- Excel inspection workbooks format `fiscal_year` as `0`, and `fiscal_quarter` / `period` as text.",
            "- USD-millions formatting remains reserved for financial value columns such as `value_usd_millions`, revenue, cash, debt, assets, liabilities, operating cash flow, and capex.",
            "",
        ]
    )


def main() -> None:
    project_root = find_project_root(Path.cwd())
    manifest_path = project_root / MANIFEST_RELATIVE_PATH
    batch_dir = manifest_path.parent
    interim_dir = project_root / INTERIM_DIR_RELATIVE_PATH
    summary_path = project_root / SUMMARY_RELATIVE_PATH
    inspection_workbook_path = project_root / INSPECTION_WORKBOOK_RELATIVE_PATH
    inspection_guide_path = project_root / INSPECTION_GUIDE_RELATIVE_PATH
    formatting_check_path = project_root / FORMATTING_CHECK_RELATIVE_PATH

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    manifest = pd.read_csv(manifest_path)
    required_manifest_columns = {
        "file_name",
        "retrieved_at",
        "data_tab",
        "period",
        "unit_scale",
        "source_platform",
    }
    missing_manifest_columns = required_manifest_columns - set(manifest.columns)
    if missing_manifest_columns:
        raise ValueError(f"Manifest missing required columns: {sorted(missing_manifest_columns)}")

    missing_files = [
        file_name
        for file_name in manifest["file_name"]
        if not (batch_dir / file_name).exists()
    ]
    if missing_files:
        raise FileNotFoundError("Manifest references missing raw files:\n" + "\n".join(missing_files))

    raw_file_mtimes_before = {
        file_name: (batch_dir / file_name).stat().st_mtime_ns
        for file_name in manifest["file_name"]
    }

    interim_dir.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    mapping_df = build_mapping_table(manifest, batch_dir)
    (
        annual_long_df,
        quarterly_long_df,
        annual_coverage,
        quarterly_coverage,
        conversion_counts,
    ) = build_long_tables(manifest, batch_dir, mapping_df)

    annual_wide_df = build_wide_table(annual_long_df, mapping_df, "annual")
    quarterly_wide_df = build_wide_table(quarterly_long_df, mapping_df, "quarterly")

    mapping_df.to_csv(interim_dir / "qbts_line_item_mapping.csv", index=False)
    annual_long_df.to_csv(interim_dir / "qbts_annual_long_standardized.csv", index=False)
    quarterly_long_df.to_csv(interim_dir / "qbts_quarterly_long_standardized.csv", index=False)
    annual_wide_df.to_csv(interim_dir / "qbts_annual_wide_standardized.csv", index=False)
    quarterly_wide_df.to_csv(interim_dir / "qbts_quarterly_wide_standardized.csv", index=False)

    summary_text = build_summary(
        manifest=manifest,
        mapping_df=mapping_df,
        annual_long_df=annual_long_df,
        quarterly_long_df=quarterly_long_df,
        annual_coverage=annual_coverage,
        quarterly_coverage=quarterly_coverage,
        conversion_counts=conversion_counts,
    )
    summary_path.write_text(summary_text, encoding="utf-8")

    core_financial_metric_columns = frozenset(
        mapping_df.loc[
            mapping_df["use_in_core_financials"] == True,  # noqa: E712
            "canonical_metric",
        ]
    )
    inspection_result = build_inspection_workbook_from_csvs(
        workbook_path=inspection_workbook_path,
        sheet_specs=[
            CsvSheetSpec(sheet_name=sheet_name, csv_path=interim_dir / csv_name)
            for sheet_name, csv_name in INSPECTION_SHEETS
        ],
        config=InspectionWorkbookConfig(
            financial_metric_columns=core_financial_metric_columns,
            currency_row_allowed_values_by_column={
                "statement_or_tab": frozenset(CORE_GAAP_TABS),
            },
        ),
    )
    inspection_guide_path.parent.mkdir(parents=True, exist_ok=True)
    inspection_guide_path.write_text(
        build_inspection_guide(
            inspection_workbook_path=inspection_workbook_path.relative_to(project_root),
            included_sheets=list(inspection_result.included_sheets),
        ),
        encoding="utf-8",
    )

    raw_file_mtimes_after = {
        file_name: (batch_dir / file_name).stat().st_mtime_ns
        for file_name in manifest["file_name"]
    }
    raw_files_unchanged = raw_file_mtimes_before == raw_file_mtimes_after
    formatting_check_path.write_text(
        build_interim_formatting_check(
            annual_long_df=annual_long_df,
            quarterly_long_df=quarterly_long_df,
            annual_wide_df=annual_wide_df,
            quarterly_wide_df=quarterly_wide_df,
            raw_files_unchanged=raw_files_unchanged,
        ),
        encoding="utf-8",
    )

    print(f"Saved mapping file to: {interim_dir / 'qbts_line_item_mapping.csv'}")
    print(f"Saved annual long file to: {interim_dir / 'qbts_annual_long_standardized.csv'}")
    print(f"Saved quarterly long file to: {interim_dir / 'qbts_quarterly_long_standardized.csv'}")
    print(f"Saved annual wide file to: {interim_dir / 'qbts_annual_wide_standardized.csv'}")
    print(f"Saved quarterly wide file to: {interim_dir / 'qbts_quarterly_wide_standardized.csv'}")
    print(f"Saved build summary to: {summary_path}")
    print(f"Created Excel inspection workbook: {inspection_workbook_path}")
    print("Included sheets: " + ", ".join(inspection_result.included_sheets))
    print("CSV files used:")
    for csv_file in inspection_result.csv_files_used:
        print(f"- {csv_file}")
    print("CSV files missing:")
    if inspection_result.missing_csv_files:
        for csv_file in inspection_result.missing_csv_files:
            print(f"- {csv_file}")
    else:
        print("- None")
    print(f"Saved inspection guide to: {inspection_guide_path}")
    print(f"Saved interim formatting check to: {formatting_check_path}")


if __name__ == "__main__":
    main()
