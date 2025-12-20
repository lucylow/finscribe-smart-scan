import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

interface KeyboardShortcutsOptions {
  onUpload?: () => void;
  onAnalyze?: () => void;
  onCompare?: () => void;
  disabled?: boolean;
}

export function useKeyboardShortcuts({
  onUpload,
  onAnalyze,
  onCompare,
  disabled = false,
}: KeyboardShortcutsOptions) {
  const navigate = useNavigate();

  useEffect(() => {
    if (disabled) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      // Ignore if user is typing in an input, textarea, or contenteditable
      const target = event.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return;
      }

      // Ctrl/Cmd + K for quick navigation
      if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
        event.preventDefault();
        navigate('/app/upload');
        return;
      }

      // Ctrl/Cmd + Enter to analyze (when on upload page)
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter' && onAnalyze) {
        event.preventDefault();
        onAnalyze();
        return;
      }

      // Escape to clear selection or go back
      if (event.key === 'Escape') {
        // Could be used to clear file selection or navigate back
        if (onUpload) {
          // Only clear if we're on upload page
          const path = window.location.pathname;
          if (path.includes('/upload')) {
            // This would need to be passed as a clear function
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [navigate, onUpload, onAnalyze, onCompare, disabled]);
}

