import React from 'react';
import { motion } from 'framer-motion';
import { Progress } from '@/components/ui/progress';
import { Check, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ProcessingStatusProps {
  progress: number;
  processing: boolean;
}

function ProcessingStatus({ progress, processing }: ProcessingStatusProps) {
  if (!processing && progress === 0) return null;

  const steps = [
    { label: 'Uploading document', progress: 30, icon: '📄' },
    { label: 'Analyzing layout with PaddleOCR-VL', progress: 60, icon: '🔍' },
    { label: 'Semantic enrichment with ERNIE 4.5', progress: 85, icon: '🧠' },
    { label: 'Validating financial rules', progress: 100, icon: '✓' },
  ];

  const currentStep = steps.findIndex(step => progress <= step.progress);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full p-6 bg-card rounded-xl border shadow-sm"
    >
      <div className="flex justify-between mb-3">
        <span className="text-sm font-medium text-foreground">
          {processing ? 'Processing your document...' : 'Upload complete'}
        </span>
        <span className="text-sm font-mono text-primary font-semibold">
          {Math.round(progress)}%
        </span>
      </div>
      
      <div className="relative h-3 mb-6 bg-muted rounded-full overflow-hidden">
        <motion.div 
          className="absolute inset-y-0 left-0 bg-gradient-to-r from-primary to-secondary rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3, ease: "easeOut" }}
        />
        <motion.div 
          className="absolute inset-y-0 left-0 bg-gradient-to-r from-primary-glow/50 to-secondary-glow/50 rounded-full animate-shimmer"
          style={{ 
            width: `${progress}%`,
            backgroundSize: '200% 100%'
          }}
        />
      </div>

      {processing && (
        <div className="space-y-3">
          {steps.slice(0, currentStep + 1).map((step, index) => {
            const isComplete = index < currentStep;
            const isCurrent = index === currentStep;
            
            return (
              <motion.div
                key={step.label}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="flex items-center gap-3"
              >
                <div
                  className={cn(
                    "w-8 h-8 rounded-lg flex items-center justify-center text-sm font-medium transition-all",
                    isComplete 
                      ? "bg-secondary text-secondary-foreground" 
                      : isCurrent 
                        ? "bg-primary text-primary-foreground animate-pulse-glow" 
                        : "bg-muted text-muted-foreground"
                  )}
                >
                  {isComplete ? (
                    <Check className="w-4 h-4" />
                  ) : isCurrent ? (
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                    >
                      <Loader2 className="w-4 h-4" />
                    </motion.div>
                  ) : (
                    <span>{step.icon}</span>
                  )}
                </div>
                <span 
                  className={cn(
                    "text-sm transition-colors",
                    isComplete 
                      ? "text-muted-foreground line-through" 
                      : isCurrent 
                        ? "text-foreground font-medium" 
                        : "text-muted-foreground"
                  )}
                >
                  {step.label}
                </span>
              </motion.div>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}

export default ProcessingStatus;