const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const analyzeDocument = async (formData: FormData) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Analysis failed');
    }
    
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error instanceof Error ? error : new Error('Analysis failed');
  }
};

export const compareWithBaseline = async (formData: FormData) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/compare`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Comparison failed');
    }
    
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error instanceof Error ? error : new Error('Comparison failed');
  }
};

export const getHealthStatus = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/health`);
    return await response.json();
  } catch (error) {
    console.error('Health check failed:', error);
    return { status: 'unhealthy', error: error instanceof Error ? error.message : 'Unknown error' };
  }
};
