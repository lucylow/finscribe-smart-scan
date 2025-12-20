/**
 * Free External APIs Service for FinScribe
 * 
 * This module provides integrations with free external APIs that don't require API keys.
 * All APIs include proper error handling and fallbacks for demo purposes.
 */

// ============================================================================
// Types
// ============================================================================

export interface OCRResult {
  text: string;
  confidence?: number;
  language?: string;
}

export interface ExchangeRate {
  base: string;
  rates: Record<string, number>;
  timestamp?: number;
}

export interface CurrencyConversion {
  from: string;
  to: string;
  amount: number;
  converted: number;
  rate: number;
}

export interface MockInvoice {
  invoice_id: string;
  vendor: {
    name: string;
    email: string;
    address?: string;
  };
  amount: number;
  currency: string;
  date: string;
  items: Array<{
    description: string;
    quantity: number;
    price: number;
  }>;
}

export interface TranslationResult {
  original: string;
  translated: string;
  sourceLang: string;
  targetLang: string;
}

export interface GeolocationData {
  country: string;
  country_name: string;
  currency: string;
  city?: string;
  region?: string;
}

// ============================================================================
// OCR Service (OCR.space - Free Tier)
// ============================================================================

/**
 * Extract text from an image using OCR.space free API
 * Free tier: 25,000 requests/month
 * 
 * @param imageFile - File object or Blob containing the image
 * @param language - Language code (default: 'eng')
 * @returns Extracted text from the image
 */
export async function ocrImage(
  imageFile: File | Blob,
  language: string = 'eng'
): Promise<OCRResult> {
  try {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('apikey', 'helloworld'); // Free public key
    formData.append('language', language);
    formData.append('isOverlayRequired', 'false');
    formData.append('OCREngine', '2');

    const response = await fetch('https://api.ocr.space/parse/image', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`OCR API returned ${response.status}`);
    }

    const data = await response.json();
    
    if (data.ParsedResults && data.ParsedResults.length > 0) {
      return {
        text: data.ParsedResults[0].ParsedText,
        confidence: data.ParsedResults[0].TextOverlay?.MeanConfidence,
        language: language,
      };
    }

    throw new Error('No text found in image');
  } catch (error) {
    console.warn('OCR API error:', error);
    // Return mock data as fallback
    return {
      text: `INVOICE #: INV-${new Date().getFullYear()}-${Math.floor(Math.random() * 9000) + 1000}\nVENDOR: TechCorp Solutions Inc.\nDATE: ${new Date().toISOString().split('T')[0]}\nTOTAL: $${(Math.random() * 5000 + 500).toFixed(2)}\nITEMS:\n1. Software License - $${(Math.random() * 2000 + 500).toFixed(2)}\n2. Support Package - $${(Math.random() * 500 + 100).toFixed(2)}`,
      confidence: 0.85,
      language: language,
    };
  }
}

// ============================================================================
// Currency Exchange Rates
// ============================================================================

/**
 * Get exchange rates from free API
 * No API key required, but has rate limits
 * 
 * @param baseCurrency - Base currency code (default: 'USD')
 * @returns Exchange rates object
 */
export async function getExchangeRates(
  baseCurrency: string = 'USD'
): Promise<ExchangeRate> {
  try {
    const response = await fetch(
      `https://api.exchangerate-api.com/v4/latest/${baseCurrency}`
    );

    if (!response.ok) {
      throw new Error(`Exchange rate API returned ${response.status}`);
    }

    const data = await response.json();
    return {
      base: data.base,
      rates: data.rates,
      timestamp: Date.now(),
    };
  } catch (error) {
    console.warn('Exchange rate API error:', error);
    // Return cached/fallback rates
    return {
      base: baseCurrency,
      rates: {
        USD: 1.0,
        EUR: 0.92,
        GBP: 0.79,
        JPY: 148.5,
        CAD: 1.35,
        AUD: 1.52,
        CHF: 0.88,
        CNY: 7.24,
        INR: 83.0,
        MXN: 17.0,
      },
      timestamp: Date.now(),
    };
  }
}

/**
 * Convert currency amount
 * 
 * @param amount - Amount to convert
 * @param from - Source currency code
 * @param to - Target currency code
 * @returns Conversion result
 */
export async function convertCurrency(
  amount: number,
  from: string,
  to: string
): Promise<CurrencyConversion> {
  try {
    const rates = await getExchangeRates(from);
    const rate = rates.rates[to] || 1;
    const converted = amount * rate;

    return {
      from,
      to,
      amount,
      converted: Number(converted.toFixed(2)),
      rate: Number(rate.toFixed(4)),
    };
  } catch (error) {
    console.error('Currency conversion error:', error);
    throw error;
  }
}

// ============================================================================
// QR Code Generation (Client-side)
// ============================================================================

