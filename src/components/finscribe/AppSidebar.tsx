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
  HelpCircle,
  ChevronRight
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface AppSidebarProps {
  activeMode: string;
  onModeChange: (mode: string) => void;
}

interface NavigationItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
  shortcut?: string;
  category: 'main' | 'tools';
}

const navigationItems: NavigationItem[] = [
  { 
    id: 'upload', 
    label: 'Upload & Analyze', 
    icon: Upload, 
    description: 'Process documents',
    shortcut: '⌘U',
    category: 'main'
  },
  { 
    id: 'compare', 
    label: 'Compare Models', 
    icon: GitCompare, 
    description: 'Fine-tuned vs Baseline',
    shortcut: '⌘C',
    category: 'main'
  },
  { 
    id: 'compare-documents', 
    label: 'Compare Documents', 
    icon: FileText, 
    description: 'Quote vs Invoice',
    category: 'tools'
  },
  { 
    id: 'features', 
    label: 'Features Demo', 
    icon: Wrench, 
    description: 'Interactive demos',
    category: 'tools'
  },
  { 
    id: 'metrics', 
    label: 'Performance', 
    icon: BarChart3, 
    description: 'Analytics dashboard',
    category: 'tools'
  },
  { 
    id: 'api', 
    label: 'API Playground', 
    icon: Rocket, 
    description: 'Test endpoints',
    category: 'tools'
  },
];

const mainNavItems = navigationItems.filter(item => item.category === 'main');
const toolsNavItems = navigationItems.filter(item => item.category === 'tools');

const quickStats = [
  { label: 'Processed', value: '1,247', change: '+128', icon: FileText },
  { label: 'Accuracy', value: '94.2%', change: '+3.1%', icon: Target },
  { label: 'Avg Time', value: '1.3s', change: '-0.2s', icon: Clock },
  { label: 'Success', value: '98.5%', change: '+1.2%', icon: TrendingUp },
];

function AppSidebar({ activeMode, onModeChange }: AppSidebarProps) {
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
      <nav className="flex-1 p-3 space-y-4 overflow-y-auto [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-muted [&::-webkit-scrollbar-track]:bg-transparent hover:[&::-webkit-scrollbar-thumb]:bg-muted-foreground/30">
        {/* Main Navigation */}
        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-3 py-2 mb-1">Main</p>
          <div className="space-y-1">
            {mainNavItems.map((item) => {
              const isActive = activeMode === item.id;
              return (
                <motion.button
                  key={item.id}
                  onClick={() => {
                    onModeChange(item.id);
                    navigate(`/app/${item.id}`);
                  }}
                  whileHover={{ x: 2 }}
                  whileTap={{ scale: 0.98 }}
                  aria-label={`Navigate to ${item.label}`}
                  aria-current={isActive ? "page" : undefined}
                  className={cn(
                    "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 relative group",
                    isActive
                      ? "bg-primary/10 text-primary border border-primary/20 shadow-sm"
                      : "hover:bg-muted/80 text-muted-foreground hover:text-foreground border border-transparent"
                  )}
                >
                  <div className={cn(
                    "absolute left-0 top-1/2 -translate-y-1/2 w-1 h-0 rounded-r-full bg-primary transition-all duration-200",
                    isActive ? "h-full" : "group-hover:h-4"
                  )} />
                  <item.icon className={cn(
                    "w-4 h-4 flex-shrink-0 transition-colors",
                    isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground"
                  )} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className={cn(
                        "text-sm font-medium truncate",
                        isActive ? "text-primary" : ""
                      )}>
                        {item.label}
                      </p>
                      {item.shortcut && (
                        <kbd className="hidden lg:inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100">
                          {item.shortcut}
                        </kbd>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground truncate mt-0.5">{item.description}</p>
                  </div>
                  {isActive && (
                    <ChevronRight className="w-4 h-4 text-primary flex-shrink-0" />
                  )}
                </motion.button>
              );
            })}
          </div>
        </div>

        <Separator />

        {/* Tools Navigation */}
        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-3 py-2 mb-1">Tools</p>
          <div className="space-y-1">
            {toolsNavItems.map((item) => {
              const isActive = activeMode === item.id;
              return (
                <motion.button
                  key={item.id}
                  onClick={() => {
                    onModeChange(item.id);
                    navigate(`/app/${item.id}`);
                  }}
                  whileHover={{ x: 2 }}
                  whileTap={{ scale: 0.98 }}
                  aria-label={`Navigate to ${item.label}`}
                  aria-current={isActive ? "page" : undefined}
                  className={cn(
                    "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 relative group",
                    isActive
                      ? "bg-primary/10 text-primary border border-primary/20 shadow-sm"
                      : "hover:bg-muted/80 text-muted-foreground hover:text-foreground border border-transparent"
                  )}
                >
                  <div className={cn(
                    "absolute left-0 top-1/2 -translate-y-1/2 w-1 h-0 rounded-r-full bg-primary transition-all duration-200",
                    isActive ? "h-full" : "group-hover:h-4"
                  )} />
                  <item.icon className={cn(
                    "w-4 h-4 flex-shrink-0 transition-colors",
                    isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground"
                  )} />
                  <div className="min-w-0 flex-1">
                    <p className={cn(
                      "text-sm font-medium truncate",
                      isActive ? "text-primary" : ""
                    )}>
                      {item.label}
                    </p>
                    <p className="text-xs text-muted-foreground truncate mt-0.5">{item.description}</p>
                  </div>
                  {isActive && (
                    <ChevronRight className="w-4 h-4 text-primary flex-shrink-0" />
                  )}
                </motion.button>
              );
            })}
          </div>
        </div>

        <Separator className="my-4" />

        {/* Quick Links */}
        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-3 py-2 mb-1">Quick Links</p>
          <div className="space-y-1">
            <Link
              to="/"
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-all duration-200 group"
            >
              <Home className="w-4 h-4 group-hover:text-primary transition-colors" />
              <span className="text-sm font-medium">Home</span>
            </Link>
            <a
              href="/#features"
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-all duration-200 group"
            >
              <Settings className="w-4 h-4 group-hover:text-primary transition-colors" />
              <span className="text-sm font-medium">Features</span>
            </a>
            <a
              href="/#faq"
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-all duration-200 group"
            >
              <HelpCircle className="w-4 h-4 group-hover:text-primary transition-colors" />
              <span className="text-sm font-medium">FAQ</span>
            </a>
          </div>
        </div>
      </nav>

      {/* Quick Stats */}
      <div className="p-4 border-t bg-muted/30">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Quick Stats</p>
        <div className="grid grid-cols-2 gap-2">
          {quickStats.map((stat) => (
            <motion.div 
              key={stat.label}
              className="p-2.5 bg-card rounded-lg border hover:border-primary/20 transition-colors cursor-default"
              whileHover={{ scale: 1.02 }}
            >
              <div className="flex items-center gap-1.5 mb-1.5">
                <stat.icon className="w-3.5 h-3.5 text-primary" />
                <span className="text-xs text-muted-foreground font-medium">{stat.label}</span>
              </div>
              <p className="text-sm font-bold mb-1">{stat.value}</p>
              <Badge className="text-[10px] bg-success/20 text-success border-0 px-1.5 py-0.5 font-medium">
                {stat.change}
              </Badge>
            </motion.div>
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
