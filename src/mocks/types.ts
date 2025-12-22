/**
 * Type definitions for mock data structures
 * These should match the API response types
 */

export interface MockInvoiceData {
  invoice_id?: string;
  vendor_name?: string;
  vendor_address?: string;
  vendor_tax_id?: string;
  vendor_contact?: string;
  invoice_number?: string;
  invoice_date?: string;
  po_number?: string;
  due_date?: string;
  line_items?: Array<{
    description?: string;
    quantity?: number;
    unit_price?: number;
    line_total?: number;
  }>;
  subtotal?: number;
  tax?: number;
  discount?: number;
  total?: number;
  validation_status?: 'success' | 'warning' | 'error';
  validation_issues?: Array<{
    severity: 'error' | 'warning';
    message: string;
  }>;
  confidence_scores?: Record<string, number>;
}

export interface MockDocumentStatus {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
  stage?: string;
  result?: MockInvoiceData;
  error?: string;
  document_id?: string;
}

export interface MockDashboardMetrics {
  overview: {
    documentsProcessed: number;
    averageProcessingTime: number;
    estimatedCostSavings: number;
    overallAccuracyScore: number;
    mrr: number;
    activeUsers: number;
    accuracy: number;
    documentsRemaining: number;
    quota: number;
  };
  usage: Array<{
    month: string;
    documents: number;
    apiCalls: number;
  }>;
  accuracyOverTime: Array<{
    version: string;
    date: string;
    accuracy: number;
  }>;
  errorDistribution: Array<{
    fieldType: string;
    errorCount: number;
  }>;
  automationMetrics: {
    humanInTheLoop: number;
    fullyAutomated: number;
  };
  subscription: {
    tier: string;
    billingCycle: string;
    nextBillingDate: string;
    monthlyPrice: number;
    status: string;
  };
  recentActivity: Array<{
    time: string;
    user: string;
    action: string;
    document?: string;
  }>;
  usageAlerts?: Array<{
    type: string;
    title: string;
    message: string;
    action?: string;
  }>;
}

