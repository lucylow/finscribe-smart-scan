import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence, type Variants } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { 
  CloudUpload, 
  GitCompare, 
  Download, 
  Zap, 
  Target, 
  Shield, 
  X,
  FileText,
  Clock,
  TrendingUp,
  CheckCircle,
  Sparkles,
  ArrowRight,
  FileJson,
  FileSpreadsheet,
  Home,
  Menu,
  DollarSign,
  HelpCircle
} from 'lucide-react';
import DocumentUpload from '@/components/finscribe/DocumentUpload';
import ProcessingStatus from '@/components/finscribe/ProcessingStatus';
import ResultsDisplay from '@/components/finscribe/ResultsDisplay';
import ComparisonView from '@/components/finscribe/ComparisonView';
import ModelInfo from '@/components/finscribe/ModelInfo';
import { analyzeDocument, compareWithBaseline } from '@/services/api';

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2,
    },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { duration: 0.5 }
  },
};

const stats = [
  { icon: FileText, label: 'Documents Processed', value: '12,847', color: 'primary' as const },
  { icon: Target, label: 'Accuracy Rate', value: '99.2%', color: 'secondary' as const },
  { icon: Clock, label: 'Avg. Processing', value: '2.3s', color: 'accent' as const },
  { icon: TrendingUp, label: 'Time Saved', value: '342hrs', color: 'success' as const },
];

