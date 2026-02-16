'use client'

import { useEffect, useState } from 'react'
import { Loader2, CheckCircle, XCircle } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ProcessingStatusProps {
  jobId: string
  onComplete: (data: any) => void
  onError: (error: string) => void
}

const STEPS = [
  { id: 'upload', label: 'Video uploaded', threshold: 0 },
  { id: 'poses', label: 'Extracting poses', threshold: 10 },
  { id: 'tracking', label: 'Tracking movement', threshold: 50 },
  { id: 'metrics', label: 'Calculating metrics', threshold: 70 },
  { id: 'video', label: 'Generating annotated video', threshold: 85 },
  { id: 'feedback', label: 'Creating coach feedback', threshold: 95 },
]

export default function ProcessingStatus({ jobId, onComplete, onError }: ProcessingStatusProps) {
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState('processing')

  useEffect(() => {
    let interval: NodeJS.Timeout

    const pollStatus = async () => {
      try {
        const response = await fetch(`${API_URL}/job/${jobId}`)
        const data = await response.json()

        setProgress(data.progress || 0)
        setStatus(data.status)

        if (data.status === 'completed') {
          clearInterval(interval)
          // Fetch full results
          const resultResponse = await fetch(`${API_URL}/job/${jobId}/result`)
          const resultData = await resultResponse.json()
          onComplete({
            jobId,
            metrics: resultData.metrics,
            formattedMetrics: resultData.formatted_metrics,
            feedback: resultData.feedback,
            videoUrl: `${API_URL}${resultData.video_url}`,
          })
        } else if (data.status === 'failed') {
          clearInterval(interval)
          onError(data.error || 'Processing failed')
        }
      } catch (err) {
        console.error('Poll error:', err)
      }
    }

    // Poll every 2 seconds
    pollStatus()
    interval = setInterval(pollStatus, 2000)

    return () => clearInterval(interval)
  }, [jobId, onComplete, onError])

  const currentStepIndex = STEPS.findIndex(
    (step, i) => progress < (STEPS[i + 1]?.threshold ?? 100)
  )

  return (
    <div className="max-w-md mx-auto">
      <div className="metric-card">
        {/* Progress circle */}
        <div className="flex justify-center mb-8">
          <div className="relative w-32 h-32">
            <svg className="w-full h-full transform -rotate-90">
              <circle
                cx="64"
                cy="64"
                r="56"
                className="fill-none stroke-gray-800"
                strokeWidth="8"
              />
              <circle
                cx="64"
                cy="64"
                r="56"
                className="fill-none stroke-brand-500 transition-all duration-500"
                strokeWidth="8"
                strokeDasharray={`${(progress / 100) * 352} 352`}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl font-bold text-white">{progress}%</span>
            </div>
          </div>
        </div>

        {/* Steps */}
        <div className="space-y-3">
          {STEPS.map((step, index) => {
            const isComplete = progress >= (STEPS[index + 1]?.threshold ?? 100)
            const isCurrent = index === currentStepIndex

            return (
              <div
                key={step.id}
                className={`flex items-center gap-3 transition-opacity ${
                  index > currentStepIndex ? 'opacity-40' : ''
                }`}
              >
                <div className="w-6 h-6 flex items-center justify-center">
                  {isComplete ? (
                    <CheckCircle className="w-5 h-5 text-brand-500" />
                  ) : isCurrent ? (
                    <Loader2 className="w-5 h-5 text-brand-500 animate-spin" />
                  ) : (
                    <div className="w-3 h-3 rounded-full bg-gray-700" />
                  )}
                </div>
                <span className={`text-sm ${
                  isComplete ? 'text-gray-300' : isCurrent ? 'text-white' : 'text-gray-500'
                }`}>
                  {step.label}
                </span>
              </div>
            )
          })}
        </div>

        <p className="text-center text-gray-500 text-sm mt-6">
          This usually takes 30-60 seconds
        </p>
      </div>
    </div>
  )
}
