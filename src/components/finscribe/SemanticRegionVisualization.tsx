import React from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  MapPin, 
  User, 
  TableIcon, 
  DollarSign, 
  CheckCircle,
  Eye
} from 'lucide-react';

interface SemanticRegion {
  type: string;
  name: string;
  confidence: number;
  fields: string[];
  color: string;
  icon: React.ElementType;
}

const semanticRegions: SemanticRegion[] = [
  { 
    type: 'vendor_block', 
    name: 'Vendor Block', 
    confidence: 0.99, 
    fields: ['Company Name', 'Address', 'Tax ID', 'Contact'],
    color: 'primary',
    icon: MapPin
  },
  { 
    type: 'client_info', 
    name: 'Client Info', 
    confidence: 0.97, 
    fields: ['Invoice #', 'Date', 'PO #', 'Due Date'],
    color: 'secondary',
    icon: User
  },
  { 
    type: 'line_items', 
    name: 'Line Items Table', 
    confidence: 0.95, 
    fields: ['Description', 'Qty', 'Price', 'Total'],
    color: 'accent',
    icon: TableIcon
  },
  { 
    type: 'totals', 
    name: 'Totals Section', 
    confidence: 0.98, 
    fields: ['Subtotal', 'Tax', 'Discount', 'Grand Total'],
    color: 'success',
    icon: DollarSign
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0 }
};

function SemanticRegionVisualization() {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      {/* Document Layout Visualization */}
      <motion.div variants={itemVariants}>
        <Card className="overflow-hidden">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-semibold flex items-center gap-2">
                <Eye className="w-4 h-4 text-primary" />
                Semantic Region Detection
              </h4>
              <Badge variant="outline" className="text-xs">
                4 regions detected
              </Badge>
            </div>
            
            {/* Mock Document Layout */}
            <div className="relative bg-muted/30 rounded-lg p-4 border-2 border-dashed border-muted min-h-[300px]">
              {/* Vendor Block */}
              <motion.div 
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.1 }}
                className="absolute top-4 left-4 w-[45%] h-[22%] rounded-lg border-2 border-primary bg-primary/10 flex items-center justify-center"
              >
                <span className="text-xs font-medium text-primary">Vendor Block</span>
              </motion.div>
              
              {/* Client Info */}
              <motion.div 
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2 }}
                className="absolute top-4 right-4 w-[45%] h-[18%] rounded-lg border-2 border-secondary bg-secondary/10 flex items-center justify-center"
              >
                <span className="text-xs font-medium text-secondary">Client Info</span>
              </motion.div>
              
              {/* Line Items Table */}
              <motion.div 
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.3 }}
                className="absolute top-[35%] left-4 right-4 h-[35%] rounded-lg border-2 border-accent bg-accent/30 flex items-center justify-center"
              >
                <span className="text-xs font-medium text-accent-foreground">Line Items Table</span>
              </motion.div>
              
              {/* Totals Section */}
              <motion.div 
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.4 }}
                className="absolute bottom-4 right-4 w-[45%] h-[18%] rounded-lg border-2 border-success bg-success/10 flex items-center justify-center"
              >
                <span className="text-xs font-medium text-success">Totals Section</span>
              </motion.div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Region Details */}
      <motion.div variants={itemVariants} className="grid md:grid-cols-2 gap-4">
        {semanticRegions.map((region, index) => (
          <motion.div
            key={region.type}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Card className="h-full hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                      region.color === 'primary' ? 'bg-primary/20 text-primary' :
                      region.color === 'secondary' ? 'bg-secondary/20 text-secondary' :
                      region.color === 'success' ? 'bg-success/20 text-success' :
                      'bg-accent text-accent-foreground'
                    }`}>
                      <region.icon className="w-4 h-4" />
                    </div>
                    <span className="font-medium">{region.name}</span>
                  </div>
                  <Badge variant="outline" className="text-xs">
                    {(region.confidence * 100).toFixed(0)}%
                  </Badge>
                </div>
                
                <Progress 
                  value={region.confidence * 100} 
                  className="h-2 mb-3"
                />
                
                <div className="flex flex-wrap gap-1">
                  {region.fields.map((field) => (
                    <span 
                      key={field}
                      className="inline-flex items-center gap-1 px-2 py-0.5 bg-muted rounded text-xs"
                    >
                      <CheckCircle className="w-3 h-3 text-success" />
                      {field}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </motion.div>
    </motion.div>
  );
}

export default SemanticRegionVisualization;
