# Free APIs Integration Guide for FinScribe

This document explains how to use the free external APIs integrated into FinScribe. All APIs are free and don't require API keys for basic usage.

## 📦 Installation

The free APIs service requires the `qrcode` package for QR code generation:

```bash
npm install qrcode
npm install --save-dev @types/qrcode  # For TypeScript support
```

## 🚀 Quick Start

### Using React Hooks (Recommended)

The easiest way to use these APIs is through the provided React hooks:

```tsx
import { useOCR, useExchangeRates, useQRCode, useTranslation } from '@/hooks/useFreeApis';

function MyComponent() {
  // OCR Hook
  const { extractText, loading, error, result } = useOCR();
  
  // Exchange Rates Hook
  const { rates, loading: ratesLoading, convert } = useExchangeRates('USD');
  
  // QR Code Hook
  const { generate, dataUrl } = useQRCode();
  
  // Translation Hook
  const { translate, result: translation } = useTranslation();

  const handleFileUpload = async (file: File) => {
    const ocrResult = await extractText(file);
    console.log('Extracted text:', ocrResult.text);
  };

  return (
    <div>
      {/* Your component JSX */}
    </div>
  );
}
```

### Direct API Usage

You can also use the APIs directly without hooks:

```typescript
import {
  ocrImage,
  getExchangeRates,
  convertCurrency,
  generateQRCode,
  translateText,
  generateMockInvoice,
  getUserLocation,
} from '@/services/freeApis';

// OCR
const result = await ocrImage(imageFile, 'eng');
console.log(result.text);

// Exchange Rates
const rates = await getExchangeRates('USD');
console.log(rates.rates.EUR); // 0.92

// Currency Conversion
const conversion = await convertCurrency(100, 'USD', 'EUR');
console.log(conversion.converted); // 92.00

// QR Code
const qrDataUrl = await generateQRCode('https://example.com/invoice/123');
// Use qrDataUrl as src for <img> tag

// Translation
const translation = await translateText('Hello', 'es', 'en');
console.log(translation.translated); // "Hola"

// Mock Invoice
const invoice = generateMockInvoice();
console.log(invoice.invoice_id, invoice.amount);

// User Location
const location = await getUserLocation();
console.log(location.country, location.currency);
```

## 📚 Available APIs

### 1. OCR (Optical Character Recognition)

**Service:** OCR.space (Free Tier)
**Limit:** 25,000 requests/month
**No API Key Required:** Uses public free key

```tsx
import { useOCR } from '@/hooks/useFreeApis';

function DocumentUpload() {
  const { extractText, loading, error, result } = useOCR();

  const handleUpload = async (file: File) => {
    try {
      const ocrResult = await extractText(file, 'eng');
      // Use ocrResult.text
    } catch (err) {
      console.error('OCR failed:', err);
    }
  };

  return (
    <div>
      <input type="file" onChange={(e) => {
        const file = e.target.files?.[0];
        if (file) handleUpload(file);
      }} />
      {loading && <p>Extracting text...</p>}
      {error && <p>Error: {error}</p>}
      {result && <pre>{result.text}</pre>}
    </div>
  );
}
```

### 2. Exchange Rates

**Service:** ExchangeRate-API
**Limit:** No strict limit, but rate-limited
**No API Key Required**

```tsx
import { useExchangeRates } from '@/hooks/useFreeApis';

function CurrencyConverter() {
  const { rates, loading, convert } = useExchangeRates('USD');

  const handleConvert = async () => {
    const conversion = await convert(100, 'USD', 'EUR');
    console.log(`$100 USD = €${conversion.converted} EUR`);
  };

  if (loading) return <p>Loading rates...</p>;
  if (!rates) return null;

  return (
    <div>
      <h3>Exchange Rates (Base: {rates.base})</h3>
      <ul>
        {Object.entries(rates.rates).map(([currency, rate]) => (
          <li key={currency}>{currency}: {rate}</li>
        ))}
      </ul>
      <button onClick={handleConvert}>Convert $100 to EUR</button>
    </div>
  );
}
```

### 3. QR Code Generation

**Service:** Client-side (qrcode library)
**No API Key Required**

