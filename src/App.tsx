import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { toast } from "sonner";
import { lazy, Suspense } from "react";
import { ThemeProvider } from "@/components/ThemeProvider";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import ErrorBoundary from "./components/ErrorBoundary";
import { Skeleton } from "@/components/ui/skeleton";

// Lazy load pages for better performance
const Index = lazy(() => import("./pages/Index"));
const FinScribe = lazy(() => import("./pages/FinScribe"));
const Auth = lazy(() => import("./pages/Auth"));
const PricingPage = lazy(() => import("./pages/PricingPage"));
const Demo = lazy(() => import("./pages/Demo"));
const NotFound = lazy(() => import("./pages/NotFound"));

// Configure QueryClient with error handling
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error: unknown) => {
        // Don't retry on 4xx errors (client errors)
        const errorObj = error as { statusCode?: number };
        if (errorObj?.statusCode && errorObj.statusCode >= 400 && errorObj.statusCode < 500) {
          return false;
        }
        // Retry up to 2 times for other errors
        return failureCount < 2;
      },
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      staleTime: 5 * 60 * 1000, // 5 minutes
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
});

// Global error handlers
if (typeof window !== 'undefined') {
  // Handle unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    toast.error('An unexpected error occurred', {
      description: event.reason?.message || 'Please refresh the page and try again.',
    });
    // Prevent default browser error handling
    event.preventDefault();
  });

  // Handle errors (both JavaScript errors and resource loading errors)
  window.addEventListener('error', (event) => {
    // Resource loading errors have event.target but no event.error
    if (event.target && event.target !== window && !event.error) {
      const target = event.target as HTMLElement;
      console.error('Resource loading error:', {
        tag: target.tagName,
        src: (target as HTMLImageElement).src || (target as HTMLScriptElement).src,
      });
      // Don't show toast for resource errors as they're usually non-critical
      return;
    }

    // Handle general JavaScript errors (have event.error)
    if (event.error) {
      console.error('Global error:', event.error);
      // ErrorBoundary will handle React errors, this is for non-React errors
      if (!event.error?.componentStack) {
        toast.error('An unexpected error occurred', {
          description: 'Please refresh the page and try again.',
        });
      }
    }
  }, true);
}

// Loading fallback component
const PageSkeleton = () => (
  <div className="min-h-screen p-6 space-y-6">
    <Skeleton className="h-12 w-64" />
    <div className="space-y-4">
      <Skeleton className="h-8 w-full" />
      <Skeleton className="h-8 w-3/4" />
      <Skeleton className="h-64 w-full" />
    </div>
  </div>
);

const App = () => (
  <ErrorBoundary>
    <ThemeProvider defaultTheme="system" storageKey="finscribe-ui-theme">
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <TooltipProvider>
            <Toaster />
            <Sonner />
            <BrowserRouter>
              <Suspense fallback={<PageSkeleton />}>
                <Routes>
                  <Route path="/" element={<Index />} />
                  <Route path="/auth" element={<Auth />} />
                  <Route path="/pricing" element={<PricingPage />} />
                  <Route path="/demo" element={<Demo />} />
                  <Route
                    path="/app"
                    element={
                      <ProtectedRoute>
                        <Navigate to="/app/upload" replace />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/app/*"
                    element={
                      <ProtectedRoute>
                        <FinScribe />
                      </ProtectedRoute>
                    }
                  />
                  {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
                  <Route path="*" element={<NotFound />} />
                </Routes>
              </Suspense>
            </BrowserRouter>
          </TooltipProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  </ErrorBoundary>
);

export default App;
