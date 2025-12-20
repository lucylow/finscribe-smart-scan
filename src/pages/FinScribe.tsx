import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
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

const FinScribe = () => {
  const [activeMode, setActiveMode] = useState('upload');
  const [file, setFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processing, setProcessing] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [comparisonResults, setComparisonResults] = useState<any>(null);
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
      return;
    }

    setProcessing(true);
    setError(null);
    
    try {
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 100);

      const formData = new FormData();
      formData.append('file', file);

      const response = await analyzeDocument(formData);
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      setResults(response);
      setActiveMode('results');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error');
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
      setActiveMode('compare');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error');
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

      case 'results':
        return results ? (
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
            <Button className="mt-4" onClick={() => setActiveMode('upload')}>
              Go to Upload
            </Button>
          </div>
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

            {/* Mobile Logo */}
            <div className="lg:hidden flex items-center gap-2">
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

          {/* Mobile Navigation */}
          <div className="flex lg:hidden gap-2 overflow-x-auto">
            {['upload', 'compare', 'features', 'metrics', 'api'].map((mode) => (
              <Button
                key={mode}
                variant={activeMode === mode ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setActiveMode(mode)}
                className="capitalize whitespace-nowrap"
              >
                {mode === 'upload' ? 'Upload' : 
                 mode === 'compare' ? 'Compare' :
                 mode === 'features' ? 'Demo' :
                 mode === 'metrics' ? 'Metrics' : 'API'}
              </Button>
            ))}
          </div>

          <Badge variant="outline" className="hidden sm:flex">Privacy-First</Badge>
        </header>

        {/* Content Area */}
        <main className="flex-1 p-6 overflow-auto">
          <AnimatePresence mode="wait">
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mb-6"
              >
                <Alert variant="destructive">
                  <AlertDescription className="flex items-center justify-between">
                    {error}
                    <Button variant="ghost" size="sm" onClick={() => setError(null)}>
                      <X className="w-4 h-4" />
                    </Button>
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
        <footer className="border-t bg-muted/30 px-6 py-4">
          <div className="flex flex-wrap justify-between items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-primary" />
              <span>FinScribe AI - PaddleOCR-VL + ERNIE 4.5</span>
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
