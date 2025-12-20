import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { 
  CloudUpload, 
  GitCompare, 
  Download, 
  Zap, 
  X,
  FileJson,
  FileSpreadsheet,
  FileText,
  Sparkles,
  ArrowRight,
  CheckCircle,
  Menu,
  PanelLeftClose,
  PanelLeft
} from 'lucide-react';
import DocumentUpload from '@/components/finscribe/DocumentUpload';
import ProcessingStatus from '@/components/finscribe/ProcessingStatus';
import ResultsDisplay from '@/components/finscribe/ResultsDisplay';
import ComparisonView from '@/components/finscribe/ComparisonView';
import ModelInfo from '@/components/finscribe/ModelInfo';
import SemanticRegionVisualization from '@/components/finscribe/SemanticRegionVisualization';
import PerformanceMetrics from '@/components/finscribe/PerformanceMetrics';
import APIPlayground from '@/components/finscribe/APIPlayground';
import AppSidebar from '@/components/finscribe/AppSidebar';
import { analyzeDocument, compareWithBaseline } from '@/services/api';
import { ErrorHandler } from '@/lib/errorHandler';

interface AnalysisResult {
  success: boolean;
  job_id: string;
  data?: Record<string, unknown>;
  validation?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  markdown_output?: string;
  raw_ocr_output?: Record<string, unknown>;
}

interface ComparisonResult {
  success: boolean;
  job_id: string;
  fine_tuned_result?: Record<string, unknown>;
  baseline_result?: Record<string, unknown>;
  comparison_summary?: Record<string, unknown>;
}

