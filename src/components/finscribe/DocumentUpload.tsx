import React, { useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDropzone } from 'react-dropzone';
import { CloudUpload, FileText, X, Image, FileCheck, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface DocumentUploadProps {
  onFileSelect: (file: File | null) => void;
  file: File | null;
}

function DocumentUpload({ onFileSelect, file }: DocumentUploadProps) {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0]);
    }
  }, [onFileSelect]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.gif'],
      'application/pdf': ['.pdf']
    },
    maxFiles: 1,
  });

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (type: string) => {
    if (type.includes('pdf')) return FileText;
    if (type.includes('image')) return Image;
    return FileText;
  };

  const dropzoneProps = getRootProps();
  
  return (
    <div className="space-y-4">
      <motion.div
        onClick={dropzoneProps.onClick}
        onKeyDown={dropzoneProps.onKeyDown}
        onFocus={dropzoneProps.onFocus}
        onBlur={dropzoneProps.onBlur}
        tabIndex={dropzoneProps.tabIndex}
        role={dropzoneProps.role}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
        className={cn(
          "relative p-12 text-center cursor-pointer rounded-xl transition-all duration-300 overflow-hidden",
          "border-2 border-dashed",
          isDragActive 
            ? "border-primary bg-primary/5 shadow-lg shadow-primary/10" 
            : file 
              ? "border-primary bg-primary/5"
              : "border-muted-foreground/30 hover:border-primary hover:bg-accent/30"
        )}
      >
        <input {...getInputProps()} />
        
        {/* Animated background pattern */}
        <div className="absolute inset-0 opacity-30">
          <div className="absolute top-4 left-8 w-16 h-16 border-2 border-primary/20 rounded-lg rotate-12 animate-float" />
          <div className="absolute bottom-8 right-12 w-12 h-12 border-2 border-secondary/20 rounded-lg -rotate-6 animate-float-delayed" />
          <div className="absolute top-1/2 right-8 w-8 h-8 border-2 border-accent/20 rounded-lg rotate-45 animate-float" />
        </div>

        <div className="relative z-10">
          <motion.div
            animate={isDragActive ? { scale: 1.1, y: -5 } : { scale: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className={cn(
              "w-20 h-20 rounded-xl mx-auto mb-6 flex items-center justify-center transition-all",
              isDragActive ? "bg-primary text-primary-foreground shadow-lg shadow-primary/30" : 
              file ? "bg-primary text-primary-foreground" :
              "bg-muted text-muted-foreground"
            )}
          >
            {file ? (
              <FileCheck className="w-10 h-10" />
            ) : (
              <CloudUpload className="w-10 h-10" />
            )}
          </motion.div>
          
          <AnimatePresence mode="wait">
            {isDragActive ? (
              <motion.div
                key="drop"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <h3 className="text-xl font-semibold text-primary mb-2">
                  Drop your file here
                </h3>
                <p className="text-muted-foreground">Release to upload</p>
              </motion.div>
            ) : file ? (
              <motion.div
                key="selected"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <h3 className="text-xl font-semibold text-primary mb-2 flex items-center justify-center gap-2">
                  <Sparkles className="w-5 h-5" />
                  File Ready for Analysis
                </h3>
                <p className="text-muted-foreground">Click "Analyze with AI" to process</p>
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <h3 className="text-xl font-semibold mb-2">
                  Drag & drop your document here
                </h3>
                <p className="text-muted-foreground mb-4">or click to browse files</p>
                <div className="flex justify-center gap-2 flex-wrap">
                  <span className="px-3 py-1 bg-primary/10 text-primary rounded-full text-xs font-medium">PDF</span>
                  <span className="px-3 py-1 bg-primary/10 text-primary rounded-full text-xs font-medium">PNG</span>
                  <span className="px-3 py-1 bg-primary/10 text-primary rounded-full text-xs font-medium">JPG</span>
                  <span className="px-3 py-1 bg-muted text-muted-foreground rounded-full text-xs font-medium">Max 50MB</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      <AnimatePresence>
        {file && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="flex items-center p-4 bg-card rounded-xl border shadow-sm">
              {React.createElement(getFileIcon(file.type), {
                className: "w-12 h-12 text-primary mr-4 flex-shrink-0"
              })}
              <div className="flex-grow min-w-0">
                <p className="font-medium truncate text-foreground">{file.name}</p>
                <p className="text-sm text-muted-foreground">
                  {formatFileSize(file.size)} • {file.type.split('/')[1]?.toUpperCase() || 'File'}
                </p>
              </div>
              <Button 
                variant="ghost" 
                size="icon"
                className="flex-shrink-0 hover:bg-destructive/10 hover:text-destructive"
                onClick={(e) => {
                  e.stopPropagation();
                  onFileSelect(null);
                }}
              >
                <X className="w-5 h-5" />
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default DocumentUpload;