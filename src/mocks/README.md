# Mock Data Layer

This directory contains the mock data layer for the FinScribe Smart Scan frontend. It provides type-safe mock data generation and API mocking using Mock Service Worker (MSW).

## Structure

```
src/mocks/
├── types.ts                  # TypeScript type definitions
├── factories/                # Data factory functions
│   ├── invoiceFactory.ts     # Invoice data generation
│   ├── dashboardFactory.ts   # Dashboard metrics generation
│   └── documentStatusFactory.ts # Document status generation
├── scenarios/                # Pre-defined test scenarios
│   └── errorScenarios.ts     # Error and edge case scenarios
├── handlers.ts               # MSW request handlers
├── browser.ts                # Browser MSW setup
├── index.ts                  # Main exports
└── README.md                 # This file
```

## Usage

### Enabling Mock API

Set the `VITE_USE_MOCK_API` environment variable to `true` in your `.env` file:

```env
VITE_USE_MOCK_API=true
```

The mock service worker will automatically start in development mode when this variable is set.

### Using Mock Factories

```typescript
import { createMockInvoice, createErrorInvoice } from '@/mocks';

// Create a standard invoice
const invoice = createMockInvoice();

// Create an invoice with validation errors
const errorInvoice = createErrorInvoice();

// Create a custom invoice with overrides
const customInvoice = createMockInvoice({
  vendor_name: 'Custom Vendor',
  total: 1500.00,
});
```

### API Scenarios

Mock handlers support scenario-based responses via query parameters:

- `?scenario=error` - Returns error invoice
- `?scenario=complex` - Returns complex invoice with many line items
- `?scenario=processing` - Returns processing status

## Factories

### Invoice Factory

- `createMockInvoice(overrides?)` - Creates a standard valid invoice
- `createErrorInvoice()` - Creates an invoice with validation errors
- `createWarningInvoice()` - Creates an invoice with low confidence warnings
- `createComplexInvoice()` - Creates an invoice with many line items

### Dashboard Factory

- `createMockDashboardMetrics()` - Creates complete dashboard metrics

### Document Status Factory

- `createMockDocumentStatus(status, resultOverride?)` - Creates document status
- `createErrorDocumentStatus()` - Creates a completed status with error result
- `createWarningDocumentStatus()` - Creates a completed status with warning result

## Testing

Mock data factories are designed to be used in component tests:

```typescript
import { render } from '@testing-library/react';
import { createErrorInvoice } from '@/mocks';
import CorrectionsPanel from './CorrectionsPanel';

test('displays validation errors', () => {
  const errorInvoice = createErrorInvoice();
  const { getByText } = render(<CorrectionsPanel data={errorInvoice} />);
  expect(getByText(/arithmetic mismatch/i)).toBeInTheDocument();
});
```

## Type Safety

All mock factories return objects that conform to the TypeScript interfaces defined in `types.ts`. This ensures type safety across the application.

## Notes

- Mock Service Worker only runs in development when `VITE_USE_MOCK_API=true`
- In production builds, the mock layer is completely excluded
- Mock handlers use wildcard patterns (`*/api/v1/...`) to work with any base URL