```tsx
import { useQRCode } from '@/hooks/useFreeApis';

function InvoiceQRCode({ invoiceId }: { invoiceId: string }) {
  const { generate, dataUrl, loading } = useQRCode();

  useEffect(() => {
    generate(`https://finscribe.com/invoice/${invoiceId}`);
  }, [invoiceId, generate]);

  if (loading) return <p>Generating QR code...</p>;
  if (!dataUrl) return null;

  return <img src={dataUrl} alt="Invoice QR Code" />;
}
```

### 4. Translation

**Service:** MyMemory Translation API
**Limit:** 10,000 words/day
**No API Key Required**

```tsx
import { useTranslation } from '@/hooks/useFreeApis';

function InvoiceTranslator({ text }: { text: string }) {
  const { translate, loading, result } = useTranslation();
  const [targetLang, setTargetLang] = useState('es');

  const handleTranslate = async () => {
    await translate(text, targetLang, 'en');
  };

  return (
    <div>
      <select value={targetLang} onChange={(e) => setTargetLang(e.target.value)}>
        <option value="es">Spanish</option>
        <option value="fr">French</option>
        <option value="de">German</option>
      </select>
      <button onClick={handleTranslate} disabled={loading}>
        Translate
      </button>
      {result && <p>{result.translated}</p>}
    </div>
  );
}
```

### 5. Mock Invoice Generation

**Service:** Local generation (no API)
**No API Key Required**

```tsx
import { useMockInvoice } from '@/hooks/useFreeApis';

function MockInvoiceDemo() {
  const { invoice, generate } = useMockInvoice();

  if (!invoice) return <p>Loading...</p>;

  return (
    <div>
      <h3>Mock Invoice: {invoice.invoice_id}</h3>
      <p>Vendor: {invoice.vendor.name}</p>
      <p>Amount: {invoice.currency} {invoice.amount}</p>
      <p>Date: {invoice.date}</p>
      <ul>
        {invoice.items.map((item, i) => (
          <li key={i}>
            {item.description} - {item.quantity}x ${item.price}
          </li>
        ))}
      </ul>
      <button onClick={generate}>Generate New Invoice</button>
    </div>
  );
}
```

### 6. Geolocation

**Service:** ipapi.co
**Limit:** 1,000 requests/day (free tier)
**No API Key Required**

```tsx
import { useGeolocation } from '@/hooks/useFreeApis';

function LocationDisplay() {
  const { location, loading, flag } = useGeolocation();

  if (loading) return <p>Detecting location...</p>;
  if (!location) return null;

  return (
    <div>
      <p>{flag} {location.country_name}</p>
      <p>Currency: {location.currency}</p>
      {location.city && <p>City: {location.city}</p>}
    </div>
  );
}
```

### 7. Cryptocurrency Prices

**Service:** CoinGecko API
**Limit:** Rate-limited (no API key needed)
**No API Key Required**

```tsx
import { useCryptoPrices } from '@/hooks/useFreeApis';

function CryptoPrices() {
  const { prices, loading } = useCryptoPrices(['bitcoin', 'ethereum'], 'usd');

  if (loading) return <p>Loading prices...</p>;
  if (!prices) return null;

  return (
    <div>
      <h3>Cryptocurrency Prices</h3>
      <p>Bitcoin: ${prices.bitcoin?.usd}</p>
      <p>Ethereum: ${prices.ethereum?.usd}</p>
    </div>
  );
}
```

## 🔧 Advanced Usage

### Caching

The service includes built-in caching for expensive operations:

```typescript
import { getCachedExchangeRates, getCachedUserLocation } from '@/services/freeApis';

// Exchange rates are cached for 1 hour
const rates = await getCachedExchangeRates('USD');

// User location is cached for 24 hours
const location = await getCachedUserLocation();
```

### Manual Cache Management

```typescript
import { setCache, getCache, clearCache } from '@/services/freeApis';

// Set cache manually
setCache('my_key', { data: 'value' }, 3600000); // 1 hour TTL

// Get cached data
const cached = getCache<MyType>('my_key');

// Clear all cache
clearCache();
```

### Error Handling

All APIs include fallback mechanisms. If an API fails, they return mock/default data:

```typescript
import { ocrImage } from '@/services/freeApis';

