/**
 * OCR Extract Edge Function
 * 
 * Priority order:
 * 1. PaddleOCR + ERNIE (free/open-source, preferred)
 * 2. Lovable AI (Gemini) - fallback only (costs money)
 * 
 * Uses PaddleOCR for OCR extraction and ERNIE for semantic enrichment.
 * Falls back to Lovable AI only if PaddleOCR/ERNIE services are unavailable.
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

interface OCRRequest {
  imageBase64?: string;
  imageUrl?: string;
  extractionType?: 'invoice' | 'receipt' | 'general';
}

interface ExtractedInvoice {
  vendor_name: string;
  invoice_number: string;
  invoice_date: string;
  due_date: string;
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

const INVOICE_EXTRACTION_PROMPT = `You are an expert OCR and document extraction AI. Analyze this invoice/document image and extract all relevant information.

Return a JSON object with the following structure:
{
  "vendor_name": "Company name on the invoice",
  "invoice_number": "Invoice/receipt number",
  "invoice_date": "Date in YYYY-MM-DD format",
  "due_date": "Due date in YYYY-MM-DD format or null",
  "total_amount": 0.00,
  "currency": "USD",
  "line_items": [
    {
      "description": "Item description",
      "quantity": 1,
      "unit_price": 0.00,
      "total": 0.00
    }
  ],
  "tax_amount": 0.00,
  "subtotal": 0.00,
  "raw_text": "All text extracted from the document",
  "confidence": 0.95
}

Be precise with numbers and dates. If a field is not visible or unclear, use null or an empty string.
Extract ALL line items visible on the invoice.
Return ONLY valid JSON, no markdown or explanation.`;

const RECEIPT_EXTRACTION_PROMPT = `You are an expert OCR AI. Analyze this receipt image and extract all information.

Return a JSON object:
{
  "merchant_name": "Store/restaurant name",
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "items": [{"name": "Item", "price": 0.00, "quantity": 1}],
  "subtotal": 0.00,
  "tax": 0.00,
  "total": 0.00,
  "payment_method": "cash/card/etc",
  "raw_text": "All text from receipt",
  "confidence": 0.95
}

Return ONLY valid JSON.`;

const GENERAL_OCR_PROMPT = `Extract all text from this image. Return a JSON object:
{
  "text": "All extracted text, preserving layout where possible",
  "sections": ["Array of distinct text sections"],
  "confidence": 0.95
}

Return ONLY valid JSON.`;

/**
 * Normalize PaddleOCR results to expected format
 */
function normalizePaddleOCRResult(ocrResult: any, extractionType: string): any {
  // If already in expected format, return as-is
  if (ocrResult.vendor_name || ocrResult.merchant_name || ocrResult.text) {
    return ocrResult;
  }

  // Extract text from various PaddleOCR response formats
  let rawText = '';
  if (ocrResult.text) {
    rawText = ocrResult.text;
  } else if (ocrResult.data?.text) {
    rawText = ocrResult.data.text;
  } else if (Array.isArray(ocrResult.data)) {
    // PaddleOCR often returns array of [bbox, (text, confidence)]
    rawText = ocrResult.data
      .map((item: any) => {
        if (Array.isArray(item) && item.length >= 2 && Array.isArray(item[1])) {
          return item[1][0]; // Extract text from [bbox, [text, confidence]]
        }
        return '';
      })
      .filter((t: string) => t)
      .join('\n');
  }

  // If we have raw text, try to parse it
  if (rawText && extractionType === 'invoice') {
    return parseInvoiceFromText(rawText, 0.85);
  } else if (rawText && extractionType === 'receipt') {
    return parseReceiptFromText(rawText, 0.85);
  } else if (rawText) {
    return {
      text: rawText,
      sections: rawText.split('\n').filter(line => line.trim()),
      confidence: 0.85,
    };
  }

  // Return as-is if we can't normalize
  return ocrResult;
}

