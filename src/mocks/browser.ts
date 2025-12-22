import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';

/**
 * Setup Mock Service Worker for browser environment
 * This should only be called in development when VITE_USE_MOCK_API is true
 */
export const worker = setupWorker(...handlers);

/**
 * Start MSW worker
 */
export async function startMockServiceWorker() {
  if (import.meta.env.VITE_USE_MOCK_API === 'true') {
    await worker.start({
      onUnhandledRequest: 'bypass', // Don't warn about unhandled requests
    });
    console.log('🔶 Mock Service Worker started');
  }
}

