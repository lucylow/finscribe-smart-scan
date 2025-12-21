import { toast } from 'sonner';
import { APIError, NetworkError, TimeoutError } from '@/services/api';

/**
 * Centralized error handling utility
 */
export class ErrorHandler {
  /**
   * Categorize error type for better user messaging
   */
  static categorizeError(error: unknown): {
    type: 'api' | 'network' | 'timeout' | 'validation' | 'unknown';
    message: string;
    userFriendly: string;
    shouldRetry: boolean;
  } {
    if (error instanceof APIError) {
      return {
        type: 'api',
        message: error.message,
        userFriendly: this.getUserFriendlyMessage(error),
        shouldRetry: error.statusCode ? error.statusCode >= 500 : false,
      };
    }

    if (error instanceof NetworkError) {
      return {
        type: 'network',
        message: error.message,
        userFriendly: 'Network connection error. Please check your internet connection and try again.',
        shouldRetry: true,
      };
    }

    if (error instanceof TimeoutError) {
      return {
        type: 'timeout',
        message: error.message,
        userFriendly: 'Request timed out. The operation is taking longer than expected. Please try again.',
        shouldRetry: true,
      };
    }

    if (error instanceof Error) {
      // Check for validation errors
      if (error.message.includes('validation') || error.message.includes('invalid')) {
        return {
          type: 'validation',
          message: error.message,
          userFriendly: error.message,
          shouldRetry: false,
        };
      }

      return {
        type: 'unknown',
        message: error.message,
        userFriendly: 'An unexpected error occurred. Please try again or contact support if the problem persists.',
        shouldRetry: false,
      };
    }

    return {
      type: 'unknown',
      message: 'Unknown error',
      userFriendly: 'An unexpected error occurred. Please try again.',
      shouldRetry: false,
    };
  }

  /**
   * Get user-friendly message based on API error status code
   */
  private static getUserFriendlyMessage(error: APIError): string {
    if (!error.statusCode) {
      return error.message;
    }

    switch (error.statusCode) {
      case 400:
        return 'Invalid request. Please check your input and try again.';
      case 401:
        return 'Authentication required. Please sign in and try again.';
      case 403:
        return 'You do not have permission to perform this action.';
      case 404:
        return 'The requested resource was not found.';
      case 413:
        return 'File too large. Please use a smaller file (max 50MB).';
      case 429:
        return 'Too many requests. Please wait a moment and try again.';
      case 500:
        return 'Server error. Our team has been notified. Please try again later.';
      case 502:
      case 503:
        return 'Service temporarily unavailable. Please try again in a few moments.';
      case 504:
        return 'Request timeout. The server is taking too long to respond.';
      default:
        return error.message || 'An error occurred. Please try again.';
    }
  }

  /**
   * Handle error and show appropriate toast notification
   */
  static handleError(error: unknown, options?: {
    showToast?: boolean;
    logToConsole?: boolean;
    customMessage?: string;
  }): string {
    const {
      showToast = true,
      logToConsole = true,
      customMessage,
    } = options || {};

    const categorized = this.categorizeError(error);

    if (logToConsole) {
      console.error('Error handled:', {
        type: categorized.type,
        message: categorized.message,
        error,
      });
    }

    const messageToShow = customMessage || categorized.userFriendly;

    if (showToast) {
      toast.error('Error', {
        description: messageToShow,
        duration: categorized.type === 'network' || categorized.type === 'timeout' ? 5000 : 4000,
      });
    }

    return messageToShow;
  }

  /**
   * Handle file validation errors
   */
  static validateFile(file: File, options?: {
    maxSizeMB?: number;
    allowedTypes?: string[];
  }): { valid: boolean; error?: string } {
    const { maxSizeMB = 50, allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'application/pdf'] } = options || {};

    // Check file size
    const maxSizeBytes = maxSizeMB * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      return {
        valid: false,
        error: `File size exceeds ${maxSizeMB}MB limit. Please use a smaller file.`,
      };
    }

    // Check file type
    if (!allowedTypes.includes(file.type)) {
      return {
        valid: false,
        error: `File type not supported. Please use: ${allowedTypes.map(t => t.split('/')[1]).join(', ')}.`,
      };
    }

    // Check if file is empty
    if (file.size === 0) {
      return {
        valid: false,
        error: 'File is empty. Please select a valid file.',
      };
    }

    return { valid: true };
  }

  /**
   * Check if error is retryable
   */
  static isRetryable(error: unknown): boolean {
    const categorized = this.categorizeError(error);
    return categorized.shouldRetry;
  }

  /**
   * Get retry delay in milliseconds based on attempt number
   */
  static getRetryDelay(attempt: number, baseDelay = 1000): number {
    return Math.min(baseDelay * Math.pow(2, attempt), 30000); // Max 30 seconds
  }
}


