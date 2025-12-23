/**
 * OCR Extract Edge Function - DEMO MODE
 * Returns realistic sample invoice data for hackathon demo.
 * No external AI services required.
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

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

// Demo templates for variety
// Walmart Receipt Mock Data - for hackathon demo
function generateWalmartReceiptExtraction(): ExtractedInvoice {
  const today = new Date();
  const receiptTime = "04:32 PM";
  
  const lineItems = [
    { description: "GV 2% MILK GAL", quantity: 1, unit_price: 3.48, total: 3.48 },
    { description: "BANANAS LB", quantity: 1, unit_price: 1.67, total: 1.67 },
    { description: "GV WHITE BREAD", quantity: 1, unit_price: 1.28, total: 1.28 },
    { description: "EGGS LARGE 12CT", quantity: 1, unit_price: 2.97, total: 2.97 },
    { description: "CHICKEN BREAST", quantity: 2.34, unit_price: 3.47, total: 8.12 },
    { description: "ROMA TOMATOES", quantity: 1, unit_price: 1.24, total: 1.24 },
    { description: "YELLOW ONION 3LB", quantity: 1, unit_price: 2.98, total: 2.98 },
    { description: "GV BUTTER SALTED", quantity: 1, unit_price: 3.64, total: 3.64 },
  ];
  
  const subtotal = lineItems.reduce((sum, item) => sum + item.total, 0);
  const taxAmount = Math.round(subtotal * 0.0825 * 100) / 100;
  const total = Math.round((subtotal + taxAmount) * 100) / 100;

  const rawText = `WALMART SUPERCENTER
Store #4528
2501 SE SIMPLE SAVINGS BLVD
BENTONVILLE, AR 72712
(479) 273-4567

ST# 4528  OP# 004832  TE# 12  TR# 8847

GV 2% MILK GAL           3.48
BANANAS LB               1.67
GV WHITE BREAD           1.28
EGGS LARGE 12CT          2.97
CHICKEN BREAST  2.34 lb @ 3.47/lb    8.12
ROMA TOMATOES            1.24
YELLOW ONION 3LB         2.98
GV BUTTER SALTED         3.64

        SUBTOTAL        ${subtotal.toFixed(2)}
        TAX 8.25%        ${taxAmount.toFixed(2)}
        TOTAL           ${total.toFixed(2)}

VISA DEBIT TEND          ${total.toFixed(2)}
        CHANGE DUE        0.00

CARD # ************4892
APPROVAL # 847291

${today.toLocaleDateString('en-US')}  ${receiptTime}

# ITEMS SOLD 8

         THANK YOU FOR SHOPPING
            AT WALMART
       SAVE MONEY. LIVE BETTER.

        TC# 7291 8847 3829 4721`;

  return {
    vendor_name: "Walmart Supercenter #4528",
    invoice_number: "TR# 8847",
    invoice_date: today.toISOString().split('T')[0],
    due_date: today.toISOString().split('T')[0],
    total_amount: total,
    currency: "USD",
    line_items: lineItems,
    tax_amount: taxAmount,
    subtotal: subtotal,
    raw_text: rawText,
    confidence: 0.96,
  };
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    console.log("Processing invoice extraction (Demo Mode - No AI Credits Used)");
    
    const body = await req.json();
    const filename = body.filename || body.image?.name || 'document';
    
    console.log(`Processing file: ${filename}`);
    
    // Simulate OCR processing time
    await new Promise(resolve => setTimeout(resolve, 600 + Math.random() * 400));
    
    const extractedData = generateWalmartReceiptExtraction();
    
    console.log("Walmart receipt OCR complete:", {
      invoice_number: extractedData.invoice_number,
      vendor: extractedData.vendor_name,
      total: extractedData.total_amount,
      items: extractedData.line_items.length
    });

    return new Response(
      JSON.stringify({
        success: true,
        data: extractedData,
        mode: 'demo',
        message: 'Demo mode - realistic sample invoice data'
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
