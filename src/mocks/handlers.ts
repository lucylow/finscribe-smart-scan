import { http, HttpResponse } from 'msw';
import { createMockInvoice, createErrorInvoice, createComplexInvoice } from './factories/invoiceFactory';
import { createMockDashboardMetrics } from './factories/dashboardFactory';
import { createMockDocumentStatus, createErrorDocumentStatus } from './factories/documentStatusFactory';

/**
 * Mock Service Worker handlers for API endpoints
 * Uses path patterns that work with any base URL
 */
export const handlers = [
  // Document upload endpoint
  http.post('*/api/v1/analyze', async ({ request }) => {
    const formData = await request.formData();
    const file = formData.get('file') as File;
    
    // Simulate processing delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Return job ID
    const jobId = `job-${Date.now()}`;
    const origin = new URL(request.url).origin;
    return HttpResponse.json({
      job_id: jobId,
      poll_url: `${origin}/api/v1/jobs/${jobId}`,
      status: 'pending',
    });
  }),

  // Job status polling endpoint
  http.get('*/api/v1/jobs/:jobId', ({ params, request }) => {
    const { jobId } = params;
    const scenario = new URL(window.location.href).searchParams.get('scenario');
    
    // Simulate different scenarios based on query parameter
    let status;
    if (scenario === 'error') {
      status = createErrorDocumentStatus();
      status.job_id = jobId as string;
    } else if (scenario === 'processing') {
      status = createMockDocumentStatus('processing');
      status.job_id = jobId as string;
    } else {
      status = createMockDocumentStatus('completed');
      status.job_id = jobId as string;
    }
    
    return HttpResponse.json(status);
  }),

  // Document result endpoint
  http.get('*/api/v1/document/result/:docId', ({ params, request }) => {
    const { docId } = params;
    const scenario = new URL(window.location.href).searchParams.get('scenario');
    
    let invoice;
    if (scenario === 'error') {
      invoice = createErrorInvoice();
    } else if (scenario === 'complex') {
      invoice = createComplexInvoice();
    } else {
      invoice = createMockInvoice();
    }
    
    invoice.invoice_id = docId as string;
    
    return HttpResponse.json({
      success: true,
      job_id: `job-${docId}`,
      data: invoice,
      validation: {
        is_valid: invoice.validation_status === 'success',
        issues: invoice.validation_issues || [],
      },
      metadata: {
        processed_at: new Date().toISOString(),
        confidence_scores: invoice.confidence_scores,
      },
    });
  }),

  // Dashboard metrics endpoint
  http.get('*/api/v1/dashboard/metrics', () => {
    const metrics = createMockDashboardMetrics();
    return HttpResponse.json(metrics);
  }),

  // Demo OCR endpoint
  http.post('*/api/v1/demo/ocr', async ({ request }) => {
    await new Promise(resolve => setTimeout(resolve, 800));
    
    return HttpResponse.json({
      text: 'Sample OCR text from mock service',
      regions: [
        {
          type: 'vendor',
          bbox: [10, 20, 100, 30],
          text: 'Sample Vendor Name',
          confidence: 0.95,
        },
      ],
      tables: [],
      meta: {
        backend: 'mock',
        duration: 0.8,
        latency_ms: 800,
        filename: 'mock-invoice.pdf',
      },
    });
  }),

  // Demo accept and queue endpoint
  http.post('*/api/v1/demo/accept_and_queue', async ({ request }) => {
    await new Promise(resolve => setTimeout(resolve, 300));
    
    const body = await request.json() as { doc_id?: string; corrected?: Record<string, unknown>; meta?: Record<string, unknown> };
    
    return HttpResponse.json({
      ok: true,
      queued: true,
      file: `queued-${body.doc_id || Date.now()}.jsonl`,
    });
  }),

  // Demo metrics endpoint
  http.get('*/api/v1/demo/metrics', () => {
    return HttpResponse.json({
      queued: 42,
      demo_mode: 'mock',
      ocr_backend: 'mock',
      queue_file: 'mock-queue.jsonl',
    });
  }),

  // Health check endpoint
  http.get('*/api/v1/health', () => {
    return HttpResponse.json({
      status: 'healthy',
      version: '1.0.0',
      mock: true,
    });
  }),
];

