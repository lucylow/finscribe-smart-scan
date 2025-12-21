import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Save, 
  Send, 
  CheckCircle2, 
  AlertCircle, 
  Loader2,
  Building2,
  FileText,
  DollarSign,
  TableIcon,
  Calendar,
  Hash
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { submitCorrections } from '@/services/api';

export interface FieldValue {
  value: string | number | null;
  originalValue?: string | number | null;
  isValid: boolean;
  error?: string;
  isDirty: boolean;
  isSaving?: boolean;
}

export interface CorrectionsData {
  vendor?: {
    name?: FieldValue;
    address?: FieldValue;
    taxId?: FieldValue;
    contact?: FieldValue;
  };
  invoice_info?: {
    invoiceNumber?: FieldValue;
    date?: FieldValue;
    poNumber?: FieldValue;
    dueDate?: FieldValue;
  };
  line_items?: Array<{
    description?: FieldValue;
    quantity?: FieldValue;
    unitPrice?: FieldValue;
    lineTotal?: FieldValue;
  }>;
  totals?: {
    subtotal?: FieldValue;
    tax?: FieldValue;
    discount?: FieldValue;
    total?: FieldValue;
  };
}

interface CorrectionsPanelProps {
  data: CorrectionsData;
  resultId?: string;
  onDataChange?: (data: CorrectionsData) => void;
  highlightedFieldId?: string | null;
  onFieldHighlight?: (fieldId: string | null) => void;
  className?: string;
}

// Validation functions
const validators = {
  number: (value: string): { valid: boolean; error?: string } => {
    if (!value.trim()) return { valid: true }; // Empty is allowed
    const num = parseFloat(value.replace(/,/g, ''));
    if (isNaN(num)) {
      return { valid: false, error: 'Must be a valid number' };
    }
    return { valid: true };
  },
  currency: (value: string): { valid: boolean; error?: string } => {
    if (!value.trim()) return { valid: true };
    const cleaned = value.replace(/[$,]/g, '');
    const num = parseFloat(cleaned);
    if (isNaN(num) || num < 0) {
      return { valid: false, error: 'Must be a valid positive currency amount' };
    }
    return { valid: true };
  },
  date: (value: string): { valid: boolean; error?: string } => {
    if (!value.trim()) return { valid: true };
    const date = new Date(value);
    if (isNaN(date.getTime())) {
      return { valid: false, error: 'Must be a valid date (YYYY-MM-DD)' };
    }
    return { valid: true };
  },
  text: (): { valid: boolean; error?: string } => {
    return { valid: true };
  },
};

// Format currency for display
const formatCurrency = (value: string | number | null): string => {
  if (value === null || value === undefined || value === '') return '';
  const num = typeof value === 'string' ? parseFloat(value.replace(/[$,]/g, '')) : value;
  if (isNaN(num)) return String(value);
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(num);
};

// Parse currency from input
const parseCurrency = (value: string): number | null => {
  const cleaned = value.replace(/[$,]/g, '');
  const num = parseFloat(cleaned);
  return isNaN(num) ? null : num;
};

