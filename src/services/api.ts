const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Result types
interface AnalysisResultData {
  data?: Record<string, unknown>;
  validation?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  markdown_output?: string;
  raw_ocr_output?: Record<string, unknown>;
  extracted_data?: unknown[];
  document_id?: string;
  status?: string;
  active_learning_ready?: boolean;
}

interface ComparisonResultData {
  comparison?: Record<string, unknown>;
  document1?: Record<string, unknown>;
  document2?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

interface BaselineComparisonResultData {
  fine_tuned_result?: Record<string, unknown>;
  baseline_result?: Record<string, unknown>;
  comparison_summary?: Record<string, unknown>;
}

// Job status types
interface JobResponse {
  job_id: string;
  poll_url: string;
  status: string;
}

interface JobStatus {
  job_id: string;
  status: string;
  progress: number;
  stage?: string;
  result?: AnalysisResultData | ComparisonResultData | BaselineComparisonResultData;
  error?: string;
}

// Poll interval configuration
const POLL_INTERVAL_MS = 500;
const MAX_POLL_ATTEMPTS = 120; // 60 seconds max
const REQUEST_TIMEOUT_MS = 300000; // 5 minutes for upload/processing

// Custom error classes
export class APIError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'APIError';
  }
}

export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NetworkError';
  }
}

export class TimeoutError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'TimeoutError';
  }
}

/**
 * Poll job status until completion or failure
 */