/**
 * Generate QR code data URL for invoice sharing
 * Uses qrcode library (needs to be installed: npm install qrcode)
 * 
 * @param data - Data to encode in QR code
 * @returns Base64 data URL of the QR code image
 */
export async function generateQRCode(data: string | object): Promise<string> {
  try {
    // Dynamic import to avoid bundling if not used
    const QRCode = await import('qrcode');
    const dataString = typeof data === 'string' ? data : JSON.stringify(data);
    
    const dataUrl = await QRCode.toDataURL(dataString, {
      errorCorrectionLevel: 'L',
      type: 'image/png',
      margin: 1,
      color: {
        dark: '#000000',
        light: '#FFFFFF',
      },
    }) as string;

    return dataUrl;
  } catch (error) {
    console.warn('QR code generation error:', error);
    // Return a placeholder data URL
    return 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2YzZjRmNiIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM2YjcyODAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5RUiBDb2RlPC90ZXh0Pjwvc3ZnPg==';
  }
}

// ============================================================================
// Translation Service (MyMemory - Free Tier)
// ============================================================================

/**
 * Translate text using MyMemory free translation API
 * Free tier: 10,000 words/day
 * 
 * @param text - Text to translate
 * @param targetLang - Target language code (default: 'es')
 * @param sourceLang - Source language code (default: 'en')
 * @returns Translation result
 */
export async function translateText(
  text: string,
  targetLang: string = 'es',
  sourceLang: string = 'en'
): Promise<TranslationResult> {
  try {
    const url = new URL('https://api.mymemory.translated.net/get');
    url.searchParams.append('q', text);
    url.searchParams.append('langpair', `${sourceLang}|${targetLang}`);

    const response = await fetch(url.toString());

    if (!response.ok) {
      throw new Error(`Translation API returned ${response.status}`);
    }

    const data = await response.json();

    if (data.responseStatus === 200 && data.responseData) {
      return {
        original: text,
        translated: data.responseData.translatedText,
        sourceLang: sourceLang,
        targetLang: targetLang,
      };
    }

    throw new Error('Translation failed');
  } catch (error) {
    console.warn('Translation API error:', error);
    // Return original text as fallback
    return {
      original: text,
      translated: text,
      sourceLang: sourceLang,
      targetLang: targetLang,
    };
  }
}

// ============================================================================
// Mock Invoice Generation
// ============================================================================

/**
 * Generate mock invoice data for demo purposes
 * 
 * @returns Mock invoice object
 */
export function generateMockInvoice(): MockInvoice {
  const vendors = [
    { name: 'TechCorp Solutions Inc.', email: 'billing@techcorp.com' },
    { name: 'Global Solutions Ltd.', email: 'billing@globalsol.com' },
    { name: 'Innovate Co.', email: 'billing@innovate.com' },
    { name: 'Digital Services Group', email: 'billing@digital.com' },
    { name: 'Enterprise Systems', email: 'billing@enterprise.com' },
  ];

  const items = [
    'Software License',
    'Support Package',
    'Consulting Services',
    'Hardware Equipment',
    'Training Program',
    'Maintenance Contract',
    'Cloud Services',
    'API Access',
  ];

  const currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD'];

  const vendor = vendors[Math.floor(Math.random() * vendors.length)];
  const currency = currencies[Math.floor(Math.random() * currencies.length)];
  const numItems = Math.floor(Math.random() * 4) + 1; // 1-5 items

  const invoiceItems = Array.from({ length: numItems }, () => {
    const quantity = Math.floor(Math.random() * 10) + 1;
    const price = Math.random() * 1000 + 50;
    return {
      description: items[Math.floor(Math.random() * items.length)],
      quantity,
      price: Number(price.toFixed(2)),
    };
  });

  const totalAmount = invoiceItems.reduce(
    (sum, item) => sum + item.price * item.quantity,
    0
  );

  return {
    invoice_id: `INV-${new Date().getFullYear()}-${Math.floor(Math.random() * 9000) + 1000}`,
    vendor: {
      ...vendor,
      address: `${Math.floor(Math.random() * 9999)} Business St, City, Country`,
    },
    amount: Number(totalAmount.toFixed(2)),
    currency,
    date: new Date().toISOString().split('T')[0],
    items: invoiceItems,
  };
}

// ============================================================================
// Geolocation Service (IP-based)
// ============================================================================

/**
 * Get user location based on IP address
 * Free tier: No API key required
 * 
 * @returns Geolocation data
 */
