import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

export type ValidationStatusType = 'success' | 'warning' | 'error' | 'info';

interface ValidationStatusProps {
  status: ValidationStatusType;
  message?: string;
  className?: string;
  showIcon?: boolean;
  variant?: 'default' | 'subtle' | 'outlined';
  children?: React.ReactNode;
}

const statusConfig: Record<
  ValidationStatusType,
  {
    icon: React.ElementType;
    iconClassName: string;
    bgClassName: string;
    borderClassName: string;
    textClassName: string;
  }
> = {
  success: {
    icon: CheckCircle2,
    iconClassName: 'text-success',
    bgClassName: 'bg-success/10',
    borderClassName: 'border-success/30',
    textClassName: 'text-success-foreground',
  },
  warning: {
    icon: AlertTriangle,
    iconClassName: 'text-warning',
    bgClassName: 'bg-warning/10',
    borderClassName: 'border-warning/30',
    textClassName: 'text-warning-foreground',
  },
  error: {
    icon: XCircle,
    iconClassName: 'text-destructive',
    bgClassName: 'bg-destructive/10',
    borderClassName: 'border-destructive/30',
    textClassName: 'text-destructive-foreground',
  },
  info: {
    icon: Info,
    iconClassName: 'text-primary',
    bgClassName: 'bg-primary/10',
    borderClassName: 'border-primary/30',
    textClassName: 'text-primary-foreground',
  },
};

/**
 * ValidationStatus component applies semantic color tokens to indicate validation state
 * 
 * @example
 * <ValidationStatus status="success" message="Field validated successfully">
 *   <input value="123.45" />
 * </ValidationStatus>
 * 
 * @example
 * <ValidationStatus status="error" message="Arithmetic mismatch: Subtotal + Tax != Total">
 *   <div className="financial-value">$1,234.56</div>
 * </ValidationStatus>
 */
export function ValidationStatus({
  status,
  message,
  className,
  showIcon = true,
  variant = 'default',
  children,
}: ValidationStatusProps) {
  const config = statusConfig[status];
  const Icon = config.icon;

  const baseClassName = cn(
    'relative transition-all duration-200',
    variant === 'subtle' && config.bgClassName,
    variant === 'outlined' && `border ${config.borderClassName}`,
    variant === 'outlined' && 'rounded-md p-2',
    className
  );

  const content = (
    <div className={baseClassName}>
      {showIcon && (
        <div className="absolute -top-1 -right-1 z-10">
          <Icon
            className={cn('w-4 h-4', config.iconClassName)}
            aria-hidden="true"
          />
        </div>
      )}
      {children}
      {variant === 'outlined' && message && (
        <p className={cn('text-xs mt-1', config.textClassName)}>{message}</p>
      )}
    </div>
  );

  if (message && variant !== 'outlined') {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            {content}
          </TooltipTrigger>
          <TooltipContent side="top" className="max-w-xs">
            <div className="flex items-start gap-2">
              <Icon className={cn('w-4 h-4 mt-0.5 flex-shrink-0', config.iconClassName)} />
              <p className="text-sm">{message}</p>
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return content;
}

/**
 * ValidationStatusBadge - A badge variant of ValidationStatus for inline use
 */
interface ValidationStatusBadgeProps {
  status: ValidationStatusType;
  message?: string;
  className?: string;
}

export function ValidationStatusBadge({
  status,
  message,
  className,
}: ValidationStatusBadgeProps) {
  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium',
        config.bgClassName,
        config.borderClassName && `border ${config.borderClassName}`,
        config.textClassName,
        className
      )}
      role="status"
      aria-live="polite"
    >
      <Icon className={cn('w-3 h-3', config.iconClassName)} aria-hidden="true" />
      {message && <span>{message}</span>}
    </div>
  );
}

