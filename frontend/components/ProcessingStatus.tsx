'use client'

import { useEffect, useState } from 'react'
import { Square, Check } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ProcessingStatusProps {
  jobId: string
  onComplete: (data: any) => void
  onError: (error: string) => void
}

const STEPS = [
  { id: 'upload', label: 'VIDEO INGESTION', threshold: 0 },
  { id: 'poses', label: 'POSE EXTRACTION', threshold: 10 },
  { id: 'tracking', label: 'MOVEMENT TRACKING', threshold: 50 },
  { id: 'metrics', label: 'METRIC CALCULATION', threshold: 70 },
  { id: 'video', label: 'VIDEO ANNOTATION', threshold: 85 },
  { id: 'feedback', label: 'FEEDBACK GENERATION', threshold: 95 },
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
          const resultResponse = await fetch(`${API_URL}/job/${jobId}/result`)
          const resultData = await resultResponse.json()
          onComplete({
            jobId,
            metrics: resultData.metrics,
            formattedMetrics: resultData.formatted_metrics,
            feedback: resultData.feedback,
            videoUrl: `${API_URL}${resultData.video_url}`,
            cleanVideoUrl: `${API_URL}${resultData.clean_video_url}`,
          })
        } else if (data.status === 'failed') {
          clearInterval(interval)
          onError(data.error || 'Processing failed')
        }
      } catch (err) {
        console.error('Poll error:', err)
      }
    }

    pollStatus()
    interval = setInterval(pollStatus, 2000)

    return () => clearInterval(interval)
  }, [jobId, onComplete, onError])

  const currentStepIndex = STEPS.findIndex(
    (step, i) => progress < (STEPS[i + 1]?.threshold ?? 100)
  )

  return (
    <div className="max-w-2xl mx-auto animate-slide-up">
      <div className="relative p-12 border-4 border-current"
           style={{ 
             clipPath: 'polygon(0 0, calc(100% - 24px) 0, 100% 24px, 100% 100%, 24px 100%, 0 calc(100% - 24px))',
             background: 'linear-gradient(135deg, rgba(255, 255, 0, 0.02) 0%, transparent 100%)'
           }}>
        
        <div className="flex justify-center mb-12">
          <div className="relative">
            <svg className="w-48 h-48 transform -rotate-90">
              <circle
                cx="96"
                cy="96"
                r="88"
                className="fill-none stroke-current opacity-10"
                strokeWidth="3"
              />
              <circle
                cx="96"
                cy="96"
                r="88"
                className="fill-none stroke-[rgb(var(--neon-yellow))] transition-all duration-700 ease-out"
                strokeWidth="3"
                strokeDasharray={`${(progress / 100) * 553} 553`}
                strokeLinecap="square"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <div className="font-display text-6xl mb-1" 
                   style={{
                     background: 'linear-gradient(135deg, rgb(var(--neon-yellow)) 0%, rgb(var(--neon-pink)) 100%)',
                     WebkitBackgroundClip: 'text',
                     WebkitTextFillColor: 'transparent',
                     backgroundClip: 'text'
                   }}>
                {progress}
              </div>
              <div className="text-[10px] tracking-widest opacity-40">PERCENT</div>
            </div>
            
            <div className="absolute top-0 left-0 w-3 h-3 bg-[rgb(var(--neon-yellow))] animate-pulse-neon" />
            <div className="absolute bottom-0 right-0 w-3 h-3 bg-[rgb(var(--neon-pink))]" />
          </div>
        </div>

        <div className="space-y-1 mb-8">
          {STEPS.map((step, index) => {
            const isComplete = progress >= (STEPS[index + 1]?.threshold ?? 100)
            const isCurrent = index === currentStepIndex

            return (
              <div
                key={step.id}
                className={`flex items-center gap-4 p-3 transition-all duration-300 ${
                  isCurrent ? 'translate-x-2' : ''
                }`}
                style={{
                  opacity: index > currentStepIndex ? 0.3 : 1,
                  borderLeft: isCurrent ? '3px solid rgb(var(--neon-yellow))' : '3px solid transparent'
                }}
              >
                <div className="w-5 h-5 flex items-center justify-center flex-shrink-0">
                  {isComplete ? (
                    <div className="w-4 h-4 bg-[rgb(var(--neon-green))]" />
                  ) : isCurrent ? (
                    <div className="w-4 h-4 border-2 border-[rgb(var(--neon-yellow))] animate-pulse" />
                  ) : (
                    <div className="w-3 h-3 border border-current opacity-30" />
                  )}
                </div>
                <span className={`font-display text-sm tracking-wider ${
                  isCurrent ? 'text-[rgb(var(--neon-yellow))]' : ''
                }`}>
                  {step.label}
                </span>
              </div>
            )
          })}
        </div>

        <div className="flex items-center justify-center gap-4 pt-6 border-t border-current opacity-30">
          <div className="h-px w-12 bg-current" />
          <p className="text-[10px] tracking-widest">
            ESTIMATED TIME: 30-60 SECONDS
          </p>
          <div className="h-px w-12 bg-current" />
        </div>
      </div>
    </div>
  )
}
