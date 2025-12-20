import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { ArrowRight, Sparkles, CheckCircle, Zap, Shield, Clock } from "lucide-react";
import { Link } from "react-router-dom";

const benefits = [
  { icon: Zap, text: "Instant setup, no coding required" },
  { icon: Shield, text: "Bank-level security & compliance" },
  { icon: Clock, text: "24/7 priority support" },
];

const CTA = () => {
  return (
    <section id="cta" className="section-padding relative overflow-hidden">
      {/* Gradient Background */}
      <div className="absolute inset-0 gradient-primary" />
      
      {/* Animated decorative elements */}
      <motion.div
        className="absolute top-20 left-10 w-64 h-64 bg-white/5 rounded-full blur-3xl"
        animate={{ 
          scale: [1, 1.2, 1],
          opacity: [0.3, 0.5, 0.3]
        }}
        transition={{ duration: 6, repeat: Infinity }}
      />
      <motion.div
        className="absolute bottom-10 right-20 w-80 h-80 bg-secondary/10 rounded-full blur-3xl"
        animate={{ 
          scale: [1.2, 1, 1.2],
          opacity: [0.4, 0.6, 0.4]
        }}
        transition={{ duration: 8, repeat: Infinity }}
      />
      
      <div className="container-custom relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center text-primary-foreground"
        >
          <motion.div
            initial={{ scale: 0 }}
            whileInView={{ scale: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2, type: "spring" }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 backdrop-blur-sm text-sm font-medium mb-6"
          >
            <Sparkles className="w-4 h-4" />
            Limited Time Offer: 30% off first year
          </motion.div>
          
          <h2 className="text-3xl md:text-5xl font-bold mb-6 leading-tight">
            Ready to Transform Your
            <br />
            <span className="text-secondary">Document Processing?</span>
          </h2>
          
          <p className="text-xl opacity-90 mb-8 max-w-2xl mx-auto">
            Join thousands of businesses automating their financial workflows. 
            Start your free trial today—no credit card required.
          </p>

          {/* Benefits */}
          <motion.div 
            className="flex flex-wrap justify-center gap-6 mb-10"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            {benefits.map((benefit, index) => (
              <motion.div
                key={benefit.text}
                className="flex items-center gap-2 text-sm opacity-90"
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.4 + index * 0.1 }}
              >
                <div className="w-6 h-6 rounded-full bg-secondary/20 flex items-center justify-center">
                  <benefit.icon className="w-3 h-3" />
                </div>
                {benefit.text}
              </motion.div>
            ))}
          </motion.div>

          <motion.div 
            className="flex flex-col sm:flex-row gap-4 justify-center"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.5 }}
          >
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Button variant="hero" size="lg" asChild className="group shadow-xl">
                <Link to="/app">
                  Start 14-Day Free Trial
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Link>
              </Button>
            </motion.div>
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Button variant="heroOutline" size="lg" className="backdrop-blur-sm">
                Schedule a Demo
              </Button>
            </motion.div>
          </motion.div>

          <motion.p 
            className="mt-10 opacity-80 text-sm"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 0.8 }}
            viewport={{ once: true }}
            transition={{ delay: 0.7 }}
          >
            Trusted by 2,500+ companies worldwide • SOC 2 Type II Certified
          </motion.p>
        </motion.div>
      </div>
    </section>
  );
};

export default CTA;
