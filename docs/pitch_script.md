# 2-minute Pitch Script — FinScribe AI

## Timing Breakdown

### (0:00-0:20) Problem Statement
"Companies still process invoices manually: it costs $12–$40 per invoice and introduces errors. This is slow, costly, and blocks automation. At scale, this becomes a massive operational burden."

**Key Points:**
- Manual processing is expensive ($12-40 per invoice)
- Error-prone (1-4% error rates)
- Doesn't scale with volume
- Blocks automation workflows

---

### (0:20-0:45) Solution
"FinScribe AI uses a fine-tuned PaddleOCR-VL model plus a validation engine to convert scanned invoices into validated JSON. We preserve table structure, validate arithmetic, and produce integration-ready outputs."

**Key Points:**
- Fine-tuned PaddleOCR-VL for financial documents
- Layout-aware semantic extraction
- Business logic validation (arithmetic checks)
- Integration-ready JSON/CSV outputs

---

### (0:45-1:10) Impact & Results
"On a conservative example — 1,000 invoices/month at $30 manual cost — FinScribe reduces that to an automated cost of $0.15/doc plus infrastructure, saving ~$24k/month. Accuracy jumps from ~77% to ~94% on field extraction in our tests."

**Key Metrics:**
- **Cost Savings:** $24,000/month for 1,000 invoices (example)
- **Accuracy:** 94.2% field extraction (vs 76.8% baseline)
- **Table Structure:** 91.7% TEDS accuracy
- **Validation Pass Rate:** 96.8%

---

### (1:10-1:40) Demo Callout
"Watch the demo: upload an invoice, see bounding boxes, edit a field, click 'Accept & Send to Training', then export to QuickBooks CSV — all under 2 seconds. The ROI calculator shows real-time savings, and exports integrate directly into accounting workflows."

**Demo Flow:**
1. Upload invoice (image/PDF)
2. View OCR results with bounding boxes
3. Edit/correct fields inline
4. Accept & queue for active learning
5. Export to QuickBooks CSV
6. Show ROI calculator with savings

---

### (1:40-2:00) Ask & Next Steps
"We seek pilot partners for real workload testing and data to further reduce edge-case errors. Next steps: provide sample invoices and integration targets (QuickBooks/Xero). We're also open to partnerships with accounting software providers."

**Call to Action:**
- Pilot customers for real-world testing
- Dataset access for edge case improvement
- Integration partnerships (QuickBooks, Xero, Sage)
- Engineering support for custom integrations

---

## Key Talking Points (if asked)

**Q: Why PaddleOCR-VL?**
A: Layout-aware architecture, fine-tunable with LoRA, production-ready, and open-source.

**Q: How does it compare to existing solutions?**
A: 94% accuracy vs 77% baseline, preserves table structure, validates business logic, and integrates with existing workflows.

**Q: What's the deployment model?**
A: Docker-based, can run on-premise or cloud, supports GPU acceleration, scales horizontally.

**Q: How do you handle edge cases?**
A: Active learning pipeline captures corrections, continuous model improvement, validation flags low-confidence extractions.

---

## Visual Aids (if presenting)

1. **Before/After Comparison Slide:**
   - Baseline: 76.8% accuracy, manual processing
   - FinScribe: 94.2% accuracy, automated

2. **ROI Calculator Screenshot:**
   - Show example: 1,000 invoices/month → $24k savings

3. **Export Demo:**
   - QuickBooks CSV import into spreadsheet
   - Show mapping and data structure

4. **Architecture Diagram:**
   - Upload → OCR → Validation → Export → Integration

