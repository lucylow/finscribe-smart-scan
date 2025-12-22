/**
 * OCR Service using Supabase Edge Functions
 * 
 * Provides OCR and AI extraction capabilities using Lovable AI (Gemini Vision)
 */

import { supabase } from '@/integrations/supabase/client';

const SUPABASE_URL = 'https://dvypmevjyxdeyhaofued.supabase.co';

export interface ExtractedInvoice {
  vendor_name: string;
  invoice_number: string;
  invoice_date: string;
  due_date: string | null;
  total_amount: number;
  currency: string;
  line_items: Array<{
    description: string;
    quantity: number;
    unit_price: number;
    total: number;
  }>;
  tax_amount: number;
  subtotal: number;
  raw_text: string;
  confidence: number;
}

export interface OCRResult {
  success: boolean;
  extractionType: string;
  data: ExtractedInvoice | Record<string, unknown>;
  model: string;
  timestamp: string;
  error?: string;
}

export interface EnhanceResult {
  success: boolean;
  action: string;
  result: Record<string, unknown>;
  timestamp: string;
  error?: string;
}

/**
 * Convert file to base64
 */
async function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      // Remove data URL prefix to get pure base64
      const base64 = result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/**
 * Extract text and structured data from an invoice image using AI OCR
 */
export async function extractFromImage(
  file: File,
  extractionType: 'invoice' | 'receipt' | 'general' = 'invoice'
): Promise<OCRResult> {
  try {
    const imageBase64 = await fileToBase64(file);
    
    const response = await fetch(`${SUPABASE_URL}/functions/v1/ocr-extract`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        imageBase64,
        extractionType,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(errorData.error || `OCR failed: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('OCR extraction error:', error);
    throw error;
  }
}

/**
 * Extract from image URL (for already-uploaded images)
 */
export async function extractFromUrl(
  imageUrl: string,
  extractionType: 'invoice' | 'receipt' | 'general' = 'invoice'
): Promise<OCRResult> {
  try {
    const response = await fetch(`${SUPABASE_URL}/functions/v1/ocr-extract`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        imageUrl,
        extractionType,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(errorData.error || `OCR failed: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('OCR extraction error:', error);
    throw error;
  }
}

/**
 * Enhance/validate extracted data using AI
 */
export async function enhanceExtractedData(
  extractedData: Record<string, unknown>,
  action: 'validate' | 'enhance' | 'categorize' | 'summarize' = 'validate',
  rawText?: string
): Promise<EnhanceResult> {
  try {
    const response = await fetch(`${SUPABASE_URL}/functions/v1/ai-enhance`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        extractedData,
        rawText,
        action,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(errorData.error || `Enhancement failed: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('AI enhancement error:', error);
    throw error;
  }
}

/**
 * Full pipeline: Extract + Validate + Enhance
 */
export async function processDocument(
  file: File,
  options: {
    extractionType?: 'invoice' | 'receipt' | 'general';
    validate?: boolean;
    enhance?: boolean;
    categorize?: boolean;
  } = {}
): Promise<{
  extraction: OCRResult;
  validation?: EnhanceResult;
  enhancement?: EnhanceResult;
  categorization?: EnhanceResult;
}> {
  const { 
    extractionType = 'invoice', 
    validate = true, 
    enhance = false,
    categorize = false 
  } = options;

  // Step 1: Extract data from image
  const extraction = await extractFromImage(file, extractionType);
  
  if (!extraction.success) {
    throw new Error(extraction.error || 'Extraction failed');
  }

  const result: {
    extraction: OCRResult;
    validation?: EnhanceResult;
    enhancement?: EnhanceResult;
    categorization?: EnhanceResult;
  } = { extraction };

  const extractedData = extraction.data as Record<string, unknown>;
  const rawText = (extractedData.raw_text as string) || '';

  // Step 2: Validate (optional but default on)
  if (validate) {
    try {
      result.validation = await enhanceExtractedData(extractedData, 'validate', rawText);
    } catch (e) {
      console.warn('Validation failed, continuing:', e);
    }
  }

  // Step 3: Enhance (optional)
  if (enhance) {
    try {
      result.enhancement = await enhanceExtractedData(extractedData, 'enhance', rawText);
    } catch (e) {
      console.warn('Enhancement failed, continuing:', e);
    }
  }

  // Step 4: Categorize (optional)
  if (categorize) {
    try {
      result.categorization = await enhanceExtractedData(extractedData, 'categorize', rawText);
    } catch (e) {
      console.warn('Categorization failed, continuing:', e);
    }
  }

  return result;
}

/**
 * Get a summary of an invoice for quick review
 */
export async function summarizeDocument(
  extractedData: Record<string, unknown>
): Promise<EnhanceResult> {
  return enhanceExtractedData(extractedData, 'summarize');
}