try {
  const result = await ocrImage(file);
  // Use result.text
} catch (error) {
  // API failed, but result still contains fallback mock data
  console.warn('OCR API failed, using fallback:', error);
}
```

## 🎯 Integration Examples

### Example 1: Invoice Upload with OCR

```tsx
import { useOCR, useQRCode } from '@/hooks/useFreeApis';
import { useState } from 'react';

function InvoiceUpload() {
  const { extractText, loading: ocrLoading, result: ocrResult } = useOCR();
  const { generate: generateQR, dataUrl: qrCode } = useQRCode();
  const [invoiceData, setInvoiceData] = useState(null);

  const handleFileUpload = async (file: File) => {
    const ocrResult = await extractText(file);
    // Parse OCR text into structured data
    const parsed = parseInvoiceText(ocrResult.text);
    setInvoiceData(parsed);
    
    // Generate QR code for invoice
    await generateQR(JSON.stringify(parsed));
  };

  return (
    <div>
      <input type="file" onChange={(e) => {
        const file = e.target.files?.[0];
        if (file) handleFileUpload(file);
      }} />
      
      {ocrLoading && <p>Extracting text...</p>}
      {ocrResult && <pre>{ocrResult.text}</pre>}
      {invoiceData && (
        <div>
          <h3>Invoice: {invoiceData.id}</h3>
          <p>Amount: {invoiceData.amount}</p>
          {qrCode && <img src={qrCode} alt="QR Code" />}
        </div>
      )}
    </div>
  );
}
```

### Example 2: Multi-Currency Invoice Display

```tsx
import { useExchangeRates } from '@/hooks/useFreeApis';

function MultiCurrencyInvoice({ invoice }: { invoice: Invoice }) {
  const { rates, convert } = useExchangeRates(invoice.currency);
  const [displayCurrency, setDisplayCurrency] = useState('USD');
  const [convertedAmount, setConvertedAmount] = useState(invoice.amount);

  useEffect(() => {
    if (rates && invoice.currency !== displayCurrency) {
      convert(invoice.amount, invoice.currency, displayCurrency)
        .then(result => setConvertedAmount(result.converted));
    }
  }, [invoice, displayCurrency, rates, convert]);

  return (
    <div>
      <h3>Invoice: {invoice.id}</h3>
      <p>
        Amount: {invoice.currency} {invoice.amount}
      </p>
      <select value={displayCurrency} onChange={(e) => setDisplayCurrency(e.target.value)}>
        <option value="USD">USD</option>
        <option value="EUR">EUR</option>
        <option value="GBP">GBP</option>
      </select>
      <p>
        Converted: {displayCurrency} {convertedAmount.toFixed(2)}
      </p>
    </div>
  );
}
```

## ⚠️ Rate Limits & Best Practices

1. **OCR.space**: 25,000 requests/month
   - Cache results when possible
   - Use client-side OCR (Tesseract.js) for high-volume scenarios

2. **Exchange Rates**: Rate-limited
   - Use `getCachedExchangeRates()` which caches for 1 hour
   - Don't fetch on every render

3. **Translation**: 10,000 words/day
   - Cache translations
   - Batch multiple translations when possible

4. **Geolocation**: 1,000 requests/day
   - Use `getCachedUserLocation()` which caches for 24 hours
   - Only fetch once per session

5. **General Tips**:
   - Always handle errors gracefully
   - Use React hooks for automatic cleanup
   - Implement loading states
   - Cache expensive operations
   - Use fallback data when APIs fail

## 🐛 Troubleshooting

### QR Code not generating

Make sure `qrcode` is installed:
```bash
npm install qrcode @types/qrcode
```

### API errors

All APIs have fallback mechanisms. If you see warnings in the console, the service is using mock data. This is expected behavior for demo purposes.

### TypeScript errors

Make sure you have the correct type definitions:
```bash
npm install --save-dev @types/qrcode
```

## 📝 Notes

- All APIs are free and don't require API keys for basic usage
- Some APIs have rate limits - see individual service documentation
- Fallback/mock data is provided when APIs fail
- Caching is implemented to minimize API calls
- All functions are fully typed with TypeScript