const FinScribe = () => {
  const [activeTab, setActiveTab] = useState('upload');
  const [file, setFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processing, setProcessing] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [comparisonResults, setComparisonResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

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
      setActiveTab('results');
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
      setActiveTab('comparison');
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

  return (
    <div className="min-h-screen bg-background">
      {/* Fixed Header with Navigation */}
      <motion.header 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="sticky top-0 z-50 bg-card/95 backdrop-blur-md border-b border-border"
      >
        <div className="container-custom py-3">
          <div className="flex items-center justify-between">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3 group">
              <motion.div 
                className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center"
                whileHover={{ scale: 1.05 }}
              >
                <Sparkles className="w-5 h-5 text-primary-foreground" />
              </motion.div>
              <div>
                <h1 className="text-xl font-bold tracking-tight text-foreground">
                  Fin<span className="text-primary">Scribe</span> AI
                </h1>
                <p className="text-xs text-muted-foreground hidden sm:block">Powered by PaddleOCR-VL</p>
              </div>
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-1">
              <Link 
                to="/" 
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-muted"
              >
                <Home className="w-4 h-4" />
                Home
              </Link>
              <Link 
                to="/app" 
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-primary bg-primary/10 rounded-lg"
              >
                <Zap className="w-4 h-4" />
                App
              </Link>
              <a 
                href="/#features" 
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-muted"
              >
                <Target className="w-4 h-4" />
                Features
              </a>
              <a 
                href="/#pricing" 
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-muted"
              >
                <DollarSign className="w-4 h-4" />
                Pricing
              </a>
              <a 
                href="/#faq" 
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-muted"
              >
                <HelpCircle className="w-4 h-4" />
                FAQ
              </a>
            </nav>

            {/* Right side badges & mobile menu */}
            <div className="flex items-center gap-3">
              <Badge className="hidden lg:flex gap-1 items-center bg-primary/10 text-primary border-0">
                <CheckCircle className="w-3 h-3" />
                98% Accuracy
              </Badge>
              <Badge variant="outline" className="hidden lg:flex">Privacy-First</Badge>
              
              {/* Mobile menu button */}
              <div className="md:hidden">
                <Button variant="ghost" size="icon" asChild>
                  <Link to="/">
                    <Home className="w-5 h-5" />
                  </Link>
                </Button>
              </div>
            </div>
          </div>
        </div>
      </motion.header>

      {/* Stats Bar */}
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="container-custom py-6 border-b border-border/50"
      >
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {stats.map((stat, i) => (
            <motion.div 
              key={stat.label}
              variants={itemVariants}
              whileHover={{ scale: 1.02 }}
              className="flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors"
            >
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                stat.color === 'primary' ? 'bg-primary/10 text-primary' :
                stat.color === 'secondary' ? 'bg-secondary/10 text-secondary' :
                stat.color === 'accent' ? 'bg-accent text-accent-foreground' :
                'bg-success/10 text-success'
              }`}>
                <stat.icon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-lg font-bold text-foreground">{stat.value}</p>
                <p className="text-xs text-muted-foreground">{stat.label}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Main Content */}
      <main className="container-custom pb-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card className="shadow-card border-0 overflow-hidden">
            <CardContent className="p-0">
              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <div className="border-b bg-muted/30 p-2">
                  <TabsList className="grid w-full grid-cols-4 h-12 bg-transparent gap-1">
                    <TabsTrigger 
                      value="upload" 
                      className="data-[state=active]:bg-card data-[state=active]:shadow-sm rounded-lg transition-all"
                    >
                      <CloudUpload className="w-4 h-4 mr-2 hidden sm:block" />
                      Upload
                    </TabsTrigger>
                    <TabsTrigger 
                      value="results" 
                      disabled={!results}
                      className="data-[state=active]:bg-card data-[state=active]:shadow-sm rounded-lg transition-all"
                    >
                      <FileText className="w-4 h-4 mr-2 hidden sm:block" />
                      Results
                    </TabsTrigger>
                    <TabsTrigger 
                      value="comparison" 
                      disabled={!comparisonResults}
                      className="data-[state=active]:bg-card data-[state=active]:shadow-sm rounded-lg transition-all"
                    >
                      <GitCompare className="w-4 h-4 mr-2 hidden sm:block" />
                      Compare
                    </TabsTrigger>
                    <TabsTrigger 
                      value="details"
                      className="data-[state=active]:bg-card data-[state=active]:shadow-sm rounded-lg transition-all"
                    >
                      <Target className="w-4 h-4 mr-2 hidden sm:block" />
                      Models
                    </TabsTrigger>
                  </TabsList>
                </div>

                <div className="p-6">
                  <AnimatePresence mode="wait">
                    {error && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                      >
                        <Alert variant="destructive" className="mb-6">
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

                  <TabsContent value="upload" className="mt-0">
                    <motion.div
                      variants={containerVariants}
                      initial="hidden"
                      animate="visible"
                    >
                      <motion.div variants={itemVariants} className="text-center mb-8">
                        <h2 className="text-3xl md:text-4xl font-bold mb-3">
                          Transform Your <span className="text-gradient">Financial Documents</span>
                        </h2>
                        <p className="text-muted-foreground max-w-lg mx-auto">
                          Upload invoices, receipts, or statements to extract perfect structured data with AI
                        </p>
                      </motion.div>

                      <div className="grid lg:grid-cols-5 gap-8">
                        <motion.div variants={itemVariants} className="lg:col-span-3 space-y-4">
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
                        </motion.div>

                        <motion.div variants={itemVariants} className="lg:col-span-2">
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
                                    transition={{ delay: 0.5 + i * 0.1 }}
                                  >
                                    <CheckCircle className="w-4 h-4 text-secondary flex-shrink-0" />
                                    <span>{item}</span>
                                  </motion.li>
                                ))}
                              </ul>
                              
                              <div className="p-4 rounded-xl bg-primary/5 border border-primary/10">
                                <p className="text-xs text-muted-foreground">
                                  <strong className="text-foreground">Pro Tip:</strong> For best results, use clear images or PDFs with minimal skew. The AI handles multiple languages and complex layouts automatically.
                                </p>
                              </div>
                            </CardContent>
                          </Card>
                        </motion.div>
                      </div>
                    </motion.div>
                  </TabsContent>

                  <TabsContent value="results" className="mt-0">
                    {results && (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
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
                    )}
                  </TabsContent>

                  <TabsContent value="comparison" className="mt-0">
                    {comparisonResults && (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                      >
                        <ComparisonView data={comparisonResults} />
                      </motion.div>
                    )}
                  </TabsContent>

                  <TabsContent value="details" className="mt-0">
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                    >
                      <ModelInfo />
                    </motion.div>
                  </TabsContent>
                </div>
              </Tabs>
            </CardContent>
          </Card>
        </motion.div>

        {/* Feature Cards */}
        <motion.div 
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="grid md:grid-cols-3 gap-6 mt-8"
        >
          {[
            { icon: Zap, title: 'Fast Processing', desc: 'Documents processed in 2-3 seconds using optimized AI models', color: 'primary' },
            { icon: Target, title: 'High Accuracy', desc: '99%+ accuracy on key fields with PaddleOCR-VL fine-tuning', color: 'secondary' },
            { icon: Shield, title: 'Enterprise Secure', desc: 'End-to-end encryption with SOC 2 & GDPR compliance', color: 'accent' },
          ].map((feature, i) => (
            <motion.div
              key={feature.title}
              variants={itemVariants}
              whileHover={{ y: -4, transition: { duration: 0.2 } }}
            >
              <Card className="h-full border-0 shadow-card hover:shadow-card-hover transition-shadow">
                <CardContent className="pt-6">
                  <div className={`w-12 h-12 rounded-xl mb-4 flex items-center justify-center ${
                    feature.color === 'primary' ? 'bg-primary/10 text-primary' :
                    feature.color === 'secondary' ? 'bg-secondary/10 text-secondary' :
                    'bg-accent/10 text-accent'
                  }`}>
                    <feature.icon className="w-6 h-6" />
                  </div>
                  <h3 className="font-semibold text-lg mb-2">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground">{feature.desc}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </main>
    </div>
  );
};

export default FinScribe;