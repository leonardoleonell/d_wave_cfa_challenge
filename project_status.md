# D-Wave CFA Challenge Project — Handoff

## Objective
Build the definitive Financial Analysis and Valuation for D-Wave Quantum Inc. (QBTS), using only public information, for the CFA Research Challenge.

## Thesis direction
Maintain a contrarian/fundamentalist view. D-Wave has meaningful quantum computing optionality, but the current market price appears to embed aggressive commercialization assumptions. The likely recommendation is SELL / Underperform unless the updated model materially changes.

## Current project structure
- data/raw/filings/
- data/raw/legacy/
- data/raw/perplexity/
- data/interim/perplexity/
- data/processed/
- data/processed/validation_ready/
- data/sources/
- notebooks/
- outputs/charts/
- outputs/tables/
- outputs/text/
- report_sections/
- slides/

## Work completed in previous version
- Cleaned D-Wave financials from Comdinheiro/SEC exports.
- Converted financial values to USD millions.
- Validated Capex and debt.
- Built financial analysis.
- Built forecast 2026–2032.
- Built EV/Sales valuation.
- Built DCF cross-check.
- Updated shares outstanding to 370.03 million.
- Built market-implied valuation.
- Built final valuation summary.
- Created markdown/PDF slides.

## Important previous results
- 2025 revenue around $24.6mm.
- 2025 gross margin around 82.6%.
- R&D and SG&A were extremely high as % of revenue.
- FCF remained negative.
- Net cash was around $848.5mm.
- Previous base EV/Sales target price was around $9.95–10.25.
- Previous weighted target price was around $8.24.
- Current price used previously was around $22.35.
- Market-implied EV/Sales on 2027E revenue was above 100x.
- Street consensus from Perplexity was bullish, with average target around $37, but the thesis remains contrarian.

## Methodology to keep
Primary valuation:
- EV/Sales using capped scenario multiples:
  - Bear: 25.0x
  - Base: 40.0x
  - Bull: 60.0x

Secondary valuation:
- DCF as conservative cross-check:
  - Bear: WACC 20%, terminal growth 2%, terminal FCF margin 5%
  - Base: WACC 17%, terminal growth 3%, terminal FCF margin 10%
  - Bull: WACC 14%, terminal growth 4%, terminal FCF margin 15%

Final valuation:
- 80% EV/Sales
- 20% DCF

Important rationale:
- Raw quantum peer EV/Sales multiples should not be used directly because they are distorted by very small revenue bases.
- P/E and EV/EBITDA are not appropriate because earnings and EBITDA are negative/not normalized.
- DCF is secondary because explicit FCF remains negative and terminal assumptions dominate.

## Next task
Rebuild the definitive version using Perplexity data:
1. Export from Perplexity Finance, using consistent units and explicit period selection:
   - Key Stats
   - Income Statement
   - Balance Sheet
   - Cash Flow
   - Segments & KPIs, if available
   - Adjusted, if analytically useful
   - Ratios, if available
2. Save untouched exports in a dated batch folder under `data/raw/perplexity/`.
3. Record each extraction in `data/sources/perplexity_pull_log.csv`.
4. Standardize line items and units in `data/interim/perplexity/`.
5. Clean and consolidate validated history into `data/processed/qbts_financials_perplexity_clean.csv`.
6. Validate historical financials before any modeling.
7. Only then rebuild Financial Analysis, forecast, peer analysis, valuation, and final recommendation.