export async function getUserLocation(): Promise<GeolocationData> {
  try {
    const response = await fetch('https://ipapi.co/json/');

    if (!response.ok) {
      throw new Error(`Geolocation API returned ${response.status}`);
    }

    const data = await response.json();

    return {
      country: data.country_code || 'US',
      country_name: data.country_name || 'United States',
      currency: data.currency || 'USD',
      city: data.city,
      region: data.region,
    };
  } catch (error) {
    console.warn('Geolocation API error:', error);
    // Return default US location
    return {
      country: 'US',
      country_name: 'United States',
      currency: 'USD',
    };
  }
}

// ============================================================================
// Country Flags (Emoji-based)
// ============================================================================

/**
 * Get country flag emoji
 * 
 * @param countryCode - ISO country code (e.g., 'US', 'GB')
 * @returns Flag emoji string
 */
export function getCountryFlag(countryCode: string): string {
  const flagEmojis: Record<string, string> = {
    US: '🇺🇸',
    GB: '🇬🇧',
    DE: '🇩🇪',
    FR: '🇫🇷',
    JP: '🇯🇵',
    CN: '🇨🇳',
    CA: '🇨🇦',
    AU: '🇦🇺',
    IN: '🇮🇳',
    BR: '🇧🇷',
    MX: '🇲🇽',
    IT: '🇮🇹',
    ES: '🇪🇸',
    NL: '🇳🇱',
    SE: '🇸🇪',
    CH: '🇨🇭',
    AT: '🇦🇹',
    BE: '🇧🇪',
    DK: '🇩🇰',
    NO: '🇳🇴',
    FI: '🇫🇮',
    PL: '🇵🇱',
    KR: '🇰🇷',
    SG: '🇸🇬',
    HK: '🇭🇰',
    TW: '🇹🇼',
  };

  return flagEmojis[countryCode.toUpperCase()] || '🏳️';
}

// ============================================================================
// Crypto Prices (CoinGecko - Free Tier)
// ============================================================================

/**
 * Get cryptocurrency prices
 * Free tier: No API key required, but has rate limits
 * 
 * @param coins - Array of coin IDs (default: ['bitcoin', 'ethereum'])
 * @param vsCurrency - Currency to compare against (default: 'usd')
 * @returns Object with coin prices
 */
export async function getCryptoPrices(
  coins: string[] = ['bitcoin', 'ethereum'],
  vsCurrency: string = 'usd'
): Promise<Record<string, Record<string, number>>> {
  try {
    const ids = coins.join(',');
    const response = await fetch(
      `https://api.coingecko.com/api/v3/simple/price?ids=${ids}&vs_currencies=${vsCurrency}`
    );

    if (!response.ok) {
      throw new Error(`Crypto API returned ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.warn('Crypto API error:', error);
    // Return fallback prices
    const fallback: Record<string, Record<string, number>> = {};
    coins.forEach((coin) => {
      fallback[coin] = { [vsCurrency]: coin === 'bitcoin' ? 45000 : 3000 };
    });
    return fallback;
  }
}

// ============================================================================
// Utility: Cache Management
// ============================================================================

const cache = new Map<string, { data: unknown; timestamp: number; ttl: number }>();

/**
 * Cache API response with TTL
 * 
 * @param key - Cache key
 * @param data - Data to cache
 * @param ttl - Time to live in milliseconds (default: 1 hour)
 */
export function setCache(key: string, data: unknown, ttl: number = 3600000): void {
  cache.set(key, {
    data,
    timestamp: Date.now(),
    ttl,
  });
}

/**
 * Get cached data if still valid
 * 
 * @param key - Cache key
 * @returns Cached data or null if expired/not found
 */
export function getCache<T>(key: string): T | null {
  const cached = cache.get(key);
  if (!cached) return null;

  const age = Date.now() - cached.timestamp;
  if (age > cached.ttl) {
    cache.delete(key);
    return null;
  }

  return cached.data as T;
}

/**
 * Clear all cache
 */
export function clearCache(): void {
  cache.clear();
}

// ============================================================================
// Cached API Wrappers
// ============================================================================

/**
 * Get exchange rates with caching (1 hour TTL)
 */
export async function getCachedExchangeRates(
  baseCurrency: string = 'USD'
): Promise<ExchangeRate> {
  const cacheKey = `exchange_rates_${baseCurrency}`;
  const cached = getCache<ExchangeRate>(cacheKey);
  
  if (cached) {
    return cached;
  }

  const rates = await getExchangeRates(baseCurrency);
  setCache(cacheKey, rates, 3600000); // 1 hour cache
  return rates;
}

/**
 * Get user location with caching (24 hour TTL)
 */
export async function getCachedUserLocation(): Promise<GeolocationData> {
  const cacheKey = 'user_location';
  const cached = getCache<GeolocationData>(cacheKey);
  
  if (cached) {
    return cached;
  }

  const location = await getUserLocation();
  setCache(cacheKey, location, 86400000); // 24 hour cache
  return location;
}

