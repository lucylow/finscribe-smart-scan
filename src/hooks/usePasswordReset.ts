import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/hooks/use-toast';
import { handleSupabaseError } from '@/integrations/supabase/utils';

/**
 * Hook for password reset functionality
 */
export function usePasswordReset() {
  const { resetPassword, updatePassword } = useAuth();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);

  const requestPasswordReset = async (email: string) => {
    setLoading(true);
    try {
      const { error } = await resetPassword(email);
      if (error) {
        toast({
          title: 'Error',
          description: handleSupabaseError(error),
          variant: 'destructive',
        });
        return { success: false, error };
      }
      toast({
        title: 'Success',
        description: 'Password reset email sent! Check your inbox.',
      });
      return { success: true };
    } catch (error) {
      toast({
        title: 'Error',
        description: handleSupabaseError(error),
        variant: 'destructive',
      });
      return { success: false, error };
    } finally {
      setLoading(false);
    }
  };

  const changePassword = async (newPassword: string) => {
    setLoading(true);
    try {
      const { error } = await updatePassword(newPassword);
      if (error) {
        toast({
          title: 'Error',
          description: handleSupabaseError(error),
          variant: 'destructive',
        });
        return { success: false, error };
      }
      toast({
        title: 'Success',
        description: 'Password updated successfully!',
      });
      return { success: true };
    } catch (error) {
      toast({
        title: 'Error',
        description: handleSupabaseError(error),
        variant: 'destructive',
      });
      return { success: false, error };
    } finally {
      setLoading(false);
    }
  };

  return {
    requestPasswordReset,
    changePassword,
    loading,
  };
}


