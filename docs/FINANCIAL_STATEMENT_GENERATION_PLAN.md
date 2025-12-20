# Financial Statement Generation Plan

## Overview

This document outlines the plan for adding financial statement generation capabilities to the synthetic data generator, supporting Income Statements, Balance Sheets, and Cash Flow Statements in both GAAP and IFRS formats.

## Statement Types

### 1. Income Statement (Profit & Loss / P&L)

#### Format Variations

**Single-Step Format**:
```
Revenue
  Operating Revenue
  Other Revenue
Expenses
  Cost of Goods Sold
  Operating Expenses
  Interest Expense
  Tax Expense
Net Income
```

**Multi-Step Format**:
```
Revenue
  - Cost of Goods Sold
= Gross Profit
  - Operating Expenses
    - SG&A
    - R&D
    - Depreciation
= Operating Income
  + Other Income
  - Interest Expense
= Income Before Tax
  - Income Tax
= Net Income
```

#### Key Features to Generate:
- Comparative periods (current year vs. previous year)
- Percentage columns (year-over-year changes)
- Section headers (Revenue, Expenses, etc.)
- Calculation lines (gross profit, operating income, etc.)
- Notes references (e.g., "See Note 5")

### 2. Balance Sheet

#### Format Variations

**Two-Column Format** (Assets | Liabilities + Equity):
```
ASSETS                    LIABILITIES AND EQUITY
Current Assets           Current Liabilities
  Cash                     Accounts Payable
  Accounts Receivable      Short-term Debt
  Inventory                Accrued Expenses
Non-Current Assets       Non-Current Liabilities
  Property, Plant           Long-term Debt
    & Equipment            Deferred Tax
  Intangibles            Equity
                         Common Stock
                         Retained Earnings
```

**Single-Column Format** (Stacked):
```
ASSETS
  Current Assets
    ...
  Non-Current Assets
    ...
LIABILITIES
  Current Liabilities
    ...
  Non-Current Liabilities
    ...
EQUITY
  ...
```

#### Key Features to Generate:
- Three main sections (Assets, Liabilities, Equity)
- Sub-categorizations (Current vs. Non-Current)
- Totals at each level
- Balance equation validation (Assets = Liabilities + Equity)
- Comparative periods

### 3. Cash Flow Statement

#### Method Variations

**Direct Method** (less common):
```
OPERATING ACTIVITIES
  Cash received from customers
  Cash paid to suppliers
  Cash paid to employees
  Interest paid
  Taxes paid
Net cash from operating activities

INVESTING ACTIVITIES
  Capital expenditures
  Asset sales
  Investments
Net cash from investing activities

FINANCING ACTIVITIES
  Debt issuance
  Debt repayment
  Equity issuance
  Dividends paid
Net cash from financing activities

Net change in cash
Beginning cash
Ending cash
```

**Indirect Method** (more common):
```
OPERATING ACTIVITIES
  Net Income
  Adjustments:
    Depreciation
    Amortization
    Changes in:
      Accounts Receivable
      Inventory
      Accounts Payable
      Accrued Expenses
Net cash from operating activities
...
```

#### Key Features to Generate:
- Three main sections (Operating, Investing, Financing)
- Adjustment lines for indirect method
- Negative amounts (often in parentheses)
- Reconciliation (beginning to ending cash)

## Regulatory Framework Support

### GAAP (US)
- Specific disclosure requirements
- Standardized format expectations
- Extensive footnotes
- Terminology: "Revenue", "Net Income", etc.

### IFRS (International)
- More principle-based
- Different classifications
- Terminology variations: "Turnover" vs "Revenue" in some regions
- Different segment reporting

## Implementation Plan

### Phase 1: Data Structures

Create dataclasses for each statement type:

