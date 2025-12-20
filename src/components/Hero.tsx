import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { ArrowRight, Sparkles, CheckCircle, Play, FileText, Zap, Shield, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";

const stats = [
  { value: "99.2%", label: "Accuracy", icon: TrendingUp },
  { value: "2.3s", label: "Per Document", icon: Zap },
  { value: "50K+", label: "Documents/Day", icon: FileText },
];

const Hero = () => {
  return (
    <section id="home" className="gradient-hero pt-32 pb-24 relative overflow-hidden">
      {/* Animated grid background */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,hsl(var(--primary)/0.03)_1px,transparent_1px),linear-gradient(to_bottom,hsl(var(--primary)/0.03)_1px,transparent_1px)] bg-[size:4rem_4rem]" />
      
      {/* Animated background blobs */}
      <motion.div
        className="absolute top-20 right-0 w-[700px] h-[700px] bg-gradient-to-br from-secondary/20 to-primary/10 rounded-full blur-3xl"
        animate={{
          x: [0, 50, 0],
          y: [0, -30, 0],
          scale: [1, 1.1, 1],
        }}
        transition={{
          duration: 10,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
      <motion.div
        className="absolute -bottom-20 -left-20 w-[500px] h-[500px] bg-gradient-to-tr from-primary/10 to-secondary/5 rounded-full blur-3xl"
        animate={{
          x: [0, -30, 0],
          y: [0, 50, 0],
        }}
        transition={{
          duration: 12,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
      
      <div className="container-custom relative z-10">
        <div className="flex flex-col lg:flex-row items-center gap-16">
          <motion.div
            className="flex-1 text-center lg:text-left"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <motion.div
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 text-primary text-sm font-medium mb-6"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 }}
              whileHover={{ scale: 1.05, backgroundColor: "hsl(var(--primary) / 0.15)" }}
            >
              <Sparkles className="w-4 h-4" />
              Powered by PaddleOCR-VL & ERNIE 5
            </motion.div>
            
            <motion.h1
              className="text-4xl md:text-5xl lg:text-6xl font-extrabold leading-[1.1] mb-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              Transform Financial
              <br />
              Documents with{" "}
              <span className="text-gradient">AI Magic</span>
            </motion.h1>
            
            <motion.p
              className="text-xl md:text-2xl text-muted-foreground italic mb-4 font-light"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
            >
              From Paper to Perfect Data.
            </motion.p>
            
            <motion.p
              className="text-lg text-foreground/60 mb-8 max-w-xl mx-auto lg:mx-0"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              Extract structured data from invoices, receipts, and statements 
              with 99%+ accuracy in seconds—not hours.
            </motion.p>
            
            <motion.div
              className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start mb-10"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
            >
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button asChild size="lg" className="shadow-btn group">
                  <Link to="/app">
                    Start Free Trial
                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                  </Link>
                </Button>
              </motion.div>
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button variant="outline" size="lg" asChild className="group">
                  <a href="#demo">
                    <Play className="w-4 h-4 mr-2 group-hover:scale-110 transition-transform" />
                    See How It Works
                  </a>
                </Button>
              </motion.div>
            </motion.div>

            {/* Trust badges */}
            <motion.div
              className="flex flex-wrap items-center gap-4 justify-center lg:justify-start"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.8 }}
            >
              {[
                "No credit card required",
                "14-day free trial",
                "SOC 2 Certified"
              ].map((text, i) => (
                <div key={text} className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <CheckCircle className="w-4 h-4 text-secondary" />
                  {text}
                </div>
              ))}
            </motion.div>
          </motion.div>
          
          <motion.div
            className="flex-1 flex justify-center w-full"
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
          >
            <div className="relative w-full max-w-lg">
              {/* Main image with glass effect */}
              <motion.div
                className="relative rounded-2xl overflow-hidden shadow-2xl border border-white/10"
                whileHover={{ scale: 1.02 }}
                transition={{ duration: 0.4 }}
              >
                <div className="absolute inset-0 bg-gradient-to-tr from-primary/20 to-secondary/20 mix-blend-overlay z-10" />
                <img
                  src="https://images.unsplash.com/photo-1551288049-bebda4e38f71?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
                  alt="FinScribe AI Dashboard"
                  className="w-full h-auto"
                />
              </motion.div>
              
              {/* Stats cards */}
              <motion.div
                className="absolute -bottom-6 -left-6 glass-card p-4 rounded-xl shadow-card flex items-center gap-3"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.9 }}
                whileHover={{ scale: 1.05, y: -5 }}
              >
                <div className="w-12 h-12 bg-gradient-to-br from-secondary to-secondary/70 rounded-xl flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-white" />
                </div>
                <div>
                  <p className="font-bold text-lg">99.2%</p>
                  <p className="text-xs text-muted-foreground">Accuracy Rate</p>
                </div>
              </motion.div>

              <motion.div
                className="absolute -top-4 -right-4 glass-card px-4 py-3 rounded-xl shadow-card"
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 1, type: "spring" }}
                whileHover={{ scale: 1.05 }}
              >
                <div className="flex items-center gap-2">
                  <motion.div 
                    className="w-2.5 h-2.5 bg-secondary rounded-full"
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  />
                  <span className="text-sm font-medium">AI Processing Live</span>
                </div>
              </motion.div>

              <motion.div
                className="absolute top-1/2 -right-8 glass-card p-3 rounded-xl shadow-card"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 1.1 }}
                whileHover={{ scale: 1.05, x: 5 }}
              >
                <div className="flex items-center gap-2">
                  <Shield className="w-5 h-5 text-primary" />
                  <span className="text-xs font-medium">Bank-Level<br/>Security</span>
                </div>
              </motion.div>
            </div>
          </motion.div>
        </div>

        {/* Bottom stats bar */}
        <motion.div
          className="mt-20 grid grid-cols-3 gap-4 max-w-2xl mx-auto"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.2 }}
        >
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              className="text-center p-4 rounded-xl bg-card/50 backdrop-blur-sm border border-border/50"
              whileHover={{ y: -5, backgroundColor: "hsl(var(--card))" }}
            >
              <stat.icon className="w-5 h-5 mx-auto mb-2 text-primary" />
              <p className="text-2xl font-bold">{stat.value}</p>
              <p className="text-xs text-muted-foreground">{stat.label}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
};

export default Hero;
