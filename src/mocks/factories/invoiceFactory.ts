import { faker } from '@faker-js/faker';
import { MockInvoiceData } from '../types';

/**
 * Factory for creating mock invoice data
 */
export const createMockInvoice = (overrides?: Partial<MockInvoiceData>): MockInvoiceData => {
  const baseData: MockInvoiceData = {
    invoice_id: faker.string.uuid(),
    vendor_name: faker.company.name(),
    vendor_address: faker.location.streetAddress({ useFullAddress: true }),
    vendor_tax_id: faker.string.alphanumeric(9),
    vendor_contact: faker.internet.email(),
    invoice_number: faker.string.alphanumeric(8).toUpperCase(),
    invoice_date: faker.date.recent({ days: 30 }).toISOString().split('T')[0],
    po_number: faker.string.alphanumeric(6).toUpperCase(),
    due_date: faker.date.future({ days: 30 }).toISOString().split('T')[0],
    line_items: Array.from({ length: faker.number.int({ min: 3, max: 8 }) }, () => ({
      description: faker.commerce.productName(),
      quantity: faker.number.int({ min: 1, max: 10 }),
      unit_price: parseFloat(faker.commerce.price({ min: 10, max: 500, dec: 2 })),
      line_total: 0, // Will be calculated
    })).map(item => ({
      ...item,
      line_total: item.quantity * item.unit_price,
    })),
    subtotal: 0, // Will be calculated
    tax: 0, // Will be calculated
    discount: 0,
    total: 0, // Will be calculated
    validation_status: 'success' as const,
    validation_issues: [],
    confidence_scores: {},
  };

  // Calculate totals
  baseData.subtotal = baseData.line_items!.reduce((sum, item) => sum + item.line_total!, 0);
  baseData.tax = parseFloat((baseData.subtotal * 0.08).toFixed(2)); // 8% tax
  baseData.total = parseFloat((baseData.subtotal + baseData.tax - baseData.discount).toFixed(2));

  // Generate confidence scores
  baseData.confidence_scores = {
    vendor_name: faker.number.float({ min: 0.85, max: 0.99, fractionDigits: 2 }),
    invoice_number: faker.number.float({ min: 0.90, max: 0.99, fractionDigits: 2 }),
    invoice_date: faker.number.float({ min: 0.88, max: 0.98, fractionDigits: 2 }),
    total: faker.number.float({ min: 0.92, max: 0.99, fractionDigits: 2 }),
  };

  // Apply overrides
  return { ...baseData, ...overrides };
};

/**
 * Create an invoice with validation errors (for testing error scenarios)
 */
export const createErrorInvoice = (): MockInvoiceData => {
  const baseInvoice = createMockInvoice();
  
  // Intentionally create arithmetic mismatch
  const incorrectTotal = baseInvoice.subtotal! + baseInvoice.tax! + 10; // Add extra $10 error
  
  return {
    ...baseInvoice,
    total: incorrectTotal,
    validation_status: 'error' as const,
    validation_issues: [
      {
        severity: 'error' as const,
        message: `Arithmetic Mismatch: Subtotal ($${baseInvoice.subtotal!.toFixed(2)}) + Tax ($${baseInvoice.tax!.toFixed(2)}) != Total ($${incorrectTotal.toFixed(2)})`,
      },
    ],
    confidence_scores: {
      ...baseInvoice.confidence_scores,
      total: 0.65, // Low confidence for total
    },
  };
};

/**
 * Create an invoice with warnings (low confidence scores)
 */
export const createWarningInvoice = (): MockInvoiceData => {
  const baseInvoice = createMockInvoice();
  
  return {
    ...baseInvoice,
    validation_status: 'warning' as const,
    validation_issues: [
      {
        severity: 'warning' as const,
        message: 'Confidence Score < 90%: Some fields may require manual review',
      },
    ],
    confidence_scores: {
      vendor_name: 0.85,
      invoice_number: 0.82,
      invoice_date: 0.88,
      total: 0.87,
    },
  };
};

/**
 * Create a complex invoice with many line items
 */
export const createComplexInvoice = (): MockInvoiceData => {
  return createMockInvoice({
    line_items: Array.from({ length: 20 }, () => ({
      description: faker.commerce.productName(),
      quantity: faker.number.int({ min: 1, max: 50 }),
      unit_price: parseFloat(faker.commerce.price({ min: 5, max: 1000, dec: 2 })),
      line_total: 0,
    })).map(item => ({
      ...item,
      line_total: item.quantity * item.unit_price,
    })),
  });
};