async function pollJobStatus(jobId: string): Promise<JobStatus> {
  let attempts = 0;
  
  while (attempts < MAX_POLL_ATTEMPTS) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout per poll
      
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}`, {
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
        
        if (!response.ok) {
          if (response.status === 404) {
            throw new APIError(
              `Job not found: ${jobId}`,
              response.status,
              await response.json().catch(() => null)
            );
          }
          const errorData = await response.json().catch(() => ({ detail: response.statusText }));
          throw new APIError(
            errorData.error || errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
            response.status,
            errorData
          );
        }
        
        const status: JobStatus = await response.json();
        
        if (status.status === 'completed') {
          return status;
        }
        
        if (status.status === 'failed') {
          throw new APIError(
            status.error || 'Job processing failed',
            500,
            { jobId, status }
          );
        }
        
        // Wait before next poll
        await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL_MS));
        attempts++;
      } catch (error: unknown) {
        clearTimeout(timeoutId);
        const err = error as { name?: string };
        if (err.name === 'AbortError') {
          throw new TimeoutError('Poll request timed out');
        }
        throw error;
      }
    } catch (error: unknown) {
      if (error instanceof APIError || error instanceof TimeoutError) {
        throw error;
      }
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new NetworkError('Network error while polling job status. Please check your connection.');
      }
      throw error;
    }
  }
  
  throw new TimeoutError(`Job timed out after ${MAX_POLL_ATTEMPTS * POLL_INTERVAL_MS / 1000} seconds`);
}

/**
 * Analyze a document with the FinScribe AI pipeline
 */
export const analyzeDocument = async (formData: FormData) => {
  try {
    // Step 1: Submit the document for analysis
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    
    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
    } catch (error: unknown) {
      clearTimeout(timeoutId);
      const err = error as { name?: string; message?: string };
      if (err.name === 'AbortError') {
        throw new TimeoutError('Upload request timed out. The file may be too large or the connection is slow.');
      }
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new NetworkError('Network error. Please check your connection and try again.');
      }
      throw error;
    }
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      
      // Handle specific error cases
      if (response.status === 400) {
        throw new APIError(
          errorData.error || errorData.detail || 'Invalid file. Please check file type and size.',
          response.status,
          errorData
        );
      }
      if (response.status === 413) {
        throw new APIError(
          'File too large. Please use a smaller file.',
          response.status,
          errorData
        );
      }
      
      throw new APIError(
        errorData.error || errorData.detail || `Analysis request failed: ${response.statusText}`,
        response.status,
        errorData
      );
    }
    
    const jobResponse: JobResponse = await response.json();
    
    if (!jobResponse.job_id) {
      throw new APIError('Invalid response: missing job_id', 500);
    }
    
    // Step 2: Poll for completion
    const finalStatus = await pollJobStatus(jobResponse.job_id);
    
    // Step 3: Return result in format expected by frontend
    if (finalStatus.result) {
      const result = finalStatus.result as AnalysisResultData;
      return {
        success: true,
        job_id: jobResponse.job_id,
        data: result.data || result,
        validation: result.validation,
        metadata: result.metadata,
        markdown_output: result.markdown_output,
        raw_ocr_output: result.raw_ocr_output
      };
    }
    
    throw new APIError('No result returned from analysis', 500);
  } catch (error) {
    console.error('API Error:', error);
    if (error instanceof APIError || error instanceof NetworkError || error instanceof TimeoutError) {
      throw error;
    }
    throw new APIError(error instanceof Error ? error.message : 'Analysis failed');
  }
};

/**
 * Compare two documents side-by-side (e.g., quote vs invoice)
 */
export const compareDocuments = async (file1: File, file2: File) => {
  try {
    const formData = new FormData();
    formData.append('file1', file1);
    formData.append('file2', file2);

    // Step 1: Submit both documents for comparison
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    
    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}/api/v1/compare-documents`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
    } catch (error: unknown) {
      clearTimeout(timeoutId);
      const err = error as { name?: string; message?: string };
      if (err.name === 'AbortError') {
        throw new TimeoutError('Upload request timed out. The files may be too large or the connection is slow.');
      }
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new NetworkError('Network error. Please check your connection and try again.');
      }
      throw error;
    }
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      
      if (response.status === 400) {
        throw new APIError(
          errorData.error || errorData.detail || 'Invalid file(s). Please check file types and sizes.',
          response.status,
          errorData
        );
      }
      if (response.status === 413) {
        throw new APIError(
          'File(s) too large. Please use smaller files.',
          response.status,
          errorData
        );
      }
      
      throw new APIError(
        errorData.error || errorData.detail || `Document comparison request failed: ${response.statusText}`,
        response.status,
        errorData
      );
    }
    
    const jobResponse: JobResponse = await response.json();
    
    if (!jobResponse.job_id) {
      throw new APIError('Invalid response: missing job_id', 500);
    }
    
    // Step 2: Poll for completion
    const finalStatus = await pollJobStatus(jobResponse.job_id);
    
    // Step 3: Return result in format expected by frontend
    if (finalStatus.result) {
      const result = finalStatus.result as ComparisonResultData;
      return {
        success: true,
        job_id: jobResponse.job_id,
        comparison: result.comparison,
        document1: result.document1,
        document2: result.document2,
        metadata: result.metadata
      };
    }
    
    throw new APIError('No result returned from document comparison', 500);
  } catch (error) {
    console.error('API Error:', error);
    if (error instanceof APIError || error instanceof NetworkError || error instanceof TimeoutError) {
      throw error;
    }
    throw new APIError(error instanceof Error ? error.message : 'Document comparison failed');
  }
};

/**
 * Compare document analysis with baseline model
 */
