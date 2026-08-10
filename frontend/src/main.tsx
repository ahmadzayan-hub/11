import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './app/App'
import { StoreProvider } from './app/store'
import './shared/styles/tokens.css'
import './shared/styles/base.css'
import './shared/styles/app.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <StoreProvider>
      <App />
    </StoreProvider>
  </StrictMode>,
)

// Installable PWA: register the service worker in production builds only,
// so development and tests always see live code.
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      /* offline caching is progressive enhancement — the app works without it */
    })
  })
}
