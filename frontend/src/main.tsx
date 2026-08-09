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
