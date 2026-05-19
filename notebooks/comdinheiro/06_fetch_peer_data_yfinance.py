from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

try:
    import yfinance as yf
except ImportError as exc:
    raise SystemExit(
        "ERROR: yfinance is not installed. Install it with: .\\.venv\\Scripts\\python -m pip install yfinance"
    ) from exc


TICKER_CONFIG = {
    "QBTS": {"category": "Subject company", "include_in_final_peer_group": False},
    "IONQ": {"category": "Quantum pure play", "include_in_final_peer_group": True},
    "RGTI": {"category": "Quantum pure play", "include_in_final_peer_group": True},
    "QUBT": {"category": "Quantum pure play", "include_in_final_peer_group": True},
    "ARQQ": {"category": "Quantum/security", "include_in_final_peer_group": False},
    "NVDA": {"category": "AI infrastructure", "include_in_final_peer_group": False},
    "PLTR": {"category": "Advanced software/AI", "include_in_final_peer_group": False},
    "SNOW": {"category": "Cloud software", "include_in_final_peer_group": False},
    "NET": {"category": "Cloud infrastructure", "include_in_final_peer_group": False},
}

OUTPUT_COLUMNS = [
    "company",
    "ticker",
    "category",
    "currency",
    "share_price",
    "market_cap",
    "enterprise_value",
    "cash",
    "total_debt",
    "net_debt",
    "revenue_ltm",
    "gross_profit",
    "gross_margin",
    "ebitda",
    "ebitda_margin",
    "revenue_growth",
    "beta",
    "average_volume",
    "shares_outstanding",
    "ev_sales_ltm",
    "include_in_final_peer_group",
    "notes",
]

MILLION = 1_000_000


def find_project_root(start: Path) -> Path:
    """Find the project root from either the repo root or notebooks folder."""
    start = start.resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "data" / "processed").exists():
            return candidate
    raise FileNotFoundError("Could not find project data/processed directory from the current path.")


