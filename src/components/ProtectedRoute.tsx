import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Skeleton } from '@/components/ui/skeleton';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAuth?: boolean;
  redirectTo?: string;
}

/**
 * ProtectedRoute component that handles authentication-based routing
 * 
 * @param requireAuth - If true, redirects to login if not authenticated
 * @param redirectTo - Where to redirect if authentication check fails
 */
export function ProtectedRoute({
  children,
  requireAuth = true,
  redirectTo = '/auth',
}: ProtectedRouteProps) {
  const { user, loading } = useAuth();
  const location = useLocation();

  // Show loading skeleton while checking auth
  if (loading) {
    return (
      <div className="min-h-screen p-6 space-y-6">
        <Skeleton className="h-12 w-64" />
        <div className="space-y-4">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-3/4" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  // If auth is required and user is not authenticated, redirect to login
  if (requireAuth && !user) {
    return <Navigate to={redirectTo} state={{ from: location }} replace />;
  }

  // If auth should not be present (like login page) and user is authenticated, redirect to app
  if (!requireAuth && user) {
    return <Navigate to="/app" replace />;
  }

  return <>{children}</>;
}


