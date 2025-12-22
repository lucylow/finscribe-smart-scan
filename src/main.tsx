import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";

// Initialize Mock Service Worker in development if enabled
async function enableMocking() {
  if (import.meta.env.VITE_USE_MOCK_API === 'true') {
    const { startMockServiceWorker } = await import('./mocks/browser');
    await startMockServiceWorker();
  }
}

// Start the app after enabling mocking
enableMocking().then(() => {
  createRoot(document.getElementById("root")!).render(<App />);
});
