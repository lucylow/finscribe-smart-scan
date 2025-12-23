/**
 * OCR Extract Edge Function - PaddleOCR-VL via Hugging Face
 * Uses PaddlePaddle/PaddleOCR-VL model for real OCR extraction
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

interface LineItem {
  description: string;
  quantity: number;
  unit_price: number;
  total: number;
}

interface ExtractedInvoice {
  vendor_name: string;
  invoice_number: string;
  invoice_date: string;
  due_date: string;
  total_amount: number;
  currency: string;
  line_items: LineItem[];
  tax_amount: number;
  subtotal: number;
  raw_text: string;
  confidence: number;
}

/**
 * Call PaddleOCR-VL model via Hugging Face Inference API
 */
async function callPaddleOCRVL(imageBase64: string, hfToken: string): Promise<string> {
  console.log("Calling PaddleOCR-VL model via Hugging Face...");
  
  // PaddleOCR-VL model endpoint - using new router.huggingface.co URL
  const modelEndpoint = "https://router.huggingface.co/hf-inference/models/PaddlePaddle/PaddleOCR-VL-0.9B";
  
  const response = await fetch(modelEndpoint, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${hfToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      inputs: {
        image: imageBase64,
        text: "Please extract all text from this receipt or invoice image. Include all line items, prices, totals, dates, and vendor information."
      },
      parameters: {
        max_new_tokens: 2048,
      }
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.error("HuggingFace API error:", response.status, errorText);
    
    // Check if model is loading
    if (response.status === 503) {
      const errorJson = JSON.parse(errorText);
      if (errorJson.error?.includes("loading")) {
        throw new Error("Model is loading. Please try again in 20-30 seconds.");
      }
    }
    
    throw new Error(`HuggingFace API error: ${response.status} - ${errorText}`);
  }

  const result = await response.json();
  console.log("PaddleOCR-VL raw response:", JSON.stringify(result).substring(0, 500));
  
  // Handle different response formats
  if (typeof result === 'string') {
    return result;
  } else if (Array.isArray(result) && result.length > 0) {
    if (typeof result[0] === 'string') {
      return result[0];
    } else if (result[0].generated_text) {
      return result[0].generated_text;
    }
  } else if (result.generated_text) {
    return result.generated_text;
  } else if (result.text) {
    return result.text;
  }
  
  return JSON.stringify(result);
}

/**
 * Parse OCR text into structured invoice data
 */
function parseReceiptText(rawText: string): ExtractedInvoice {
  const lines = rawText.split('\n').map(l => l.trim()).filter(l => l);
  
  // Extract vendor name (usually first non-empty line)
  let vendorName = "Unknown Vendor";
  if (lines.length > 0) {
    vendorName = lines[0];
  }
  
  // Look for common patterns
  let invoiceNumber = "";
  let invoiceDate = new Date().toISOString().split('T')[0];
  let totalAmount = 0;
  let taxAmount = 0;
  let subtotal = 0;
  const lineItems: LineItem[] = [];
  
  // Pattern matching for receipt data
  const datePattern = /(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})/;
  const pricePattern = /\$?\d+\.\d{2}/g;
  const invoicePattern = /(?:invoice|receipt|order|tr|tc)[#:\s]*([A-Z0-9\-]+)/i;
  const totalPattern = /(?:total|amount due|grand total)[:\s]*\$?(\d+\.?\d*)/i;
  const taxPattern = /(?:tax|vat|gst)[:\s]*\$?(\d+\.?\d*)/i;
  const subtotalPattern = /(?:subtotal|sub-total)[:\s]*\$?(\d+\.?\d*)/i;
  
  for (const line of lines) {
    // Find invoice/receipt number
    const invoiceMatch = line.match(invoicePattern);
    if (invoiceMatch) {
      invoiceNumber = invoiceMatch[1];
    }
    
    // Find date
    const dateMatch = line.match(datePattern);
    if (dateMatch) {
      invoiceDate = dateMatch[1];
    }
    
    // Find total
    const totalMatch = line.match(totalPattern);
    if (totalMatch) {
      totalAmount = parseFloat(totalMatch[1]);
    }
    
    // Find tax
    const taxMatch = line.match(taxPattern);
    if (taxMatch) {
      taxAmount = parseFloat(taxMatch[1]);
    }
    
    // Find subtotal
    const subtotalMatch = line.match(subtotalPattern);
    if (subtotalMatch) {
      subtotal = parseFloat(subtotalMatch[1]);
    }
    
    // Try to identify line items (lines with prices that aren't totals)
    const prices = line.match(pricePattern);
    if (prices && !line.toLowerCase().includes('total') && 
        !line.toLowerCase().includes('tax') && 
        !line.toLowerCase().includes('change') &&
        !line.toLowerCase().includes('tend')) {
      const description = line.replace(pricePattern, '').trim();
      if (description.length > 2) {
        const price = parseFloat(prices[prices.length - 1].replace('$', ''));
        lineItems.push({
          description: description.substring(0, 50),
          quantity: 1,
          unit_price: price,
          total: price
        });
      }
    }
  }
  
  // Calculate subtotal if not found
  if (subtotal === 0 && lineItems.length > 0) {
    subtotal = lineItems.reduce((sum, item) => sum + item.total, 0);
  }
  
  // Calculate total if not found
  if (totalAmount === 0) {
    totalAmount = subtotal + taxAmount;
  }
  
  return {
    vendor_name: vendorName,
    invoice_number: invoiceNumber || `OCR-${Date.now()}`,
    invoice_date: invoiceDate,
    due_date: invoiceDate,
    total_amount: totalAmount,
    currency: "USD",
    line_items: lineItems,
    tax_amount: taxAmount,
    subtotal: subtotal,
    raw_text: rawText,
    confidence: 0.85,
  };
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const hfToken = Deno.env.get('HUGGING_FACE_ACCESS_TOKEN');
    if (!hfToken) {
      console.error("HUGGING_FACE_ACCESS_TOKEN not configured");
      return new Response(
        JSON.stringify({
          success: false,
          error: "HUGGING_FACE_ACCESS_TOKEN not configured. Please add your Hugging Face token."
        }),
        { 
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
        }
      );
    }
    
    const body = await req.json();
    const { imageBase64, imageUrl, extractionType } = body;
    
    console.log(`Processing ${extractionType || 'document'} with PaddleOCR-VL...`);
    
    let base64Data = imageBase64;
    
    // If URL provided, fetch and convert to base64
    if (imageUrl && !imageBase64) {
      console.log("Fetching image from URL:", imageUrl);
      const imageResponse = await fetch(imageUrl);
      const imageBuffer = await imageResponse.arrayBuffer();
      base64Data = btoa(String.fromCharCode(...new Uint8Array(imageBuffer)));
    }
    
    if (!base64Data) {
      return new Response(
        JSON.stringify({
          success: false,
          error: "No image provided. Please provide imageBase64 or imageUrl."
        }),
        { 
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
        }
      );
    }
    
    let extractedData: ExtractedInvoice;
    let usedFallback = false;
    
    try {
      // Call PaddleOCR-VL
      const rawText = await callPaddleOCRVL(base64Data, hfToken);
      console.log("OCR extracted text length:", rawText.length);
      console.log("OCR text preview:", rawText.substring(0, 300));
      
      // Parse the extracted text into structured data
      extractedData = parseReceiptText(rawText);
      
      console.log("Extraction complete:", {
        vendor: extractedData.vendor_name,
        invoice_number: extractedData.invoice_number,
        total: extractedData.total_amount,
        items: extractedData.line_items.length
      });
    } catch (ocrError) {
      console.warn("PaddleOCR-VL failed, using mock fallback:", ocrError);
      usedFallback = true;
      
      // Mock fallback data
      extractedData = {
        vendor_name: "Sample Store",
        invoice_number: `MOCK-${Date.now()}`,
        invoice_date: new Date().toISOString().split('T')[0],
        due_date: new Date().toISOString().split('T')[0],
        total_amount: 45.99,
        currency: "USD",
        line_items: [
          { description: "Item 1", quantity: 2, unit_price: 12.99, total: 25.98 },
          { description: "Item 2", quantity: 1, unit_price: 15.00, total: 15.00 },
          { description: "Item 3", quantity: 1, unit_price: 5.01, total: 5.01 }
        ],
        tax_amount: 3.50,
        subtotal: 42.49,
        raw_text: "(Mock data - OCR service unavailable)",
        confidence: 0.0
      };
    }

    return new Response(
      JSON.stringify({
        success: true,
        extractionType: extractionType || 'invoice',
        data: extractedData,
        model: usedFallback ? 'mock-fallback' : 'PaddleOCR-VL-0.9B',
        usedFallback,
        timestamp: new Date().toISOString()
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );

  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error('OCR extraction error:', errorMessage);
    
    return new Response(
      JSON.stringify({
        success: false,
        error: errorMessage
      }),
      { 
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    );
  }
});