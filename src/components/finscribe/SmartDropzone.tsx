import React, { useCallback, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDropzone, type FileRejection } from 'react-dropzone';
import { 
  CloudUpload, 
  FileText, 
  X, 
  Image, 
  FileCheck, 
  Sparkles, 
  AlertTriangle,
  Loader2,
  RefreshCw,
  CheckCircle2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { ErrorHandler } from '@/lib/errorHandler';
import { toast } from 'sonner';

export interface QueuedFile {
  id: string;
  file: File;
  thumbnail?: string;
  status: 'queued' | 'uploading' | 'completed' | 'error' | 'cancelled';
  progress: number;
  error?: string;
  pages?: number; // For PDFs
}

interface SmartDropzoneProps {
  onFilesChange: (files: QueuedFile[]) => void;
  maxFiles?: number;
  maxSizeMB?: number;
  accept?: Record<string, string[]>;
  disabled?: boolean;
}

const DEFAULT_MAX_SIZE = 10 * 1024 * 1024; // 10MB default
const COMPRESSION_THRESHOLD = 2 * 1024 * 1024; // 2MB

/**
 * Create a thumbnail from an image file
 */
async function createThumbnail(file: File, maxWidth = 200, maxHeight = 200): Promise<string> {
  return new Promise((resolve, reject) => {
    if (!file.type.startsWith('image/')) {
      // For PDFs, return a placeholder
      resolve('');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new window.Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        let width = img.width;
        let height = img.height;

        // Calculate new dimensions
        if (width > height) {
          if (width > maxWidth) {
            height = (height * maxWidth) / width;
            width = maxWidth;
          }
        } else {
          if (height > maxHeight) {
            width = (width * maxHeight) / height;
            height = maxHeight;
          }
        }

        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          reject(new Error('Could not get canvas context'));
          return;
        }

        ctx.drawImage(img, 0, 0, width, height);
        resolve(canvas.toDataURL('image/jpeg', 0.8));
      };
      img.onerror = () => reject(new Error('Failed to load image'));
      img.src = e.target?.result as string;
    };
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsDataURL(file);
  });
}

/**
 * Compress image if it's larger than threshold
 */
async function compressImage(file: File, maxSizeMB: number): Promise<File> {
  if (file.size <= COMPRESSION_THRESHOLD || !file.type.startsWith('image/')) {
    return file;
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new window.Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        let width = img.width;
        let height = img.height;
        const maxDimension = 1920; // Max width/height

        // Resize if needed
        if (width > maxDimension || height > maxDimension) {
          if (width > height) {
            height = (height * maxDimension) / width;
            width = maxDimension;
          } else {
            width = (width * maxDimension) / height;
            height = maxDimension;
          }
        }

        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          reject(new Error('Could not get canvas context'));
          return;
        }

        ctx.drawImage(img, 0, 0, width, height);
        
        // Try different quality levels
        let quality = 0.9;
        const tryCompress = () => {
          canvas.toBlob(
            (blob) => {
              if (!blob) {
                reject(new Error('Failed to compress image'));
                return;
              }
              
              const sizeMB = blob.size / (1024 * 1024);
              if (sizeMB > maxSizeMB && quality > 0.1) {
                quality -= 0.1;
                tryCompress();
              } else {
                const compressedFile = new File([blob], file.name, {
                  type: 'image/jpeg',
                  lastModified: Date.now(),
                });
                resolve(compressedFile);
              }
            },
            'image/jpeg',
            quality
          );
        };
        tryCompress();
      };
      img.onerror = () => reject(new Error('Failed to load image'));
      img.src = e.target?.result as string;
    };
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsDataURL(file);
  });
}

