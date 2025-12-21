# QuickBooks CSV Mapping Guide

This document explains how the exported `finscribe_qb_export.csv` maps to QuickBooks Online import fields (Sales Receipts / Invoices).

---

## Export Format

FinScribe exports a QuickBooks-compatible CSV with the following columns:

| Column | Description | QuickBooks Field |
|--------|-------------|------------------|
| Customer | Vendor/Client name | Customer |
| Invoice Number | Invoice identifier | Invoice Number |
| Invoice Date | Issue date (YYYY-MM-DD) | Invoice Date |
| Item | Product/Service name | Item |
| Description | Line item description | Description |
| Quantity | Item quantity | Qty |
| Rate | Unit price | Rate |
| Amount | Line total | Amount |
| Taxable | Tax status (TRUE/FALSE) | Taxable |

---

## Quick Steps to Import

### 1. Export from FinScribe
- Navigate to the Export panel in the demo UI
- Click "Download QuickBooks CSV"
- Save the file as `finscribe_qb_export.csv`

### 2. Prepare for QuickBooks Import
- Open the CSV in Excel or Google Sheets
- Verify data looks correct (dates, amounts, customer names)
- Save as CSV (UTF-8 encoding recommended)

### 3. Import into QuickBooks Online

**Option A: Sales Receipt Import**
1. Go to **Gear** → **Import Data** → **Sales Receipts**
2. Upload `finscribe_qb_export.csv`
3. Map columns:
   - Customer → Customer
   - Invoice Number → Reference Number
   - Invoice Date → Date
   - Item → Product/Service
   - Description → Description
   - Quantity → Qty
   - Rate → Rate
   - Amount → Amount
   - Taxable → Taxable
4. Review and import

**Option B: Invoice Import**
1. Go to **Gear** → **Import Data** → **Invoices**
2. Follow similar mapping as above
3. Note: QuickBooks may require additional fields (terms, payment method)

---

## Column Mapping Details

### Customer Field
- **Source:** Extracted from `vendor.name` or `client.name` in FinScribe output
- **QuickBooks:** Must match an existing Customer in QuickBooks, or will be created
- **Note:** If customer doesn't exist, QuickBooks will prompt to create it during import

### Invoice Number
- **Source:** `invoice_number` field from FinScribe
- **QuickBooks:** Used as Reference Number or Invoice Number
- **Validation:** QuickBooks may check for duplicates

### Invoice Date
- **Format:** YYYY-MM-DD (e.g., 2024-03-15)
- **QuickBooks:** Automatically parsed as date
- **Note:** Ensure dates are within valid accounting periods

### Item Field
- **FinScribe Default:** "ImportedItem"
- **QuickBooks:** Must match an existing Product/Service item
- **Recommendation:** 
  - Create a generic "Service" or "Product" item in QuickBooks first
  - Or update the CSV to use existing item names before import

### Description
- **Source:** Line item `description` from FinScribe
- **QuickBooks:** Free-form text field
- **Note:** Can be customized in the CSV before import

### Quantity, Rate, Amount
- **Source:** Extracted from line items (`quantity`, `unit_price`, `line_total`)
- **QuickBooks:** Validates that `Amount = Quantity × Rate`
- **Note:** FinScribe validates arithmetic before export

### Taxable
- **Default:** TRUE
- **QuickBooks:** Boolean field for tax calculation
- **Note:** Can be edited in CSV before import if needed

---

## Example CSV Output

```csv
Customer,Invoice Number,Invoice Date,Item,Description,Quantity,Rate,Amount,Taxable
TechCorp Inc.,INV-2024-001,2024-03-15,ImportedItem,Professional Services,10,150.00,1500.00,TRUE
TechCorp Inc.,INV-2024-001,2024-03-15,ImportedItem,Consulting Hours,5,200.00,1000.00,TRUE
```

---

## Troubleshooting

### Issue: Customer not found
**Solution:** Create the customer in QuickBooks first, or update the CSV to use existing customer names.

### Issue: Item not found
**Solution:** Create a generic "Service" or "Product" item in QuickBooks, or update the CSV to use existing item names.

### Issue: Date format error
**Solution:** Ensure dates are in YYYY-MM-DD format. QuickBooks may accept MM/DD/YYYY, but YYYY-MM-DD is more reliable.

### Issue: Amount mismatch
**Solution:** FinScribe validates arithmetic before export. If QuickBooks still shows errors, check for rounding differences (QuickBooks uses 2 decimal places).

### Issue: Duplicate invoice numbers
**Solution:** QuickBooks may reject duplicates. Either update invoice numbers in the CSV or handle duplicates in QuickBooks import settings.

---

## Advanced Customization

### Custom Item Names
Edit the CSV before import to use specific QuickBooks item names:
```csv
Customer,Invoice Number,Invoice Date,Item,Description,Quantity,Rate,Amount,Taxable
TechCorp Inc.,INV-001,2024-03-15,Service,Professional Services,10,150.00,1500.00,TRUE
```

### Tax Configuration
Update the `Taxable` column based on your tax rules:
```csv
Customer,Invoice Number,Invoice Date,Item,Description,Quantity,Rate,Amount,Taxable
TechCorp Inc.,INV-001,2024-03-15,Service,Professional Services,10,150.00,1500.00,FALSE
```

### Multiple Line Items
Each line item from FinScribe becomes a separate row in the CSV. QuickBooks will group them by Invoice Number during import.

---

## Notes

- QuickBooks import features may vary by region and account type
- Some QuickBooks plans may have import limitations
- Always review imported data in QuickBooks before finalizing
- Consider importing a small test batch first
- FinScribe exports are designed for QuickBooks Online; desktop versions may require different formats

---

## Support

For issues with:
- **FinScribe exports:** Check the Export panel in the demo UI or API docs
- **QuickBooks import:** Refer to QuickBooks Online help or support
- **Data mapping:** Review the FinScribe output JSON to understand field mappings

