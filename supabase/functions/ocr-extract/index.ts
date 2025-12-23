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
const demoInvoices = [
  {
    vendor: "TechFlow Solutions Inc.",
    address: "1234 Innovation Drive, Suite 500, San Francisco, CA 94105",
    items: [
      { description: "Professional Services - Q4 2024", quantity: 40, unit_price: 150.00 },
      { description: "Software License (Annual)", quantity: 1, unit_price: 2400.00 },
      { description: "Cloud Infrastructure", quantity: 1, unit_price: 850.00 },
    ]
  },
  {
    vendor: "CloudSoft Technologies",
    address: "5678 Tech Boulevard, Austin, TX 78701",
    items: [
      { description: "SaaS Platform Subscription", quantity: 12, unit_price: 299.00 },
      { description: "API Integration Services", quantity: 1, unit_price: 1500.00 },
      { description: "Premium Support Plan", quantity: 1, unit_price: 500.00 },
    ]
  },
  {
    vendor: "Digital Dynamics LLC",
    address: "900 Startup Way, Seattle, WA 98101",
    items: [
      { description: "Web Development Services", quantity: 80, unit_price: 125.00 },
      { description: "UI/UX Design Package", quantity: 1, unit_price: 3500.00 },
      { description: "Hosting & Maintenance", quantity: 6, unit_price: 150.00 },
    ]
  }
];

function generateDemoExtraction(): ExtractedInvoice {
  const template = demoInvoices[Math.floor(Math.random() * demoInvoices.length)];
  const invoiceNum = `INV-${Math.floor(10000 + Math.random() * 90000)}`;
  const today = new Date();
  const dueDate = new Date(today);
  dueDate.setDate(dueDate.getDate() + 30);
  
  const lineItems = template.items.map(item => ({
    description: item.description,
    quantity: item.quantity,
    unit_price: item.unit_price,
    total: item.quantity * item.unit_price,
  }));
  
  const subtotal = lineItems.reduce((sum, item) => sum + item.total, 0);
  const taxAmount = Math.round(subtotal * 0.0825 * 100) / 100;
  const total = subtotal + taxAmount;

  const rawText = `INVOICE
${invoiceNum}
Date: ${today.toISOString().split('T')[0]}
Due: ${dueDate.toISOString().split('T')[0]}

From: ${template.vendor}
${template.address}

To: Acme Corporation
789 Business Park
Los Angeles, CA 90210

Items:
${lineItems.map(item => `- ${item.description}: $${item.total.toFixed(2)}`).join('\n')}

Subtotal: $${subtotal.toFixed(2)}
Tax (8.25%): $${taxAmount.toFixed(2)}
Total: $${total.toFixed(2)}

Payment Terms: Net 30`;

  return {
    vendor_name: template.vendor,
    invoice_number: invoiceNum,
    invoice_date: today.toISOString().split('T')[0],
    due_date: dueDate.toISOString().split('T')[0],
    total_amount: total,
    currency: "USD",
    line_items: lineItems,
    tax_amount: taxAmount,
    subtotal: subtotal,
    raw_text: rawText,
    confidence: 0.92 + Math.random() * 0.07,
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
    
    // Simulate processing time for realism
    await new Promise(resolve => setTimeout(resolve, 800 + Math.random() * 700));
    
    const extractedData = generateDemoExtraction();
    
    console.log("Demo extraction complete:", {
      invoice_number: extractedData.invoice_number,
      vendor: extractedData.vendor_name,
      total: extractedData.total_amount,
      confidence: extractedData.confidence.toFixed(2)
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
