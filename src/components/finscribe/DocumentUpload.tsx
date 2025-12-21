import React, { useCallback, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDropzone, type FileRejection } from 'react-dropzone';
import { CloudUpload, FileText, X, Image, FileCheck, Sparkles, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { cn } from '@/lib/utils';
import { ErrorHandler } from '@/lib/errorHandler';
import { toast } from 'sonner';

interface DocumentUploadProps {
  onFileSelect: (file: File | null) => void;
  file: File | null;
}

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

function DocumentUpload({ onFileSelect, file }: DocumentUploadProps) {
  const [validationError, setValidationError] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
    // Clear previous validation errors
    setValidationError(null);

    // Handle rejected files
    if (rejectedFiles.length > 0) {
      const rejection = rejectedFiles[0];
      let errorMessage = 'File rejected. ';
      
      if (rejection.errors) {
        const error = rejection.errors[0];
        if (error.code === 'file-too-large') {
          errorMessage = `File is too large. Maximum size is ${MAX_FILE_SIZE / (1024 * 1024)}MB.`;
        } else if (error.code === 'file-invalid-type') {
          errorMessage = 'File type not supported. Please use PDF, PNG, JPG, or GIF.';
        } else {
          errorMessage = error.message || 'Invalid file.';
        }
      }
      
      setValidationError(errorMessage);
      ErrorHandler.handleError(new Error(errorMessage), {
        showToast: true,
        logToConsole: true,
      });
      return;
    }

    if (acceptedFiles.length > 0) {
      const selectedFile = acceptedFiles[0];
      
      // Use centralized validation
      const validation = ErrorHandler.validateFile(selectedFile, {
        maxSizeMB: MAX_FILE_SIZE / (1024 * 1024),
      });
      
      if (!validation.valid) {
        const errorMsg = validation.error || 'Invalid file';
        setValidationError(errorMsg);
        ErrorHandler.handleError(new Error(errorMsg), {
          showToast: true,
          logToConsole: true,
        });
        return;
      }

      // File is valid
      setValidationError(null);
      onFileSelect(selectedFile);
      toast.success('File selected', {
        description: `${selectedFile.name} is ready for analysis.`,
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
      <AnimatePresence>
        {validationError && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{validationError}</AlertDescription>
            </Alert>
          </motion.div>
        )}
      </AnimatePresence>
      
      <motion.div
        onClick={dropzoneProps.onClick}
        onKeyDown={dropzoneProps.onKeyDown}
        onFocus={dropzoneProps.onFocus}
        onBlur={dropzoneProps.onBlur}
        onDragEnter={dropzoneProps.onDragEnter}
        onDragLeave={dropzoneProps.onDragLeave}
        onDragOver={dropzoneProps.onDragOver}
        onDrop={dropzoneProps.onDrop}
        ref={dropzoneProps.ref}
        tabIndex={dropzoneProps.tabIndex}
        role={dropzoneProps.role}
        aria-label="Document upload area"
        aria-describedby="upload-instructions"
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
        className={cn(
          "relative p-12 text-center cursor-pointer rounded-xl transition-all duration-300 overflow-hidden group",
          "border-2 border-dashed focus-within:ring-2 focus-within:ring-primary focus-within:ring-offset-2",
          isDragActive 
            ? "border-primary bg-primary/10 shadow-lg shadow-primary/20 border-solid" 
            : file 
              ? "border-primary bg-primary/5 shadow-md"
              : "border-muted-foreground/30 hover:border-primary/50 hover:bg-accent/30 hover:shadow-md"
        )}
      >
        <input {...getInputProps()} aria-label="File input" />
        <span id="upload-instructions" className="sr-only">
          Drag and drop a document here, or click to browse. Supported formats: PDF, PNG, JPG, JPEG. Maximum file size: 50MB.
        </span>
        
        {/* Animated background pattern */}
        <div className="absolute inset-0 opacity-20 group-hover:opacity-30 transition-opacity">
          <motion.div 
            className="absolute top-4 left-8 w-16 h-16 border-2 border-primary/20 rounded-lg rotate-12"
            animate={{
              y: [0, -10, 0],
              rotate: [12, 15, 12],
            }}
            transition={{
              duration: 4,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
          <motion.div 
            className="absolute bottom-8 right-12 w-12 h-12 border-2 border-secondary/20 rounded-lg -rotate-6"
            animate={{
              y: [0, 10, 0],
              rotate: [-6, -9, -6],
            }}
            transition={{
              duration: 5,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 0.5,
            }}
          />
          <motion.div 
            className="absolute top-1/2 right-8 w-8 h-8 border-2 border-accent/20 rounded-lg rotate-45"
            animate={{
              y: [0, -8, 0],
              rotate: [45, 50, 45],
            }}
            transition={{
              duration: 3.5,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 1,
            }}
          />
        </div>
        
        {/* Gradient overlay on hover */}
        <motion.div
          className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
          initial={false}
        />

        <div className="relative z-10">
          <motion.div
            animate={isDragActive ? { 
              scale: 1.15, 
              y: -8,
              rotate: [0, 5, -5, 0]
            } : file ? {
              scale: 1,
              rotate: 0
            } : { 
              scale: 1, 
              y: 0,
              rotate: 0
            }}
            transition={{ 
              duration: isDragActive ? 0.3 : 0.2,
              rotate: { duration: 0.5, repeat: isDragActive ? Infinity : 0, repeatDelay: 0.5 }
            }}
            className={cn(
              "w-20 h-20 rounded-xl mx-auto mb-6 flex items-center justify-center transition-all relative",
              isDragActive ? "bg-primary text-primary-foreground shadow-lg shadow-primary/30 pulse-glow" : 
              file ? "bg-primary text-primary-foreground shadow-md" :
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
            <motion.div 
              className="flex items-center p-4 bg-card rounded-xl border shadow-sm card-hover group"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
            >
              <motion.div
                animate={{ rotate: [0, 5, -5, 0] }}
                transition={{ duration: 0.5, delay: 0.2 }}
              >
                {React.createElement(getFileIcon(file.type), {
                  className: "w-12 h-12 text-primary mr-4 flex-shrink-0 group-hover:scale-110 transition-transform"
                })}
              </motion.div>
              <div className="flex-grow min-w-0">
                <p className="font-medium truncate text-foreground">{file.name}</p>
                <p className="text-sm text-muted-foreground">
                  {formatFileSize(file.size)} • {file.type.split('/')[1]?.toUpperCase() || 'File'}
                </p>
              </div>
              <Button 
                variant="ghost" 
                size="icon"
                className="flex-shrink-0 hover:bg-destructive/10 hover:text-destructive transition-all hover:scale-110"
                onClick={(e) => {
                  e.stopPropagation();
                  setValidationError(null);
                  onFileSelect(null);
                }}
                aria-label="Remove file"
              >
                <X className="w-5 h-5" />
              </Button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default DocumentUpload;