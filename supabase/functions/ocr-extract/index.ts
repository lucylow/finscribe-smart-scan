/**
 * OCR Extract Edge Function
 * 
 * Uses Lovable AI (Gemini) vision capabilities to extract text and structured data
 * from invoice/document images.
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

serve(async (req) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const LOVABLE_API_KEY = Deno.env.get('LOVABLE_API_KEY');
    if (!LOVABLE_API_KEY) {
      console.error('LOVABLE_API_KEY is not configured');
      throw new Error('AI service not configured');
    }

    const { imageBase64, imageUrl, extractionType = 'invoice' }: OCRRequest = await req.json();

    if (!imageBase64 && !imageUrl) {
      return new Response(
        JSON.stringify({ error: 'Either imageBase64 or imageUrl is required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

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

    console.log(`Processing ${extractionType} extraction request`);

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
      console.error("AI gateway error:", response.status, errorText);
      
      if (response.status === 429) {
        return new Response(
          JSON.stringify({ error: "Rate limit exceeded. Please try again in a moment." }),
          { status: 429, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
      }
      if (response.status === 402) {
        return new Response(
          JSON.stringify({ error: "AI credits exhausted. Please add credits to continue." }),
          { status: 402, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
      }
      
      throw new Error(`AI service error: ${response.status}`);
    }

    const aiResponse = await response.json();
    const content = aiResponse.choices?.[0]?.message?.content;

    if (!content) {
      throw new Error('No response from AI service');
    }

    console.log("AI extraction complete");

    // Parse the JSON response from AI
    let extractedData;
    try {
      // Clean the response - remove markdown code blocks if present
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
      
      extractedData = JSON.parse(cleanContent.trim());
    } catch (parseError) {
      console.error("Failed to parse AI response as JSON:", content);
      // Return raw text if JSON parsing fails
      extractedData = {
        raw_text: content,
        confidence: 0.5,
        parse_error: true
      };
    }

    return new Response(
      JSON.stringify({
        success: true,
        extractionType,
        data: extractedData,
        model: "google/gemini-2.5-pro",
        timestamp: new Date().toISOString()
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
