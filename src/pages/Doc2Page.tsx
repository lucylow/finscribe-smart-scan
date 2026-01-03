import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Upload, FileImage, ExternalLink, Loader2, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";
import { Link } from "react-router-dom";

export default function Doc2Page() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [generatedHtml, setGeneratedHtml] = useState<string | null>(null);
  const [pageUrl, setPageUrl] = useState<string | null>(null);
  const [previewImage, setPreviewImage] = useState<string | null>(null);

  const processWithBase64 = async (imageBase64: string, fileName: string, previewUrl?: string) => {
    setIsProcessing(true);
    setGeneratedHtml(null);
    setPageUrl(null);
    if (previewUrl) setPreviewImage(previewUrl);

    try {
      const { data, error } = await supabase.functions.invoke('doc2page', {
        body: { imageBase64, fileName }
      });

      if (error) throw error;

      if (data.success && data.html) {
        setGeneratedHtml(data.html);
        const blob = new Blob([data.html], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        setPageUrl(url);

        toast.success(
          data.usedFallback 
            ? "Document processed with fallback (demo mode)" 
            : "Document processed successfully!",
          { description: `Model: ${data.model}` }
        );
      } else {
        throw new Error(data.error || "Failed to process document");
      }
    } catch (error) {
      console.error("Doc2Page error:", error);
      toast.error("Failed to process document", {
        description: error instanceof Error ? error.message : "Unknown error"
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const processDocument = async (file: File) => {
    const reader = new FileReader();
    const base64Promise = new Promise<string>((resolve, reject) => {
      reader.onload = () => {
        const result = reader.result as string;
        const base64 = result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
    });
    reader.readAsDataURL(file);
    const imageBase64 = await base64Promise;
    const previewUrl = `data:${file.type};base64,${imageBase64}`;
    setPreviewImage(previewUrl);
    await processWithBase64(imageBase64, file.name, previewUrl);
  };

  const runDemo = async () => {
    // Use a hardcoded Walmart receipt base64 demo - trigger fallback with mock
    setPreviewImage("/placeholder.svg");
    await processWithBase64("DEMO_WALMART_RECEIPT", "WalmartReceipt.jpeg", "/placeholder.svg");
  };

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      processDocument(file);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.webp'],
      'application/pdf': ['.pdf']
    },
    maxFiles: 1,
    disabled: isProcessing
  });

  const openInNewTab = () => {
    if (pageUrl) {
      window.open(pageUrl, '_blank');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-muted/30 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Link to="/">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-purple-600 bg-clip-text text-transparent">
              Doc2Page
            </h1>
            <p className="text-muted-foreground">
              Convert documents to HTML pages with ERNIE & PaddleOCR
            </p>
          </div>
        </div>

        {/* Upload Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileImage className="h-5 w-5" />
              Upload Document
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div
              {...getRootProps()}
              className={`
                border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
                transition-all duration-200
                ${isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'}
                ${isProcessing ? 'opacity-50 cursor-not-allowed' : ''}
              `}
            >
              <input {...getInputProps()} />
              {isProcessing ? (
                <div className="flex flex-col items-center gap-4">
                  <Loader2 className="h-12 w-12 animate-spin text-primary" />
                  <p className="text-muted-foreground">Processing with Doc2Page...</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-4">
                  <Upload className="h-12 w-12 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Drop your document here</p>
                    <p className="text-sm text-muted-foreground">or click to browse</p>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Supports: PNG, JPG, JPEG, WebP, PDF
                  </p>
                  <Button 
                    variant="secondary" 
                    className="mt-4"
                    onClick={(e) => { e.stopPropagation(); runDemo(); }}
                  >
                    🧾 Try Demo (Walmart Receipt)
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Preview Image */}
        {previewImage && (
          <Card>
            <CardHeader>
              <CardTitle>Uploaded Document</CardTitle>
            </CardHeader>
            <CardContent>
              <img 
                src={previewImage} 
                alt="Uploaded document" 
                className="max-w-full h-auto rounded-lg border"
              />
            </CardContent>
          </Card>
        )}

        {/* Generated Page */}
        {pageUrl && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Generated HTML Page</span>
                <Button onClick={openInNewTab} className="gap-2">
                  <ExternalLink className="h-4 w-4" />
                  Open Page URL
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-muted/50 rounded-lg p-4 mb-4">
                <p className="text-sm font-mono break-all">
                  <span className="text-muted-foreground">Generated URL: </span>
                  <a 
                    href={pageUrl} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    {pageUrl}
                  </a>
                </p>
              </div>
              
              <div className="border rounded-lg overflow-hidden" style={{ height: '600px' }}>
                <iframe
                  src={pageUrl}
                  title="Generated Document Page"
                  className="w-full h-full"
                  sandbox="allow-same-origin"
                />
              </div>
            </CardContent>
          </Card>
        )}

        {/* Info */}
        <Card className="bg-gradient-to-r from-purple-500/10 to-pink-500/10 border-purple-500/20">
          <CardContent className="pt-6">
            <p className="text-center text-sm">
              Powered by{" "}
              <a 
                href="https://huggingface.co/spaces/PaddlePaddle/doc2page" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-primary font-medium hover:underline"
              >
                ERNIE & PaddleOCR: Doc2Page
              </a>
              {" "}• Falls back to mock HTML if HF API is unavailable
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
