import React from 'react';
import { motion } from 'framer-motion';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, XCircle, TrendingUp, Zap, Timer, Globe, Brain, Cpu, BarChart3, Settings2 } from 'lucide-react';

interface ComparisonViewProps {
  data?: Record<string, unknown>;
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 }
};

function ComparisonView({ data }: ComparisonViewProps) {
  const comparisonData = {
    accuracy: {
      fineTuned: 98.5,
      baseline: 76.2,
      improvement: '+22.3%'
    },
    fields: [
      { field: 'Vendor Name', fineTuned: true, baseline: false },
      { field: 'Invoice Number', fineTuned: true, baseline: true },
      { field: 'Line Items', fineTuned: true, baseline: false },
      { field: 'Tax Amount', fineTuned: true, baseline: true },
      { field: 'Total Amount', fineTuned: true, baseline: true },
    ],
    metrics: [
      { metric: 'Processing Time', fineTuned: '2.3s', baseline: '1.8s', icon: Timer },
      { metric: 'Table Recognition', fineTuned: '95%', baseline: '68%', icon: BarChart3 },
      { metric: 'Multi-currency', fineTuned: 'Yes', baseline: 'No', icon: Globe },
      { metric: 'Layout Understanding', fineTuned: 'Advanced', baseline: 'Basic', icon: Brain },
    ]
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <motion.div variants={itemVariants} className="text-center mb-8">
        <h2 className="text-2xl md:text-3xl font-bold mb-2">
          Model <span className="text-gradient">Performance</span> Comparison
        </h2>
        <p className="text-muted-foreground">Fine-Tuned PaddleOCR-VL vs Generic OCR Baseline</p>
      </motion.div>

      {/* Accuracy Hero Cards */}
      <motion.div variants={itemVariants} className="grid grid-cols-3 gap-4 mb-8">
        <Card className="bg-gradient-to-br from-primary/20 to-primary/5 border-primary/30 text-center overflow-hidden relative">
          <div className="absolute top-0 right-0 w-20 h-20 bg-primary/10 rounded-full -translate-y-1/2 translate-x-1/2" />
          <CardContent className="pt-6 pb-6">
            <TrendingUp className="w-8 h-8 text-primary mx-auto mb-2" />
            <p className="text-3xl md:text-4xl font-bold text-primary">
              {comparisonData.accuracy.improvement}
            </p>
            <p className="text-sm text-muted-foreground mt-1">Improvement</p>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-secondary/20 to-secondary/5 border-secondary/30 text-center overflow-hidden relative">
          <div className="absolute top-0 right-0 w-20 h-20 bg-secondary/10 rounded-full -translate-y-1/2 translate-x-1/2" />
          <CardContent className="pt-6 pb-6">
            <Zap className="w-8 h-8 text-secondary mx-auto mb-2" />
            <p className="text-3xl md:text-4xl font-bold text-secondary">
              {comparisonData.accuracy.fineTuned}%
            </p>
            <p className="text-sm text-muted-foreground mt-1">Fine-Tuned</p>
          </CardContent>
        </Card>
        
        <Card className="bg-muted/50 text-center">
          <CardContent className="pt-6 pb-6">
            <Cpu className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
            <p className="text-3xl md:text-4xl font-bold text-muted-foreground">
              {comparisonData.accuracy.baseline}%
            </p>
            <p className="text-sm text-muted-foreground mt-1">Baseline</p>
          </CardContent>
        </Card>
      </motion.div>

      <motion.div variants={itemVariants}>
        <Tabs defaultValue="fields">
          <TabsList className="mb-4 bg-muted/50 p-1 w-full justify-start">
            <TabsTrigger value="fields" className="gap-2">
              <CheckCircle className="w-4 h-4" />
              Field Accuracy
            </TabsTrigger>
            <TabsTrigger value="metrics" className="gap-2">
              <BarChart3 className="w-4 h-4" />
              Metrics
            </TabsTrigger>
            <TabsTrigger value="technical" className="gap-2">
              <Settings2 className="w-4 h-4" />
              Technical
            </TabsTrigger>
          </TabsList>

          <TabsContent value="fields">
            <Card className="overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50">
                    <TableHead>Field</TableHead>
                    <TableHead className="text-center">Fine-Tuned</TableHead>
                    <TableHead className="text-center">Baseline</TableHead>
                    <TableHead className="text-center">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {comparisonData.fields.map((row, index) => (
                    <motion.tr 
                      key={index}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="border-b transition-colors hover:bg-muted/50"
                    >
                      <TableCell className="font-medium">{row.field}</TableCell>
                      <TableCell className="text-center">
                        {row.fineTuned ? 
                          <CheckCircle className="w-5 h-5 text-success mx-auto" /> : 
                          <XCircle className="w-5 h-5 text-destructive mx-auto" />
                        }
                      </TableCell>
                      <TableCell className="text-center">
                        {row.baseline ? 
                          <CheckCircle className="w-5 h-5 text-success mx-auto" /> : 
                          <XCircle className="w-5 h-5 text-destructive mx-auto" />
                        }
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge 
                          variant={row.fineTuned && !row.baseline ? "default" : "secondary"}
                          className={row.fineTuned && !row.baseline ? "bg-primary/20 text-primary border-primary/30" : ""}
                        >
                          {row.fineTuned && !row.baseline ? "✓ Exclusive" : "Both"}
                        </Badge>
                      </TableCell>
                    </motion.tr>
                  ))}
                </TableBody>
              </Table>
            </Card>
          </TabsContent>

          <TabsContent value="metrics">
            <div className="grid md:grid-cols-2 gap-4">
              {comparisonData.metrics.map((metric, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <Card className="h-full hover:shadow-md transition-shadow">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base flex items-center gap-2">
                        <metric.icon className="w-4 h-4 text-primary" />
                        {metric.metric}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex justify-between items-end">
                        <div>
                          <p className="text-xs text-muted-foreground mb-1">Fine-Tuned</p>
                          <p className="text-2xl font-bold text-primary">{metric.fineTuned}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-xs text-muted-foreground mb-1">Baseline</p>
                          <p className="text-xl font-semibold text-muted-foreground">{metric.baseline}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="technical">
            <Card className="overflow-hidden">
              <CardHeader className="bg-muted/30">
                <CardTitle className="flex items-center gap-2">
                  <Settings2 className="w-5 h-5" />
                  Technical Architecture Comparison
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="p-5 bg-gradient-to-br from-primary/10 to-primary/5 rounded-xl border border-primary/20">
                    <div className="flex items-center gap-2 mb-4">
                      <Zap className="w-5 h-5 text-primary" />
                      <h4 className="font-semibold">Fine-Tuned PaddleOCR-VL</h4>
                    </div>
                    <ul className="text-sm space-y-2 text-muted-foreground">
                      <li className="flex items-start gap-2">
                        <CheckCircle className="w-4 h-4 text-success mt-0.5 flex-shrink-0" />
                        Custom training on 5,000+ financial documents
                      </li>
                      <li className="flex items-start gap-2">
                        <CheckCircle className="w-4 h-4 text-success mt-0.5 flex-shrink-0" />
                        Specialized for table parsing and layout understanding
                      </li>
                      <li className="flex items-start gap-2">
                        <CheckCircle className="w-4 h-4 text-success mt-0.5 flex-shrink-0" />
                        Multi-currency and language support
                      </li>
                      <li className="flex items-start gap-2">
                        <CheckCircle className="w-4 h-4 text-success mt-0.5 flex-shrink-0" />
                        Integration with ERNIE 4.5 for semantic validation
                      </li>
                    </ul>
                  </div>
                  
                  <div className="p-5 bg-muted/50 rounded-xl border">
                    <div className="flex items-center gap-2 mb-4">
                      <Cpu className="w-5 h-5 text-muted-foreground" />
                      <h4 className="font-semibold">Generic OCR Baseline</h4>
                    </div>
                    <ul className="text-sm space-y-2 text-muted-foreground">
                      <li className="flex items-start gap-2">
                        <XCircle className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                        General-purpose text extraction only
                      </li>
                      <li className="flex items-start gap-2">
                        <XCircle className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                        Limited table structure understanding
                      </li>
                      <li className="flex items-start gap-2">
                        <XCircle className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                        Single currency/language typically
                      </li>
                      <li className="flex items-start gap-2">
                        <XCircle className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                        No semantic validation capabilities
                      </li>
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </motion.div>
    </motion.div>
  );
}

export default ComparisonView;
