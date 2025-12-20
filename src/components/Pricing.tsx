import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Check, X, Star } from "lucide-react";
import { useState } from "react";
import { startCheckout } from "@/lib/checkout";
import { toast } from "sonner";

const plans = [
  {
    name: "Free",
    tier: "free",
    price: "$0",
    period: "/month",
    description: "For trying FinScribe",
    features: [
      { text: "50 documents / month", included: true },
      { text: "Basic OCR fields", included: true },
      { text: "Web UI only", included: true },
      { text: "API access", included: false },
      { text: "CSV export", included: false },
    ],
    popular: false,
    cta: "Get Started",
    highlight: false,
  },
  {
    name: "Starter",
    tier: "starter",
    price: "$49",
    period: "/month",
    description: "For freelancers & SMBs",
    features: [
      { text: "500 documents / month", included: true },
      { text: "Full JSON & CSV export", included: true },
      { text: "API access", included: true },
      { text: "Email support", included: true },
      { text: "Batch processing", included: false },
    ],
    popular: true,
    cta: "Upgrade",
    highlight: true,
  },
  {
    name: "Pro",
    tier: "pro",
    price: "$149",
    period: "/month",
    description: "For accounting teams",
    features: [
      { text: "5,000 documents / month", included: true },
      { text: "Batch processing", included: true },
      { text: "QuickBooks + Xero sync", included: true },
      { text: "Webhooks", included: true },
      { text: "Priority support", included: true },
    ],
    popular: false,
    cta: "Go Pro",
    highlight: false,
  },
  {
    name: "Enterprise",
    tier: "enterprise",
    price: "Custom",
    period: "",
    description: "For large orgs",
    features: [
      { text: "Unlimited documents", included: true },
      { text: "Custom fields", included: true },
      { text: "On-prem / VPC deploy", included: true },
      { text: "SLA + SOC-2", included: true },
      { text: "24/7 Priority support", included: true },
    ],
    popular: false,
    cta: "Contact Sales",
    highlight: false,
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
  const [loading, setLoading] = useState<string | null>(null);

  // Get partner code from URL params
  const getPartnerCode = () => {
    const params = new URLSearchParams(window.location.search);
    return params.get("partner") || undefined;
  };

  const handleCheckout = async (planTier: string) => {
    if (planTier === "enterprise") {
      // Enterprise requires contact sales
      window.location.href = "mailto:sales@finscribe.ai?subject=Enterprise Plan Inquiry";
      return;
    }

    if (planTier === "free") {
      // Free plan - redirect to signup
      window.location.href = "/auth?plan=free";
      return;
    }

    setLoading(planTier);
    try {
      const partnerCode = getPartnerCode();
      const checkoutUrl = await startCheckout(planTier, partnerCode);
      window.location.href = checkoutUrl;
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to start checkout. Please try again."
      );
      setLoading(null);
    }
  };

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
          className="grid grid-cols-1 md:grid-cols-4 gap-6 max-w-7xl mx-auto"
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
              className={`bg-card rounded-2xl p-6 shadow-card transition-all duration-300 relative ${
                plan.highlight
                  ? "ring-2 ring-indigo-600 scale-105 z-10"
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
                {plan.price !== "Custom" && (
                  <span className="text-muted-foreground">{plan.period}</span>
                )}
              </motion.div>
              
              <p className="text-center text-muted-foreground text-sm mb-8">
                {plan.description}
              </p>

              <ul className="space-y-2 text-sm mb-8">
                {plan.features.map((feature, idx) => (
                  <motion.li
                    key={feature.text}
                    className="flex items-center gap-2"
                    initial={{ opacity: 0, x: -10 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: idx * 0.05 }}
                  >
                    {feature.included ? (
                      <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
                    ) : (
                      <X className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                    )}
                    <span className={feature.included ? "" : "text-muted-foreground"}>
                      {feature.text}
                    </span>
                  </motion.li>
                ))}
              </ul>

              <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                <Button
                  variant={plan.highlight ? "default" : "outline"}
                  className={`w-full ${
                    plan.highlight ? "bg-indigo-600 hover:bg-indigo-700" : ""
                  }`}
                  onClick={() => handleCheckout(plan.tier)}
                  disabled={loading === plan.tier}
                >
                  {loading === plan.tier ? "Loading..." : plan.cta}
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