/**
 * Call PaddleOCR service for text extraction
 */
async function callPaddleOCR(imageBase64: string, imageUrl: string | undefined, extractionType: string): Promise<any> {
  const PADDLEOCR_URL = Deno.env.get('PADDLEOCR_VLLM_URL');
  
  if (!PADDLEOCR_URL) {
    throw new Error('PADDLEOCR_VLLM_URL not configured');
  }

  console.log(`Calling PaddleOCR service at ${PADDLEOCR_URL}`);
  
  try {
    let imageBytes: Uint8Array;
    
    if (imageBase64) {
      // Convert base64 to bytes
      imageBytes = Uint8Array.from(atob(imageBase64), c => c.charCodeAt(0));
    } else if (imageUrl) {
      // Fetch image from URL
      const imageResponse = await fetch(imageUrl);
      const arrayBuffer = await imageResponse.arrayBuffer();
      imageBytes = new Uint8Array(arrayBuffer);
    } else {
      throw new Error('No image provided for PaddleOCR');
    }

    // Try /v1/ocr endpoint first (common pattern)
    const ocrEndpoint = PADDLEOCR_URL.endsWith('/ocr') 
      ? PADDLEOCR_URL 
      : `${PADDLEOCR_URL.replace(/\/$/, '')}/ocr`;

    // Create FormData for multipart upload
    const formData = new FormData();
    const blob = new Blob([imageBytes], { type: 'image/jpeg' });
    formData.append('file', blob, 'document.jpg');

    const response = await fetch(ocrEndpoint, {
      method: 'POST',
      body: formData,
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`PaddleOCR service returned ${response.status}: ${errorText}`);
    }

    const result = await response.json();
    console.log('PaddleOCR extraction successful');
    
    // Normalize the result to expected format
    return normalizePaddleOCRResult(result, extractionType);
  } catch (error) {
    console.error("PaddleOCR error:", error);
    throw error;
  }
}

/**
 * Call ERNIE VLM service for semantic enrichment
 */
