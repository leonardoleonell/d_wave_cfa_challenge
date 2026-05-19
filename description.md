Where we are now
You have finished the raw-data collection setup for the definitive rebuild of the D-Wave analysis.

The project is no longer in the old “single raw folder feeding the old model” state. It now has a cleaner ingestion architecture:

data/
├─ raw/
│  ├─ filings/
│  ├─ legacy/
│  └─ perplexity/
│     └─ 2026-05-15_batch01/
│        ├─ annual/
│        ├─ quarterly/
│        └─ manifest.csv
├─ interim/
│  └─ perplexity/
├─ processed/
│  └─ validation_ready/
└─ sources/
What has already been completed
The old source files were reorganized

SEC / filing exports are now in data/raw/filings/
the old Comdinheiro file is now in data/raw/legacy/
The Perplexity raw-ingestion structure was created

data/raw/perplexity/
dated batch folder:
data/raw/perplexity/2026-05-15_batch01/
You manually downloaded all available Perplexity data

annual tabs
quarterly tabs
Those raw exports were inspected and renamed consistently

annual and quarterly files now follow a standardized naming convention
the filenames include:
tab
period
units
actual coverage range
retrieval date
raw status
The manifest was completed

data/raw/perplexity/2026-05-15_batch01/manifest.csv
it now records:
file name
retrieval timestamp
data tab
annual vs quarterly
exact period covered
unit scale
file format
source platform
notes
We discovered an important fact about the quarterly data

the quarterly files do not all begin in the same quarter
For example:

balance sheet: 2020Q3-2026Q1
ratios: 2020Q3-2026Q1
segments & KPIs: 2021Q1-2026Q1
income statement: 2021Q3-2026Q1
cash flow: 2021Q4-2026Q1
That means the raw batch is now accurately documented instead of assuming all tabs share the same history.

What this means
You now have a well-organized raw evidence layer.

But you do not yet have a clean dataset that should be used for analysis, forecasting, or valuation.

At this moment, the project has:

raw annual exports
raw quarterly exports
good provenance
good file naming
good folder hygiene
But it does not yet have:

standardized metric names
normalized values
reconciled annual vs quarterly figures
a canonical historical dataset for the rebuild
So we are exactly at the boundary between:

data collection
and

data cleaning / standardization
The next step I suggested
The next step is to build the interim Perplexity data layer inside:

data/interim/perplexity/
This is the stage where we transform the raw exports into a consistent, reviewable working dataset before anything enters data/processed/.

Concretely, the next step would create files like:
qbts_line_item_mapping.csv
qbts_annual_long_standardized.csv
qbts_quarterly_long_standardized.csv
qbts_annual_wide_standardized.csv
qbts_quarterly_wide_standardized.csv
qbts_annual_vs_quarterly_reconciliation.csv
qbts_data_quality_notes.md
What would happen in that next step
1. Map raw Perplexity labels to canonical metric names
Example:

Raw label	Standardized name
Total Revenues	revenue
Gross Profit	gross_profit
Research & Development Expenses	r_and_d
Selling, General & Administrative Expenses	sga
This becomes the translation layer that makes the dataset reproducible and auditable.

2. Standardize the data structure
We would normalize:

dates
quarter labels
numeric formats
missing values
signs
units
annual and quarterly layouts
3. Separate usable financial metrics from contextual metrics
For example:

income statement / balance sheet / cash flow metrics may enter the final clean dataset
ratios, percentages, and adjusted metrics may be retained for review but not automatically merged into the core GAAP history
4. Reconcile annual and quarterly information
For full years where quarterly data exists, we would test:

sum of Q1–Q4 ≈ annual total
For balance sheet metrics, we would test:

Q4 ending balance ≈ annual year-end balance
This is where we catch:

rounding
inconsistent definitions
missing quarters
possible Perplexity export anomalies
5. Produce the first clean historical dataset
Only after the above would we create the final historical base file, likely:

data/processed/qbts_financials_perplexity_clean.csv
That file would later replace the old historical base for the definitive rebuild.

In plain language
You have finished building the library shelves and placing every source document in the right spot.

The next step is to build the cataloging system:

what each line item means,
how each number should be named,
which rows are trusted,
how annual and quarterly data relate,
and what exact dataset is safe to use later.