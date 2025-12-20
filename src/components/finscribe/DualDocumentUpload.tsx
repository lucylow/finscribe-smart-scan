import React, { useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDropzone } from 'react-dropzone';
import { CloudUpload, FileText, X, Image, FileCheck, Sparkles, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

interface DualDocumentUploadProps {
  onFile1Select: (file: File | null) => void;
  onFile2Select: (file: File | null) => void;
  file1: File | null;
  file2: File | null;
}

function DualDocumentUpload({ onFile1Select, onFile2Select, file1, file2 }: DualDocumentUploadProps) {
  const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

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

  const FileUploadSlot = ({
    file,
    onFileSelect,
    label,
    acceptFiles
  }: {
    file: File | null;
    onFileSelect: (file: File | null) => void;
    label: string;
    acceptFiles?: (files: File[]) => void;
  }) => {
    const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
      // Handle rejected files
      if (rejectedFiles.length > 0) {
        const rejection = rejectedFiles[0];
        if (rejection.errors) {
          const error = rejection.errors[0];
          if (error.code === 'file-too-large') {
            toast.error('File too large', {
              description: `Please select a file smaller than ${MAX_FILE_SIZE / (1024 * 1024)}MB.`,
            });
            return;
          }
          if (error.code === 'file-invalid-type') {
            toast.error('Invalid file type', {
              description: 'Please select a PDF or image file (PNG, JPG, JPEG).',
            });
            return;
          }
          toast.error('File rejected', {
            description: error.message || 'Please try a different file.',
          });
          return;
        }
      }

      if (acceptedFiles.length > 0) {
        const selectedFile = acceptedFiles[0];
        
        // Additional validation
        if (selectedFile.size > MAX_FILE_SIZE) {
          toast.error('File too large', {
            description: `Please select a file smaller than ${MAX_FILE_SIZE / (1024 * 1024)}MB.`,
          });
          return;
        }

        onFileSelect(selectedFile);
        toast.success('File selected', {
          description: `${selectedFile.name} is ready.`,
          duration: 2000,
        });
      }
    }, [onFileSelect]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
      onDrop,
      accept: {
        'image/*': ['.jpeg', '.jpg', '.png', '.gif'],
        'application/pdf': ['.pdf']
      },
      maxFiles: 1,
      maxSize: MAX_FILE_SIZE,
    });

    const dropzoneProps = getRootProps();

    return (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-center">{label}</h3>
        <motion.div
          onClick={dropzoneProps.onClick}
          onKeyDown={dropzoneProps.onKeyDown}
          onFocus={dropzoneProps.onFocus}
          onBlur={dropzoneProps.onBlur}
          tabIndex={dropzoneProps.tabIndex}
          role={dropzoneProps.role}
          aria-label={`${label} upload area`}
          aria-describedby={`${label.toLowerCase().replace(/\s+/g, '-')}-instructions`}
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          className={cn(
            "relative p-8 text-center cursor-pointer rounded-xl transition-all duration-300 overflow-hidden",
            "border-2 border-dashed focus-within:ring-2 focus-within:ring-primary focus-within:ring-offset-2",
            isDragActive 
              ? "border-primary bg-primary/5 shadow-lg shadow-primary/10" 
              : file 
                ? "border-primary bg-primary/5"
                : "border-muted-foreground/30 hover:border-primary hover:bg-accent/30"
          )}
        >
          <input {...getInputProps()} aria-label={`${label} file input`} />
          <span id={`${label.toLowerCase().replace(/\s+/g, '-')}-instructions`} className="sr-only">
            Drag and drop a document here, or click to browse. Supported formats: PDF, PNG, JPG, JPEG. Maximum file size: 50MB.
          </span>
          
          <div className="relative z-10">
            <motion.div
              animate={isDragActive ? { scale: 1.1, y: -5 } : { scale: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              className={cn(
                "w-16 h-16 rounded-xl mx-auto mb-4 flex items-center justify-center transition-all",
                isDragActive ? "bg-primary text-primary-foreground shadow-lg shadow-primary/30" : 
                file ? "bg-primary text-primary-foreground" :
                "bg-muted text-muted-foreground"
              )}
            >
              {file ? (
                <FileCheck className="w-8 h-8" />
              ) : (
                <CloudUpload className="w-8 h-8" />
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
                  <p className="text-sm font-semibold text-primary mb-1">
                    Drop your file here
                  </p>
                  <p className="text-xs text-muted-foreground">Release to upload</p>
                </motion.div>
              ) : file ? (
                <motion.div
                  key="selected"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                >
                  <p className="text-sm font-semibold text-primary mb-1 flex items-center justify-center gap-2">
                    <Sparkles className="w-4 h-4" />
                    File Ready
                  </p>
                  <p className="text-xs text-muted-foreground">Click to change</p>
                </motion.div>
              ) : (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                >
                  <p className="text-sm font-semibold mb-1">
                    Drag & drop or click
                  </p>
                  <p className="text-xs text-muted-foreground mb-2">to select file</p>
                  <div className="flex justify-center gap-1 flex-wrap">
                    <span className="px-2 py-0.5 bg-primary/10 text-primary rounded-full text-xs">PDF</span>
                    <span className="px-2 py-0.5 bg-primary/10 text-primary rounded-full text-xs">PNG</span>
                    <span className="px-2 py-0.5 bg-primary/10 text-primary rounded-full text-xs">JPG</span>
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
              <div className="flex items-center p-3 bg-card rounded-lg border shadow-sm">
                {React.createElement(getFileIcon(file.type), {
                  className: "w-8 h-8 text-primary mr-3 flex-shrink-0"
                })}
                <div className="flex-grow min-w-0">
                  <p className="text-sm font-medium truncate text-foreground">{file.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatFileSize(file.size)} • {file.type.split('/')[1]?.toUpperCase() || 'File'}
                  </p>
                </div>
                <Button 
                  variant="ghost" 
                  size="icon"
                  className="flex-shrink-0 h-8 w-8 hover:bg-destructive/10 hover:text-destructive"
                  onClick={(e) => {
                    e.stopPropagation();
                    onFileSelect(null);
                  }}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="grid md:grid-cols-2 gap-6">
        <FileUploadSlot
          file={file1}
          onFileSelect={onFile1Select}
          label="Document 1 (e.g., Quote/Proposal)"
        />
        
        <div className="hidden md:flex items-center justify-center">
          <ArrowRight className="w-8 h-8 text-muted-foreground" />
        </div>
        
        <FileUploadSlot
          file={file2}
          onFileSelect={onFile2Select}
          label="Document 2 (e.g., Invoice)"
        />
      </div>

      {file1 && file2 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-primary/5 border border-primary/20 rounded-xl"
        >
          <div className="flex items-center gap-3">
            <Sparkles className="w-5 h-5 text-primary" />
            <div className="flex-1">
              <p className="text-sm font-semibold text-foreground">Ready to Compare</p>
              <p className="text-xs text-muted-foreground">
                Both documents are ready. Click "Compare Documents" to analyze differences.
              </p>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}

export default DualDocumentUpload;

