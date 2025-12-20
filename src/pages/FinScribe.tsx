import React, { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate, useLocation, Routes, Route, Navigate, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { 
  CloudUpload, 
  GitCompare, 
  Download, 
  Zap, 
  X,
  FileJson,
  FileSpreadsheet,
  Sparkles,
  ArrowRight,
  CheckCircle,
  Menu,
  PanelLeftClose,
  PanelLeft,
  AlertTriangle
} from 'lucide-react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import DocumentUpload from '@/components/finscribe/DocumentUpload';
import ProcessingStatus from '@/components/finscribe/ProcessingStatus';
import ResultsDisplay from '@/components/finscribe/ResultsDisplay';
import ComparisonView from '@/components/finscribe/ComparisonView';
import ModelInfo from '@/components/finscribe/ModelInfo';
import SemanticRegionVisualization from '@/components/finscribe/SemanticRegionVisualization';
import PerformanceMetrics from '@/components/finscribe/PerformanceMetrics';
import APIPlayground from '@/components/finscribe/APIPlayground';
import AppSidebar from '@/components/finscribe/AppSidebar';
import { analyzeDocument, compareWithBaseline, APIError, NetworkError, TimeoutError } from '@/services/api';

const FinScribe = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [file, setFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processing, setProcessing] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [comparisonResults, setComparisonResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Extract active mode from URL
  const activeMode = location.pathname.split('/').pop() || 'upload';

  const handleFileSelect = useCallback((selectedFile: File | null) => {
    setFile(selectedFile);
    setError(null);
    setResults(null);
    setComparisonResults(null);
  }, []);

  const handleAnalyze = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setProcessing(true);
    setError(null);
    
    let progressInterval: NodeJS.Timeout | null = null;
    
    try {
      progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            if (progressInterval) {
              clearInterval(progressInterval);
            }
            return 90;
          }
          return prev + 10;
        });
      }, 100);

      const formData = new FormData();
      formData.append('file', file);

      const response = await analyzeDocument(formData);
      
      if (progressInterval) {
        clearInterval(progressInterval);
      }
      setUploadProgress(100);
      
      setResults(response);
      navigate('/app/results');
    } catch (err) {
      if (progressInterval) {
        clearInterval(progressInterval);
      }
      let errorMessage = 'An error occurred while processing your document.';
      
      if (err instanceof APIError) {
        errorMessage = err.message;
      } else if (err instanceof NetworkError) {
        errorMessage = 'Network error. Please check your internet connection and try again.';
      } else if (err instanceof TimeoutError) {
        errorMessage = 'Request timed out. The file may be too large or processing is taking longer than expected. Please try again.';
      } else if (err instanceof Error) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
      console.error('Analysis error:', err);
    } finally {
      setProcessing(false);
      setTimeout(() => setUploadProgress(0), 1000);
    }
  };

  const handleCompare = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setProcessing(true);
    setError(null);
    
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await compareWithBaseline(formData);
      
      setComparisonResults(response);
      navigate('/app/compare');
    } catch (err) {
      let errorMessage = 'An error occurred while comparing models.';
      
      if (err instanceof APIError) {
        errorMessage = err.message;
      } else if (err instanceof NetworkError) {
        errorMessage = 'Network error. Please check your internet connection and try again.';
      } else if (err instanceof TimeoutError) {
        errorMessage = 'Request timed out. The file may be too large or processing is taking longer than expected. Please try again.';
      } else if (err instanceof Error) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
      console.error('Comparison error:', err);
    } finally {
      setProcessing(false);
    }
  };

  const handleDownloadResults = (format: 'json' | 'csv' = 'json') => {
    if (!results) return;
    
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
      dataStr = JSON.stringify(results.data, null, 2);
      mimeType = 'application/json';
      extension = 'json';
    }
    
    const dataUri = `data:${mimeType};charset=utf-8,${encodeURIComponent(dataStr)}`;
    const exportFileDefaultName = `finscribe-analysis-${Date.now()}.${extension}`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  // Component for Upload page
  const UploadPage = () => (
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

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-4">
          <DocumentUpload onFileSelect={handleFileSelect} file={file} />
          
          <AnimatePresence>
            {file && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                <ProcessingStatus progress={uploadProgress} processing={processing} />
              </motion.div>
            )}
          </AnimatePresence>

          <div className="flex flex-wrap gap-3 justify-center pt-4">
            <Button
              size="lg"
              onClick={handleAnalyze}
              disabled={!file || processing}
              className="shadow-btn min-w-[180px] group"
            >
              {processing ? (
                <>
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                    className="mr-2"
                  >
                    <Sparkles className="w-4 h-4" />
                  </motion.div>
                  Processing...
                </>
              ) : (
                <>
                  <CloudUpload className="w-4 h-4 mr-2" />
                  Analyze with AI
                  <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </Button>
            
            <Button
              variant="outline"
              size="lg"
              onClick={handleCompare}
              disabled={!file || processing}
              className="min-w-[160px]"
            >
              <GitCompare className="w-4 h-4 mr-2" />
              Compare Models
            </Button>
          </div>
        </div>

        <div>
          <Card className="h-full bg-gradient-to-br from-muted/50 to-muted/30 border-muted">
            <CardContent className="pt-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5 text-primary" />
                Supported Documents
              </h3>
              <ul className="space-y-3 mb-6">
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
                  >
                    <CheckCircle className="w-4 h-4 text-success flex-shrink-0" />
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

  // Component for Results page
  const ResultsPage = () => (
    results ? (
      <motion.div
        key="results"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
      >
        <div className="flex flex-wrap justify-between items-center mb-6 gap-4">
          <h2 className="text-2xl font-bold">Analysis Results</h2>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => handleDownloadResults('json')}>
              <FileJson className="w-4 h-4 mr-2" />
              JSON
            </Button>
            <Button variant="outline" size="sm" onClick={() => handleDownloadResults('csv')}>
              <FileSpreadsheet className="w-4 h-4 mr-2" />
              CSV
            </Button>
          </div>
        </div>
        <ResultsDisplay results={results} />
      </motion.div>
    ) : (
      <div className="text-center py-12">
        <p className="text-muted-foreground">No results yet. Upload and analyze a document first.</p>
        <Button className="mt-4" onClick={() => navigate('/app/upload')}>
          Go to Upload
        </Button>
      </div>
    )
  );

  // Component for Compare page
  const ComparePage = () => (
    comparisonResults ? (
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
        <Button className="mt-4" onClick={() => navigate('/app/upload')}>
          Go to Upload
        </Button>
      </div>
    )
  );

  // Component for Features page
  const FeaturesPage = () => (
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

  // Component for Metrics page
  const MetricsPage = () => (
    <motion.div
      key="metrics"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
    >
      <PerformanceMetrics />
    </motion.div>
  );

  // Component for API page
  const APIPage = () => (
    <motion.div
      key="api"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
    >
      <APIPlayground />
    </motion.div>
  );

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
            <AppSidebar activeMode={activeMode} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <header className="sticky top-0 z-40 bg-card/95 backdrop-blur-md border-b px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button 
              variant="ghost" 
              size="icon"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="hidden lg:flex"
            >
              {sidebarOpen ? (
                <PanelLeftClose className="w-5 h-5" />
              ) : (
                <PanelLeft className="w-5 h-5" />
              )}
            </Button>

            {/* Mobile Logo and Menu */}
            <div className="lg:hidden flex items-center gap-3">
              <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
                <SheetTrigger asChild>
                  <Button variant="ghost" size="icon">
                    <Menu className="w-5 h-5" />
                  </Button>
                </SheetTrigger>
                <SheetContent side="left" className="w-64 p-0">
                  <SheetHeader className="p-4 border-b">
                    <SheetTitle className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                        <Sparkles className="w-4 h-4 text-primary-foreground" />
                      </div>
                      <span className="font-bold">FinScribe</span>
                    </SheetTitle>
                  </SheetHeader>
                  <div className="p-3 space-y-1">
                    {[
                      { path: 'upload', label: 'Upload & Analyze', icon: CloudUpload },
                      { path: 'compare', label: 'Compare Models', icon: GitCompare },
                      { path: 'features', label: 'Features Demo', icon: Sparkles },
                      { path: 'metrics', label: 'Performance', icon: CheckCircle },
                      { path: 'api', label: 'API Playground', icon: Zap }
                    ].map(({ path, label, icon: Icon }) => (
                      <Button
                        key={path}
                        variant={activeMode === path ? 'default' : 'ghost'}
                        className="w-full justify-start"
                        onClick={() => {
                          navigate(`/app/${path}`);
                          setMobileMenuOpen(false);
                        }}
                      >
                        <Icon className="w-4 h-4 mr-2" />
                        {label}
                      </Button>
                    ))}
                    <div className="pt-4 mt-4 border-t">
                      <Button
                        variant="outline"
                        className="w-full justify-start"
                        onClick={() => {
                          navigate('/');
                          setMobileMenuOpen(false);
                        }}
                      >
                        <Sparkles className="w-4 h-4 mr-2" />
                        Back to Home
                      </Button>
                    </div>
                  </div>
                </SheetContent>
              </Sheet>
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-primary-foreground" />
              </div>
              <span className="font-bold">FinScribe</span>
            </div>

            <Badge className="hidden md:flex gap-1 items-center bg-primary/10 text-primary border-0">
              <CheckCircle className="w-3 h-3" />
              98% Accuracy
            </Badge>
          </div>

          {/* Desktop Badge */}
          <Badge variant="outline" className="hidden sm:flex">Privacy-First</Badge>

        </header>

        {/* Content Area */}
        <main className="flex-1 p-6 overflow-auto">
          {/* Breadcrumb Navigation */}
          <Breadcrumb className="mb-4">
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink asChild>
                  <Link to="/">Home</Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbLink asChild>
                  <Link to="/app/upload">App</Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              {activeMode !== 'upload' && (
                <>
                  <BreadcrumbSeparator />
                  <BreadcrumbItem>
                    <BreadcrumbPage className="capitalize">{activeMode}</BreadcrumbPage>
                  </BreadcrumbItem>
                </>
              )}
            </BreadcrumbList>
          </Breadcrumb>

          <AnimatePresence mode="wait">
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mb-6"
              >
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription className="flex items-center justify-between gap-4">
                    <span className="flex-1">{error}</span>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => setError(null)}
                      className="flex-shrink-0"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </AlertDescription>
                </Alert>
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence mode="wait">
            <Routes>
              <Route path="upload" element={<UploadPage />} />
              <Route path="results" element={<ResultsPage />} />
              <Route path="compare" element={<ComparePage />} />
              <Route path="features" element={<FeaturesPage />} />
              <Route path="metrics" element={<MetricsPage />} />
              <Route path="api" element={<APIPage />} />
              <Route path="*" element={<Navigate to="/app/upload" replace />} />
            </Routes>
          </AnimatePresence>
        </main>

        {/* Footer */}
        <footer className="border-t bg-muted/30 px-6 py-4">
          <div className="flex flex-wrap justify-between items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-primary" />
              <span>FinScribe AI - PaddleOCR-VL + ERNIE 5</span>
            </div>
            <div className="flex items-center gap-4">
              <span>ERNIE AI Developer Challenge</span>
              <a 
                href="https://github.com" 
                target="_blank" 
                rel="noopener noreferrer"
                className="hover:text-primary transition-colors"
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
