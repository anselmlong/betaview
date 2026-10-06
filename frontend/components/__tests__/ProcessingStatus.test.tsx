import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import ProcessingStatus from '@/components/ProcessingStatus'

const mockFetch = vi.fn()
global.fetch = mockFetch

describe('ProcessingStatus', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('reports an error and stops polling when the job no longer exists', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: 'Job not found' }),
    })
    const onError = vi.fn()

    render(<ProcessingStatus jobId="job-1" onComplete={vi.fn()} onError={onError} />)

    await waitFor(() => expect(onError).toHaveBeenCalledTimes(1))
    expect(onError.mock.calls[0][0]).toMatch(/no longer available/i)
    expect(mockFetch).toHaveBeenCalledTimes(1)
  })

  it('reports an error when the finished result cannot be loaded', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ status: 'completed', progress: 100 }),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: 'Job not found' }),
      })
    const onComplete = vi.fn()
    const onError = vi.fn()

    render(<ProcessingStatus jobId="job-1" onComplete={onComplete} onError={onError} />)

    await waitFor(() => expect(onError).toHaveBeenCalledTimes(1))
    expect(onComplete).not.toHaveBeenCalled()
  })
})
