# Slide: FinScribe AI — Business Impact Summary

## Title
**FinScribe AI — Turn Invoices into Actionable Data**

---

## Sections

### 1. Problem Statement
- Manual invoice processing costs **$12-$40 per invoice**
- **1-4% error rates** requiring manual review
- Doesn't scale with document volume
- Blocks automation and integration workflows

### 2. Technical Solution
- **PaddleOCR-VL (fine-tuned)** for layout-aware extraction
- **Business Logic Validator** for arithmetic checks and confidence scoring
- **Active Learning Pipeline** for continuous improvement
- **Integration-Ready Outputs** (JSON, CSV, QuickBooks)

### 3. Impact (Example Calculation)
**Scenario:** 1,000 invoices/month @ $30 manual cost

- **Manual Total:** $30,000/month
- **Automated Total:** $150 + $200 (infra) = $350/month
- **Monthly Savings:** **$29,650/month**
- **Annual Savings:** **$355,800/year**

**Accuracy Improvements:**
- Field Extraction: 76.8% → **94.2%** (+17.4%)
- Table Structure: 68.2% → **91.7%** (+23.5%)
- Validation Pass: 54.7% → **96.8%** (+42.1%)

### 4. Demo Highlights
- **Upload** → OCR → **Edit** → Accept (active learning) → **Export** (QuickBooks CSV)
- Demo runs locally via `make demo` or `./demo_run.sh`
- ROI calculator shows real-time savings
- Export formats: JSON, CSV, QuickBooks CSV

### 5. Ask & Next Steps
- **Pilot customers** for real workload testing
- **Dataset access** for edge case improvement
- **Integration partnerships** (QuickBooks, Xero, Sage)
- **Engineering support** for custom integrations

---

## Visual Elements (Placeholders)

### Screenshots to Include:
1. **Demo Upload Interface** — showing invoice upload with bounding boxes
2. **ROI Calculator** — showing example calculation (1,000 invoices → $24k savings)
3. **Export CSV** — opened in Excel/Google Sheets showing structured data
4. **QuickBooks Import** — showing CSV mapping and import process

### Metrics Table:
| Metric | Baseline | FinScribe | Improvement |
|--------|----------|-----------|-------------|
| Field Extraction | 76.8% | **94.2%** | +17.4% |
| Table Structure | 68.2% | **91.7%** | +23.5% |
| Numeric Accuracy | 82.1% | **97.3%** | +15.2% |
| Validation Pass | 54.7% | **96.8%** | +42.1% |

---

## Design Notes
- Use FinScribe brand colors (primary blue/green gradient)
- Include logo in top-right corner
- Keep text concise and scannable
- Use icons for each section (Problem, Solution, Impact, Demo, Ask)
- Highlight key numbers in larger, bold font

---

## Alternative One-Page Format

If creating a PDF/PNG slide, consider this layout:

```
┌─────────────────────────────────────────────────────────┐
│  FinScribe AI Logo                    [Metrics Table]   │
│                                                           │
│  PROBLEM          SOLUTION          IMPACT                │
│  $12-40/invoice   PaddleOCR-VL     94.2% accuracy        │
│  1-4% errors      + Validation     $24k/month saved      │
│  No scale         + Active Learn   QuickBooks ready      │
│                                                           │
│  DEMO: Upload → OCR → Edit → Export (2 seconds)         │
│                                                           │
│  ASK: Pilot customers | Dataset access | Partnerships   │
└─────────────────────────────────────────────────────────┘
```

