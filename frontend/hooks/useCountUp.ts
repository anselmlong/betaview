import { useEffect, useState } from 'react'

// Eases a number from 0 to `target` once, after `delayMs`. Jumps straight
// to the target when the user prefers reduced motion.
export function useCountUp(target: number, durationMs = 900, delayMs = 0): number {
  const [value, setValue] = useState(0)

  useEffect(() => {
    if (
      typeof window === 'undefined' ||
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    ) {
      setValue(target)
      return
    }

    let frame = 0
    let start: number | null = null
    const timeout = setTimeout(() => {
      const tick = (now: number) => {
        start ??= now
        const t = Math.min((now - start) / durationMs, 1)
        const eased = t === 1 ? 1 : 1 - Math.pow(2, -10 * t)
        setValue(target * eased)
        if (t < 1) frame = requestAnimationFrame(tick)
      }
      frame = requestAnimationFrame(tick)
    }, delayMs)

    return () => {
      clearTimeout(timeout)
      cancelAnimationFrame(frame)
    }
  }, [target, durationMs, delayMs])

  return value
}