function CorrectionsPanel({
  data,
  resultId,
  onDataChange,
  highlightedFieldId,
  onFieldHighlight,
  className,
}: CorrectionsPanelProps) {
  const [localData, setLocalData] = useState<CorrectionsData>(data);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [queuedCount, setQueuedCount] = useState(0);
  const saveTimeoutsRef = useRef<Map<string, NodeJS.Timeout>>(new Map());
  const fieldRefsRef = useRef<Map<string, HTMLInputElement | HTMLTextAreaElement>>(new Map());

  // Sync with external data changes
  useEffect(() => {
    setLocalData(data);
  }, [data]);

  // Scroll to highlighted field
  useEffect(() => {
    if (highlightedFieldId) {
      const fieldRef = fieldRefsRef.current.get(highlightedFieldId);
      if (fieldRef) {
        fieldRef.scrollIntoView({ behavior: 'smooth', block: 'center' });
        fieldRef.focus();
        // Remove highlight after a moment
        setTimeout(() => {
          if (onFieldHighlight) {
            onFieldHighlight(null);
          }
        }, 2000);
      }
    }
  }, [highlightedFieldId, onFieldHighlight]);

  // Update field value with validation
  const updateField = useCallback(
    (path: string[], value: string, validator: (v: string) => { valid: boolean; error?: string }) => {
      const validation = validator(value);
      
      setLocalData((prev) => {
        const newData = { ...prev };
        let current: any = newData;
        
        // Navigate to the field
        for (let i = 0; i < path.length - 1; i++) {
          if (!current[path[i]]) {
            current[path[i]] = {};
          }
          current = current[path[i]];
        }
        
        const fieldName = path[path.length - 1];
        const originalValue = current[fieldName]?.originalValue ?? current[fieldName]?.value;
        
        // Parse value based on type
        let parsedValue: string | number | null = value;
        if (validator === validators.currency) {
          parsedValue = parseCurrency(value);
        } else if (validator === validators.number) {
          parsedValue = value.trim() === '' ? null : parseFloat(value.replace(/,/g, ''));
        }
        
        current[fieldName] = {
          value: parsedValue,
          originalValue,
          isValid: validation.valid,
          error: validation.error,
          isDirty: String(parsedValue) !== String(originalValue),
          isSaving: false,
        };
        
        return newData;
      });

      // Debounced save
      const fieldId = path.join('.');
      const existingTimeout = saveTimeoutsRef.current.get(fieldId);
      if (existingTimeout) {
        clearTimeout(existingTimeout);
      }

      const timeout = setTimeout(() => {
        // Optimistic save
        setLocalData((prev) => {
          const newData = { ...prev };
          let current: any = newData;
          for (let i = 0; i < path.length - 1; i++) {
            current = current[path[i]];
          }
          const fieldName = path[path.length - 1];
          if (current[fieldName]) {
            current[fieldName].isSaving = true;
          }
          return newData;
        });

        // Simulate API call (replace with actual API call)
        setTimeout(() => {
          setLocalData((prev) => {
            const newData = { ...prev };
            let current: any = newData;
            for (let i = 0; i < path.length - 1; i++) {
              current = current[path[i]];
            }
            const fieldName = path[path.length - 1];
            if (current[fieldName]) {
              current[fieldName].isSaving = false;
            }
            return newData;
          });

          toast.success('Saved', {
            description: 'Changes saved successfully',
            duration: 2000,
          });
        }, 500);

        saveTimeoutsRef.current.delete(fieldId);
      }, 500);

      saveTimeoutsRef.current.set(fieldId, timeout);

      // Notify parent
      if (onDataChange) {
        setTimeout(() => {
          setLocalData((current) => {
            onDataChange(current);
            return current;
          });
        }, 0);
      }
    },
    [onDataChange]
  );

  // Get all changed fields
  const getChangedFields = useCallback((): string[] => {
    const changed: string[] = [];
    
    const traverse = (obj: any, prefix: string = '') => {
      for (const key in obj) {
        const field = obj[key];
        if (field && typeof field === 'object' && 'isDirty' in field) {
          if (field.isDirty) {
            changed.push(prefix ? `${prefix}.${key}` : key);
          }
        } else if (field && typeof field === 'object') {
          traverse(field, prefix ? `${prefix}.${key}` : key);
        }
      }
    };
    
    traverse(localData);
    return changed;
  }, [localData]);

  // Check if all required fields are valid
  const isValid = useCallback((): boolean => {
    const traverse = (obj: any): boolean => {
      for (const key in obj) {
        const field = obj[key];
        if (field && typeof field === 'object' && 'isValid' in field) {
          if (!field.isValid) {
            return false;
          }
        } else if (field && typeof field === 'object') {
          if (!traverse(field)) {
            return false;
          }
        }
      }
      return true;
    };
    
    return traverse(localData);
  }, [localData]);

  // Export to active learning
  const handleExport = useCallback(async () => {
    if (!resultId) {
      toast.error('No result ID available', {
        description: 'Cannot export corrections without a result ID.',
      });
      return;
    }

    setIsExporting(true);
    try {
      // Prepare corrections payload
      const corrections: Record<string, unknown> = {};
      
      const extractValues = (obj: any, prefix: string = '') => {
        for (const key in obj) {
          const field = obj[key];
          if (field && typeof field === 'object' && 'value' in field) {
            corrections[prefix ? `${prefix}.${key}` : key] = field.value;
          } else if (field && typeof field === 'object') {
            extractValues(field, prefix ? `${prefix}.${key}` : key);
          }
        }
      };
      
      extractValues(localData);

      await submitCorrections(resultId, corrections);
      
      setQueuedCount((prev) => prev + 1);
      setShowExportDialog(false);
      
      toast.success('Exported to training queue', {
        description: 'Your corrections have been added to the active learning queue.',
        duration: 3000,
      });
    } catch (error) {
      toast.error('Export failed', {
        description: error instanceof Error ? error.message : 'Failed to export corrections.',
        duration: 4000,
      });
    } finally {
      setIsExporting(false);
    }
  }, [resultId, localData]);

  // Render field input
  const renderField = (
    label: string,
    path: string[],
    field: FieldValue | undefined,
    type: 'text' | 'number' | 'currency' | 'date' = 'text',
    icon?: React.ElementType,
    placeholder?: string
  ) => {
    const fieldId = path.join('.');
    const Icon = icon;
    const value = field?.value ?? '';
    const displayValue = type === 'currency' && value ? formatCurrency(value as number) : String(value);
    
    return (
      <div className="space-y-1.5">
        <label htmlFor={fieldId} className="text-sm font-medium flex items-center gap-2">
          {Icon && <Icon className="w-4 h-4 text-muted-foreground" />}
          {label}
        </label>
        <div className="relative">
          <Input
            id={fieldId}
            ref={(el) => {
              if (el) {
                fieldRefsRef.current.set(fieldId, el);
              } else {
                fieldRefsRef.current.delete(fieldId);
              }
            }}
            type={type === 'date' ? 'date' : type === 'number' ? 'number' : 'text'}
            value={displayValue}
            onChange={(e) => {
              const validator =
                type === 'currency'
                  ? validators.currency
                  : type === 'number'
                    ? validators.number
                    : type === 'date'
                      ? validators.date
                      : validators.text;
              updateField(path, e.target.value, validator);
            }}
            onBlur={() => {
              // Trigger save on blur
              const timeout = saveTimeoutsRef.current.get(fieldId);
              if (timeout) {
                clearTimeout(timeout);
                saveTimeoutsRef.current.delete(fieldId);
                // Trigger save immediately
                const field = field;
                if (field?.isDirty) {
                  // Save logic here
                }
              }
            }}
            placeholder={placeholder}
            className={cn(
              field?.isDirty && 'border-primary',
              !field?.isValid && 'border-destructive',
              field?.isSaving && 'opacity-70'
            )}
            aria-label={label}
            aria-invalid={!field?.isValid}
            aria-describedby={field?.error ? `${fieldId}-error` : undefined}
          />
          {field?.isSaving && (
            <div className="absolute right-2 top-1/2 -translate-y-1/2">
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            </div>
          )}
          {field?.isDirty && !field?.isSaving && (
            <div className="absolute right-2 top-1/2 -translate-y-1/2">
              <CheckCircle2 className="w-4 h-4 text-success" />
            </div>
          )}
        </div>
        {field?.error && (
          <p id={`${fieldId}-error`} className="text-xs text-destructive flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            {field.error}
          </p>
        )}
      </div>
    );
  };

  const changedFields = getChangedFields();
  const canExport = isValid() && changedFields.length > 0;

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Corrections</h3>
        <div className="flex items-center gap-2">
          {queuedCount > 0 && (
            <Badge variant="secondary">
              {queuedCount} queued
            </Badge>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowExportDialog(true)}
            disabled={!canExport || !resultId}
            aria-label="Export corrections to training queue"
          >
            <Send className="w-4 h-4 mr-2" />
            Export to Training
          </Button>
        </div>
      </div>

      {/* Vendor Information */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Building2 className="w-4 h-4" />
            Vendor Information
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {renderField('Vendor Name', ['vendor', 'name'], localData.vendor?.name, 'text', Building2, 'Company name')}
          {renderField('Address', ['vendor', 'address'], localData.vendor?.address, 'text', undefined, 'Street address')}
          {renderField('Tax ID', ['vendor', 'taxId'], localData.vendor?.taxId, 'text', Hash, 'Tax identification number')}
          {renderField('Contact', ['vendor', 'contact'], localData.vendor?.contact, 'text', undefined, 'Contact information')}
        </CardContent>
      </Card>

      {/* Invoice Information */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Invoice Information
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {renderField('Invoice Number', ['invoice_info', 'invoiceNumber'], localData.invoice_info?.invoiceNumber, 'text', Hash, 'Invoice #')}
          {renderField('Date', ['invoice_info', 'date'], localData.invoice_info?.date, 'date', Calendar, 'YYYY-MM-DD')}
          {renderField('PO Number', ['invoice_info', 'poNumber'], localData.invoice_info?.poNumber, 'text', Hash, 'Purchase order number')}
          {renderField('Due Date', ['invoice_info', 'dueDate'], localData.invoice_info?.dueDate, 'date', Calendar, 'YYYY-MM-DD')}
        </CardContent>
      </Card>

      {/* Line Items */}
      {localData.line_items && localData.line_items.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <TableIcon className="w-4 h-4" />
              Line Items
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Description</TableHead>
                    <TableHead className="text-right">Qty</TableHead>
                    <TableHead className="text-right">Unit Price</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {localData.line_items.map((item, index) => (
                    <TableRow key={index}>
                      <TableCell>
                        <Textarea
                          value={String(item.description?.value ?? '')}
                          onChange={(e) => updateField(['line_items', String(index), 'description'], e.target.value, validators.text)}
                          placeholder="Item description"
                          className="min-h-[60px]"
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          value={String(item.quantity?.value ?? '')}
                          onChange={(e) => updateField(['line_items', String(index), 'quantity'], e.target.value, validators.number)}
                          placeholder="0"
                          className="text-right"
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          type="text"
                          value={item.unitPrice?.value ? formatCurrency(item.unitPrice.value as number) : ''}
                          onChange={(e) => updateField(['line_items', String(index), 'unitPrice'], e.target.value, validators.currency)}
                          placeholder="$0.00"
                          className="text-right"
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          type="text"
                          value={item.lineTotal?.value ? formatCurrency(item.lineTotal.value as number) : ''}
                          onChange={(e) => updateField(['line_items', String(index), 'lineTotal'], e.target.value, validators.currency)}
                          placeholder="$0.00"
                          className="text-right font-semibold"
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Totals */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <DollarSign className="w-4 h-4" />
            Totals
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {renderField('Subtotal', ['totals', 'subtotal'], localData.totals?.subtotal, 'currency', DollarSign)}
          {renderField('Tax', ['totals', 'tax'], localData.totals?.tax, 'currency', DollarSign)}
          {renderField('Discount', ['totals', 'discount'], localData.totals?.discount, 'currency', DollarSign)}
          {renderField('Total', ['totals', 'total'], localData.totals?.total, 'currency', DollarSign)}
        </CardContent>
      </Card>

      {/* Export Confirmation Dialog */}
      <Dialog open={showExportDialog} onOpenChange={setShowExportDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Export Corrections to Training Queue</DialogTitle>
            <DialogDescription>
              The following fields have been corrected and will be sent to the active learning queue:
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[300px] overflow-y-auto">
            <ul className="space-y-2">
              {changedFields.map((field) => (
                <li key={field} className="flex items-center gap-2 text-sm">
                  <CheckCircle2 className="w-4 h-4 text-success" />
                  <span className="font-mono text-xs">{field}</span>
                </li>
              ))}
            </ul>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowExportDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleExport} disabled={isExporting}>
              {isExporting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Exporting...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Export
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default CorrectionsPanel;

