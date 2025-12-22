import { faker } from '@faker-js/faker';
import { MockDocumentStatus, MockInvoiceData } from '../types';
import { createMockInvoice, createErrorInvoice, createWarningInvoice } from './invoiceFactory';

/**
 * Factory for creating mock document status
 */
export const createMockDocumentStatus = (
  status: 'pending' | 'processing' | 'completed' | 'failed' = 'pending',
  resultOverride?: MockInvoiceData
): MockDocumentStatus => {
  const jobId = faker.string.uuid();
  const baseStatus: MockDocumentStatus = {
    job_id: jobId,
    status,
    progress: status === 'completed' ? 100 : status === 'failed' ? 0 : faker.number.int({ min: 0, max: 95 }),
    stage: status === 'processing' ? faker.helpers.arrayElement(['OCR', 'Parsing', 'Validation']) : undefined,
    document_id: faker.string.uuid(),
  };

  if (status === 'completed') {
    baseStatus.result = resultOverride || createMockInvoice({
      invoice_id: baseStatus.document_id,
    });
  } else if (status === 'failed') {
    baseStatus.error = faker.helpers.arrayElement([
      'OCR processing failed',
      'Invalid document format',
      'Network timeout',
      'Parsing error',
    ]);
  }

  return baseStatus;
};

/**
 * Create a document status with error result (for testing error scenarios)
 */
export const createErrorDocumentStatus = (): MockDocumentStatus => {
  return createMockDocumentStatus('completed', createErrorInvoice());
};

/**
 * Create a document status with warning result (for testing warning scenarios)
 */
export const createWarningDocumentStatus = (): MockDocumentStatus => {
  return createMockDocumentStatus('completed', createWarningInvoice());
};