async function callERNIE(ocrResults: any, imageBase64: string, imageUrl: string | undefined, extractionType: string): Promise<any> {
  const ERNIE_URL = Deno.env.get('ERNIE_VLLM_URL');
  
  if (!ERNIE_URL) {
    console.log('ERNIE_VLLM_URL not configured, skipping ERNIE enrichment');
    return null;
  }

  console.log(`Calling ERNIE service at ${ERNIE_URL} for enrichment`);
  
  try {
    // Select prompt based on extraction type
    let systemPrompt = INVOICE_EXTRACTION_PROMPT;
    if (extractionType === 'receipt') {
      systemPrompt = RECEIPT_EXTRACTION_PROMPT;
    } else if (extractionType === 'general') {
      systemPrompt = GENERAL_OCR_PROMPT;
    }

    // Build image content
    const imageContent = imageBase64 
      ? { type: "image_url", image_url: { url: `data:image/jpeg;base64,${imageBase64}` } }
      : { type: "image_url", image_url: { url: imageUrl } };

    // Prepare ERNIE request (vLLM format)
    const chatEndpoint = ERNIE_URL.endsWith('/chat/completions')
      ? ERNIE_URL
      : `${ERNIE_URL.replace(/\/$/, '')}/chat/completions`;

    const erniePayload = {
      model: "baidu/ERNIE-5", // Default ERNIE model
      messages: [
        { role: "system", content: systemPrompt },
        {
          role: "user",
          content: [
            { type: "text", text: `OCR Results:\n${JSON.stringify(ocrResults, null, 2)}\n\nExtract and validate all information from this document image.` },
            imageContent
          ]
        }
      ],
      max_tokens: 4096,
    };

    const response = await fetch(chatEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(erniePayload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.warn(`ERNIE service returned ${response.status}: ${errorText}`);
      return null; // Non-fatal, return null to continue
    }

    const ernieResult = await response.json();
    const content = ernieResult.choices?.[0]?.message?.content;

    if (!content) {
      console.warn('ERNIE returned no content');
      return null;
    }

    console.log('ERNIE enrichment successful');

    // Parse JSON response
    try {
      let cleanContent = content.trim();
      if (cleanContent.startsWith('```json')) {
        cleanContent = cleanContent.slice(7);
      }
      if (cleanContent.startsWith('```')) {
        cleanContent = cleanContent.slice(3);
      }
      if (cleanContent.endsWith('```')) {
        cleanContent = cleanContent.slice(0, -3);
      }
      
      return JSON.parse(cleanContent.trim());
    } catch (parseError) {
      console.warn("Failed to parse ERNIE response as JSON, using raw text");
      return {
        raw_text: content,
        confidence: 0.8,
        parse_error: true
      };
    }
  } catch (error) {
    console.error("ERNIE enrichment error:", error);
    return null; // Non-fatal, return null to continue
  }
}

/**
 * Fallback OCR using OCR.space free API
 * Used when primary services are unavailable
 */
async function fallbackOCR(imageBase64: string, imageUrl: string | undefined, extractionType: string): Promise<any> {
  console.log("Using fallback OCR service (OCR.space)");
  
  try {
    let imageBlob: Blob;
    
    if (imageBase64) {
      // Convert base64 to blob
      const imageBytes = Uint8Array.from(atob(imageBase64), c => c.charCodeAt(0));
      imageBlob = new Blob([imageBytes], { type: 'image/jpeg' });
    } else if (imageUrl) {
      // Fetch image from URL
      const imageResponse = await fetch(imageUrl);
      imageBlob = await imageResponse.blob();
    } else {
      throw new Error('No image provided for fallback OCR');
    }

    // Use OCR.space free API
    const formData = new FormData();
    formData.append('image', imageBlob, 'document.jpg');
    formData.append('apikey', 'helloworld'); // Free public key
    formData.append('language', 'eng');
    formData.append('isOverlayRequired', 'false');
    formData.append('OCREngine', '2');

    const ocrResponse = await fetch('https://api.ocr.space/parse/image', {
      method: 'POST',
      body: formData,
    });

    if (!ocrResponse.ok) {
      throw new Error(`OCR.space API returned ${ocrResponse.status}`);
    }

    const ocrData = await ocrResponse.json();
    const rawText = ocrData.ParsedResults?.[0]?.ParsedText || '';
    const confidence = ocrData.ParsedResults?.[0]?.TextOverlay?.MeanConfidence || 0.7;

    // Basic parsing for invoice structure
    if (extractionType === 'invoice') {
      return parseInvoiceFromText(rawText, confidence);
    } else if (extractionType === 'receipt') {
      return parseReceiptFromText(rawText, confidence);
    } else {
      return {
        text: rawText,
        sections: rawText.split('\n').filter(line => line.trim()),
        confidence: confidence / 100,
      };
    }
  } catch (error) {
    console.error("Fallback OCR error:", error);
    throw error;
  }
}

/**
 * Basic invoice parsing from OCR text
 */
function parseInvoiceFromText(text: string, confidence: number): ExtractedInvoice {
  const lines = text.split('\n').map(l => l.trim()).filter(l => l);
  
  // Extract invoice number
  const invoiceNumberMatch = text.match(/(?:invoice|inv)[\s#:]*([A-Z0-9\-]+)/i);
  const invoiceNumber = invoiceNumberMatch ? invoiceNumberMatch[1] : '';
  
  // Extract dates
  const datePattern = /\b(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4}|\d{1,2}\/\d{1,2}\/\d{4})\b/g;
  const dates = text.match(datePattern) || [];
  const invoiceDate = dates[0] || new Date().toISOString().split('T')[0];
  const dueDate = dates[1] || null;
  
  // Extract vendor name (usually first line or after "FROM:")
  const vendorMatch = text.match(/(?:from|vendor|bill\s*to)[\s:]*([^\n]+)/i);
  const vendorName = vendorMatch ? vendorMatch[1].trim() : (lines[0] || 'Unknown Vendor');
  
  // Extract currency
  const currencyMatch = text.match(/\b(USD|EUR|GBP|JPY|CAD|AUD|INR|CNY)\b/i);
  const currency = currencyMatch ? currencyMatch[1].toUpperCase() : 'USD';
  
  // Extract amounts
  const amountPattern = /(?:total|amount|sum)[\s:]*\$?([\d,]+\.?\d*)/i;
  const totalMatch = text.match(amountPattern);
  const totalAmount = totalMatch ? parseFloat(totalMatch[1].replace(/,/g, '')) : 0;
  
  // Extract line items (basic pattern matching)
  const lineItems: Array<{description: string; quantity: number; unit_price: number; total: number}> = [];
  const itemPattern = /(.+?)\s+(\d+)\s+\$?([\d,]+\.?\d*)\s+\$?([\d,]+\.?\d*)/;
  
  for (const line of lines) {
    const match = line.match(itemPattern);
    if (match) {
      lineItems.push({
        description: match[1].trim(),
        quantity: parseInt(match[2]) || 1,
        unit_price: parseFloat(match[3].replace(/,/g, '')) || 0,
        total: parseFloat(match[4].replace(/,/g, '')) || 0,
      });
    }
  }
  
  // If no line items found, create one from total
  if (lineItems.length === 0 && totalAmount > 0) {
    lineItems.push({
      description: 'Item',
      quantity: 1,
      unit_price: totalAmount,
      total: totalAmount,
    });
  }
  
  const subtotal = lineItems.reduce((sum, item) => sum + item.total, 0);
  const taxAmount = totalAmount - subtotal;
  
  return {
    vendor_name: vendorName,
    invoice_number: invoiceNumber,
    invoice_date: invoiceDate,
    due_date: dueDate,
    total_amount: totalAmount,
    currency: currency,
    line_items: lineItems,
    tax_amount: Math.max(0, taxAmount),
    subtotal: subtotal,
    raw_text: text,
    confidence: confidence / 100,
  };
}

/**
 * Basic receipt parsing from OCR text
 */
function parseReceiptFromText(text: string, confidence: number): any {
  const lines = text.split('\n').map(l => l.trim()).filter(l => l);
  
  const merchantMatch = text.match(/(?:merchant|store|restaurant)[\s:]*([^\n]+)/i);
  const merchantName = merchantMatch ? merchantMatch[1].trim() : (lines[0] || 'Unknown Merchant');
  
  const datePattern = /\b(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})\b/;
  const dateMatch = text.match(datePattern);
  const date = dateMatch ? dateMatch[1] : new Date().toISOString().split('T')[0];
  
  const timePattern = /\b(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)\b/i;
  const timeMatch = text.match(timePattern);
  const time = timeMatch ? timeMatch[1] : '';
  
  const amountPattern = /(?:total|amount)[\s:]*\$?([\d,]+\.?\d*)/i;
  const totalMatch = text.match(amountPattern);
  const total = totalMatch ? parseFloat(totalMatch[1].replace(/,/g, '')) : 0;
  
  const items: Array<{name: string; price: number; quantity: number}> = [];
  const itemPattern = /(.+?)\s+\$?([\d,]+\.?\d*)/;
  
  for (const line of lines.slice(0, 20)) { // Check first 20 lines
    const match = line.match(itemPattern);
    if (match && parseFloat(match[2]) > 0 && parseFloat(match[2]) < 10000) {
      items.push({
        name: match[1].trim(),
        price: parseFloat(match[2].replace(/,/g, '')),
        quantity: 1,
      });
    }
  }
  
  return {
    merchant_name: merchantName,
    date: date,
    time: time,
    items: items.length > 0 ? items : [{ name: 'Item', price: total, quantity: 1 }],
    subtotal: total * 0.9,
    tax: total * 0.1,
    total: total,
    payment_method: 'unknown',
    raw_text: text,
    confidence: confidence / 100,
  };
}

/**
 * Call Lovable AI (Gemini) - fallback only (costs money)
 */
async function callLovableAI(imageBase64: string, imageUrl: string | undefined, extractionType: string): Promise<any> {
  const LOVABLE_API_KEY = Deno.env.get('LOVABLE_API_KEY');
  
  if (!LOVABLE_API_KEY) {
    throw new Error('LOVABLE_API_KEY not configured');
  }

  console.log('Using Lovable AI (Gemini) as fallback');

  // Select prompt based on extraction type
  let systemPrompt = INVOICE_EXTRACTION_PROMPT;
  if (extractionType === 'receipt') {
    systemPrompt = RECEIPT_EXTRACTION_PROMPT;
  } else if (extractionType === 'general') {
    systemPrompt = GENERAL_OCR_PROMPT;
  }

  // Build image content for vision model
  const imageContent = imageBase64 
    ? { type: "image_url", image_url: { url: `data:image/jpeg;base64,${imageBase64}` } }
    : { type: "image_url", image_url: { url: imageUrl } };

  // Call Lovable AI with vision capabilities (Gemini 2.5 Pro for best vision)
  const response = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${LOVABLE_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "google/gemini-2.5-pro",
      messages: [
        { role: "system", content: systemPrompt },
        { 
          role: "user", 
          content: [
            { type: "text", text: "Extract all information from this document image." },
            imageContent
          ]
        }
      ],
      max_tokens: 4096,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.error("Lovable AI gateway error:", response.status, errorText);
    
    if (response.status === 429) {
      throw new Error("Rate limit exceeded. Please try again in a moment.");
    }
    
    if (response.status === 402) {
      const creditError = new Error("AI credits exhausted. Please add credits to continue.");
      (creditError as any).status = 402;
      (creditError as any).code = 'CREDITS_EXHAUSTED';
      throw creditError;
    }
    
    throw new Error(`Lovable AI service error: ${response.status}`);
  }

  const aiResponse = await response.json();
  const content = aiResponse.choices?.[0]?.message?.content;

  if (!content) {
    throw new Error('No response from Lovable AI service');
  }

  // Parse the JSON response from AI
  let cleanContent = content.trim();
  if (cleanContent.startsWith('```json')) {
    cleanContent = cleanContent.slice(7);
  }
  if (cleanContent.startsWith('```')) {
    cleanContent = cleanContent.slice(3);
  }
  if (cleanContent.endsWith('```')) {
    cleanContent = cleanContent.slice(0, -3);
  }
  
  try {
    return JSON.parse(cleanContent.trim());
  } catch (parseError) {
    console.error("Failed to parse Lovable AI response as JSON:", content);
    return {
      raw_text: content,
      confidence: 0.5,
      parse_error: true
    };
  }
}

serve(async (req) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { imageBase64, imageUrl, extractionType = 'invoice' }: OCRRequest = await req.json();

    if (!imageBase64 && !imageUrl) {
      return new Response(
        JSON.stringify({ error: 'Either imageBase64 or imageUrl is required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    console.log(`Processing ${extractionType} extraction request`);

    // STEP 1: Try PaddleOCR first (preferred, free)
    let ocrResults: any = null;
    let extractedData: any = null;
    let usedModel = 'unknown';

    try {
      console.log('Attempting PaddleOCR extraction...');
      ocrResults = await callPaddleOCR(imageBase64 || '', imageUrl, extractionType);
      usedModel = 'paddleocr';
      console.log('PaddleOCR extraction successful');
    } catch (paddleError) {
      console.warn(`PaddleOCR failed: ${paddleError instanceof Error ? paddleError.message : 'Unknown error'}`);
      // Continue to try ERNIE or fallback
    }

    // STEP 2: Try ERNIE for enrichment if PaddleOCR succeeded
    if (ocrResults) {
      try {
        console.log('Attempting ERNIE enrichment...');
        const ernieData = await callERNIE(ocrResults, imageBase64 || '', imageUrl, extractionType);
        if (ernieData) {
          extractedData = ernieData;
          usedModel = 'paddleocr+ernie';
          console.log('ERNIE enrichment successful');
        } else {
          // ERNIE failed but PaddleOCR succeeded, use OCR results
          extractedData = ocrResults;
          console.log('Using PaddleOCR results without ERNIE enrichment');
        }
      } catch (ernieError) {
        console.warn(`ERNIE enrichment failed: ${ernieError instanceof Error ? ernieError.message : 'Unknown error'}`);
        // Use PaddleOCR results if ERNIE fails
        extractedData = ocrResults;
        console.log('Using PaddleOCR results after ERNIE failure');
      }
    }

    // STEP 3: If PaddleOCR/ERNIE failed, try Lovable AI (fallback, costs money)
    if (!extractedData) {
      const LOVABLE_API_KEY = Deno.env.get('LOVABLE_API_KEY');
      
      if (LOVABLE_API_KEY) {
        try {
          console.log('PaddleOCR/ERNIE unavailable, falling back to Lovable AI...');
          extractedData = await callLovableAI(imageBase64 || '', imageUrl, extractionType);
          usedModel = 'lovable-gemini';
          console.log('Lovable AI extraction successful');
        } catch (lovableError) {
          // If it's a credit exhaustion error, return 402 immediately
          if ((lovableError as any)?.code === 'CREDITS_EXHAUSTED' || (lovableError as any)?.status === 402) {
            console.error('AI credits exhausted');
            return new Response(
              JSON.stringify({ 
                error: "AI credits exhausted.",
                error_code: "CREDITS_EXHAUSTED",
                message: "AI credits have been exhausted. Please add credits to your account to continue using AI features.",
                success: false
              }),
              { status: 402, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
            );
          }
          console.error(`Lovable AI fallback failed: ${lovableError instanceof Error ? lovableError.message : 'Unknown error'}`);
          // Continue to final fallback for other errors
        }
      } else {
        console.log('LOVABLE_API_KEY not configured, skipping Lovable AI fallback');
      }
    }

    // STEP 4: Final fallback to OCR.space (free but less accurate)
    if (!extractedData) {
      try {
        console.log('All primary services failed, using OCR.space fallback...');
        extractedData = await fallbackOCR(imageBase64 || '', imageUrl, extractionType);
        usedModel = 'ocr.space-fallback';
        console.log('OCR.space fallback successful');
      } catch (fallbackError) {
        console.error("All OCR services failed:", fallbackError);
        return new Response(
          JSON.stringify({ 
            error: 'All OCR services failed. Please check service configurations.',
            details: fallbackError instanceof Error ? fallbackError.message : 'Unknown error',
            success: false
          }),
          { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
      }
    }

    // Return successful result
    return new Response(
      JSON.stringify({
        success: true,
        extractionType,
        data: extractedData,
        model: usedModel,
        timestamp: new Date().toISOString(),
        ...(usedModel === 'lovable-gemini' ? {
          warning: "Used Lovable AI (paid service) as fallback. Configure PADDLEOCR_VLLM_URL and ERNIE_VLLM_URL to avoid costs."
        } : {}),
        ...(usedModel === 'ocr.space-fallback' ? {
          warning: "Used free OCR.space service. Configure PADDLEOCR_VLLM_URL and ERNIE_VLLM_URL for better accuracy."
        } : {})
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error("OCR extraction error:", error);
    return new Response(
      JSON.stringify({ 
        error: error instanceof Error ? error.message : 'Unknown error',
        success: false 
      }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  }
});
