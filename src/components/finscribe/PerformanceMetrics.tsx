import React from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  TrendingUp, 
  Target, 
  Clock, 
  CheckCircle,
  AlertTriangle,
  FileText,
  Zap,
  BarChart3
} from 'lucide-react';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0 }
};

// Mock performance data
const performanceMetrics = {
  accuracy: { current: 94.2, change: +2.8, trend: 'up' },
  tableRecognition: { current: 91.7, change: +4.2, trend: 'up' },
  processingSpeed: { current: 1.3, change: -0.4, trend: 'down' },
  successRate: { current: 98.5, change: +1.2, trend: 'up' },
  documentsToday: { current: 89, change: +12, trend: 'up' },
  apiUptime: { current: 99.9, change: 0, trend: 'stable' },
};

const errorAnalysis = [
  { type: 'Invoices', errorRate: 2.1, commonIssue: 'Handwritten text' },
  { type: 'Receipts', errorRate: 3.8, commonIssue: 'Poor scan quality' },
  { type: 'Statements', errorRate: 1.5, commonIssue: 'Complex tables' },
  { type: 'Purchase Orders', errorRate: 4.2, commonIssue: 'Non-standard format' },
];

const dailyAccuracy = [92, 93, 91, 94, 93, 95, 94, 96, 95, 94, 93, 95, 96, 94];

function PerformanceMetrics() {
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
          Performance <span className="text-gradient">Analytics</span>
        </h2>
        <p className="text-muted-foreground">Real-time insights into OCR processing performance</p>
      </motion.div>

      {/* Key Metrics Grid */}
      <motion.div variants={itemVariants} className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <Card className="bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
          <CardContent className="p-4 text-center">
            <Target className="w-6 h-6 text-primary mx-auto mb-2" />
            <p className="text-2xl font-bold">{performanceMetrics.accuracy.current}%</p>
            <p className="text-xs text-muted-foreground">Field Accuracy</p>
            <Badge className="mt-2 bg-success/20 text-success border-0 text-xs">
              +{performanceMetrics.accuracy.change}%
            </Badge>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-secondary/10 to-secondary/5 border-secondary/20">
          <CardContent className="p-4 text-center">
            <BarChart3 className="w-6 h-6 text-secondary mx-auto mb-2" />
            <p className="text-2xl font-bold">{performanceMetrics.tableRecognition.current}%</p>
            <p className="text-xs text-muted-foreground">Table TEDS</p>
            <Badge className="mt-2 bg-success/20 text-success border-0 text-xs">
              +{performanceMetrics.tableRecognition.change}%
            </Badge>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-accent to-accent/50">
          <CardContent className="p-4 text-center">
            <Clock className="w-6 h-6 text-accent-foreground mx-auto mb-2" />
            <p className="text-2xl font-bold">{performanceMetrics.processingSpeed.current}s</p>
            <p className="text-xs text-muted-foreground">Avg Speed</p>
            <Badge className="mt-2 bg-success/20 text-success border-0 text-xs">
              {performanceMetrics.processingSpeed.change}s
            </Badge>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-success/10 to-success/5 border-success/20">
          <CardContent className="p-4 text-center">
            <CheckCircle className="w-6 h-6 text-success mx-auto mb-2" />
            <p className="text-2xl font-bold">{performanceMetrics.successRate.current}%</p>
            <p className="text-xs text-muted-foreground">Success Rate</p>
            <Badge className="mt-2 bg-success/20 text-success border-0 text-xs">
              +{performanceMetrics.successRate.change}%
            </Badge>
          </CardContent>
        </Card>

        <Card className="bg-muted/50">
          <CardContent className="p-4 text-center">
            <FileText className="w-6 h-6 text-muted-foreground mx-auto mb-2" />
            <p className="text-2xl font-bold">{performanceMetrics.documentsToday.current}</p>
            <p className="text-xs text-muted-foreground">Docs/Day</p>
            <Badge className="mt-2 bg-primary/20 text-primary border-0 text-xs">
              +{performanceMetrics.documentsToday.change}
            </Badge>
          </CardContent>
        </Card>

        <Card className="bg-muted/50">
          <CardContent className="p-4 text-center">
            <Zap className="w-6 h-6 text-muted-foreground mx-auto mb-2" />
            <p className="text-2xl font-bold">{performanceMetrics.apiUptime.current}%</p>
            <p className="text-xs text-muted-foreground">API Uptime</p>
            <Badge variant="outline" className="mt-2 text-xs">
              Stable
            </Badge>
          </CardContent>
        </Card>
      </motion.div>

      {/* Accuracy Trend Chart (Simple Bar Representation) */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary" />
              Daily Field Accuracy Trend
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-1 h-32">
              {dailyAccuracy.map((value, index) => (
                <motion.div
                  key={index}
                  initial={{ height: 0 }}
                  animate={{ height: `${(value - 85) * 6}%` }}
                  transition={{ delay: index * 0.05, duration: 0.3 }}
                  className="flex-1 bg-gradient-to-t from-primary to-primary/60 rounded-t-sm relative group cursor-pointer"
                  style={{ minHeight: '8px' }}
                >
                  <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-card px-1.5 py-0.5 rounded text-xs font-medium opacity-0 group-hover:opacity-100 transition-opacity shadow-md border whitespace-nowrap z-10">
                    {value}%
                  </div>
                </motion.div>
              ))}
            </div>
            <div className="flex justify-between mt-2 text-xs text-muted-foreground">
              <span>14 days ago</span>
              <span>Today</span>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Error Analysis */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-warning" />
              Error Analysis by Document Type
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {errorAnalysis.map((item, index) => (
                <motion.div
                  key={item.type}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="flex items-center gap-4"
                >
                  <div className="w-28 font-medium text-sm">{item.type}</div>
                  <div className="flex-1">
                    <Progress 
                      value={item.errorRate * 10} 
                      className="h-2"
                    />
                  </div>
                  <div className="w-12 text-right text-sm font-semibold text-destructive">
                    {item.errorRate}%
                  </div>
                  <div className="w-36 text-xs text-muted-foreground hidden md:block">
                    {item.commonIssue}
                  </div>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}

export default PerformanceMetrics;
