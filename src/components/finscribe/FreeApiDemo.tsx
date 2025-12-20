/**
 * Free APIs Demo Component
 * 
 * Demonstrates how to use the free external APIs integrated into FinScribe
 */

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  useOCR,
  useExchangeRates,
  useQRCode,
  useTranslation,
  useMockInvoice,
  useGeolocation,
  useCryptoPrices,
} from '@/hooks/useFreeApis';
import {
  FileText,
  DollarSign,
  QrCode,
  Languages,
  Receipt,
  MapPin,
  Coins,
  Loader2,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';

export default function FreeApiDemo() {
  return (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold mb-2">
          Free APIs <span className="text-gradient">Integration Demo</span>
        </h2>
        <p className="text-muted-foreground">
          Explore free external APIs that don't require API keys
        </p>
      </div>

      <Tabs defaultValue="ocr" className="w-full">
        <TabsList className="grid w-full grid-cols-4 lg:grid-cols-7">
          <TabsTrigger value="ocr">OCR</TabsTrigger>
          <TabsTrigger value="currency">Currency</TabsTrigger>
          <TabsTrigger value="qr">QR Code</TabsTrigger>
          <TabsTrigger value="translate">Translate</TabsTrigger>
          <TabsTrigger value="invoice">Mock Invoice</TabsTrigger>
          <TabsTrigger value="location">Location</TabsTrigger>
          <TabsTrigger value="crypto">Crypto</TabsTrigger>
        </TabsList>

        <TabsContent value="ocr" className="space-y-4">
          <OCRDemo />
        </TabsContent>

        <TabsContent value="currency" className="space-y-4">
          <CurrencyDemo />
        </TabsContent>

        <TabsContent value="qr" className="space-y-4">
          <QRCodeDemo />
        </TabsContent>

        <TabsContent value="translate" className="space-y-4">
          <TranslationDemo />
        </TabsContent>

        <TabsContent value="invoice" className="space-y-4">
          <MockInvoiceDemo />
        </TabsContent>

        <TabsContent value="location" className="space-y-4">
          <LocationDemo />
        </TabsContent>

        <TabsContent value="crypto" className="space-y-4">
          <CryptoDemo />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// OCR Demo Component
function OCRDemo() {
  const { extractText, loading, error, result } = useOCR();
  const [file, setFile] = useState<File | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const handleExtract = async () => {
    if (file) {
      await extractText(file);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="w-5 h-5" />
          OCR Text Extraction
        </CardTitle>
        <CardDescription>
          Extract text from images using OCR.space (Free: 25k requests/month)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="ocr-file">Upload Image</Label>
          <Input
            id="ocr-file"
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            disabled={loading}
          />
        </div>

        <Button onClick={handleExtract} disabled={!file || loading}>
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Extracting...
            </>
          ) : (
            'Extract Text'
          )}
        </Button>

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {result && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <span className="text-sm font-medium">Extracted Text:</span>
            </div>
            <pre className="p-4 bg-muted rounded-md text-sm overflow-auto max-h-64">
              {result.text}
            </pre>
            {result.confidence && (
              <Badge variant="outline">
                Confidence: {(result.confidence * 100).toFixed(1)}%
              </Badge>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Currency Demo Component
function CurrencyDemo() {
  const { rates, loading, convert } = useExchangeRates('USD');
  const [amount, setAmount] = useState('100');
  const [from, setFrom] = useState('USD');
  const [to, setTo] = useState('EUR');
  const [conversion, setConversion] = useState<{ amount: number; from: string; to: string; result: number; rate: number } | null>(null);
  const [converting, setConverting] = useState(false);

  const handleConvert = async () => {
    setConverting(true);
    try {
      const result = await convert(parseFloat(amount), from, to);
      setConversion(result);
    } catch (err) {
      console.error('Conversion error:', err);
    } finally {
      setConverting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <DollarSign className="w-5 h-5" />
          Currency Exchange Rates
        </CardTitle>
        <CardDescription>
          Real-time exchange rates (Free API, no key required)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading ? (
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Loading exchange rates...</span>
          </div>
        ) : rates ? (
          <>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Amount</Label>
                <Input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>From</Label>
                <select
                  className="w-full h-10 px-3 rounded-md border border-input bg-background"
                  value={from}
                  onChange={(e) => setFrom(e.target.value)}
                >
                  {Object.keys(rates.rates).map((curr) => (
                    <option key={curr} value={curr}>
                      {curr}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>To</Label>
              <select
                className="w-full h-10 px-3 rounded-md border border-input bg-background"
                value={to}
                onChange={(e) => setTo(e.target.value)}
              >
                {Object.keys(rates.rates).map((curr) => (
                  <option key={curr} value={curr}>
                    {curr}
                  </option>
                ))}
              </select>
            </div>

            <Button onClick={handleConvert} disabled={converting}>
              {converting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Converting...
                </>
              ) : (
                'Convert'
              )}
            </Button>

            {conversion && (
              <div className="p-4 bg-muted rounded-md">
                <p className="text-2xl font-bold">
                  {conversion.from} {conversion.amount} = {conversion.to}{' '}
                  {conversion.converted}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  Rate: 1 {conversion.from} = {conversion.rate} {conversion.to}
                </p>
              </div>
            )}

            <div className="mt-4">
              <Label>Available Currencies:</Label>
              <div className="flex flex-wrap gap-2 mt-2">
                {Object.keys(rates.rates).slice(0, 10).map((curr) => (
                  <Badge key={curr} variant="outline">
                    {curr}: {rates.rates[curr].toFixed(4)}
                  </Badge>
                ))}
              </div>
            </div>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}

// QR Code Demo Component
function QRCodeDemo() {
  const { generate, dataUrl, loading } = useQRCode();
  const [input, setInput] = useState('https://finscribe.com/invoice/12345');

  const handleGenerate = async () => {
    await generate(input);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <QrCode className="w-5 h-5" />
          QR Code Generator
        </CardTitle>
        <CardDescription>
          Generate QR codes for invoices, links, or any text (Client-side)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Data to Encode</Label>
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Enter text or URL"
          />
        </div>

        <Button onClick={handleGenerate} disabled={loading || !input}>
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Generating...
            </>
          ) : (
            'Generate QR Code'
          )}
        </Button>

        {dataUrl && (
          <div className="flex flex-col items-center gap-4">
            <img
              src={dataUrl}
              alt="QR Code"
              className="border rounded-lg p-4 bg-white"
            />
            <Button
              variant="outline"
              onClick={() => {
                const link = document.createElement('a');
                link.href = dataUrl;
                link.download = 'qrcode.png';
                link.click();
              }}
            >
              Download QR Code
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Translation Demo Component
function TranslationDemo() {
  const { translate, loading, result } = useTranslation();
  const [text, setText] = useState('Invoice number: INV-2024-001');
  const [targetLang, setTargetLang] = useState('es');

  const handleTranslate = async () => {
    await translate(text, targetLang, 'en');
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Languages className="w-5 h-5" />
          Text Translation
        </CardTitle>
        <CardDescription>
          Translate invoice text to multiple languages (Free: 10k words/day)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Text to Translate</Label>
          <Input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Enter text in English"
          />
        </div>

        <div className="space-y-2">
          <Label>Target Language</Label>
          <select
            className="w-full h-10 px-3 rounded-md border border-input bg-background"
            value={targetLang}
            onChange={(e) => setTargetLang(e.target.value)}
          >
            <option value="es">Spanish</option>
            <option value="fr">French</option>
            <option value="de">German</option>
            <option value="it">Italian</option>
            <option value="pt">Portuguese</option>
            <option value="ja">Japanese</option>
            <option value="zh">Chinese</option>
          </select>
        </div>

        <Button onClick={handleTranslate} disabled={loading || !text}>
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Translating...
            </>
          ) : (
            'Translate'
          )}
        </Button>

        {result && (
          <div className="space-y-2">
            <div>
              <Label className="text-xs text-muted-foreground">Original:</Label>
              <p className="p-2 bg-muted rounded-md">{result.original}</p>
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Translated:</Label>
              <p className="p-2 bg-muted rounded-md font-medium">
                {result.translated}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Mock Invoice Demo Component
function MockInvoiceDemo() {
  const { invoice, generate } = useMockInvoice();

  if (!invoice) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Receipt className="w-5 h-5" />
          Mock Invoice Generator
        </CardTitle>
        <CardDescription>
          Generate realistic mock invoice data for testing
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label className="text-xs text-muted-foreground">Invoice ID</Label>
            <p className="font-medium">{invoice.invoice_id}</p>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Date</Label>
            <p className="font-medium">{invoice.date}</p>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Vendor</Label>
            <p className="font-medium">{invoice.vendor.name}</p>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Total Amount</Label>
            <p className="font-medium text-lg">
              {invoice.currency} {invoice.amount.toFixed(2)}
            </p>
          </div>
        </div>

        <div>
          <Label className="text-xs text-muted-foreground">Items</Label>
          <div className="mt-2 space-y-2">
            {invoice.items.map((item, i) => (
              <div
                key={i}
                className="flex justify-between p-2 bg-muted rounded-md"
              >
                <span>{item.description}</span>
                <span className="font-medium">
                  {item.quantity}x {invoice.currency} {item.price.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>

        <Button onClick={generate} variant="outline">
          Generate New Invoice
        </Button>
      </CardContent>
    </Card>
  );
}

// Location Demo Component
function LocationDemo() {
  const { location, loading, flag } = useGeolocation();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MapPin className="w-5 h-5" />
          IP Geolocation
        </CardTitle>
        <CardDescription>
          Detect user location based on IP address (Free: 1k requests/day)
        </CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Detecting location...</span>
          </div>
        ) : location ? (
          <div className="space-y-4">
            <div className="flex items-center gap-3 text-2xl">
              {flag} <span className="text-lg">{location.country_name}</span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-muted-foreground">Country Code</Label>
                <p className="font-medium">{location.country}</p>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Currency</Label>
                <p className="font-medium">{location.currency}</p>
              </div>
              {location.city && (
                <div>
                  <Label className="text-xs text-muted-foreground">City</Label>
                  <p className="font-medium">{location.city}</p>
                </div>
              )}
              {location.region && (
                <div>
                  <Label className="text-xs text-muted-foreground">Region</Label>
                  <p className="font-medium">{location.region}</p>
                </div>
              )}
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

// Crypto Demo Component
function CryptoDemo() {
  const { prices, loading } = useCryptoPrices(['bitcoin', 'ethereum'], 'usd');

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Coins className="w-5 h-5" />
          Cryptocurrency Prices
        </CardTitle>
        <CardDescription>
          Real-time cryptocurrency prices (Free API, rate-limited)
        </CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Loading prices...</span>
          </div>
        ) : prices ? (
          <div className="space-y-4">
            {Object.entries(prices).map(([coin, priceData]) => (
              <div
                key={coin}
                className="flex justify-between items-center p-4 bg-muted rounded-md"
              >
                <div>
                  <p className="font-medium capitalize">{coin}</p>
                  <p className="text-sm text-muted-foreground">
                    {Object.keys(priceData)[0].toUpperCase()}
                  </p>
                </div>
                <p className="text-2xl font-bold">
                  ${Object.values(priceData)[0].toLocaleString()}
                </p>
              </div>
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