def first_available(mapping: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None and not pd.isna(value):
            return value
    return pd.NA


def to_float(value: Any) -> float | pd.NA:
    if value is None or value is pd.NA:
        return pd.NA
    try:
        if pd.isna(value):
            return pd.NA
        return float(value)
    except (TypeError, ValueError):
        return pd.NA


def to_usd_millions(value: Any) -> float | pd.NA:
    numeric_value = to_float(value)
    if numeric_value is pd.NA:
        return pd.NA
    return numeric_value / MILLION


def safe_divide(numerator: Any, denominator: Any) -> float | pd.NA:
    numerator_value = to_float(numerator)
    denominator_value = to_float(denominator)
    if numerator_value is pd.NA or denominator_value is pd.NA or denominator_value == 0:
        return pd.NA
    return numerator_value / denominator_value


def get_fast_info(ticker: yf.Ticker) -> dict[str, Any]:
    try:
        fast_info = ticker.fast_info
        return dict(fast_info) if fast_info is not None else {}
    except Exception:
        return {}


def get_info(ticker: yf.Ticker) -> tuple[dict[str, Any], str | None]:
    try:
        info = ticker.get_info()
        return (info if isinstance(info, dict) else {}, None)
    except Exception as exc:
        return {}, str(exc)


def collect_ticker(ticker_symbol: str) -> dict[str, Any]:
    config = TICKER_CONFIG[ticker_symbol]
    ticker = yf.Ticker(ticker_symbol)
    info, info_error = get_info(ticker)
    fast_info = get_fast_info(ticker)
    notes: list[str] = []

    if info_error:
        notes.append(f"Yahoo info fetch error: {info_error}")

    company = first_available(info, ["longName", "shortName", "displayName"])
    currency = first_available(info, ["financialCurrency", "currency"])
    if currency is pd.NA:
        currency = first_available(fast_info, ["currency"])

    share_price = first_available(
        info,
        ["currentPrice", "regularMarketPrice", "previousClose"],
    )
    if share_price is pd.NA:
        share_price = first_available(fast_info, ["last_price", "lastPrice", "regular_market_previous_close"])

    raw_market_cap = first_available(info, ["marketCap"])
    if raw_market_cap is pd.NA:
        raw_market_cap = first_available(fast_info, ["market_cap", "marketCap"])

    raw_enterprise_value = first_available(info, ["enterpriseValue"])
    raw_cash = first_available(info, ["totalCash"])
    raw_total_debt = first_available(info, ["totalDebt"])
    raw_revenue_ltm = first_available(info, ["totalRevenue"])
    raw_gross_profit = first_available(info, ["grossProfits", "grossProfit"])
    raw_ebitda = first_available(info, ["ebitda"])

    market_cap = to_usd_millions(raw_market_cap)
    enterprise_value = to_usd_millions(raw_enterprise_value)
    cash = to_usd_millions(raw_cash)
    total_debt = to_usd_millions(raw_total_debt)
    revenue_ltm = to_usd_millions(raw_revenue_ltm)
    gross_profit = to_usd_millions(raw_gross_profit)
    ebitda = to_usd_millions(raw_ebitda)

    net_debt = pd.NA
    if cash is not pd.NA and total_debt is not pd.NA:
        net_debt = total_debt - cash

    gross_margin = safe_divide(gross_profit, revenue_ltm)
    ebitda_margin = safe_divide(ebitda, revenue_ltm)
    ev_sales_ltm = safe_divide(enterprise_value, revenue_ltm)

    revenue_growth = to_float(first_available(info, ["revenueGrowth"]))
    beta = to_float(first_available(info, ["beta"]))
    average_volume = to_float(first_available(info, ["averageVolume", "averageDailyVolume10Day"]))
    shares_outstanding = to_float(first_available(info, ["sharesOutstanding"]))

    if currency is not pd.NA and currency != "USD":
        notes.append(f"Yahoo currency is {currency}; verify whether USD conversion is needed.")

    missing_fields = []
    field_values = {
        "company": company,
        "currency": currency,
        "share_price": share_price,
        "market_cap": market_cap,
        "enterprise_value": enterprise_value,
        "cash": cash,
        "total_debt": total_debt,
        "net_debt": net_debt,
        "revenue_ltm": revenue_ltm,
        "gross_profit": gross_profit,
        "gross_margin": gross_margin,
        "ebitda": ebitda,
        "ebitda_margin": ebitda_margin,
        "revenue_growth": revenue_growth,
        "beta": beta,
        "average_volume": average_volume,
        "shares_outstanding": shares_outstanding,
        "ev_sales_ltm": ev_sales_ltm,
    }
    for field, value in field_values.items():
        if value is pd.NA or pd.isna(value):
            missing_fields.append(field)

    if missing_fields:
        notes.append("Missing/unavailable fields: " + ", ".join(missing_fields))
    if ev_sales_ltm is pd.NA:
        notes.append("EV/Sales not calculated because enterprise value or revenue was missing or zero.")

    return {
        "company": company,
        "ticker": ticker_symbol,
        "category": config["category"],
        "currency": currency,
        "share_price": to_float(share_price),
        "market_cap": market_cap,
        "enterprise_value": enterprise_value,
        "cash": cash,
        "total_debt": total_debt,
        "net_debt": net_debt,
        "revenue_ltm": revenue_ltm,
        "gross_profit": gross_profit,
        "gross_margin": gross_margin,
        "ebitda": ebitda,
        "ebitda_margin": ebitda_margin,
        "revenue_growth": revenue_growth,
        "beta": beta,
        "average_volume": average_volume,
        "shares_outstanding": shares_outstanding,
        "ev_sales_ltm": ev_sales_ltm,
        "include_in_final_peer_group": str(config["include_in_final_peer_group"]).upper(),
        "notes": " ".join(notes) if notes else "All requested fields collected or calculated from Yahoo Finance fields.",
    }


def build_summary_report(output_path: Path, data: pd.DataFrame) -> None:
    fields_to_check = [
        column
        for column in OUTPUT_COLUMNS
        if column not in {"ticker", "category", "include_in_final_peer_group", "notes"}
    ]

    lines: list[str] = []
    lines.append("# yfinance Peer Data Summary")
    lines.append("")
    lines.append("Source: Yahoo Finance via the `yfinance` Python package.")
    lines.append("")
    lines.append("Financial statement and balance sheet values are reported in USD millions where Yahoo Finance provides USD-denominated values. Missing Yahoo fields are left as `NA`.")
    lines.append("")
    lines.append("## Output")
    lines.append("")
    lines.append("- `data/processed/peer_multiples_yfinance.csv`")
    lines.append("")
    lines.append("## Field Collection By Ticker")
    lines.append("")

    for _, row in data.iterrows():
        collected = []
        missing = []
        for field in fields_to_check:
            value = row[field]
            if pd.isna(value):
                missing.append(field)
            else:
                collected.append(field)

        lines.append(f"### {row['ticker']} - {row['company'] if pd.notna(row['company']) else 'NA'}")
        lines.append("")
        lines.append(f"- Category: {row['category']}")
        lines.append(f"- Include in final peer group: {row['include_in_final_peer_group']}")
        lines.append(f"- Collected fields: {', '.join(collected) if collected else 'None'}")
        lines.append(f"- Missing fields: {', '.join(missing) if missing else 'None'}")
        lines.append(f"- Notes: {row['notes']}")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    project_root = find_project_root(Path.cwd())
    output_path = project_root / "data" / "processed" / "peer_multiples_yfinance.csv"
    summary_path = project_root / "outputs" / "text" / "yfinance_peer_data_summary.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    records = []
    for ticker_symbol in TICKER_CONFIG:
        print(f"Fetching {ticker_symbol}...")
        records.append(collect_ticker(ticker_symbol))

    data = pd.DataFrame(records, columns=OUTPUT_COLUMNS)

    numeric_columns = [
        "share_price",
        "market_cap",
        "enterprise_value",
        "cash",
        "total_debt",
        "net_debt",
        "revenue_ltm",
        "gross_profit",
        "gross_margin",
        "ebitda",
        "ebitda_margin",
        "revenue_growth",
        "beta",
        "average_volume",
        "shares_outstanding",
        "ev_sales_ltm",
    ]
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data.to_csv(output_path, index=False, na_rep="NA")
    build_summary_report(summary_path, data)

    print(f"Saved peer data to: {output_path}")
    print(f"Saved summary report to: {summary_path}")
    print("")
    print(data.to_string(index=False, na_rep="NA"))


if __name__ == "__main__":
    main()
