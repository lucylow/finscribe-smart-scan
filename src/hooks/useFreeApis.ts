/**
 * React hooks for free API services
 * 
 * Provides easy-to-use hooks for integrating free external APIs in React components
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  ocrImage,
  getCachedExchangeRates,
  convertCurrency,
  generateQRCode,
  translateText,
  generateMockInvoice,
  getCachedUserLocation,
  getCountryFlag,
  getCryptoPrices,
  type OCRResult,
  type ExchangeRate,
  type CurrencyConversion,
  type TranslationResult,
  type MockInvoice,
  type GeolocationData,
} from '@/services/freeApis';

// ============================================================================
// OCR Hook
// ============================================================================

export function useOCR() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OCRResult | null>(null);

  const extractText = useCallback(async (imageFile: File | Blob, language: string = 'eng') => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const ocrResult = await ocrImage(imageFile, language);
      setResult(ocrResult);
      return ocrResult;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'OCR extraction failed';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    extractText,
    loading,
    error,
    result,
    reset: () => {
      setError(null);
      setResult(null);
    },
  };
}

// ============================================================================
// Exchange Rates Hook
// ============================================================================

export function useExchangeRates(baseCurrency: string = 'USD') {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rates, setRates] = useState<ExchangeRate | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchRates = async () => {
      setLoading(true);
      setError(null);

      try {
        const exchangeRates = await getCachedExchangeRates(baseCurrency);
        if (!cancelled) {
          setRates(exchangeRates);
        }
      } catch (err) {
        if (!cancelled) {
          const errorMessage = err instanceof Error ? err.message : 'Failed to fetch exchange rates';
          setError(errorMessage);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchRates();

    return () => {
      cancelled = true;
    };
  }, [baseCurrency]);

  const convert = useCallback(
    async (amount: number, from: string, to: string) => {
      try {
        return await convertCurrency(amount, from, to);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Currency conversion failed';
        throw new Error(errorMessage);
      }
    },
    []
  );

  return {
    rates,
    loading,
    error,
    convert,
    refetch: () => {
      setRates(null);
      // Trigger re-fetch by updating baseCurrency dependency
    },
  };
}

// ============================================================================
// QR Code Hook
// ============================================================================

export function useQRCode() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dataUrl, setDataUrl] = useState<string | null>(null);

  const generate = useCallback(async (data: string | object) => {
    setLoading(true);
    setError(null);
    setDataUrl(null);

    try {
      const qrDataUrl = await generateQRCode(data);
      setDataUrl(qrDataUrl);
      return qrDataUrl;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'QR code generation failed';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    generate,
    dataUrl,
    loading,
    error,
    reset: () => {
      setDataUrl(null);
      setError(null);
    },
  };
}

// ============================================================================
// Translation Hook
// ============================================================================

export function useTranslation() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TranslationResult | null>(null);

  const translate = useCallback(
    async (text: string, targetLang: string = 'es', sourceLang: string = 'en') => {
      setLoading(true);
      setError(null);
      setResult(null);

      try {
        const translation = await translateText(text, targetLang, sourceLang);
        setResult(translation);
        return translation;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Translation failed';
        setError(errorMessage);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  return {
    translate,
    loading,
    error,
    result,
    reset: () => {
      setError(null);
      setResult(null);
    },
  };
}

// ============================================================================
// Mock Invoice Hook
// ============================================================================

export function useMockInvoice() {
  const [invoice, setInvoice] = useState<MockInvoice | null>(null);

  const generate = useCallback(() => {
    const newInvoice = generateMockInvoice();
    setInvoice(newInvoice);
    return newInvoice;
  }, []);

  useEffect(() => {
    generate();
  }, [generate]);

  return {
    invoice,
    generate,
  };
}

// ============================================================================
// Geolocation Hook
// ============================================================================

export function useGeolocation() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [location, setLocation] = useState<GeolocationData | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchLocation = async () => {
      setLoading(true);
      setError(null);

      try {
        const userLocation = await getCachedUserLocation();
        if (!cancelled) {
          setLocation(userLocation);
        }
      } catch (err) {
        if (!cancelled) {
          const errorMessage = err instanceof Error ? err.message : 'Failed to fetch location';
          setError(errorMessage);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchLocation();

    return () => {
      cancelled = true;
    };
  }, []);

  const flag = location ? getCountryFlag(location.country) : null;

  return {
    location,
    loading,
    error,
    flag,
    refetch: async () => {
      setLocation(null);
      setError(null);
      setLoading(true);
      try {
        const userLocation = await getCachedUserLocation();
        setLocation(userLocation);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to fetch location';
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    },
  };
}

// ============================================================================
// Crypto Prices Hook
// ============================================================================

export function useCryptoPrices(coins: string[] = ['bitcoin', 'ethereum'], vsCurrency: string = 'usd') {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prices, setPrices] = useState<Record<string, Record<string, number>> | null>(null);

  // Memoize the coins array as a string for dependency comparison
  const coinsKey = useMemo(() => coins.join(','), [coins]);

  useEffect(() => {
    let cancelled = false;

    const fetchPrices = async () => {
      setLoading(true);
      setError(null);

      try {
        const cryptoPrices = await getCryptoPrices(coins, vsCurrency);
        if (!cancelled) {
          setPrices(cryptoPrices);
        }
      } catch (err) {
        if (!cancelled) {
          const errorMessage = err instanceof Error ? err.message : 'Failed to fetch crypto prices';
          setError(errorMessage);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchPrices();

    // Refresh every 5 minutes
    const interval = setInterval(fetchPrices, 300000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [coins, coinsKey, vsCurrency]);

  return {
    prices,
    loading,
    error,
    refetch: async () => {
      setPrices(null);
      setError(null);
      setLoading(true);
      try {
        const cryptoPrices = await getCryptoPrices(coins, vsCurrency);
        setPrices(cryptoPrices);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to fetch crypto prices';
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    },
  };
}