function SmartDropzone({
  onFilesChange,
  maxFiles = 5,
  maxSizeMB = 10,
  accept = {
    'image/*': ['.jpeg', '.jpg', '.png', '.gif', '.tiff'],
    'application/pdf': ['.pdf']
  },
  disabled = false,
}: SmartDropzoneProps) {
  const [queuedFiles, setQueuedFiles] = useState<QueuedFile[]>([]);
  const [validationError, setValidationError] = useState<string | null>(null);
  const abortControllersRef = useRef<Map<string, AbortController>>(new Map());

  const updateFiles = useCallback((files: QueuedFile[]) => {
    setQueuedFiles(files);
    onFilesChange(files);
  }, [onFilesChange]);

  const removeFile = useCallback((id: string) => {
    // Cancel upload if in progress
    const controller = abortControllersRef.current.get(id);
    if (controller) {
      controller.abort();
      abortControllersRef.current.delete(id);
    }

    setQueuedFiles((prev) => {
      const updated = prev.filter((f) => f.id !== id);
      updateFiles(updated);
      return updated;
    });
  }, [updateFiles]);

  const uploadFile = useCallback(async (queuedFile: QueuedFile) => {
    const controller = new AbortController();
    abortControllersRef.current.set(queuedFile.id, controller);

    setQueuedFiles((prev) =>
      prev.map((f) =>
        f.id === queuedFile.id ? { ...f, status: 'uploading' as const, progress: 0 } : f
      )
    );

    try {
      // Compress if needed
      let fileToUpload = queuedFile.file;
      if (queuedFile.file.size > COMPRESSION_THRESHOLD && queuedFile.file.type.startsWith('image/')) {
        try {
          fileToUpload = await compressImage(queuedFile.file, maxSizeMB);
          toast.info('Image compressed', {
            description: 'Large image was compressed for faster upload.',
            duration: 2000,
          });
        } catch (err) {
          console.warn('Compression failed, using original:', err);
        }
      }

      // Simulate upload progress (replace with actual upload logic)
      const progressInterval = setInterval(() => {
        if (controller.signal.aborted) {
          clearInterval(progressInterval);
          return;
        }

        setQueuedFiles((prev) =>
          prev.map((f) => {
            if (f.id === queuedFile.id && f.status === 'uploading') {
              const newProgress = Math.min(f.progress + Math.random() * 15, 95);
              return { ...f, progress: newProgress };
            }
            return f;
          })
        );
      }, 200);

      // Simulate API call (replace with actual API call)
      await new Promise((resolve, reject) => {
        setTimeout(() => {
          if (controller.signal.aborted) {
            reject(new Error('Upload cancelled'));
          } else {
            resolve(undefined);
          }
        }, 2000);
      });

      clearInterval(progressInterval);

      if (controller.signal.aborted) {
        setQueuedFiles((prev) =>
          prev.map((f) =>
            f.id === queuedFile.id ? { ...f, status: 'cancelled' as const } : f
          )
        );
        return;
      }

      setQueuedFiles((prev) =>
        prev.map((f) =>
          f.id === queuedFile.id
            ? { ...f, status: 'completed' as const, progress: 100 }
            : f
        )
      );

      abortControllersRef.current.delete(queuedFile.id);
    } catch (error) {
      if (controller.signal.aborted) {
        return;
      }

      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      setQueuedFiles((prev) =>
        prev.map((f) =>
          f.id === queuedFile.id
            ? { ...f, status: 'error' as const, error: errorMessage }
            : f
        )
      );
      abortControllersRef.current.delete(queuedFile.id);
    }
  }, [maxSizeMB]);

  const retryFile = useCallback(async (id: string) => {
    const file = queuedFiles.find((f) => f.id === id);
    if (!file) return;

    // Reset status and retry
    setQueuedFiles((prev) =>
      prev.map((f) =>
        f.id === id
          ? { ...f, status: 'queued' as const, progress: 0, error: undefined }
          : f
      )
    );

    // Simulate upload (in real app, this would call the API)
    await uploadFile(file);
  }, [queuedFiles, uploadFile]);

  const onDrop = useCallback(
    async (acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
      setValidationError(null);

      // Handle rejected files
      if (rejectedFiles.length > 0) {
        const rejection = rejectedFiles[0];
        let errorMessage = 'File rejected. ';

        if (rejection.errors) {
          const error = rejection.errors[0];
          if (error.code === 'file-too-large') {
            errorMessage = `File is too large. Maximum size is ${maxSizeMB}MB.`;
          } else if (error.code === 'file-invalid-type') {
            errorMessage = 'File type not supported.';
          } else if (error.code === 'too-many-files') {
            errorMessage = `Too many files. Maximum is ${maxFiles}.`;
          } else {
            errorMessage = error.message || 'Invalid file.';
          }
        }

        setValidationError(errorMessage);
        ErrorHandler.handleError(new Error(errorMessage), {
          showToast: true,
          logToConsole: true,
        });
      }

      // Handle accepted files
      if (acceptedFiles.length > 0) {
        const currentCount = queuedFiles.length;
        const remainingSlots = maxFiles - currentCount;
        const filesToAdd = acceptedFiles.slice(0, remainingSlots);

        if (filesToAdd.length < acceptedFiles.length) {
          toast.warning('Some files were not added', {
            description: `Maximum ${maxFiles} files allowed.`,
            duration: 3000,
          });
        }

        const newFiles: QueuedFile[] = [];

        for (const file of filesToAdd) {
          // Validate file
          const validation = ErrorHandler.validateFile(file, {
            maxSizeMB,
            allowedTypes: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/tiff', 'application/pdf'],
          });

          if (!validation.valid) {
            toast.error('Invalid file', {
              description: `${file.name}: ${validation.error}`,
              duration: 3000,
            });
            continue;
          }

          // Create thumbnail
          let thumbnail: string | undefined;
          try {
            thumbnail = await createThumbnail(file);
          } catch (err) {
            console.warn('Failed to create thumbnail:', err);
          }

          const queuedFile: QueuedFile = {
            id: `${Date.now()}-${Math.random()}`,
            file,
            thumbnail,
            status: 'queued',
            progress: 0,
          };

          newFiles.push(queuedFile);
        }

        const updated = [...queuedFiles, ...newFiles];
        updateFiles(updated);

        // Start uploading new files
        for (const file of newFiles) {
          uploadFile(file);
        }
      }
    },
    [queuedFiles, maxFiles, maxSizeMB, updateFiles, uploadFile]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept,
    maxFiles,
    maxSize: maxSizeMB * 1024 * 1024,
    disabled,
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
        {...dropzoneProps}
        aria-label="Document upload area"
        aria-describedby="upload-instructions"
        whileHover={disabled ? {} : { scale: 1.01 }}
        whileTap={disabled ? {} : { scale: 0.99 }}
        className={cn(
          "relative p-12 text-center cursor-pointer rounded-xl transition-all duration-300 overflow-hidden group",
          "border-2 border-dashed focus-within:ring-2 focus-within:ring-primary focus-within:ring-offset-2",
          disabled && "opacity-50 cursor-not-allowed",
          isDragActive
            ? "border-primary bg-primary/10 shadow-lg shadow-primary/20 border-solid"
            : queuedFiles.length > 0
              ? "border-primary bg-primary/5 shadow-md"
              : "border-muted-foreground/30 hover:border-primary/50 hover:bg-accent/30 hover:shadow-md"
        )}
      >
        <input {...getInputProps()} aria-label="File input" disabled={disabled} />
        <span id="upload-instructions" className="sr-only">
          Drag and drop documents here, or click to browse. Supported formats: PDF, PNG, JPG, JPEG, TIFF. Maximum file size: {maxSizeMB}MB. Maximum files: {maxFiles}.
        </span>

        <div className="relative z-10">
          <motion.div
            animate={
              isDragActive
                ? {
                    scale: 1.15,
                    y: -8,
                    rotate: [0, 5, -5, 0],
                  }
                : {
                    scale: 1,
                    y: 0,
                    rotate: 0,
                  }
            }
            transition={{
              duration: isDragActive ? 0.3 : 0.2,
              rotate: { duration: 0.5, repeat: isDragActive ? Infinity : 0, repeatDelay: 0.5 },
            }}
            className={cn(
              "w-20 h-20 rounded-xl mx-auto mb-6 flex items-center justify-center transition-all relative",
              isDragActive
                ? "bg-primary text-primary-foreground shadow-lg shadow-primary/30 pulse-glow"
                : queuedFiles.length > 0
                  ? "bg-primary text-primary-foreground shadow-md"
                  : "bg-muted text-muted-foreground"
            )}
          >
            {queuedFiles.length > 0 ? (
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
                  Drop your files here
                </h3>
                <p className="text-muted-foreground">Release to upload</p>
              </motion.div>
            ) : queuedFiles.length > 0 ? (
              <motion.div
                key="selected"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <h3 className="text-xl font-semibold text-primary mb-2 flex items-center justify-center gap-2">
                  <Sparkles className="w-5 h-5" />
                  {queuedFiles.length} File{queuedFiles.length > 1 ? 's' : ''} Ready
                </h3>
                <p className="text-muted-foreground">
                  {queuedFiles.filter((f) => f.status === 'completed').length} of {queuedFiles.length} uploaded
                </p>
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <h3 className="text-xl font-semibold mb-2">
                  Drag & drop your documents here
                </h3>
                <p className="text-muted-foreground mb-4">or click to browse files</p>
                <div className="flex justify-center gap-2 flex-wrap">
                  <span className="px-3 py-1 bg-primary/10 text-primary rounded-full text-xs font-medium">PDF</span>
                  <span className="px-3 py-1 bg-primary/10 text-primary rounded-full text-xs font-medium">PNG</span>
                  <span className="px-3 py-1 bg-primary/10 text-primary rounded-full text-xs font-medium">JPG</span>
                  <span className="px-3 py-1 bg-muted text-muted-foreground rounded-full text-xs font-medium">
                    Max {maxSizeMB}MB
                  </span>
                  <span className="px-3 py-1 bg-muted text-muted-foreground rounded-full text-xs font-medium">
                    Up to {maxFiles} files
                  </span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      {/* File Queue */}
      <AnimatePresence>
        {queuedFiles.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-2"
          >
            {queuedFiles.map((queuedFile) => {
              const FileIcon = getFileIcon(queuedFile.file.type);
              return (
                <motion.div
                  key={queuedFile.id}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="flex items-center gap-3 p-3 bg-card rounded-lg border shadow-sm"
                >
                  {/* Thumbnail */}
                  <div className="flex-shrink-0 w-12 h-12 rounded overflow-hidden bg-muted flex items-center justify-center">
                    {queuedFile.thumbnail ? (
                      <img
                        src={queuedFile.thumbnail}
                        alt={queuedFile.file.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <FileIcon className="w-6 h-6 text-muted-foreground" />
                    )}
                  </div>

                  {/* File Info */}
                  <div className="flex-grow min-w-0">
                    <p className="font-medium truncate text-sm">{queuedFile.file.name}</p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{formatFileSize(queuedFile.file.size)}</span>
                      {queuedFile.file.type.includes('pdf') && queuedFile.pages && (
                        <>
                          <span>•</span>
                          <span>{queuedFile.pages} page{queuedFile.pages > 1 ? 's' : ''}</span>
                        </>
                      )}
                    </div>

                    {/* Progress Bar */}
                    {queuedFile.status === 'uploading' && (
                      <div className="mt-2">
                        <Progress value={queuedFile.progress} className="h-1.5" />
                      </div>
                    )}

                    {/* Error Message */}
                    {queuedFile.status === 'error' && queuedFile.error && (
                      <p className="text-xs text-destructive mt-1">{queuedFile.error}</p>
                    )}

                    {/* Status Badge */}
                    <div className="flex items-center gap-1 mt-1">
                      {queuedFile.status === 'completed' && (
                        <span className="text-xs text-success flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" />
                          Uploaded
                        </span>
                      )}
                      {queuedFile.status === 'uploading' && (
                        <span className="text-xs text-primary flex items-center gap-1">
                          <Loader2 className="w-3 h-3 animate-spin" />
                          Uploading...
                        </span>
                      )}
                      {queuedFile.status === 'queued' && (
                        <span className="text-xs text-muted-foreground">Queued</span>
                      )}
                      {queuedFile.status === 'cancelled' && (
                        <span className="text-xs text-muted-foreground">Cancelled</span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {queuedFile.status === 'error' && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => retryFile(queuedFile.id)}
                        aria-label="Retry upload"
                      >
                        <RefreshCw className="w-4 h-4" />
                      </Button>
                    )}
                    {(queuedFile.status === 'uploading' || queuedFile.status === 'queued') && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => {
                          const controller = abortControllersRef.current.get(queuedFile.id);
                          if (controller) {
                            controller.abort();
                          }
                          removeFile(queuedFile.id);
                        }}
                        aria-label="Cancel upload"
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    )}
                    {(queuedFile.status === 'completed' || queuedFile.status === 'error' || queuedFile.status === 'cancelled') && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 hover:bg-destructive/10 hover:text-destructive"
                        onClick={() => removeFile(queuedFile.id)}
                        aria-label="Remove file"
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default SmartDropzone;

