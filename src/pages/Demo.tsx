import React, { useState, useCallback, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Upload, 
  CheckCircle2, 
  Loader2, 
  AlertCircle,
  Zap,
  Clock,
  TrendingUp
} from 'lucide-react';
import SmartDropzone from '@/components/finscribe/SmartDropzone';
import ImageViewer, { BoundingBox } from '@/components/finscribe/ImageViewer';
import CorrectionsPanel, { CorrectionsData } from '@/components/finscribe/CorrectionsPanel';
import { demoOCR, demoAcceptAndQueue, getDemoMetrics } from '@/services/api';
import { dataToCorrections } from '@/lib/ocrUtils';
import { toast } from 'sonner';

/**
 * Demo page for polished E2E demo flow:
 * upload -> OCR -> overlay bounding boxes -> structured JSON -> inline edit -> Accept & Send to Training
 */
const Demo = () => {
  const [demoMode, setDemoMode] = useState(true);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [ocrResult, setOcrResult] = useState<any>(null);
  const [boundingBoxes, setBoundingBoxes] = useState<BoundingBox[]>([]);
  const [correctionsData, setCorrectionsData] = useState<CorrectionsData | null>(null);
  const [selectedBoxId, setSelectedBoxId] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [processingTime, setProcessingTime] = useState<number | null>(null);
  const [queuedCount, setQueuedCount] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load metrics on mount
  useEffect(() => {
    loadMetrics();
  }, []);

  const loadMetrics = async () => {
    try {
      const metrics = await getDemoMetrics();
      setQueuedCount(metrics.queued);
    } catch (error) {
      console.error('Failed to load metrics:', error);
    }
  };

  // Handle file upload
  const handleFileUpload = useCallback(async (file: File) => {
    setUploadedFile(file);
    setProcessing(true);
    setProcessingTime(null);
    setOcrResult(null);
    setBoundingBoxes([]);
    setCorrectionsData(null);

    // Create object URL for image preview
    const url = URL.createObjectURL(file);
    setImageUrl(url);

    const startTime = Date.now();

    try {
      // Call demo OCR endpoint
      const result = await demoOCR(file);
      const duration = (Date.now() - startTime) / 1000;
      
      setProcessingTime(duration);
      setOcrResult(result);

      // Extract bounding boxes - convert regions to BoundingBox format
      const boxes: BoundingBox[] = (result.regions || []).map((region: any, index: number) => {
        const bbox = region.bbox || [];
        // Handle different bbox formats: [x, y, w, h] or [x1, y1, x2, y2]
        let x = 0, y = 0, width = 0, height = 0;
        if (bbox.length >= 4) {
          // Assume [x, y, w, h] format for pixel coordinates
          // Normalize to 0-1 range (assuming 1200x800 image)
          x = (bbox[0] || 0) / 1200;
          y = (bbox[1] || 0) / 800;
          width = (bbox[2] || 0) / 1200;
          height = (bbox[3] || 0) / 800;
        }
        return {
          id: `region-${index}`,
          x: Math.max(0, Math.min(1, x)),
          y: Math.max(0, Math.min(1, y)),
          width: Math.max(0, Math.min(1, width)),
          height: Math.max(0, Math.min(1, height)),
          label: region.text || region.type || 'Unknown',
          confidence: region.confidence || 0.9,
          fieldType: (region.type === 'vendor' ? 'vendor' : 
                      region.type === 'invoice_info' ? 'invoice_info' :
                      region.type === 'line_item' ? 'line_item' :
                      region.type === 'totals' ? 'totals' : 'other') as any,
        };
      });
      setBoundingBoxes(boxes);

      // Convert OCR result to corrections data format
      const corrections = dataToCorrections(result as unknown as Record<string, unknown>);
      setCorrectionsData(corrections);

      toast.success('OCR completed', {
        description: `Processed in ${duration.toFixed(2)}s`,
      });
    } catch (error) {
      console.error('OCR failed:', error);
      toast.error('OCR failed', {
        description: error instanceof Error ? error.message : 'Failed to process image',
      });
    } finally {
      setProcessing(false);
    }
  }, []);

  // Handle box click
  const handleBoxClick = useCallback((box: BoundingBox) => {
    setSelectedBoxId(box.id);
    // Scroll to corrections panel or highlight relevant field
    // This is a simplified implementation
  }, []);

  // Handle accept and queue
  const handleAcceptAndQueue = useCallback(async () => {
    if (!correctionsData || !uploadedFile) {
      toast.error('No data to queue');
      return;
    }

    try {
      await demoAcceptAndQueue(
        uploadedFile.name,
        correctionsData as any,
        {
          processing_time: processingTime,
          ocr_backend: ocrResult?.meta?.backend,
        }
      );

      setQueuedCount((prev) => prev + 1);
      
      toast.success('Queued for training', {
        description: 'Corrections have been added to the active learning queue',
      });

      // Reset for next upload
      setUploadedFile(null);
      setImageUrl(null);
      setOcrResult(null);
      setBoundingBoxes([]);
      setCorrectionsData(null);
      setSelectedBoxId(null);
      setProcessingTime(null);

      if (imageUrl) {
        URL.revokeObjectURL(imageUrl);
      }
    } catch (error) {
      console.error('Failed to queue:', error);
      toast.error('Failed to queue', {
        description: error instanceof Error ? error.message : 'Failed to add to training queue',
      });
    }
  }, [correctionsData, uploadedFile, processingTime, ocrResult, imageUrl]);

  // Cleanup object URL on unmount
  useEffect(() => {
    return () => {
      if (imageUrl) {
        URL.revokeObjectURL(imageUrl);
      }
    };
  }, [imageUrl]);

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">FinScribe Demo</h1>
            <p className="text-muted-foreground mt-2">
              Upload → OCR → Edit → Queue for Training
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Switch
                id="demo-mode"
                checked={demoMode}
                onCheckedChange={setDemoMode}
              />
              <Label htmlFor="demo-mode">Demo Mode</Label>
            </div>
            {queuedCount > 0 && (
              <Badge variant="secondary" className="text-sm">
                {queuedCount} queued
              </Badge>
            )}
          </div>
        </div>

        {/* Metrics Bar */}
        {processingTime !== null && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">Processing:</span>
                    <span className="font-semibold">{processingTime.toFixed(2)}s</span>
                  </div>
                  {ocrResult?.meta?.backend && (
                    <div className="flex items-center gap-2">
                      <Zap className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">Backend:</span>
                      <Badge variant="outline">{ocrResult.meta.backend}</Badge>
                    </div>
                  )}
                  {ocrResult?.regions && (
                    <div className="flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">Regions:</span>
                      <span className="font-semibold">{ocrResult.regions.length}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Upload & Image Viewer */}
          <div className="lg:col-span-2 space-y-6">
            {/* Upload Area */}
            {!uploadedFile && (
              <Card>
                <CardHeader>
                  <CardTitle>Upload Invoice</CardTitle>
                </CardHeader>
                <CardContent>
                  <SmartDropzone
                    onFilesChange={(files) => {
                      if (files.length > 0 && files[0].status === 'completed') {
                        handleFileUpload(files[0].file);
                      }
                    }}
                    maxFiles={1}
                    maxSizeMB={10}
                  />
                  {demoMode && (
                    <Alert className="mt-4">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        <strong>Demo Mode:</strong> Try uploading one of the sample invoices from{' '}
                        <code className="text-xs bg-muted px-1 py-0.5 rounded">examples/</code>
                      </AlertDescription>
                    </Alert>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Image Viewer with Overlay */}
            {imageUrl && (
              <Card>
                <CardHeader>
                  <CardTitle>OCR Overlay</CardTitle>
                </CardHeader>
                <CardContent>
                  {processing ? (
                    <div className="flex items-center justify-center h-[600px]">
                      <div className="text-center space-y-4">
                        <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary" />
                        <p className="text-muted-foreground">Processing OCR...</p>
                      </div>
                    </div>
                  ) : (
                    <ImageViewer
                      imageUrl={imageUrl}
                      boundingBoxes={boundingBoxes}
                      onBoxClick={handleBoxClick}
                      selectedBoxId={selectedBoxId}
                    />
                  )}
                </CardContent>
              </Card>
            )}

            {/* OCR Raw Output */}
            {ocrResult && (
              <Card>
                <CardHeader>
                  <CardTitle>OCR Output</CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="text-xs bg-muted p-4 rounded-lg overflow-auto max-h-64">
                    {JSON.stringify(ocrResult, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column: Corrections Panel */}
          <div className="space-y-6">
            {correctionsData ? (
              <Card>
                <CardHeader>
                  <CardTitle>Corrections</CardTitle>
                </CardHeader>
                <CardContent>
                  <CorrectionsPanel
                    data={correctionsData}
                    resultId={uploadedFile?.name || undefined}
                    onDataChange={setCorrectionsData}
                    highlightedFieldId={selectedBoxId}
                  />
                  <Button
                    className="w-full mt-4"
                    onClick={handleAcceptAndQueue}
                    size="lg"
                  >
                    <CheckCircle2 className="w-4 h-4 mr-2" />
                    Accept & Send to Training
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center text-muted-foreground py-12">
                    <Upload className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Upload an invoice to see corrections panel</p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Demo;

