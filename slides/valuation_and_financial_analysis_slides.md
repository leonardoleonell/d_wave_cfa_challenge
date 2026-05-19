---
title: "Financial Analysis and Valuation"
subtitle: "D-Wave Quantum Inc. (QBTS)"
author: "CFA Research Challenge Presentation"
date: ""
fontsize: 11pt
geometry: margin=0.65in
header-includes:
  - \usepackage{ragged2e}
  - \AtBeginDocument{\justifying}
  - \usepackage{booktabs}
---

<style>
body {
  font-family: "Times New Roman", Times, serif;
  font-size: 11pt;
  line-height: 1.35;
  text-align: justify;
  color: #111111;
}
h1 {
  font-size: 18pt;
  margin-top: 0.35em;
  margin-bottom: 0.9em;
  border-bottom: none;
  padding-bottom: 0;
}
h2 {
  font-size: 15pt;
  margin-top: 0.35em;
  margin-bottom: 0.9em;
  border-bottom: 1px solid #444444;
  padding-bottom: 0.35em;
}
h3 {
  font-size: 11pt;
  margin-top: 1.15em;
  margin-bottom: 0.45em;
}

ul {
  margin-top: 0.45em;
  margin-bottom: 0.9em;
}

li {
  margin-bottom: 0.35em;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 0.65em;
  margin-bottom: 0.95em;
  font-size: 9.5pt;
}
th, td {
  border-top: 1px solid #666666;
  border-bottom: 1px solid #dddddd;
  padding: 5px 7px;
}
th {
  font-weight: bold;
  background: #f3f3f3;
}
.suggested {
  font-size: 10pt;
  font-style: italic;
  margin-top: 0.25em;
  margin-bottom: 1.1em;
}
.notes {
  font-size: 10pt;
  text-align: justify;
  margin-top: 0.35em;
  margin-bottom: 0.3em;
}
</style>

# Financial Analysis and Valuation

<div class="slide">

## Slide 1. Financial Analysis: Growth, Margins, Losses, and Cash Burn

- Revenue increased from **$8.827 million in 2024** to **$24.587 million in 2025**, implying **178.5% growth** from a small base.
- Gross margin was strong at **82.6% in 2025**, supported by **$20.306 million** of gross profit.
- Operating expense intensity remained very high: **R&D was 206.3% of revenue** and **SG&A was 284.5% of revenue** in 2025.
- Operating income was **-$100.368 million** and net income was **-$355.062 million** in 2025.
- Free cash flow was **-$76.289 million**, implying cash burn of **$76.289 million**.

### Suggested Chart/Table

<div class="suggested">Use a combined historical table or chart showing revenue, gross margin, R&D/revenue, SG&A/revenue, operating income, and free cash flow for 2020-2025.</div>

### **Speaker Notes**

<div class="notes">D-Wave has a high-gross-margin revenue profile, but the company is still far from normalized profitability. The 2025 revenue step-up is meaningful, yet the company remains early-stage. The central issue is operating expense intensity: R&D and SG&A materially exceed revenue, so the investment case depends on future commercialization and operating leverage rather than current profitability.</div>

</div>

<div class="slide">

## Slide 2. Forecast: Revenue Growth, Margin Path, and Operating Leverage

- The forecast uses fiscal **2025** as the base year and projects revenue from **$44.257 million in 2026** to **$255.418 million in 2032**.
- Revenue growth decelerates from **80.0% in 2026** to **18.0% in 2032** as the revenue base expands.
- Gross margin declines from **78.0% in 2026** to **66.0% in 2032**, while remaining structurally high.
- Operating leverage is driven by lower expense intensity: R&D/revenue declines from **150.0% to 30.0%**, and SG&A/revenue declines from **200.0% to 35.0%**.
- EBIT turns positive in **2032** at **$2.554 million**, but free cash flow remains negative at **-$15.708 million**.

### Suggested Chart/Table

<div class="suggested">Use a forecast bridge table for 2026-2032 showing revenue, revenue growth, gross margin, R&D/revenue, SG&A/revenue, EBIT, and free cash flow.</div>

### **Speaker Notes**

<div class="notes">The forecast assumes continued commercialization but does not assume immediate profitability. Revenue growth slows over time, while operating expense ratios decline meaningfully. This creates a path toward operating leverage, but free cash flow remains negative through 2032, reinforcing that D-Wave's valuation depends on future scale rather than current earnings power.</div>

</div>

<div class="slide">

## Slide 3. Valuation: EV/Sales Primary Method and DCF Cross-Check

- EV/Sales is the primary method because current earnings, EBITDA, and free cash flow are not representative of normalized profitability.
- The raw quantum peer median EV/Sales LTM is **386.741x**, but it is not used directly because peer multiples are distorted by very small revenue bases.
- The Base case applies a capped **40.0x EV/Sales multiple** to **2027E revenue of $70.811 million**, producing an EV/Sales target price of **$9.95**.
- DCF is used as a conservative cross-check because explicit forecast free cash flow remains negative; the DCF Base case target price is **$1.39**.
- The final valuation uses **80% EV/Sales** and **20% DCF**, producing a final weighted target price of **$8.24**.

### Suggested Chart/Table

<div class="suggested">Use the final valuation summary table with Bear/Base/Bull target prices from EV/Sales, DCF, and the weighted valuation.</div>

| Scenario | EV/Sales Target Price | DCF Target Price | Weighted Target Price |
|---|---:|---:|---:|
| Bear | $7.08 | $1.34 | $5.93 |
| Base | $9.95 | $1.39 | $8.24 |
| Bull | $13.78 | $1.57 | $11.33 |

### **Speaker Notes**

<div class="notes">The valuation framework is deliberately conservative. EV/Sales is the primary anchor because D-Wave is still in the commercialization phase, while DCF is only a cross-check because most of the forecast period still has negative free cash flow. The model caps the EV/Sales multiple rather than applying the raw peer median, which would mechanically overstate value because quantum peers have very small revenue bases.</div>

</div>

<div class="slide">

## Slide 4. Market-Implied Expectations: Current Price Versus Model

- Current share price used: **$22.35**.
- With **370.03 million shares outstanding**, current market capitalization is **$8,270.171 million**.
- After net cash of **$848.522 million**, implied enterprise value is **$7,421.649 million**.
- On **2027E revenue of $70.811 million**, the market implies **104.81x EV/Sales**.
- To justify the current enterprise value, revenue would need to be **$185.541 million at 40.0x EV/Sales** or **$123.694 million at 60.0x EV/Sales**.

### Suggested Chart/Table

<div class="suggested">Use a market-implied valuation table comparing 2027E model revenue, implied EV/Sales, revenue required at 40.0x, and revenue required at 60.0x.</div>

| Metric | Value |
|---|---:|
| Current Share Price | $22.35 |
| Current Market Capitalization | $8,270.171 |
| Implied Enterprise Value | $7,421.649 |
| Implied EV/Sales on 2027E Revenue | 104.81x |
| Revenue Required at 40.0x EV/Sales | $185.541 |
| Revenue Required at 60.0x EV/Sales | $123.694 |

### **Speaker Notes**

<div class="notes">The current market price embeds expectations that are materially above the model's Base case. The market-implied EV/Sales multiple of 104.81x is far above the capped 40.0x Base case multiple. Alternatively, D-Wave would need a much higher revenue base than the 2027E forecast to justify the current enterprise value at high-growth EV/Sales multiples. This gap supports the downside conclusion from the final target price.</div>

</div>
