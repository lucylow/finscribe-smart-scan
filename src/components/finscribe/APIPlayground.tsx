import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { 
  Terminal, 
  Code, 
  Copy, 
  CheckCircle, 
  Play,
  Zap,
  Clock,
  Globe
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { ErrorHandler } from '@/lib/errorHandler';
import { getHealthStatus, APIError, NetworkError, TimeoutError } from '@/services/api';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0 }
};

const endpoints = [
  {
    method: 'POST',
    path: '/api/v1/analyze',
    description: 'Analyze a document (async job)',
    rateLimit: '100 req/min'
  },
  {
    method: 'POST',
    path: '/api/v1/compare',
    description: 'Compare fine-tuned vs baseline',
    rateLimit: '50 req/min'
  },
  {
    method: 'GET',
    path: '/api/v1/jobs/{job_id}',
    description: 'Check job status',
    rateLimit: '1000 req/min'
  },
  {
    method: 'GET',
    path: '/api/v1/health',
    description: 'Service health check',
    rateLimit: 'Unlimited'
  },
  {
    method: 'POST',
    path: '/api/v1/results/{id}/corrections',
    description: 'Submit corrections for active learning',
    rateLimit: '100 req/min'
  },
  {
    method: 'GET',
    path: '/admin/active_learning/export',
    description: 'Export training data (JSONL)',
    rateLimit: '10 req/min'
  },
];

const curlExample = `curl -X POST "http://localhost:8000/api/v1/analyze" \\
  -H "Content-Type: multipart/form-data" \\
  -F "file=@/path/to/invoice.pdf"`;

const pythonExample = `import requests

url = "http://localhost:8000/api/v1/analyze"

with open("invoice.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post(url, files=files)
    
result = response.json()
print(f"Job ID: {result['job_id']}")
print(f"Poll URL: {result['poll_url']}")

# Poll for results
import time
while True:
    status = requests.get(f"http://localhost:8000{result['poll_url']}").json()
    if status['status'] == 'completed':
        print(f"Results: {status['result']}")
        break
    elif status['status'] == 'failed':
        print(f"Error: {status['error']}")
        break
    time.sleep(1)`;

const responseExample = {
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "poll_url": "/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000",
  "status": "queued"
};

