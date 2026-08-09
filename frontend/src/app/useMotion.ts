import { useCallback, useSyncExternalStore } from 'react'

const MOTION_KEY = 'aos-motion'

let listeners: Array<() => void> = []

function reduced(): boolean {
  return document.documentElement.dataset.motion === 'reduce'
}

function subscribe(listener: () => void) {
  listeners.push(listener)
  return () => {
    listeners = listeners.filter((item) => item !== listener)
  }
}

/** User-level reduced-motion switch, layered on top of the system
 *  prefers-reduced-motion setting (which is always honored). */
export function useMotion() {
  const reducedMotion = useSyncExternalStore(subscribe, reduced)

  const setReducedMotion = useCallback((value: boolean) => {
    if (value) document.documentElement.dataset.motion = 'reduce'
    else delete document.documentElement.dataset.motion
    try {
      if (value) localStorage.setItem(MOTION_KEY, 'reduce')
      else localStorage.removeItem(MOTION_KEY)
    } catch {
      /* private mode — resets next visit */
    }
    listeners.forEach((listener) => listener())
  }, [])

  return { reducedMotion, setReducedMotion }
}
