import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { usePoseData } from '@/hooks/usePoseData'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('usePoseData', () => {
  beforeEach(() => {
    mockFetch.mockClear()
  })

  it('returns null when jobId is null', () => {
    const { result } = renderHook(() => usePoseData(null))

    expect(result.current.poseData).toBeNull()
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('fetches pose data when jobId is provided', async () => {
    const mockData = {
      fps: 30,
      width: 1920,
      height: 1080,
      frames: [
        {
          frame_id: 0,
          timestamp: 0,
          keypoints: {
            left_shoulder: [100, 200, 0.9],
          },
        },
      ],
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockData),
    })

    const { result } = renderHook(() => usePoseData('test-job-id'))

    expect(result.current.loading).toBe(true)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.poseData).toEqual(mockData)
    expect(result.current.error).toBeNull()
  })

  it('handles 404 error', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
    })

    const { result } = renderHook(() => usePoseData('test-job-id'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.poseData).toBeNull()
    expect(result.current.error).toBe('Pose data not found')
  })

  it('handles 400 error (job not completed)', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
    })

    const { result } = renderHook(() => usePoseData('test-job-id'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.poseData).toBeNull()
    expect(result.current.error).toBe('Job not yet completed')
  })
})
