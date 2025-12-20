import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Brain, Cpu, Database, Shield } from 'lucide-react';

function ModelInfo() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Model Architecture Details</h2>
      
      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-primary" />
              PaddleOCR-VL (Fine-Tuned)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <Badge variant="secondary" className="mb-2">Vision-Language Model</Badge>
                <p className="text-sm text-muted-foreground">
                  Fine-tuned on 5,000+ financial documents including invoices, 
                  receipts, and purchase orders for domain-specific accuracy.
                </p>
              </div>
              <div className="border-t pt-3">
                <h4 className="font-medium mb-2">Key Capabilities</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Advanced table structure recognition</li>
                  <li>• Multi-language text extraction</li>
                  <li>• Layout-aware document understanding</li>
                  <li>• Handwritten text recognition</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="w-5 h-5 text-secondary" />
              ERNIE 5 Integration
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <Badge variant="secondary" className="mb-2">Semantic Enrichment</Badge>
                <p className="text-sm text-muted-foreground">
                  Baidu's ERNIE 5 (with ERNIE 4.5 fallback) provides advanced semantic understanding and 
                  validation of extracted financial data with improved accuracy and reasoning capabilities.
                </p>
              </div>
              <div className="border-t pt-3">
                <h4 className="font-medium mb-2">Key Capabilities</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Enhanced entity relationship extraction</li>
                  <li>• Advanced financial rule validation</li>
                  <li>• Currency and date normalization</li>
                  <li>• Intelligent anomaly detection</li>
                  <li>• Multi-modal reasoning (text + vision)</li>
                </ul>
              </div>
              <div className="border-t pt-3">
                <h4 className="font-medium mb-2 text-xs">Model Support</h4>
                <div className="flex flex-wrap gap-1">
                  <Badge variant="outline" className="text-xs">ERNIE 5</Badge>
                  <Badge variant="outline" className="text-xs">ERNIE 4.5 VL</Badge>
                  <Badge variant="outline" className="text-xs">HuggingFace</Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="w-5 h-5 text-primary" />
              Training Data
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 text-center">
              <div className="p-3 bg-muted rounded-lg">
                <p className="text-2xl font-bold text-primary">5,000+</p>
                <p className="text-xs text-muted-foreground">Documents</p>
              </div>
              <div className="p-3 bg-muted rounded-lg">
                <p className="text-2xl font-bold text-primary">15+</p>
                <p className="text-xs text-muted-foreground">Languages</p>
              </div>
              <div className="p-3 bg-muted rounded-lg">
                <p className="text-2xl font-bold text-primary">50+</p>
                <p className="text-xs text-muted-foreground">Currencies</p>
              </div>
              <div className="p-3 bg-muted rounded-lg">
                <p className="text-2xl font-bold text-primary">99%+</p>
                <p className="text-xs text-muted-foreground">Accuracy</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-secondary" />
              Security & Compliance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                <Badge>SOC 2 Type II</Badge>
                <Badge>GDPR</Badge>
                <Badge>HIPAA</Badge>
                <Badge>PCI DSS</Badge>
              </div>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• End-to-end encryption (AES-256)</li>
                <li>• No document storage (ephemeral processing)</li>
                <li>• Audit logging for all operations</li>
                <li>• Role-based access control</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default ModelInfo;
