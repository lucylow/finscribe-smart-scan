import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

interface ErrorFallbackProps {
  error: Error | null;
  errorInfo: ErrorInfo | null;
  onReset: () => void;
}

const ErrorFallback: React.FC<ErrorFallbackProps> = ({ error, errorInfo, onReset }) => {
  const handleGoHome = () => {
    window.location.href = '/';
  };

  const handleReload = () => {
    window.location.reload();
  };

  const handleCopyError = async () => {
    const errorText = `Error: ${error?.toString()}\n\nStack Trace:\n${errorInfo?.componentStack || 'N/A'}`;
    try {
      await navigator.clipboard.writeText(errorText);
      // You could show a toast here if needed
    } catch (err) {
      console.error('Failed to copy error:', err);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <div className="flex items-center gap-3 mb-2">
            <AlertTriangle className="h-6 w-6 text-destructive" />
            <CardTitle className="text-2xl">Something went wrong</CardTitle>
          </div>
          <CardDescription>
            An unexpected error occurred. Please try refreshing the page or contact support if the problem persists.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Error Details</AlertTitle>
              <AlertDescription className="mt-2">
                <code className="text-sm bg-muted p-2 rounded block overflow-auto max-h-32">
                  {error.toString()}
                </code>
              </AlertDescription>
            </Alert>
          )}

          {process.env.NODE_ENV === 'development' && errorInfo && (
            <Alert>
              <AlertTitle>Stack Trace</AlertTitle>
              <AlertDescription className="mt-2">
                <code className="text-xs bg-muted p-2 rounded block overflow-auto max-h-48 whitespace-pre-wrap">
                  {errorInfo.componentStack}
                </code>
              </AlertDescription>
            </Alert>
          )}

          <div className="flex flex-wrap gap-3 pt-4">
            <Button onClick={onReset} className="flex-1 min-w-[120px]">
              <RefreshCw className="w-4 h-4 mr-2" />
              Try Again
            </Button>
            <Button
              variant="outline"
              onClick={handleReload}
              className="flex-1 min-w-[120px]"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Reload Page
            </Button>
            <Button
              variant="outline"
              onClick={handleGoHome}
              className="flex-1 min-w-[120px]"
            >
              <Home className="w-4 h-4 mr-2" />
              Go Home
            </Button>
          </div>
          
          {process.env.NODE_ENV === 'development' && (
            <div className="pt-4 border-t">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopyError}
                className="w-full"
              >
                Copy Error Details
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

class ErrorBoundaryClass extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });

    // Log to error reporting service (e.g., Sentry, LogRocket, etc.)
    if (process.env.NODE_ENV === 'production') {
      // Example: logErrorToService(error, errorInfo);
      // You can integrate with services like:
      // - Sentry.captureException(error, { contexts: { react: errorInfo } });
      // - LogRocket.captureException(error);
      // - Your custom error logging service
    }

    // Try to recover from certain errors
    const errorMessage = error.message.toLowerCase();
    if (errorMessage.includes('chunk') || errorMessage.includes('loading')) {
      // This might be a code splitting issue, suggest refresh
      console.warn('Possible code splitting error detected. User may need to refresh.');
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <ErrorFallback
          error={this.state.error}
          errorInfo={this.state.errorInfo}
          onReset={this.handleReset}
        />
      );
    }

    return this.props.children;
  }
}

const ErrorBoundary: React.FC<Props> = (props) => {
  return <ErrorBoundaryClass {...props} />;
};

export default ErrorBoundary;

