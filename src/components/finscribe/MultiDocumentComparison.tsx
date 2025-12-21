import React from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  FileText, 
  Plus, 
  Minus, 
  AlertTriangle, 
  CheckCircle, 
  TrendingUp, 
  TrendingDown,
  DollarSign,
  Package,
  ArrowRight,
  Eye
} from 'lucide-react';

interface MultiDocumentComparisonProps {
  data?: {
    comparison?: {
      comparison_summary?: {
        total_items_document1?: number;
        total_items_document2?: number;
        matching_items?: number;
        additions_count?: number;
        deletions_count?: number;
        price_changes_count?: number;
        quantity_changes_count?: number;
        total_difference?: number;
        currency?: string;
      };
      additions?: Array<{
        description?: string;
        quantity?: number;
        unit_price?: number;
        total?: number;
        reason?: string;
      }>;
      deletions?: Array<{
        description?: string;
        quantity?: number;
        unit_price?: number;
        total?: number;
        reason?: string;
      }>;
      price_changes?: Array<{
        description?: string;
        document1_price?: number;
        document2_price?: number;
        difference?: number;
        percentage_change?: number;
      }>;
      quantity_changes?: Array<{
        description?: string;
        document1_quantity?: number;
        document2_quantity?: number;
        difference?: number;
      }>;
      matching_items?: Array<{
        description?: string;
        quantity?: number;
        unit_price?: number;
        total?: number;
        status?: string;
      }>;
      discrepancies?: Array<{
        type?: string;
        description?: string;
        severity?: string;
        recommendation?: string;
      }>;
      overall_assessment?: {
        status?: string;
        confidence?: number;
        requires_review?: boolean;
        summary?: string;
      };
    };
    document1?: {
      filename?: string;
    };
    document2?: {
      filename?: string;
    };
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

function MultiDocumentComparison({ data }: MultiDocumentComparisonProps) {
  if (!data?.comparison) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">No comparison data available</p>
      </div>
    );
  }

  const comparison = data.comparison;
  const summary = comparison.comparison_summary || {};
  const assessment = comparison.overall_assessment || {};
  const additions = comparison.additions || [];
  const deletions = comparison.deletions || [];
  const priceChanges = comparison.price_changes || [];
  const quantityChanges = comparison.quantity_changes || [];
  const matchingItems = comparison.matching_items || [];
  const discrepancies = comparison.discrepancies || [];

  const getStatusBadge = (status?: string) => {
    switch (status?.toLowerCase()) {
      case 'match':
        return <Badge className="bg-green-500/20 text-green-600 border-green-500/30">Match</Badge>;
      case 'partial_match':
        return <Badge className="bg-yellow-500/20 text-yellow-600 border-yellow-500/30">Partial Match</Badge>;
      case 'mismatch':
        return <Badge className="bg-red-500/20 text-red-600 border-red-500/30">Mismatch</Badge>;
      default:
        return <Badge variant="outline">{status || 'Unknown'}</Badge>;
    }
  };

  const getSeverityBadge = (severity?: string) => {
    switch (severity?.toLowerCase()) {
      case 'high':
        return <Badge className="bg-red-500/20 text-red-600 border-red-500/30">High</Badge>;
      case 'medium':
        return <Badge className="bg-yellow-500/20 text-yellow-600 border-yellow-500/30">Medium</Badge>;
      case 'low':
        return <Badge className="bg-blue-500/20 text-blue-600 border-blue-500/30">Low</Badge>;
      default:
        return <Badge variant="outline">{severity || 'Unknown'}</Badge>;
    }
  };

  const formatCurrency = (amount?: number) => {
    if (amount === undefined || amount === null) return 'N/A';
    const currency = summary.currency || 'USD';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount);
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
          Document <span className="text-gradient">Comparison</span>
        </h2>
        <p className="text-muted-foreground">
          {data.document1?.filename || 'Document 1'} vs {data.document2?.filename || 'Document 2'}
        </p>
      </motion.div>

