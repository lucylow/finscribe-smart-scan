/**
 * Error scenario generators for testing validation and error handling
 */
import { faker } from '@faker-js/faker';
import { MockInvoiceData } from '../types';
import { createMockInvoice } from '../factories/invoiceFactory';

/**
 * Create invoice with arithmetic mismatch error
 */
export const createArithmeticMismatchInvoice = (): MockInvoiceData => {
  const base = createMockInvoice();
  const incorrectTotal = base.subtotal! + base.tax! + faker.number.float({ min: 5, max: 50, fractionDigits: 2 });
  
  return {
    ...base,
    total: parseFloat(incorrectTotal.toFixed(2)),
    validation_status: 'error',
    validation_issues: [
      {
        severity: 'error',
        message: `Arithmetic Mismatch: Subtotal ($${base.subtotal!.toFixed(2)}) + Tax ($${base.tax!.toFixed(2)}) != Total ($${incorrectTotal.toFixed(2)})`,
      },
    ],
  };
};

/**
 * Create invoice with low confidence scores (warning scenario)
 */
export const createLowConfidenceInvoice = (): MockInvoiceData => {
  const base = createMockInvoice();
  
  return {
    ...base,
    validation_status: 'warning',
    validation_issues: [
      {
        severity: 'warning',
        message: 'Confidence Score < 90%: Some fields may require manual review',
      },
    ],
    confidence_scores: {
      vendor_name: 0.78,
      invoice_number: 0.82,
      invoice_date: 0.75,
      total: 0.81,
    },
  };
};

