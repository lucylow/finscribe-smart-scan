import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Code, FileText, Receipt, ClipboardList, Upload, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

const demos = {
  invoice: {
    title: "Invoice",
    icon: FileText,
    image: "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80",
    json: `{
  "document_type": "invoice",
  "vendor": "TechSupply Corp",
  "invoice_number": "INV-2023-04567",
  "date": "2023-10-15",
  "due_date": "2023-11-14",
  "line_items": [
    {
      "description": "Wireless Keyboard",
      "quantity": 5,
      "unit_price": 45.99,
      "line_total": 229.95
    }
  ],
  "subtotal": 392.45,
  "tax": 31.40,
  "total": 423.85
}`,
    description: "FinScribe AI accurately extracts all key information from complex invoices, including line items, quantities, prices, taxes, and totals.",
  },
  receipt: {
    title: "Receipt",
    icon: Receipt,
    image: "https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80",
    json: `{
  "document_type": "receipt",
  "merchant": "Urban Cafe",
  "date": "2023-10-20",
  "time": "14:30",
  "items": [
    {"description": "Cappuccino", "price": 4.50},
    {"description": "Croissant", "price": 3.25}
  ],
  "subtotal": 9.75,
  "tax": 0.78,
  "total": 12.53
}`,
    description: "From coffee shop receipts to restaurant bills, FinScribe AI captures every detail with precision.",
  },
  "purchase-order": {
    title: "Purchase Order",
    icon: ClipboardList,
    image: "https://images.unsplash.com/photo-1554224155-6726b3ff858f?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80",
    json: `{
  "document_type": "purchase_order",
  "po_number": "PO-78910",
  "supplier": "Office Supplies Ltd",
  "issue_date": "2023-10-18",
  "delivery_date": "2023-10-25",
  "line_items": [
    {
      "item_code": "OS-455",
      "description": "Paper (500 sheets)",
      "quantity": 20,
      "total": 179.80
    }
  ],
  "total_amount": 242.30
}`,
    description: "Streamline your procurement process with automatic extraction of supplier details and pricing.",
  },
};

const Demo = () => {
  const [activeTab, setActiveTab] = useState<keyof typeof demos>("invoice");
  const [isProcessing, setIsProcessing] = useState(false);
  const [showResult, setShowResult] = useState(true);

  const handleTabChange = (tab: keyof typeof demos) => {
    setShowResult(false);
    setIsProcessing(true);
    setActiveTab(tab);
    
    // Simulate processing animation
    setTimeout(() => {
      setIsProcessing(false);
      setShowResult(true);
    }, 1500);
  };

  const handleTryDemo = () => {
    setShowResult(false);
    setIsProcessing(true);
    
    setTimeout(() => {
      setIsProcessing(false);
      setShowResult(true);
    }, 2000);
  };

  return (
    <section id="demo" className="section-padding bg-muted">
      <div className="container-custom max-w-5xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-4">
            See FinScribe AI in Action
          </h2>
          <p className="text-center text-muted-foreground mb-12 max-w-2xl mx-auto">
            Watch how our AI transforms raw documents into structured, actionable data in seconds.
          </p>
        </motion.div>

        {/* Tabs */}
        <div className="flex justify-center mb-8 border-b border-border">
          {Object.entries(demos).map(([key, value]) => {
            const Icon = value.icon;
            return (
              <button
                key={key}
                onClick={() => handleTabChange(key as keyof typeof demos)}
                className={`px-6 py-4 font-semibold transition-all relative flex items-center gap-2 ${
                  activeTab === key
                    ? "text-primary"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Icon className="w-4 h-4" />
                {value.title}
                {activeTab === key && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute bottom-0 left-0 w-full h-0.5 bg-primary"
                  />
                )}
              </button>
            );
          })}
        </div>

        {/* Content */}
        <motion.div
          className="bg-card rounded-2xl p-8 shadow-card"
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
        >
          <div className="grid md:grid-cols-5 gap-8 items-center mb-6">
            {/* Document Image */}
            <div className="md:col-span-2">
              <h4 className="font-semibold mb-3 text-muted-foreground flex items-center gap-2">
                <Upload className="w-4 h-4" />
                Raw Document
              </h4>
              <motion.div
                className="relative group cursor-pointer"
                whileHover={{ scale: 1.02 }}
                onClick={handleTryDemo}
              >
                <AnimatePresence mode="wait">
                  <motion.img
                    key={activeTab}
                    src={demos[activeTab].image}
                    alt={demos[activeTab].title}
                    className="rounded-lg border border-border shadow-sm w-full"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 20 }}
                    transition={{ duration: 0.3 }}
                  />
                </AnimatePresence>
                
                {/* Hover overlay */}
                <div className="absolute inset-0 bg-primary/80 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <div className="text-primary-foreground text-center">
                    <Sparkles className="w-8 h-8 mx-auto mb-2" />
                    <p className="font-semibold">Click to Process</p>
                  </div>
                </div>
              </motion.div>
            </div>

            {/* Arrow with processing animation */}
            <div className="hidden md:flex items-center justify-center">
              <motion.div
                className={`w-16 h-16 rounded-full flex items-center justify-center ${
                  isProcessing ? "bg-primary" : "bg-secondary/20"
                }`}
                animate={isProcessing ? { 
                  scale: [1, 1.2, 1],
                  rotate: 360 
                } : {}}
                transition={{ 
                  duration: 1,
                  repeat: isProcessing ? Infinity : 0,
                  ease: "linear"
                }}
              >
                {isProcessing ? (
                  <div className="w-6 h-6 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                ) : (
                  <ArrowRight className="w-8 h-8 text-secondary" />
                )}
              </motion.div>
            </div>

            {/* JSON Output */}
            <div className="md:col-span-2">
              <h4 className="font-semibold mb-3 text-muted-foreground flex items-center gap-2">
                <Code className="w-4 h-4" />
                Structured Data Output
              </h4>
              <div className="bg-primary/5 border-l-4 border-primary rounded-lg p-4 overflow-x-auto min-h-[280px]">
                <div className="flex items-center gap-2 mb-3 text-sm font-medium text-primary">
                  <Code className="w-4 h-4" />
                  JSON Output
                </div>
                
                <AnimatePresence mode="wait">
                  {isProcessing ? (
                    <motion.div
                      key="processing"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="space-y-2"
                    >
                      {[...Array(8)].map((_, i) => (
                        <motion.div
                          key={i}
                          className="h-4 bg-primary/10 rounded"
                          initial={{ width: "0%" }}
                          animate={{ width: `${Math.random() * 50 + 50}%` }}
                          transition={{ delay: i * 0.1, duration: 0.5 }}
                        />
                      ))}
                    </motion.div>
                  ) : showResult ? (
                    <motion.pre
                      key="result"
                      className="text-xs md:text-sm text-foreground/80 whitespace-pre-wrap"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3 }}
                    >
                      <code>{demos[activeTab].json}</code>
                    </motion.pre>
                  ) : null}
                </AnimatePresence>
              </div>
            </div>
          </div>

          <motion.p
            key={activeTab}
            className="text-center text-muted-foreground"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            {demos[activeTab].description}
          </motion.p>

          {/* Try it button */}
          <div className="text-center mt-6">
            <Button onClick={handleTryDemo} variant="outline" className="gap-2">
              <Sparkles className="w-4 h-4" />
              Simulate Processing
            </Button>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default Demo;
