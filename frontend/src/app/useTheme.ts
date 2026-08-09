import { useCallback, useSyncExternalStore } from 'react'

const THEME_KEY = 'aos-theme'

function effectiveIsDark(): boolean {
  const stored = document.documentElement.dataset.theme
  if (stored === 'dark') return true
  if (stored === 'light') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

let listeners: Array<() => void> = []

function subscribe(listener: () => void) {
  listeners.push(listener)
  const media = window.matchMedia('(prefers-color-scheme: dark)')
  media.addEventListener('change', listener)
  return () => {
    listeners = listeners.filter((item) => item !== listener)
    media.removeEventListener('change', listener)
  }
}

/** Light/dark theme with persistence. The saved choice is applied before
 *  first paint by an inline script in index.html to avoid flashing. */
export function useTheme() {
  const isDark = useSyncExternalStore(subscribe, effectiveIsDark)

  const toggleTheme = useCallback(() => {
    const next = effectiveIsDark() ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    try {
      localStorage.setItem(THEME_KEY, next)
    } catch {
      /* private mode — theme resets next visit */
    }
    listeners.forEach((listener) => listener())
  }, [])

  return { isDark, toggleTheme }
}
