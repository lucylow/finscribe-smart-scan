-- Monetization System Schema
-- Extends existing profiles table with billing and usage tracking

-- Add billing fields to profiles
ALTER TABLE public.profiles 
ADD COLUMN IF NOT EXISTS plan TEXT DEFAULT 'free' CHECK (plan IN ('free', 'starter', 'pro', 'enterprise')),
ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT,
ADD COLUMN IF NOT EXISTS api_credits INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS referred_by_partner_id UUID;

-- Create index for stripe customer lookup
CREATE INDEX IF NOT EXISTS idx_profiles_stripe_customer ON public.profiles(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_profiles_partner ON public.profiles(referred_by_partner_id);

-- Document usage tracking
CREATE TABLE IF NOT EXISTS public.document_usage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  document_id UUID,
  pages INT DEFAULT 1,
  processed_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_document_usage_user ON public.document_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_document_usage_processed ON public.document_usage(processed_at);

-- Billing cycles
CREATE TABLE IF NOT EXISTS public.billing_cycles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  docs_used INT DEFAULT 0,
  overage_cost_usd NUMERIC(10, 2) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, period_start)
);

CREATE INDEX IF NOT EXISTS idx_billing_cycles_user ON public.billing_cycles(user_id);
CREATE INDEX IF NOT EXISTS idx_billing_cycles_period ON public.billing_cycles(period_start, period_end);

-- Enterprise licenses
CREATE TABLE IF NOT EXISTS public.licenses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_name TEXT NOT NULL,
  seats INT DEFAULT 1,
  expires_at DATE,
  on_prem BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Partners (QuickBooks, Xero, etc.)
CREATE TABLE IF NOT EXISTS public.partners (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  type TEXT NOT NULL CHECK (type IN ('quickbooks', 'xero', 'other')),
  code TEXT NOT NULL UNIQUE,
  revenue_share NUMERIC(5, 4) DEFAULT 0.25 CHECK (revenue_share >= 0 AND revenue_share <= 1),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Partner referrals (revenue attribution)
CREATE TABLE IF NOT EXISTS public.partner_referrals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES public.partners(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  stripe_invoice_id TEXT,
  revenue_usd NUMERIC(10, 2) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_partner_referrals_partner ON public.partner_referrals(partner_id);
CREATE INDEX IF NOT EXISTS idx_partner_referrals_user ON public.partner_referrals(user_id);

-- Marketplace models
CREATE TABLE IF NOT EXISTS public.marketplace_models (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  price_usd INTEGER NOT NULL,
  description TEXT,
  model_path TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Premium feature purchases
CREATE TABLE IF NOT EXISTS public.premium_feature_purchases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  feature_name TEXT NOT NULL,
  price_usd NUMERIC(10, 2) NOT NULL,
  purchased_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_premium_features_user ON public.premium_feature_purchases(user_id);

-- Update triggers
CREATE TRIGGER update_billing_cycles_updated_at
  BEFORE UPDATE ON public.billing_cycles
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER update_licenses_updated_at
  BEFORE UPDATE ON public.licenses
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- RLS Policies
ALTER TABLE public.document_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.billing_cycles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.premium_feature_purchases ENABLE ROW LEVEL SECURITY;

-- Users can view their own usage
CREATE POLICY "Users can view own document usage"
ON public.document_usage FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can view own billing cycles"
ON public.billing_cycles FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can view own premium features"
ON public.premium_feature_purchases FOR SELECT
USING (auth.uid() = user_id);

-- Insert default partners
INSERT INTO public.partners (name, type, code, revenue_share) VALUES
  ('QuickBooks', 'quickbooks', 'quickbooks', 0.25),
  ('Xero', 'xero', 'xero', 0.30)
ON CONFLICT (name) DO NOTHING;

