import { motion } from "framer-motion";
import { Brain, Maximize2, Globe, Zap, Shield, Puzzle } from "lucide-react";
import { useState } from "react";

const features = [
  {
    icon: Brain,
    title: "PaddleOCR-VL Powered",
    description:
      "Built on state-of-the-art vision-language models fine-tuned specifically for financial documents, ensuring superior accuracy.",
  },
  {
    icon: Maximize2,
    title: "Multi-Format Support",
    description:
      "Process invoices, receipts, purchase orders, bank statements, and tax forms with a single, unified platform.",
  },
  {
    icon: Globe,
    title: "Multi-Currency & Language",
    description:
      "Handle documents in multiple currencies and languages, making it perfect for global businesses.",
  },
  {
    icon: Zap,
    title: "Real-Time Processing",
    description:
      "Get results in seconds, not hours. Batch process thousands of documents simultaneously.",
  },
  {
    icon: Shield,
    title: "Bank-Level Security",
    description:
      "Your financial data is encrypted end-to-end with compliance for GDPR, SOC 2, and financial regulations.",
  },
  {
    icon: Puzzle,
    title: "Easy Integration",
    description:
      "REST API and pre-built connectors for QuickBooks, Xero, SAP, NetSuite, and custom systems.",
  },
];

const comparisonData = [
  { feature: "Layout Understanding", finscribe: "Advanced", basic: "Limited", manual: "Human", finscribeWin: true },
  { feature: "Table Extraction", finscribe: "Structured", basic: "Text Only", manual: "Accurate", finscribeWin: true },
  { feature: "Speed (per doc)", finscribe: "2-3 seconds", basic: "1-2 seconds", manual: "2-5 minutes", finscribeWin: true },
  { feature: "Accuracy", finscribe: "99%+", basic: "70-85%", manual: "~95%", finscribeWin: true },
  { feature: "Cost Efficiency", finscribe: "High", basic: "Medium", manual: "Low", finscribeWin: true },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

const Features = () => {
  const [hoveredFeature, setHoveredFeature] = useState<number | null>(null);

  return (
    <section id="features" className="section-padding bg-muted">
      <div className="container-custom">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-center mb-4 tracking-tight">
            Why Choose <span className="text-gradient bg-gradient-to-r from-primary via-primary to-secondary bg-clip-text text-transparent">FinScribe AI</span>
          </h2>
          <p className="text-center text-muted-foreground mb-16 max-w-2xl mx-auto text-lg leading-relaxed">
            Powerful features designed to streamline your financial document processing workflow.
          </p>
        </motion.div>

        {/* Features Grid */}
        <motion.div
          className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 mb-20"
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-50px" }}
        >
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              variants={itemVariants}
              whileHover={{ y: -12, scale: 1.03 }}
              onHoverStart={() => setHoveredFeature(index)}
              onHoverEnd={() => setHoveredFeature(null)}
              className="bg-card p-8 rounded-2xl shadow-card hover:shadow-card-hover transition-all duration-300 text-center cursor-pointer border-2 border-transparent hover:border-primary/30 relative overflow-hidden group"
            >
              {/* Animated background gradient on hover */}
              <motion.div
                className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                initial={false}
              />
              
              <motion.div
                className="w-16 h-16 mx-auto mb-6 text-primary bg-gradient-to-br from-primary/10 to-primary/5 rounded-2xl flex items-center justify-center relative z-10 shadow-sm group-hover:shadow-md transition-shadow"
                animate={hoveredFeature === index ? { 
                  rotate: [0, -10, 10, 0],
                  scale: 1.15,
                  boxShadow: "0 8px 24px hsl(var(--primary) / 0.3)"
                } : {}}
                transition={{ duration: 0.5 }}
              >
                <feature.icon className="w-8 h-8 relative z-10" />
              </motion.div>
              <h3 className="text-xl font-bold mb-4 relative z-10 group-hover:text-primary transition-colors">{feature.title}</h3>
              <p className="text-muted-foreground relative z-10 group-hover:text-foreground/80 transition-colors">{feature.description}</p>
            </motion.div>
          ))}
        </motion.div>

        {/* Comparison Table */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h3 className="text-2xl md:text-3xl font-bold text-center mb-8 tracking-tight">
            FinScribe AI vs. Traditional OCR
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full bg-card rounded-xl shadow-card overflow-hidden">
              <thead>
                <tr className="bg-primary text-primary-foreground">
                  <th className="py-4 px-6 text-left font-bold">Feature</th>
                  <th className="py-4 px-6 text-center font-bold">FinScribe AI</th>
                  <th className="py-4 px-6 text-center font-bold">Basic OCR</th>
                  <th className="py-4 px-6 text-center font-bold">Manual Entry</th>
                </tr>
              </thead>
              <tbody>
                {comparisonData.map((row, index) => (
                  <motion.tr
                    key={row.feature}
                    className={index % 2 === 0 ? "bg-muted/50" : ""}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: index * 0.1 }}
                    whileHover={{ backgroundColor: "hsl(var(--primary) / 0.05)" }}
                  >
                    <td className="py-4 px-6 font-medium">{row.feature}</td>
                    <td className="py-4 px-6 text-center">
                      <motion.span
                        className="text-secondary font-semibold inline-flex items-center gap-1"
                        whileHover={{ scale: 1.1 }}
                      >
                        ✓ {row.finscribe}
                      </motion.span>
                    </td>
                    <td className="py-4 px-6 text-center text-destructive">
                      {row.basic.includes("Limited") || row.basic.includes("70") ? "✗" : "✓"} {row.basic}
                    </td>
                    <td className="py-4 px-6 text-center">
                      {row.manual === "Low" || row.manual.includes("minute") ? (
                        <span className="text-destructive">✗ {row.manual}</span>
                      ) : (
                        <span className="text-secondary">✓ {row.manual}</span>
                      )}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default Features;
