import { useCallback, useSyncExternalStore } from 'react'

const THEME_KEY = 'aos-theme'

export type ThemeChoice = 'light' | 'dark' | 'system'

function currentChoice(): ThemeChoice {
  const stamped = document.documentElement.dataset.theme
  return stamped === 'light' || stamped === 'dark' ? stamped : 'system'
}

function effectiveIsDark(): boolean {
  const choice = currentChoice()
  if (choice !== 'system') return choice === 'dark'
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

let listeners: Array<() => void> = []

function notify() {
  listeners.forEach((listener) => listener())
}

function subscribe(listener: () => void) {
  listeners.push(listener)
  const media = window.matchMedia('(prefers-color-scheme: dark)')
  media.addEventListener('change', listener)
  return () => {
    listeners = listeners.filter((item) => item !== listener)
    media.removeEventListener('change', listener)
  }
}

/** Theme with three states: light, dark, or follow the system. The saved
 *  choice is applied before first paint by an inline script in index.html. */
export function useTheme() {
  const isDark = useSyncExternalStore(subscribe, effectiveIsDark)
  const theme = useSyncExternalStore(subscribe, currentChoice)

  const setTheme = useCallback((choice: ThemeChoice) => {
    if (choice === 'system') {
      delete document.documentElement.dataset.theme
    } else {
      document.documentElement.dataset.theme = choice
    }
    try {
      if (choice === 'system') localStorage.removeItem(THEME_KEY)
      else localStorage.setItem(THEME_KEY, choice)
    } catch {
      /* private mode — theme resets next visit */
    }
    notify()
  }, [])

  const toggleTheme = useCallback(() => {
    setTheme(effectiveIsDark() ? 'light' : 'dark')
  }, [setTheme])

  return { theme, isDark, setTheme, toggleTheme }
}
