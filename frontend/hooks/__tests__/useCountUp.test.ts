import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useCountUp } from '@/hooks/useCountUp'

describe('useCountUp', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('jumps straight to the target when reduced motion is preferred', () => {
    vi.stubGlobal('matchMedia', (query: string) => ({
      matches: query.includes('reduce'),
      media: query,
    }))

    const { result } = renderHook(() => useCountUp(0.82, 900, 500))

    expect(result.current).toBe(0.82)
  })

  it('starts from zero when motion is allowed', () => {
    vi.stubGlobal('matchMedia', (query: string) => ({ matches: false, media: query }))

    const { result } = renderHook(() => useCountUp(0.82, 900, 500))

    expect(result.current).toBe(0)
  })
})