export const compareWithBaseline = async (formData: FormData) => {
  try {
    // Step 1: Submit the document for comparison
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    
    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}/api/v1/compare`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
    } catch (error: unknown) {
      clearTimeout(timeoutId);
      const err = error as { name?: string; message?: string };
      if (err.name === 'AbortError') {
        throw new TimeoutError('Upload request timed out. The file may be too large or the connection is slow.');
      }
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new NetworkError('Network error. Please check your connection and try again.');
      }
      throw error;
    }
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      
      if (response.status === 400) {
        throw new APIError(
          errorData.error || errorData.detail || 'Invalid file. Please check file type and size.',
          response.status,
          errorData
        );
      }
      if (response.status === 413) {
        throw new APIError(
          'File too large. Please use a smaller file.',
          response.status,
          errorData
        );
      }
      
      throw new APIError(
        errorData.error || errorData.detail || `Comparison request failed: ${response.statusText}`,
        response.status,
        errorData
      );
    }
    
    const jobResponse: JobResponse = await response.json();
    
    if (!jobResponse.job_id) {
      throw new APIError('Invalid response: missing job_id', 500);
    }
    
    // Step 2: Poll for completion
    const finalStatus = await pollJobStatus(jobResponse.job_id);
    
    // Step 3: Return result in format expected by frontend
    if (finalStatus.result) {
      const result = finalStatus.result as BaselineComparisonResultData;
      return {
        success: true,
        job_id: jobResponse.job_id,
        fine_tuned_result: result.fine_tuned_result,
        baseline_result: result.baseline_result,
        comparison_summary: result.comparison_summary
      };
    }
    
    throw new APIError('No result returned from comparison', 500);
  } catch (error) {
    console.error('API Error:', error);
    if (error instanceof APIError || error instanceof NetworkError || error instanceof TimeoutError) {
      throw error;
    }
    throw new APIError(error instanceof Error ? error.message : 'Comparison failed');
  }
};

/**
 * Get health status of the backend
 */
export const getHealthStatus = async () => {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000); // 5s timeout for health check
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/health`, {
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        return { 
          status: 'unhealthy', 
          error: `HTTP ${response.status}: ${response.statusText}` 
        };
      }
      
      return await response.json();
    } catch (error: unknown) {
      clearTimeout(timeoutId);
      const err = error as { name?: string };
      if (err.name === 'AbortError') {
        return { status: 'unhealthy', error: 'Health check timed out' };
      }
      if (error instanceof TypeError && error.message.includes('fetch')) {
        return { status: 'unhealthy', error: 'Network error - backend may be unreachable' };
      }
      throw error;
    }
  } catch (error) {
    console.error('Health check failed:', error);
    return { 
      status: 'unhealthy', 
      error: error instanceof Error ? error.message : 'Unknown error' 
    };
  }
};

/**
 * Submit corrections for active learning
 */
export const submitCorrections = async (resultId: string, corrections: Record<string, unknown>) => {
  try {
    if (!resultId) {
      throw new APIError('Result ID is required');
    }
    
    if (!corrections || Object.keys(corrections).length === 0) {
      throw new APIError('Corrections cannot be empty');
    }
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout
    
    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}/api/v1/results/${resultId}/corrections`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(corrections),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
    } catch (error: unknown) {
      clearTimeout(timeoutId);
      const err = error as { name?: string };
      if (err.name === 'AbortError') {
        throw new TimeoutError('Request timed out');
      }
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new NetworkError('Network error. Please check your connection.');
      }
      throw error;
    }
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      
      if (response.status === 404) {
        throw new APIError(
          `Result not found: ${resultId}`,
          response.status,
          errorData
        );
      }
      
      throw new APIError(
        errorData.error || errorData.detail || 'Failed to submit corrections',
        response.status,
        errorData
      );
    }
    
    return await response.json();
  } catch (error) {
    console.error('Corrections submission failed:', error);
    if (error instanceof APIError || error instanceof NetworkError || error instanceof TimeoutError) {
      throw error;
    }
    throw new APIError(error instanceof Error ? error.message : 'Failed to submit corrections');
  }
};

/**
 * Get job status (for manual polling if needed)
 */
export const getJobStatus = async (jobId: string): Promise<JobStatus> => {
  if (!jobId) {
    throw new APIError('Job ID is required');
  }
  
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout
    
    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}`, {
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
    } catch (error: unknown) {
      clearTimeout(timeoutId);
      const err = error as { name?: string };
      if (err.name === 'AbortError') {
        throw new TimeoutError('Request timed out');
      }
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new NetworkError('Network error. Please check your connection.');
      }
      throw error;
    }
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      
      if (response.status === 404) {
        throw new APIError(
          `Job not found: ${jobId}`,
          response.status,
          errorData
        );
      }
      
      throw new APIError(
        errorData.error || errorData.detail || `Failed to get job status: ${response.statusText}`,
        response.status,
        errorData
      );
    }
    
    return response.json();
  } catch (error) {
    if (error instanceof APIError || error instanceof NetworkError || error instanceof TimeoutError) {
      throw error;
    }
    throw new APIError(error instanceof Error ? error.message : 'Failed to get job status');
  }
};
