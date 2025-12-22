/**
 * AI Enhancement Edge Function
 * 
 * Enhances and validates extracted invoice data using AI.
 * Can correct errors, fill in missing fields, and improve data quality.
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

interface EnhanceRequest {
  extractedData: Record<string, unknown>;
  rawText?: string;
  action: 'validate' | 'enhance' | 'categorize' | 'summarize';
}

const VALIDATION_PROMPT = `You are a financial document validation expert. Review the extracted invoice data and:
1. Check for inconsistencies (e.g., line items don't sum to subtotal)
2. Validate date formats
3. Check currency consistency
4. Flag any suspicious or missing data

Return JSON:
{
  "is_valid": true/false,
  "errors": ["List of errors found"],
  "warnings": ["List of warnings"],
  "corrections": {"field": "corrected_value"},
  "confidence_score": 0.95
}`;

const ENHANCEMENT_PROMPT = `You are a financial data enhancement AI. Given the extracted invoice data:
1. Fill in any missing fields that can be inferred
2. Standardize formats (dates, currencies, addresses)
3. Calculate missing totals if line items are present
4. Improve data quality

Return the enhanced data as JSON with the same structure, plus:
{
  ...enhanced_data,
  "enhancements_made": ["List of improvements"],
  "confidence": 0.95
}`;

const CATEGORIZATION_PROMPT = `Analyze this invoice/expense and categorize it:
1. Expense category (e.g., Office Supplies, Travel, Software, Professional Services)
2. Suggested GL account code
3. Department allocation if determinable
4. Priority (urgent/normal/low based on due date)

Return JSON:
{
  "category": "Category name",
  "subcategory": "Subcategory if applicable",
  "suggested_gl_code": "GL code",
  "department": "Department",
  "priority": "normal",
  "tags": ["relevant", "tags"],
  "notes": "Any relevant notes"
}`;

const SUMMARY_PROMPT = `Create a brief summary of this invoice for quick review:

Return JSON:
{
  "one_liner": "Brief one-line summary",
  "key_details": "Vendor | Amount | Due Date",
  "action_required": "What needs to be done",
  "risk_flags": ["Any concerns"]
}`;

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const LOVABLE_API_KEY = Deno.env.get('LOVABLE_API_KEY');
    if (!LOVABLE_API_KEY) {
      throw new Error('AI service not configured');
    }

    const { extractedData, rawText, action = 'validate' }: EnhanceRequest = await req.json();

    if (!extractedData) {
      return new Response(
        JSON.stringify({ error: 'extractedData is required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    // Select prompt based on action
    let systemPrompt: string;
    switch (action) {
      case 'enhance':
        systemPrompt = ENHANCEMENT_PROMPT;
        break;
      case 'categorize':
        systemPrompt = CATEGORIZATION_PROMPT;
        break;
      case 'summarize':
        systemPrompt = SUMMARY_PROMPT;
        break;
      default:
        systemPrompt = VALIDATION_PROMPT;
    }

    const userContent = `Invoice Data:\n${JSON.stringify(extractedData, null, 2)}${rawText ? `\n\nRaw Text:\n${rawText}` : ''}`;

    console.log(`Processing ${action} request`);

    const response = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${LOVABLE_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "google/gemini-2.5-flash",
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userContent }
        ],
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
          JSON.stringify({ error: "AI credits exhausted." }),
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

    // Parse JSON response
    let result;
    try {
      let cleanContent = content.trim();
      if (cleanContent.startsWith('```json')) cleanContent = cleanContent.slice(7);
      if (cleanContent.startsWith('```')) cleanContent = cleanContent.slice(3);
      if (cleanContent.endsWith('```')) cleanContent = cleanContent.slice(0, -3);
      
      result = JSON.parse(cleanContent.trim());
    } catch {
      result = { raw_response: content, parse_error: true };
    }

    return new Response(
      JSON.stringify({
        success: true,
        action,
        result,
        timestamp: new Date().toISOString()
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error("AI enhancement error:", error);
    return new Response(
      JSON.stringify({ 
        error: error instanceof Error ? error.message : 'Unknown error',
        success: false 
      }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  }
});
