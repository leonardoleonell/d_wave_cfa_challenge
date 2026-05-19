# D-Wave CFA Challenge Project

This project contains the financial analysis and valuation work for D-Wave Quantum Inc. (QBTS), prepared using only public information.

## Main outputs

1. Financial Analysis section
2. Valuation section
3. Charts and tables
4. Presentation support slides
5. Q&A preparation

## Data policy

All numbers must come from public sources, including company filings, investor presentations, earnings releases, Comdinheiro exports, and public market data.

No invented numbers are allowed. Missing data must be marked as TO BE FILLED.

## Data folder logic

The rebuild now separates data by how far it has moved through the ingestion pipeline:

- `data/raw/` stores untouched source exports and source documents.
- `data/interim/` stores standardized working files that are not yet final.
- `data/processed/` stores cleaned, validated datasets that are ready for analysis.
- `data/sources/` stores provenance, extraction logs, and data definitions.

For the final Perplexity Finance rebuild:

- `data/raw/perplexity/` is for untouched exports from Perplexity Finance.
- `data/interim/perplexity/` is for normalized statement files and line-item mappings.
- `data/processed/` should only receive files after reconciliation and validation.