```python
@dataclass
class IncomeStatementData:
    period: str
    format_type: str  # single_step, multi_step
    framework: str  # GAAP, IFRS
    revenue: Dict[str, float]
    cogs: Dict[str, float]
    operating_expenses: Dict[str, float]
    other_income: Dict[str, float]
    interest_expense: float
    tax_expense: float
    net_income: float
    comparative_period: Optional[Dict] = None

@dataclass
class BalanceSheetData:
    as_of_date: str
    framework: str  # GAAP, IFRS
    assets: Dict[str, Dict[str, float]]
    liabilities: Dict[str, Dict[str, float]]
    equity: Dict[str, float]
    comparative_period: Optional[Dict] = None

@dataclass
class CashFlowStatementData:
    period: str
    method: str  # direct, indirect
    framework: str  # GAAP, IFRS
    operating: Dict[str, float]
    investing: Dict[str, float]
    financing: Dict[str, float]
    net_change: float
    beginning_cash: float
    ending_cash: float
    comparative_period: Optional[Dict] = None
```

### Phase 2: Data Generation

Create generation methods:

1. `generate_income_statement_data()` - Generate realistic P&L data
2. `generate_balance_sheet_data()` - Generate balanced balance sheet
3. `generate_cash_flow_statement_data()` - Generate cash flow with proper reconciliation

### Phase 3: PDF Layout Generation

Create layout methods:

1. `_create_income_statement_layout()` - Render income statement
2. `_create_balance_sheet_layout()` - Render balance sheet (two-column or single-column)
3. `_create_cash_flow_statement_layout()` - Render cash flow statement

### Phase 4: Challenge Categories

Categorize financial statements by challenge:

- **complex_table**: Multi-step income statements, comparative periods
- **dense_data**: Detailed balance sheets, comprehensive cash flow statements
- **calculation_heavy**: Statements requiring intermediate calculations
- **regulatory_format**: GAAP vs IFRS format differences

### Phase 5: Integration

1. Update `SyntheticInvoiceGenerator` or create `SyntheticFinancialStatementGenerator`
2. Add configuration options for statement types and distributions
3. Generate ground truth JSON with perfect labels
4. Include challenge categories in metadata

## Recommended Distribution

### Statement Types
- Income Statement: 35%
- Balance Sheet: 30%
- Cash Flow Statement: 20%
- Combined/Annual Reports: 15%

### Frameworks
- GAAP: 50% (if targeting US market)
- IFRS: 50% (if targeting international market)

### Formats
- Income Statement:
  - Multi-step: 70%
  - Single-step: 30%
- Balance Sheet:
  - Two-column: 60%
  - Single-column: 40%
- Cash Flow Statement:
  - Indirect method: 80%
  - Direct method: 20%

## Example Usage

```python
generator = SyntheticFinancialStatementGenerator()

# Generate income statement
statement_data = generator.generate_income_statement(
    format_type='multi_step',
    framework='GAAP',
    include_comparative=True
)

# Generate balance sheet
balance_sheet = generator.generate_balance_sheet(
    format_type='two_column',
    framework='IFRS',
    include_comparative=True
)

# Generate cash flow statement
cash_flow = generator.generate_cash_flow_statement(
    method='indirect',
    framework='GAAP',
    include_comparative=True
)
```

## Challenges

1. **Balance Sheet Balancing**: Ensure Assets = Liabilities + Equity
2. **Cash Flow Reconciliation**: Properly link beginning to ending cash
3. **Comparative Periods**: Generate realistic year-over-year changes
4. **Footnotes**: Generate appropriate footnote references
5. **Regulatory Compliance**: Ensure formats match GAAP/IFRS requirements

## Next Steps

1. Implement data generation logic for each statement type
2. Create layout rendering methods
3. Add validation to ensure accounting equation balances
4. Generate ground truth annotations
5. Integrate with training pipeline

## References

- BDO Global: Model IFRS statements
- KPMG: Illustrative financial statements
- SEC EDGAR: Real GAAP-formatted statements
- See `DOCUMENT_DIVERSITY_GUIDE.md` for detailed format information