const FinScribe = () => {
  const [activeMode, setActiveMode] = useState('upload');
  const [file, setFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processing, setProcessing] = useState(false);
  const [results, setResults] = useState<AnalysisResult | null>(null);
  const [comparisonResults, setComparisonResults] = useState<ComparisonResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleFileSelect = useCallback((selectedFile: File | null) => {
    setFile(selectedFile);
    setError(null);
    setResults(null);
    setComparisonResults(null);
  }, []);

  const handleAnalyze = async () => {
    if (!file) {
      setError('Please select a file first');
      toast.error('No file selected', {
        description: 'Please upload a document to analyze.',
      });
      return;
    }

    setProcessing(true);
    setError(null);
    setUploadProgress(0);
    
    let progressInterval: NodeJS.Timeout | null = null;
    
    try {
      // Simulate progress updates during upload
      progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 85) {
            return 85; // Hold at 85% until actual completion
          }
          return prev + Math.random() * 5; // Gradual progress
        });
      }, 200);

      const formData = new FormData();
      formData.append('file', file);

      toast.info('Starting analysis...', {
        description: 'Your document is being processed.',
        duration: 2000,
      });

      const response = await analyzeDocument(formData);
      
      if (progressInterval) {
        clearInterval(progressInterval);
      }
      setUploadProgress(100);
      
      setResults(response);
      setActiveMode('results');
      
      toast.success('Analysis complete!', {
        description: 'Your document has been successfully analyzed.',
        duration: 3000,
      });
    } catch (err) {
      if (progressInterval) {
        clearInterval(progressInterval);
      }
      const errorMessage = ErrorHandler.handleError(err, {
        showToast: false, // We'll show it in the UI instead
        logToConsole: true,
      });
      setError(errorMessage);
      setUploadProgress(0);
    } finally {
      setProcessing(false);
      // Reset progress after a delay
      setTimeout(() => {
        if (!processing) {
          setUploadProgress(0);
        }
      }, 2000);
    }
  };

  const handleCompare = async () => {
    if (!file) {
      setError('Please select a file first');
      toast.error('No file selected', {
        description: 'Please upload a document to compare.',
      });
      return;
    }

    setProcessing(true);
    setError(null);
    setUploadProgress(0);
    
    try {
      // Simulate progress for comparison
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 85) {
            return 85;
          }
          return prev + Math.random() * 5;
        });
      }, 200);

      const formData = new FormData();
      formData.append('file', file);

      toast.info('Comparing models...', {
        description: 'Analyzing with both fine-tuned and baseline models.',
        duration: 2000,
      });

      const response = await compareWithBaseline(formData);
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      setComparisonResults(response);
      setActiveMode('compare');
      
      toast.success('Comparison complete!', {
        description: 'Model comparison results are ready.',
        duration: 3000,
      });
    } catch (err) {
      const errorMessage = ErrorHandler.handleError(err, {
        showToast: false,
        logToConsole: true,
      });
      setError(errorMessage);
      setUploadProgress(0);
    } finally {
      setProcessing(false);
      setTimeout(() => {
        if (!processing) {
          setUploadProgress(0);
        }
      }, 2000);
    }
  };

  const handleDownloadResults = (format: 'json' | 'csv' = 'json') => {
    if (!results) {
      ErrorHandler.handleError(new Error('No results available to download'), {
        showToast: true,
        logToConsole: true,
      });
      return;
    }
    
    try {
      let dataStr: string;
      let mimeType: string;
      let extension: string;

      if (format === 'csv') {
        const headers = ['Field', 'Value'];
        const rows = Object.entries(results.data || {}).map(([key, value]) => 
          [key, typeof value === 'object' ? JSON.stringify(value) : String(value)]
        );
        dataStr = [headers, ...rows].map(row => row.join(',')).join('\n');
        mimeType = 'text/csv';
        extension = 'csv';
      } else {
        if (!results.data) {
          throw new Error('Results data is missing');
        }
        dataStr = JSON.stringify(results.data, null, 2);
        mimeType = 'application/json';
        extension = 'json';
      }
      
      const dataUri = `data:${mimeType};charset=utf-8,${encodeURIComponent(dataStr)}`;
      const exportFileDefaultName = `finscribe-analysis-${Date.now()}.${extension}`;
      
      const linkElement = document.createElement('a');
      linkElement.setAttribute('href', dataUri);
      linkElement.setAttribute('download', exportFileDefaultName);
      document.body.appendChild(linkElement);
      linkElement.click();
      document.body.removeChild(linkElement);
      
      toast.success('Download started', {
        description: `Your ${format.toUpperCase()} file is downloading.`,
        duration: 2000,
      });
    } catch (error) {
      ErrorHandler.handleError(error, {
        showToast: true,
        logToConsole: true,
        customMessage: 'Failed to download results. Please try again.',
      });
    }
  };

  const renderContent = () => {
    switch (activeMode) {
      case 'upload':
        return (
          <motion.div
            key="upload"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <div className="text-center mb-8">
              <h2 className="text-3xl md:text-4xl font-bold mb-3">
                Upload & <span className="text-gradient">Analyze</span>
              </h2>
              <p className="text-muted-foreground max-w-lg mx-auto">
                Upload invoices, receipts, or statements to extract perfect structured data with AI
              </p>
            </div>

            <div className="grid lg:grid-cols-3 gap-6 lg:gap-8">
              <div className="lg:col-span-2 space-y-4">
                <DocumentUpload onFileSelect={handleFileSelect} file={file} />
                
                <AnimatePresence>
                  {(file || processing) && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="overflow-hidden"
                    >
                      <ProcessingStatus progress={uploadProgress} processing={processing} />
                    </motion.div>
                  )}
                </AnimatePresence>

                <div className="flex flex-col sm:flex-row flex-wrap gap-3 justify-center pt-4">
                  <Button
                    size="lg"
                    onClick={handleAnalyze}
                    disabled={!file || processing}
                    className="shadow-btn min-w-full sm:min-w-[180px] group"
                    aria-label="Analyze document with AI"
                  >
                    {processing ? (
                      <>
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                          className="mr-2"
                          aria-hidden="true"
                        >
                          <Sparkles className="w-4 h-4" />
                        </motion.div>
                        <span>Processing...</span>
                      </>
                    ) : (
                      <>
                        <CloudUpload className="w-4 h-4 mr-2" aria-hidden="true" />
                        <span>Analyze with AI</span>
                        <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" aria-hidden="true" />
                      </>
                    )}
                  </Button>
                  
                  <Button
                    variant="outline"
                    size="lg"
                    onClick={handleCompare}
                    disabled={!file || processing}
                    className="min-w-full sm:min-w-[160px]"
                    aria-label="Compare with baseline model"
                  >
                    <GitCompare className="w-4 h-4 mr-2" aria-hidden="true" />
                    <span>Compare Models</span>
                  </Button>
                </div>
              </div>

              <div className="lg:block hidden">
                <Card className="h-full bg-gradient-to-br from-muted/50 to-muted/30 border-muted sticky top-24">
                  <CardContent className="pt-6">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                      <Zap className="w-5 h-5 text-primary" aria-hidden="true" />
                      <span>Supported Documents</span>
                    </h3>
                    <ul className="space-y-3 mb-6" role="list">
                      {[
                        'Invoices & Bills (Multi-currency)',
                        'Receipts & Expense Reports',
                        'Purchase Orders',
                        'Bank Statements',
                        'Financial Statements'
                      ].map((item, i) => (
                        <motion.li 
                          key={item} 
                          className="flex items-center text-sm gap-2"
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.1 }}
                          role="listitem"
                        >
                          <CheckCircle className="w-4 h-4 text-success flex-shrink-0" aria-hidden="true" />
                          <span>{item}</span>
                        </motion.li>
                      ))}
                    </ul>
                    
                    <div className="p-4 rounded-xl bg-primary/5 border border-primary/10">
                      <p className="text-xs text-muted-foreground">
                        <strong className="text-foreground">Pro Tip:</strong> For best results, use clear images or PDFs with minimal skew.
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </motion.div>
        );

      case 'results':
        return results ? (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
              <h2 className="text-xl sm:text-2xl font-bold">Analysis Results</h2>
              <div className="flex gap-2 w-full sm:w-auto">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => handleDownloadResults('json')}
                  className="flex-1 sm:flex-initial"
                  aria-label="Download results as JSON"
                >
                  <FileJson className="w-4 h-4 mr-2" aria-hidden="true" />
                  <span>JSON</span>
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => handleDownloadResults('csv')}
                  className="flex-1 sm:flex-initial"
                  aria-label="Download results as CSV"
                >
                  <FileSpreadsheet className="w-4 h-4 mr-2" aria-hidden="true" />
                  <span>CSV</span>
                </Button>
              </div>
            </div>
            <ResultsDisplay results={results} />
          </motion.div>
        ) : (
          <motion.div 
            className="text-center py-12"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="max-w-md mx-auto">
              <FileText className="w-16 h-16 text-muted-foreground mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-semibold mb-2">No results yet</h3>
              <p className="text-muted-foreground mb-6">
                Upload and analyze a document to see detailed extraction results here.
              </p>
              <Button className="mt-4" onClick={() => setActiveMode('upload')}>
                Go to Upload
              </Button>
            </div>
          </motion.div>
        );

      case 'compare':
        return comparisonResults ? (
          <motion.div
            key="compare"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <ComparisonView data={comparisonResults} />
          </motion.div>
        ) : (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No comparison yet. Upload a document and click "Compare Models".</p>
            <Button className="mt-4" onClick={() => setActiveMode('upload')}>
              Go to Upload
            </Button>
          </div>
        );

      case 'features':
        return (
          <motion.div
            key="features"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-8"
          >
            <div className="text-center mb-8">
              <h2 className="text-2xl md:text-3xl font-bold mb-2">
                Interactive <span className="text-gradient">Features Demo</span>
              </h2>
              <p className="text-muted-foreground">Explore the AI-powered document parsing capabilities</p>
            </div>
            
            <SemanticRegionVisualization />
            
            <div className="mt-8">
              <ModelInfo />
            </div>
          </motion.div>
        );

      case 'metrics':
        return (
          <motion.div
            key="metrics"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <PerformanceMetrics />
          </motion.div>
        );

      case 'api':
        return (
          <motion.div
            key="api"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <APIPlayground />
          </motion.div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar - Desktop */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 256, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="hidden lg:block flex-shrink-0 overflow-hidden"
          >
            <AppSidebar activeMode={activeMode} onModeChange={setActiveMode} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <header className="sticky top-0 z-40 bg-card/95 backdrop-blur-xl border-b border-border/50 shadow-sm px-4 py-3 sm:py-4 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
            <Button 
              variant="ghost" 
              size="icon"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="hidden lg:flex hover:bg-muted/80 rounded-lg"
              aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
            >
              {sidebarOpen ? (
                <PanelLeftClose className="w-5 h-5" />
              ) : (
                <PanelLeft className="w-5 h-5" />
              )}
            </Button>

            {/* Mobile Logo */}
            <Link to="/" className="lg:hidden flex items-center gap-2 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-4 h-4 text-primary-foreground" />
              </div>
              <span className="font-bold truncate">FinScribe</span>
            </Link>

            <Badge className="hidden md:flex gap-1 items-center bg-primary/10 text-primary border-0 flex-shrink-0">
              <CheckCircle className="w-3 h-3" />
              <span className="hidden lg:inline">98% Accuracy</span>
              <span className="lg:hidden">98%</span>
            </Badge>
          </div>

          {/* Mobile Navigation */}
          <div className="flex lg:hidden gap-1 sm:gap-2 overflow-x-auto scrollbar-hide flex-1 justify-end">
            {['upload', 'compare', 'features', 'metrics', 'api'].map((mode) => (
              <Button
                key={mode}
                variant={activeMode === mode ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setActiveMode(mode)}
                className="capitalize whitespace-nowrap text-xs sm:text-sm"
                aria-label={`Switch to ${mode} mode`}
                aria-current={activeMode === mode ? "page" : undefined}
              >
                <span className="hidden sm:inline">
                  {mode === 'upload' ? 'Upload' : 
                   mode === 'compare' ? 'Compare' :
                   mode === 'features' ? 'Demo' :
                   mode === 'metrics' ? 'Metrics' : 'API'}
                </span>
                <span className="sm:hidden">
                  {mode === 'upload' ? 'Up' : 
                   mode === 'compare' ? 'Cmp' :
                   mode === 'features' ? 'Demo' :
                   mode === 'metrics' ? 'Met' : 'API'}
                </span>
              </Button>
            ))}
          </div>

          <Badge variant="outline" className="hidden sm:flex flex-shrink-0 ml-2">Privacy-First</Badge>
        </header>

        {/* Content Area */}
        <main className="flex-1 p-4 sm:p-6 overflow-auto">
          <AnimatePresence mode="wait">
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mb-4 sm:mb-6"
                role="alert"
                aria-live="assertive"
                aria-atomic="true"
              >
                <Alert variant="destructive" className="border-destructive/50">
                  <AlertDescription className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4">
                    <span className="flex-1 text-sm sm:text-base">{error}</span>
                    <div className="flex gap-2 flex-shrink-0 w-full sm:w-auto">
                      {ErrorHandler.isRetryable(new Error(error)) && (
                        <Button 
                          variant="outline" 
                          size="sm" 
                          onClick={() => {
                            setError(null);
                            if (activeMode === 'upload' && file) {
                              handleAnalyze();
                            } else if (activeMode === 'compare' && file) {
                              handleCompare();
                            }
                          }}
                          className="text-xs sm:text-sm flex-1 sm:flex-initial"
                          aria-label="Retry operation"
                        >
                          Retry
                        </Button>
                      )}
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => setError(null)}
                        aria-label="Dismiss error"
                        className="flex-shrink-0"
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  </AlertDescription>
                </Alert>
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence mode="wait">
            {renderContent()}
          </AnimatePresence>
        </main>

        {/* Footer */}
        <footer className="border-t bg-muted/30 px-4 sm:px-6 py-3 sm:py-4">
          <div className="flex flex-col sm:flex-row justify-between items-center gap-3 sm:gap-4 text-xs sm:text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-primary" aria-hidden="true" />
              <span className="text-center sm:text-left">FinScribe AI - PaddleOCR-VL + ERNIE 4.5</span>
            </div>
            <div className="flex items-center gap-3 sm:gap-4 flex-wrap justify-center">
              <span className="hidden sm:inline">ERNIE AI Developer Challenge</span>
              <a 
                href="https://github.com" 
                target="_blank" 
                rel="noopener noreferrer"
                className="hover:text-primary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded"
                aria-label="Visit GitHub repository"
              >
                GitHub
              </a>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default FinScribe;
