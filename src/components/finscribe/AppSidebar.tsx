import React from 'react';
import { motion } from 'framer-motion';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { 
  FileText, 
  Target, 
  Clock, 
  TrendingUp,
  Upload,
  GitCompare,
  Wrench,
  BarChart3,
  Rocket,
  Sparkles,
  Home,
  Settings,
  HelpCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface AppSidebarProps {
  activeMode: string;
}

const navigationItems = [
  { id: 'upload', label: 'Upload & Analyze', icon: Upload, description: 'Process documents' },
  { id: 'compare', label: 'Compare Models', icon: GitCompare, description: 'Fine-tuned vs Baseline' },
  { id: 'features', label: 'Features Demo', icon: Wrench, description: 'Interactive demos' },
  { id: 'metrics', label: 'Performance', icon: BarChart3, description: 'Analytics dashboard' },
  { id: 'api', label: 'API Playground', icon: Rocket, description: 'Test endpoints' },
];

const quickStats = [
  { label: 'Processed', value: '1,247', change: '+128', icon: FileText },
  { label: 'Accuracy', value: '94.2%', change: '+3.1%', icon: Target },
  { label: 'Avg Time', value: '1.3s', change: '-0.2s', icon: Clock },
  { label: 'Success', value: '98.5%', change: '+1.2%', icon: TrendingUp },
];

function AppSidebar({ activeMode }: AppSidebarProps) {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <motion.aside
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="w-64 h-full bg-card border-r flex flex-col"
    >
      {/* Logo */}
      <div className="p-4 border-b">
        <Link to="/" className="flex items-center gap-3 group">
          <motion.div 
            className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center"
            whileHover={{ scale: 1.05 }}
          >
            <Sparkles className="w-5 h-5 text-primary-foreground" />
          </motion.div>
          <div>
            <h1 className="text-lg font-bold tracking-tight">
              Fin<span className="text-primary">Scribe</span>
            </h1>
            <p className="text-xs text-muted-foreground">AI Document Analyzer</p>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        <p className="text-xs font-medium text-muted-foreground px-3 py-2">Navigation</p>
        {navigationItems.map((item) => {
          const isActive = activeMode === item.id;
          return (
            <motion.button
              key={item.id}
              onClick={() => navigate(`/app/${item.id}`)}
              whileHover={{ x: 2 }}
              whileTap={{ scale: 0.98 }}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors",
                isActive
                  ? "bg-primary/10 text-primary border border-primary/20"
                  : "hover:bg-muted text-muted-foreground hover:text-foreground"
              )}
            >
              <item.icon className={cn(
                "w-4 h-4 flex-shrink-0",
                isActive ? "text-primary" : ""
              )} />
              <div className="min-w-0">
                <p className={cn(
                  "text-sm font-medium truncate",
                  isActive ? "text-primary" : ""
                )}>
                  {item.label}
                </p>
                <p className="text-xs text-muted-foreground truncate">{item.description}</p>
              </div>
            </motion.button>
          );
        })}

        <Separator className="my-4" />

        <p className="text-xs font-medium text-muted-foreground px-3 py-2">Quick Links</p>
        <Link
          to="/"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
        >
          <Home className="w-4 h-4" />
          <span className="text-sm">Home</span>
        </Link>
        <a
          href="/#features"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
        >
          <Settings className="w-4 h-4" />
          <span className="text-sm">Features</span>
        </a>
        <a
          href="/#faq"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
        >
          <HelpCircle className="w-4 h-4" />
          <span className="text-sm">FAQ</span>
        </a>
      </nav>

      {/* Quick Stats */}
      <div className="p-4 border-t bg-muted/30">
        <p className="text-xs font-medium text-muted-foreground mb-3">Quick Stats</p>
        <div className="grid grid-cols-2 gap-2">
          {quickStats.map((stat) => (
            <div 
              key={stat.label}
              className="p-2 bg-card rounded-lg border"
            >
              <div className="flex items-center gap-1.5 mb-1">
                <stat.icon className="w-3 h-3 text-primary" />
                <span className="text-xs text-muted-foreground">{stat.label}</span>
              </div>
              <p className="text-sm font-bold">{stat.value}</p>
              <Badge className="mt-1 text-[10px] bg-success/20 text-success border-0 px-1 py-0">
                {stat.change}
              </Badge>
            </div>
          ))}
        </div>
      </div>

      {/* Technical Specs */}
      <div className="p-4 border-t">
        <p className="text-xs font-medium text-muted-foreground mb-2">Technical Specs</p>
        <div className="bg-muted/50 rounded-lg p-3 font-mono text-xs space-y-1">
          <p><span className="text-muted-foreground">OCR:</span> PaddleOCR-VL-0.9B</p>
          <p><span className="text-muted-foreground">VLM:</span> ERNIE 5 / ERNIE 4.5</p>
          <p><span className="text-muted-foreground">Languages:</span> 109 supported</p>
          <p><span className="text-muted-foreground">API:</span> REST + Polling</p>
        </div>
      </div>
    </motion.aside>
  );
}

export default AppSidebar;
