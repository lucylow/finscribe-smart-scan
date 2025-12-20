import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Check, X, Star } from "lucide-react";
import { useState } from "react";

const plans = [
  {
    name: "Starter",
    price: "$49",
    period: "/month",
    description: "Perfect for freelancers and small businesses",
    features: [
      { text: "500 documents/month", included: true },
      { text: "Invoice & Receipt processing", included: true },
      { text: "JSON & CSV output", included: true },
      { text: "Web interface", included: true },
      { text: "API access", included: false },
      { text: "Purchase orders", included: false },
      { text: "Priority support", included: false },
    ],
    popular: false,
    cta: "Get Started",
  },
  {
    name: "Professional",
    price: "$199",
    period: "/month",
    description: "For growing businesses and accounting firms",
    features: [
      { text: "5,000 documents/month", included: true },
      { text: "All document types", included: true },
      { text: "JSON, CSV & Excel output", included: true },
      { text: "Web interface + API", included: true },
      { text: "Batch processing", included: true },
      { text: "Multi-currency", included: true },
      { text: "Priority support", included: false },
    ],
    popular: true,
    cta: "Start Free Trial",
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "For large organizations with advanced needs",
    features: [
      { text: "Unlimited documents", included: true },
      { text: "All document types + custom", included: true },
      { text: "All output formats", included: true },
      { text: "Full API access", included: true },
      { text: "On-premise deployment", included: true },
      { text: "Custom model training", included: true },
      { text: "24/7 Priority support", included: true },
    ],
    popular: false,
    cta: "Contact Sales",
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
    },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 40 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5 },
  },
};

const Pricing = () => {
  const [hoveredPlan, setHoveredPlan] = useState<string | null>(null);

  return (
    <section id="pricing" className="section-padding">
      <div className="container-custom">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-4">
            Simple, Transparent Pricing
          </h2>
          <p className="text-center text-muted-foreground mb-16 max-w-2xl mx-auto">
            Choose the plan that fits your needs. All plans include our core AI extraction technology.
          </p>
        </motion.div>

        <motion.div
          className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto"
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-50px" }}
        >
          {plans.map((plan) => (
            <motion.div
              key={plan.name}
              variants={cardVariants}
              whileHover={{ 
                y: -10,
                transition: { duration: 0.2 }
              }}
              onHoverStart={() => setHoveredPlan(plan.name)}
              onHoverEnd={() => setHoveredPlan(null)}
              className={`bg-card rounded-2xl p-8 shadow-card transition-all duration-300 relative ${
                plan.popular
                  ? "border-t-4 border-secondary md:scale-105 z-10"
                  : ""
              } ${hoveredPlan === plan.name ? "shadow-card-hover" : ""}`}
            >
              {plan.popular && (
                <motion.div
                  className="absolute -top-4 left-1/2 -translate-x-1/2 bg-secondary text-secondary-foreground px-4 py-1 rounded-full text-sm font-semibold flex items-center gap-1"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.3, type: "spring" }}
                >
                  <Star className="w-3 h-3" />
                  Most Popular
                </motion.div>
              )}

              <h3 className="text-xl font-bold text-center mb-2">{plan.name}</h3>
              
              <motion.div 
                className="text-center mb-4"
                animate={hoveredPlan === plan.name ? { scale: 1.05 } : { scale: 1 }}
              >
                <span className="text-4xl font-extrabold">{plan.price}</span>
                <span className="text-muted-foreground">{plan.period}</span>
              </motion.div>
              
              <p className="text-center text-muted-foreground text-sm mb-8">
                {plan.description}
              </p>

              <ul className="space-y-4 mb-8">
                {plan.features.map((feature, idx) => (
                  <motion.li
                    key={feature.text}
                    className="flex items-center gap-3"
                    initial={{ opacity: 0, x: -10 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: idx * 0.05 }}
                  >
                    {feature.included ? (
                      <motion.div
                        whileHover={{ scale: 1.2 }}
                        className="w-5 h-5 rounded-full bg-secondary/20 flex items-center justify-center"
                      >
                        <Check className="w-3 h-3 text-secondary" />
                      </motion.div>
                    ) : (
                      <X className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                    )}
                    <span className={feature.included ? "" : "text-muted-foreground"}>
                      {feature.text}
                    </span>
                  </motion.li>
                ))}
              </ul>

              <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                <Button
                  variant={plan.popular ? "default" : "outline"}
                  className="w-full"
                  asChild
                >
                  <a href="#cta">{plan.cta}</a>
                </Button>
              </motion.div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
};

export default Pricing;
