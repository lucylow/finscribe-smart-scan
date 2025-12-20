import React from 'react';
import { motion } from 'framer-motion';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { CheckCircle, XCircle, AlertTriangle, FileText, Building2, DollarSign, Code, TableIcon, Layers } from 'lucide-react';

interface LineItem {
  description: string;
  quantity: number;
  unit_price: number;
  line_total: number;
}

interface ValidationIssue {
  severity: 'error' | 'warning';
  message: string;
}

interface ResultsData {
  document_type?: string;
  vendor?: string;
  total?: number;
  line_items?: LineItem[];
  vendor_block?: Record<string, unknown>;
  financial_summary?: Record<string, unknown>;
}

interface Validation {
  is_valid: boolean;
  issues?: ValidationIssue[];
}

interface ResultsProps {
  results: {
    data: ResultsData;
    validation?: Validation;
    metadata?: Record<string, unknown>;
  };
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

function ResultsDisplay({ results }: ResultsProps) {
  const { data, validation } = results;

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Overview Cards */}
      <motion.div variants={itemVariants} className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card className="bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                <FileText className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Document Type</p>
                <p className="font-semibold">{data.document_type || 'Invoice'}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-secondary/10 to-secondary/5 border-secondary/20">
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-secondary/20 flex items-center justify-center">
                <Building2 className="w-5 h-5 text-secondary" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Vendor</p>
                <p className="font-semibold truncate max-w-[100px]">{data.vendor || 'Detected'}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-success/10 to-success/5 border-success/20">
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-success/20 flex items-center justify-center">
                <DollarSign className="w-5 h-5 text-success" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Total Amount</p>
                <p className="font-bold text-lg">${data.total?.toFixed(2) || '0.00'}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className={`bg-gradient-to-br ${validation?.is_valid ? 'from-success/10 to-success/5 border-success/20' : 'from-destructive/10 to-destructive/5 border-destructive/20'}`}>
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${validation?.is_valid ? 'bg-success/20' : 'bg-destructive/20'}`}>
                {validation?.is_valid ? (
                  <CheckCircle className="w-5 h-5 text-success" />
                ) : (
                  <AlertTriangle className="w-5 h-5 text-destructive" />
                )}
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Validation</p>
                <p className="font-semibold">{validation?.is_valid ? 'Passed' : 'Issues Found'}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Validation Issues */}
      {validation?.issues && validation.issues.length > 0 && (
        <motion.div variants={itemVariants} className="mb-6">
          <Card className="border-yellow-500/30 bg-yellow-500/5">
            <CardContent className="pt-4">
              <h4 className="font-semibold mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow-500" />
                Validation Issues
              </h4>
              <div className="space-y-2">
                {validation.issues.map((issue, idx) => (
                  <div 
                    key={idx}
                    className={`text-sm flex items-center gap-2 p-2 rounded-lg ${
                      issue.severity === 'error' ? 'bg-destructive/10 text-destructive' : 'bg-yellow-500/10 text-yellow-600'
                    }`}
                  >
                    {issue.severity === 'error' ? <XCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                    {issue.message}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Data Tabs */}
      <motion.div variants={itemVariants}>
        <Tabs defaultValue="line-items">
          <TabsList className="mb-4 bg-muted/50 p-1">
            <TabsTrigger value="line-items" className="gap-2">
              <TableIcon className="w-4 h-4" />
              Line Items
            </TabsTrigger>
            <TabsTrigger value="structured" className="gap-2">
              <Layers className="w-4 h-4" />
              Structured
            </TabsTrigger>
            <TabsTrigger value="raw" className="gap-2">
              <Code className="w-4 h-4" />
              Raw JSON
            </TabsTrigger>
          </TabsList>

          <TabsContent value="line-items">
            {data.line_items && data.line_items.length > 0 ? (
              <Card className="overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead>Description</TableHead>
                      <TableHead className="text-right">Qty</TableHead>
                      <TableHead className="text-right">Unit Price</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.line_items.map((item, index) => (
                      <motion.tr 
                        key={index}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className="border-b transition-colors hover:bg-muted/50"
                      >
                        <TableCell className="font-medium">{item.description}</TableCell>
                        <TableCell className="text-right">{item.quantity}</TableCell>
                        <TableCell className="text-right">${item.unit_price?.toFixed(2)}</TableCell>
                        <TableCell className="text-right font-semibold">${item.line_total?.toFixed(2)}</TableCell>
                      </motion.tr>
                    ))}
                    <TableRow className="bg-primary/5 font-bold">
                      <TableCell colSpan={3} className="text-right">Grand Total:</TableCell>
                      <TableCell className="text-right text-lg text-primary">${data.total?.toFixed(2)}</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </Card>
            ) : (
              <Card className="p-8 text-center">
                <TableIcon className="w-12 h-12 text-muted-foreground mx-auto mb-3" />
                <p className="text-muted-foreground">No line items detected</p>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="structured">
            <div className="grid md:grid-cols-2 gap-4">
              <Card className="overflow-hidden">
                <CardHeader className="bg-muted/30 py-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Building2 className="w-4 h-4" />
                    Vendor Information
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-4">
                  <pre className="text-xs bg-muted/50 p-3 rounded-lg overflow-auto max-h-48 font-mono">
                    {JSON.stringify(data.vendor_block || {}, null, 2)}
                  </pre>
                </CardContent>
              </Card>
              
              <Card className="overflow-hidden">
                <CardHeader className="bg-muted/30 py-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <DollarSign className="w-4 h-4" />
                    Financial Summary
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-4">
                  <pre className="text-xs bg-muted/50 p-3 rounded-lg overflow-auto max-h-48 font-mono">
                    {JSON.stringify(data.financial_summary || {}, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="raw">
            <Accordion type="single" collapsible defaultValue="json">
              <AccordionItem value="json" className="border rounded-lg overflow-hidden">
                <AccordionTrigger className="px-4 hover:no-underline hover:bg-muted/50">
                  <span className="flex items-center gap-2">
                    <Code className="w-4 h-4" />
                    Complete JSON Response
                  </span>
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4">
                  <pre className="text-xs bg-muted/50 p-4 rounded-lg overflow-auto max-h-96 font-mono">
                    {JSON.stringify(results, null, 2)}
                  </pre>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </TabsContent>
        </Tabs>
      </motion.div>
    </motion.div>
  );
}

export default ResultsDisplay;
