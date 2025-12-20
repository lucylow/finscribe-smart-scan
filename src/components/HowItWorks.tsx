import { motion } from "framer-motion";
import { Upload, Cpu, Download } from "lucide-react";

const steps = [
  {
    number: 1,
    icon: Upload,
    title: "Upload",
    description:
      "Upload your financial documents in any format—scanned PDFs, images, or even photos from your phone. FinScribe AI handles them all with ease.",
  },
  {
    number: 2,
    icon: Cpu,
    title: "Process",
    description:
      "Our AI analyzes the document layout, recognizes text and tables, and extracts semantic meaning using specialized financial document training.",
  },
  {
    number: 3,
    icon: Download,
    title: "Utilize",
    description:
      "Get perfectly structured JSON, CSV, or Excel output ready for your accounting software, ERP system, or custom applications.",
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.2,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6 },
  },
};

const HowItWorks = () => {
  return (
    <section className="section-padding">
      <div className="container-custom">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-4">
            How FinScribe AI Works
          </h2>
          <p className="text-center text-muted-foreground mb-16 max-w-2xl mx-auto">
            Our advanced PaddleOCR-VL fine-tuned model transforms your documents in three simple steps.
          </p>
        </motion.div>

        <motion.div
          className="grid md:grid-cols-3 gap-8"
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
        >
          {steps.map((step, index) => (
            <motion.div
              key={step.number}
              variants={itemVariants}
              whileHover={{ y: -10, scale: 1.02 }}
              className="bg-card p-8 rounded-2xl shadow-card hover:shadow-card-hover transition-shadow duration-300 text-center group cursor-pointer"
            >
              <motion.div
                className="w-16 h-16 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-6"
                whileHover={{ scale: 1.1, rotate: 360 }}
                transition={{ duration: 0.5 }}
              >
                {step.number}
              </motion.div>
              <motion.div 
                className="w-12 h-12 mx-auto mb-4 text-primary"
                whileHover={{ scale: 1.2 }}
              >
                <step.icon className="w-full h-full" />
              </motion.div>
              <h3 className="text-xl font-bold mb-4">{step.title}</h3>
              <p className="text-muted-foreground">{step.description}</p>
              
              {/* Connection line for desktop */}
              {index < steps.length - 1 && (
                <div className="hidden md:block absolute top-1/2 -right-4 w-8 h-0.5 bg-border" />
              )}
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
};

export default HowItWorks;