      {/* Overall Assessment */}
      {assessment.summary && (
        <motion.div variants={itemVariants}>
          <Alert className={assessment.requires_review ? 'border-yellow-500/50 bg-yellow-500/10' : 'border-green-500/50 bg-green-500/10'}>
            <AlertTriangle className={assessment.requires_review ? 'h-4 w-4 text-yellow-600' : 'h-4 w-4 text-green-600'} />
            <AlertDescription>
              <div className="flex items-center justify-between gap-4">
                <div className="flex-1">
                  <div className="font-semibold mb-1">
                    {getStatusBadge(assessment.status)}
                    <span className="ml-2">Overall Assessment</span>
                  </div>
                  <p className="text-sm">{assessment.summary}</p>
                  {assessment.confidence !== undefined && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Confidence: {(assessment.confidence * 100).toFixed(1)}%
                    </p>
                  )}
                </div>
              </div>
            </AlertDescription>
          </Alert>
        </motion.div>
      )}

      {/* Summary Cards */}
      <motion.div variants={itemVariants} className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Items</p>
                <p className="text-2xl font-bold">{summary.total_items_document1 || 0}</p>
                <p className="text-xs text-muted-foreground">Document 1</p>
              </div>
              <FileText className="w-8 h-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Items</p>
                <p className="text-2xl font-bold">{summary.total_items_document2 || 0}</p>
                <p className="text-xs text-muted-foreground">Document 2</p>
              </div>
              <FileText className="w-8 h-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Matching</p>
                <p className="text-2xl font-bold text-green-600">{summary.matching_items || 0}</p>
                <p className="text-xs text-muted-foreground">Items verified</p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Difference</p>
                <p className={`text-2xl font-bold ${(summary.total_difference || 0) > 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {formatCurrency(summary.total_difference)}
                </p>
                <p className="text-xs text-muted-foreground">Net change</p>
              </div>
              <DollarSign className={`w-8 h-8 ${(summary.total_difference || 0) > 0 ? 'text-red-600' : 'text-green-600'}`} />
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Additions */}
      {additions.length > 0 && (
        <motion.div variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Plus className="w-5 h-5 text-green-600" />
                Additions ({additions.length})
                <Badge className="bg-green-500/20 text-green-600 border-green-500/30 ml-auto">
                  New in Document 2
                </Badge>
              </CardTitle>
              <CardDescription>Items present in Document 2 but not in Document 1</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Description</TableHead>
                    <TableHead>Quantity</TableHead>
                    <TableHead>Unit Price</TableHead>
                    <TableHead>Total</TableHead>
                    <TableHead>Reason</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {additions.map((item, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="font-medium">{item.description || 'N/A'}</TableCell>
                      <TableCell>{item.quantity || 0}</TableCell>
                      <TableCell>{formatCurrency(item.unit_price)}</TableCell>
                      <TableCell className="font-semibold text-green-600">{formatCurrency(item.total)}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{item.reason || '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Deletions */}
      {deletions.length > 0 && (
        <motion.div variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Minus className="w-5 h-5 text-red-600" />
                Deletions ({deletions.length})
                <Badge className="bg-red-500/20 text-red-600 border-red-500/30 ml-auto">
                  Removed from Document 2
                </Badge>
              </CardTitle>
              <CardDescription>Items present in Document 1 but not in Document 2</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Description</TableHead>
                    <TableHead>Quantity</TableHead>
                    <TableHead>Unit Price</TableHead>
                    <TableHead>Total</TableHead>
                    <TableHead>Reason</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {deletions.map((item, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="font-medium">{item.description || 'N/A'}</TableCell>
                      <TableCell>{item.quantity || 0}</TableCell>
                      <TableCell>{formatCurrency(item.unit_price)}</TableCell>
                      <TableCell className="font-semibold text-red-600">{formatCurrency(item.total)}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{item.reason || '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Price Changes */}
      {priceChanges.length > 0 && (
        <motion.div variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-yellow-600" />
                Price Changes ({priceChanges.length})
              </CardTitle>
              <CardDescription>Items with different prices between documents</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Description</TableHead>
                    <TableHead>Doc 1 Price</TableHead>
                    <TableHead>Doc 2 Price</TableHead>
                    <TableHead>Difference</TableHead>
                    <TableHead>Change %</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {priceChanges.map((item, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="font-medium">{item.description || 'N/A'}</TableCell>
                      <TableCell>{formatCurrency(item.document1_price)}</TableCell>
                      <TableCell>{formatCurrency(item.document2_price)}</TableCell>
                      <TableCell className={`font-semibold ${(item.difference || 0) > 0 ? 'text-red-600' : 'text-green-600'}`}>
                        {formatCurrency(item.difference)}
                      </TableCell>
                      <TableCell className={item.percentage_change && item.percentage_change > 0 ? 'text-red-600' : 'text-green-600'}>
                        {item.percentage_change !== undefined ? `${item.percentage_change > 0 ? '+' : ''}${item.percentage_change.toFixed(2)}%` : 'N/A'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Quantity Changes */}
      {quantityChanges.length > 0 && (
        <motion.div variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Package className="w-5 h-5 text-blue-600" />
                Quantity Changes ({quantityChanges.length})
              </CardTitle>
              <CardDescription>Items with different quantities between documents</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Description</TableHead>
                    <TableHead>Doc 1 Qty</TableHead>
                    <TableHead>Doc 2 Qty</TableHead>
                    <TableHead>Difference</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {quantityChanges.map((item, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="font-medium">{item.description || 'N/A'}</TableCell>
                      <TableCell>{item.document1_quantity || 0}</TableCell>
                      <TableCell>{item.document2_quantity || 0}</TableCell>
                      <TableCell className={`font-semibold ${(item.difference || 0) > 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {item.difference !== undefined ? (item.difference > 0 ? '+' : '') + item.difference : 'N/A'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Matching Items */}
      {matchingItems.length > 0 && (
        <motion.div variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-green-600" />
                Matching Items ({matchingItems.length})
              </CardTitle>
              <CardDescription>Items verified as matching between both documents</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Description</TableHead>
                    <TableHead>Quantity</TableHead>
                    <TableHead>Unit Price</TableHead>
                    <TableHead>Total</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {matchingItems.map((item, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="font-medium">{item.description || 'N/A'}</TableCell>
                      <TableCell>{item.quantity || 0}</TableCell>
                      <TableCell>{formatCurrency(item.unit_price)}</TableCell>
                      <TableCell className="font-semibold">{formatCurrency(item.total)}</TableCell>
                      <TableCell>
                        <Badge className="bg-green-500/20 text-green-600 border-green-500/30">
                          {item.status || 'Verified'}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Discrepancies */}
      {discrepancies.length > 0 && (
        <motion.div variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-600" />
                Discrepancies ({discrepancies.length})
              </CardTitle>
              <CardDescription>Issues that require attention</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {discrepancies.map((disc, idx) => (
                  <Alert key={idx} variant={disc.severity === 'high' ? 'destructive' : 'default'}>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-semibold">{disc.type || 'Issue'}</span>
                            {getSeverityBadge(disc.severity)}
                          </div>
                          <p className="text-sm">{disc.description || 'No description'}</p>
                          {disc.recommendation && (
                            <p className="text-xs text-muted-foreground mt-2">
                              <strong>Recommendation:</strong> {disc.recommendation}
                            </p>
                          )}
                        </div>
                      </div>
                    </AlertDescription>
                  </Alert>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Empty State */}
      {additions.length === 0 && deletions.length === 0 && priceChanges.length === 0 && 
       quantityChanges.length === 0 && matchingItems.length === 0 && discrepancies.length === 0 && (
        <motion.div variants={itemVariants}>
          <Card>
            <CardContent className="py-12 text-center">
              <Eye className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No comparison details available</p>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </motion.div>
  );
}

export default MultiDocumentComparison;


