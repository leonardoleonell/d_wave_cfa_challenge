---
title: "Valuation"
subtitle: "D-Wave Quantum Inc. (QBTS)"
author: "CFA Research Challenge Valuation Section"
date: ""
fontsize: 11pt
geometry: margin=1in
header-includes:
  - \usepackage{ragged2e}
  - \AtBeginDocument{\justifying}
  - \usepackage{booktabs}
  - \usepackage{setspace}
  - \onehalfspacing
---

<style>
body {
  font-family: "Times New Roman", Times, serif;
  font-size: 11pt;
  line-height: 1.45;
  text-align: justify;
  color: #111111;
}
h1, h2, h3 {
  font-family: "Times New Roman", Times, serif;
  color: #111111;
}
h1 {
  text-align: center;
  font-size: 18pt;
  margin-bottom: 0.4em;
}
h2 {
  font-size: 13pt;
  margin-top: 1.1em;
  border-bottom: 1px solid #444444;
  padding-bottom: 0.2em;
}
p {
  text-align: justify;
  margin-top: 0.45em;
  margin-bottom: 0.45em;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 0.6em;
  margin-bottom: 0.8em;
  font-size: 10pt;
}
th, td {
  border-top: 1px solid #666666;
  border-bottom: 1px solid #dddddd;
  padding: 6px 8px;
}
th {
  font-weight: bold;
  background: #f3f3f3;
}
.caption {
  text-align: center;
  font-size: 10pt;
  font-style: italic;
  margin-top: 0.7em;
  margin-bottom: 0.2em;
}
.note {
  font-size: 10pt;
  text-align: justify;
}
</style>

# Valuation

## Methodology Overview

This valuation applies a blended framework that assigns primary weight to forward EV/Sales and uses discounted cash flow ("DCF") analysis as a secondary cross-check. The final target price is based on an **80% weighting to EV/Sales** and a **20% weighting to DCF**, resulting in a final weighted target price of **$8.24** per share.

All financial values are presented in USD millions unless otherwise stated. Diluted shares were unavailable in the model outputs; therefore, the valuation uses **370.03 million shares outstanding**. This approach is less conservative than using diluted shares, but it is consistent with the available valuation input file.

## Why EV/Sales Is the Primary Method

EV/Sales is the most appropriate primary valuation method because D-Wave remains an early-stage company and its current earnings, EBITDA, and free cash flow are not representative of normalized profitability. Consequently, P/E and EV/EBITDA are not appropriate primary methods. Current earnings and EBITDA do not provide a stable valuation base and would largely reflect near-term investment losses rather than the company's long-term commercialization potential.

The valuation therefore focuses on forward revenue and uses **2027E revenue of $70.811 million** as the base valuation year. This approach better reflects the company's stage of development, where revenue growth and commercialization progress are more relevant than current profitability metrics.

## Peer Group and Capped Multiple Rationale

The raw quantum peer median EV/Sales LTM multiple is **386.741x**. This figure is shown as a market reference but is not applied directly in the valuation. Quantum peer multiples are distorted by very small revenue bases, which can produce unusually high and unstable EV/Sales ratios. Directly applying the raw peer median would therefore risk overstating intrinsic value.

To address this issue, the model uses capped EV/Sales scenarios. These capped multiples preserve a market-based valuation anchor while reducing the distortion caused by extremely small peer revenue bases.

<div class="caption">Table 1. Capped EV/Sales Scenario Valuation</div>

| Scenario | EV/Sales Multiple | Target Price |
|---|---:|---:|
| Bear | 25.0x | $7.08 |
| Base | 40.0x | $9.95 |
| Bull | 60.0x | $13.78 |

## EV/Sales Valuation

In the Base case, the model applies a **40.0x EV/Sales multiple** to **2027E revenue of $70.811 million**, producing enterprise value of **$2,832.440 million**. Adding net cash of **$848.522 million** results in equity value of **$3,680.962 million**. Using **370.03 million shares outstanding**, the EV/Sales Base case target price is **$9.95**.

This method remains the primary valuation anchor because it is tied to forward commercialization revenue while avoiding reliance on current earnings or EBITDA, which are not representative of normalized profitability.

## DCF Cross-Check

DCF is used only as a conservative cross-check because explicit forecast free cash flow remains negative and the model is highly sensitive to terminal assumptions. In the DCF Base case, the model uses a **17% WACC**, **3% terminal growth**, and **10% terminal FCF margin**.

The Base case DCF produces PV of explicit FCF of **-$397.196 million** and PV of terminal value of **$62.612 million**. Enterprise value is **-$334.584 million**, equity value is **$513.938 million**, and the DCF Base case target price is **$1.39**.

Because explicit forecast FCF is negative, terminal value is the positive operating value component before adding net cash. This reinforces why DCF is treated as a secondary method rather than the primary valuation anchor.

## Market-Implied Valuation Sanity Check

At the current share price of **$22.35**, D-Wave's market capitalization is **$8,270.171 million**. After subtracting net cash of **$848.522 million**, the implied enterprise value is **$7,421.649 million**.

Against **2027E revenue of $70.811 million**, the current share price implies **104.81x EV/Sales**, materially above the capped **40.0x** Base case EV/Sales multiple. To justify the current enterprise value, D-Wave would need revenue of **$185.541 million** at **40.0x EV/Sales** or **$123.694 million** at **60.0x EV/Sales**. This indicates that the current market price implies either a much higher revenue base or a much higher EV/Sales multiple than the Base case.

## Final Target Price and Recommendation

The final valuation combines the **$9.95 EV/Sales Base case target price** with the **$1.39 DCF Base case target price**, using an **80% EV/Sales / 20% DCF** weighting. This produces a final weighted target price of **$8.24**.

<div class="caption">Table 2. Final Blended Valuation Summary</div>

| Scenario | EV/Sales Target Price | DCF Target Price | Weighted Target Price |
|---|---:|---:|---:|
| Bear | $7.08 | $1.34 | $5.93 |
| Base | $9.95 | $1.39 | $8.24 |
| Bull | $13.78 | $1.57 | $11.33 |

Relative to the current share price of **$22.35**, the final target price of **$8.24** implies approximately **63.2% downside**. Based on this valuation gap, the model supports a negative investment view at the current price.

<div class="note">Note: Figures are sourced from the model outputs listed in the valuation workstream. No additional valuation figures are introduced in this section.</div>
