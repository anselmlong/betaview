'use client'

import { useState, useEffect, useCallback } from 'react'
import { PoseData } from '@/components/VideoOverlay'

interface UsePoseDataReturn {
  poseData: PoseData | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function usePoseData(jobId: string | null): UsePoseDataReturn {
  const [poseData, setPoseData] = useState<PoseData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchPoseData = useCallback(async () => {
    if (!jobId) {
      setPoseData(null)
      setError(null)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/job/${jobId}/pose-data`)

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Pose data not found')
        } else if (response.status === 400) {
          throw new Error('Job not yet completed')
        } else {
          throw new Error(`Failed to fetch pose data: ${response.status}`)
        }
      }

      const data = await response.json()
      setPoseData(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      setPoseData(null)
    } finally {
      setLoading(false)
    }
  }, [jobId])

  useEffect(() => {
    fetchPoseData()
  }, [fetchPoseData])

  return {
    poseData,
    loading,
    error,
    refetch: fetchPoseData,
  }
}