function APIPlayground() {
  const { toast } = useToast();
  const [copied, setCopied] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState('sk_demo_1234567890abcdef');
  const [testResult, setTestResult] = useState<string | null>(null);

  const handleCopy = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(id);
      toast({
        title: "Copied to clipboard",
        description: "Code snippet copied successfully",
      });
      setTimeout(() => setCopied(null), 2000);
    } catch (error) {
      ErrorHandler.handleError(error, {
        showToast: true,
        logToConsole: true,
        customMessage: 'Failed to copy to clipboard. Please try again.',
      });
    }
  };

  const handleTestConnection = async () => {
    setTestResult('connecting');
    
    try {
      // Actually test the API connection
      const healthStatus = await getHealthStatus();
      
      if (healthStatus.status === 'healthy') {
        setTestResult('success');
        toast({
          title: "Connection successful!",
          description: "API is responding normally",
        });
      } else {
        throw new Error('API health check failed');
      }
    } catch (error) {
      setTestResult(null);
      
      let errorMessage = 'Failed to connect to API.';
      
      if (error instanceof APIError) {
        errorMessage = `API Error: ${error.message}`;
      } else if (error instanceof NetworkError) {
        errorMessage = 'Network error. Please check your connection.';
      } else if (error instanceof TimeoutError) {
        errorMessage = 'Connection timeout. The API may be slow or unavailable.';
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }
      
      ErrorHandler.handleError(error, {
        showToast: true,
        logToConsole: true,
        customMessage: errorMessage,
      });
    }
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      {/* Header */}
      <motion.div variants={itemVariants} className="text-center mb-8">
        <h2 className="text-2xl md:text-3xl font-bold mb-2">
          API <span className="text-gradient">Playground</span>
        </h2>
        <p className="text-muted-foreground">Test and explore the FinScribe AI REST API</p>
      </motion.div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Endpoints List */}
        <motion.div variants={itemVariants}>
          <Card className="h-full">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Globe className="w-4 h-4 text-primary" />
                API Endpoints
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {endpoints.map((endpoint, index) => (
                <motion.div
                  key={endpoint.path}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="p-3 bg-muted/50 rounded-lg border hover:border-primary/30 transition-colors"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Badge 
                      variant={endpoint.method === 'POST' ? 'default' : 'secondary'}
                      className={`text-xs font-mono ${
                        endpoint.method === 'POST' 
                          ? 'bg-primary text-primary-foreground' 
                          : 'bg-secondary/20 text-secondary'
                      }`}
                    >
                      {endpoint.method}
                    </Badge>
                    <code className="text-sm font-mono text-foreground">{endpoint.path}</code>
                  </div>
                  <p className="text-xs text-muted-foreground">{endpoint.description}</p>
                  <div className="flex items-center gap-1 mt-1.5">
                    <Clock className="w-3 h-3 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">{endpoint.rateLimit}</span>
                  </div>
                </motion.div>
              ))}
            </CardContent>
          </Card>
        </motion.div>

        {/* Code Examples */}
        <motion.div variants={itemVariants}>
          <Card className="h-full">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Code className="w-4 h-4 text-primary" />
                Try the API
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="curl">
                <TabsList className="mb-4 bg-muted/50">
                  <TabsTrigger value="curl" className="gap-2">
                    <Terminal className="w-3 h-3" />
                    cURL
                  </TabsTrigger>
                  <TabsTrigger value="python" className="gap-2">
                    <Code className="w-3 h-3" />
                    Python
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="curl" className="space-y-4">
                  <div className="relative">
                    <pre className="bg-muted/70 p-4 rounded-lg text-xs font-mono overflow-x-auto border">
                      {curlExample}
                    </pre>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="absolute top-2 right-2 h-8 w-8"
                      onClick={() => handleCopy(curlExample, 'curl')}
                    >
                      {copied === 'curl' ? (
                        <CheckCircle className="w-4 h-4 text-success" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                  
                  <div>
                    <p className="text-xs text-muted-foreground mb-2">Response:</p>
                    <pre className="bg-muted/70 p-4 rounded-lg text-xs font-mono overflow-x-auto border">
                      {JSON.stringify(responseExample, null, 2)}
                    </pre>
                  </div>
                </TabsContent>

                <TabsContent value="python" className="space-y-4">
                  <div className="relative">
                    <pre className="bg-muted/70 p-4 rounded-lg text-xs font-mono overflow-x-auto max-h-64 border">
                      {pythonExample}
                    </pre>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="absolute top-2 right-2 h-8 w-8"
                      onClick={() => handleCopy(pythonExample, 'python')}
                    >
                      {copied === 'python' ? (
                        <CheckCircle className="w-4 h-4 text-success" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                </TabsContent>
              </Tabs>

              {/* API Key & Test */}
              <div className="mt-6 pt-4 border-t space-y-4">
                <div>
                  <label className="text-sm font-medium mb-2 block">API Key (demo)</label>
                  <Input 
                    type="password" 
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    className="font-mono text-sm"
                  />
                </div>
                
                <Button 
                  onClick={handleTestConnection}
                  disabled={testResult === 'connecting'}
                  className="w-full"
                >
                  {testResult === 'connecting' ? (
                    <>
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                        className="mr-2"
                      >
                        <Zap className="w-4 h-4" />
                      </motion.div>
                      Testing Connection...
                    </>
                  ) : testResult === 'success' ? (
                    <>
                      <CheckCircle className="w-4 h-4 mr-2 text-success" />
                      Connected Successfully!
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-2" />
                      Test API Connection
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </motion.div>
  );
}

export default APIPlayground;
