const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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
  result?: any;
  error?: string;
}

// Poll interval configuration
const POLL_INTERVAL_MS = 500;
const MAX_POLL_ATTEMPTS = 120; // 60 seconds max

/**
 * Poll job status until completion or failure
 */
async function pollJobStatus(jobId: string): Promise<JobStatus> {
  let attempts = 0;
  
  while (attempts < MAX_POLL_ATTEMPTS) {
    const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get job status: ${response.statusText}`);
    }
    
    const status: JobStatus = await response.json();
    
    if (status.status === 'completed') {
      return status;
    }
    
    if (status.status === 'failed') {
      throw new Error(status.error || 'Job processing failed');
    }
    
    // Wait before next poll
    await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL_MS));
    attempts++;
  }
  
  throw new Error('Job timed out after 60 seconds');
}

/**
 * Analyze a document with the FinScribe AI pipeline
 */
export const analyzeDocument = async (formData: FormData) => {
  try {
    // Step 1: Submit the document for analysis
    const response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || error.error || 'Analysis failed');
    }
    
    const jobResponse: JobResponse = await response.json();
    
    // Step 2: Poll for completion
    const finalStatus = await pollJobStatus(jobResponse.job_id);
    
    // Step 3: Return result in format expected by frontend
    if (finalStatus.result) {
      return {
        success: true,
        job_id: jobResponse.job_id,
        data: finalStatus.result.data || finalStatus.result,
        validation: finalStatus.result.validation,
        metadata: finalStatus.result.metadata,
        raw_ocr_output: finalStatus.result.raw_ocr_output
      };
    }
    
    throw new Error('No result returned from analysis');
  } catch (error) {
    console.error('API Error:', error);
    throw error instanceof Error ? error : new Error('Analysis failed');
  }
};

/**
 * Compare document analysis with baseline model
 */
export const compareWithBaseline = async (formData: FormData) => {
  try {
    // Step 1: Submit the document for comparison
    const response = await fetch(`${API_BASE_URL}/api/v1/compare`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || error.error || 'Comparison failed');
    }
    
    const jobResponse: JobResponse = await response.json();
    
    // Step 2: Poll for completion
    const finalStatus = await pollJobStatus(jobResponse.job_id);
    
    // Step 3: Return result in format expected by frontend
    if (finalStatus.result) {
      return {
        success: true,
        job_id: jobResponse.job_id,
        fine_tuned_result: finalStatus.result.fine_tuned_result,
        baseline_result: finalStatus.result.baseline_result,
        comparison_summary: finalStatus.result.comparison_summary
      };
    }
    
    throw new Error('No result returned from comparison');
  } catch (error) {
    console.error('API Error:', error);
    throw error instanceof Error ? error : new Error('Comparison failed');
  }
};

/**
 * Get health status of the backend
 */
export const getHealthStatus = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/health`);
    return await response.json();
  } catch (error) {
    console.error('Health check failed:', error);
    return { status: 'unhealthy', error: error instanceof Error ? error.message : 'Unknown error' };
  }
};

/**
 * Submit corrections for active learning
 */
export const submitCorrections = async (resultId: string, corrections: Record<string, any>) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/results/${resultId}/corrections`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(corrections),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to submit corrections');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Corrections submission failed:', error);
    throw error instanceof Error ? error : new Error('Failed to submit corrections');
  }
};

/**
 * Get job status (for manual polling if needed)
 */
export const getJobStatus = async (jobId: string): Promise<JobStatus> => {
  const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}`);
  
  if (!response.ok) {
    throw new Error(`Failed to get job status: ${response.statusText}`);
  }
  
  return response.json();
};
