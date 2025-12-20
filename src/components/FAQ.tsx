import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const faqs = [
  {
    question: "What makes FinScribe AI different from other OCR solutions?",
    answer:
      "FinScribe AI is built on PaddleOCR-VL, a specialized vision-language model fine-tuned specifically for financial documents. Unlike basic OCR that just extracts text, our AI understands document layout, semantics, and relationships between elements (like connecting a price to its corresponding item). This results in much higher accuracy, especially for complex documents like invoices with tables.",
  },
  {
    question: "What document formats do you support?",
    answer:
      "We support all common document formats: PDF (both scanned and digital), PNG, JPEG, TIFF, and BMP. You can upload single files or zip archives for batch processing. Our AI handles documents from various sources including scanner outputs, smartphone photos, and email attachments.",
  },
  {
    question: "How accurate is FinScribe AI?",
    answer:
      "For standard invoice fields (vendor, date, total amount), we achieve 99%+ accuracy. For complex line-item extraction from tables, accuracy ranges from 95-98% depending on document quality and complexity. You can try our free tier to see the accuracy for your specific documents.",
  },
  {
    question: "Can I integrate FinScribe AI with my existing accounting software?",
    answer:
      "Yes! We offer pre-built integrations for QuickBooks, Xero, Sage, NetSuite, and SAP. For custom systems, our comprehensive REST API allows easy integration with any software. Professional and Enterprise plans include API access and webhook support for automated workflows.",
  },
  {
    question: "Is my financial data secure with FinScribe AI?",
    answer:
      "Absolutely. We employ bank-level security with end-to-end encryption, SOC 2 compliance, and GDPR adherence. Your documents are processed in secure environments and never used for training our models without explicit permission. Enterprise plans offer on-premise deployment for maximum data control.",
  },
  {
    question: "What's included in the free trial?",
    answer:
      "Our 14-day free trial includes full access to the Professional plan features: processing up to 500 documents, all document types, API access, and multi-currency support. No credit card is required to start the trial, and you can upgrade, downgrade, or cancel at any time.",
  },
];

const FAQ = () => {
  return (
    <section id="faq" className="section-padding bg-muted">
      <div className="container-custom max-w-3xl">
        <h2 className="text-3xl md:text-4xl font-bold text-center mb-4">
          Frequently Asked Questions
        </h2>
        <p className="text-center text-muted-foreground mb-12">
          Everything you need to know about FinScribe AI.
        </p>

        <Accordion type="single" collapsible className="space-y-4">
          {faqs.map((faq, index) => (
            <AccordionItem
              key={index}
              value={`item-${index}`}
              className="bg-card rounded-xl shadow-sm border-none px-6"
            >
              <AccordionTrigger className="text-left font-semibold hover:no-underline py-5">
                {faq.question}
              </AccordionTrigger>
              <AccordionContent className="text-muted-foreground pb-5">
                {faq.answer}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
};

export default FAQ;
