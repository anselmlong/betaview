'use client'

import { useState, useRef } from 'react'
import { 
  Download, RotateCcw, TrendingUp, Target, 
  Timer, Activity, ChevronRight
} from 'lucide-react'
import VideoOverlay, { OverlayConfig } from '@/components/VideoOverlay'
import TogglePanel from '@/components/TogglePanel'
import { usePoseData } from '@/hooks/usePoseData'

interface AnalysisResultsProps {
  data: {
    jobId: string
    metrics: any
    formattedMetrics: any
    feedback: string
    videoUrl: string
    cleanVideoUrl: string
  }
  onReset: () => void
}

export default function AnalysisResults({ data, onReset }: AnalysisResultsProps) {
  const [showFeedback, setShowFeedback] = useState(true)
  const [overlayConfig, setOverlayConfig] = useState<OverlayConfig>({
    skeleton: true,
    bodyTension: true,
    footStability: false,
    elbowAngles: false,
    hipPath: true,
  })
  const videoRef = useRef<HTMLVideoElement>(null)
  const { formattedMetrics, feedback, videoUrl, cleanVideoUrl } = data
  const jobId = videoUrl.split('/').pop() || data.jobId
  const { poseData } = usePoseData(jobId)

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="notch [--notch:20px] relative border-4 border-current overflow-hidden animate-slide-up">
            <div className="relative w-full aspect-video bg-[rgb(var(--concrete))]">
              <video
                ref={videoRef}
                src={cleanVideoUrl}
                controls
                className="w-full h-full"
                crossOrigin="anonymous"
                preload="metadata"
                aria-label="Your climb with pose overlays"
              />
              {poseData && (
                <VideoOverlay
                  videoRef={videoRef}
                  poseData={poseData}
                  config={overlayConfig}
                  width={poseData.width}
                  height={poseData.height}
                />
              )}
            </div>
            {poseData && (
              <TogglePanel
                config={overlayConfig}
                onChange={setOverlayConfig}
              />
            )}
            <div aria-hidden="true" className="absolute top-4 left-4 flex gap-2 pointer-events-none">
              <div className="w-3 h-3 bg-[rgb(var(--safety-red))]" />
              <div className="w-3 h-3 bg-[rgb(var(--neon-yellow))]" />
              <div className="w-3 h-3 bg-[rgb(var(--neon-green))]" />
            </div>
          </div>

          <div className="metric-card animate-slide-up" style={{ animationDelay: '0.1s' }}>
            <h2>
              <button
                type="button"
                onClick={() => setShowFeedback(!showFeedback)}
                aria-expanded={showFeedback}
                aria-controls="coach-feedback"
                className="focus-inset w-full flex items-center gap-3 text-left group"
              >
                <span aria-hidden="true" className="w-8 h-8 border-2 border-[rgb(var(--neon-yellow))] flex items-center justify-center transition-colors group-hover:bg-[rgb(var(--neon-yellow))] group-hover:text-[rgb(var(--concrete))]">
                  <ChevronRight className={`w-4 h-4 transition-transform ${showFeedback ? 'rotate-90' : ''}`} />
                </span>
                <span className="font-display text-2xl tracking-wide">
                  COACH FEEDBACK
                </span>
              </button>
            </h2>
            
            {showFeedback && (
              <div id="coach-feedback" className="mt-6 space-y-4 sm:pl-11 max-w-prose animate-slide-up">
                {feedback.split('\n\n').map((paragraph, i) => (
                  <p key={i} className="text-sm leading-relaxed opacity-80">
                    {paragraph}
                  </p>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <MetricCard
            icon={<TrendingUp className="w-6 h-6" />}
            label={formattedMetrics.pathEfficiency.label}
            value={`${(formattedMetrics.pathEfficiency.value * 100).toFixed(0)}%`}
            rating={formattedMetrics.pathEfficiency.rating}
            description={formattedMetrics.pathEfficiency.description}
            delay="0.2s"
          />
          <MetricCard
            icon={<Target className="w-6 h-6" />}
            label={formattedMetrics.stability.label}
            value={`${(formattedMetrics.stability.value * 100).toFixed(0)}%`}
            rating={formattedMetrics.stability.rating}
            description={formattedMetrics.stability.description}
            delay="0.3s"
          />
          <MetricCard
            icon={<Activity className="w-6 h-6" />}
            label={formattedMetrics.bodyTension.label}
            value={`${(formattedMetrics.bodyTension.value * 100).toFixed(0)}%`}
            rating={formattedMetrics.bodyTension.rating}
            description={formattedMetrics.bodyTension.description}
            delay="0.4s"
          />
          <MetricCard
            icon={<Timer className="w-6 h-6" />}
            label="Duration"
            value={`${formattedMetrics.duration.toFixed(1)}s`}
            subtext={`${formattedMetrics.rhythm.moveCount} moves`}
            delay="0.5s"
          />
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 pt-6 animate-slide-up" style={{ animationDelay: '0.6s' }}>
        <a
          href={videoUrl}
          download={`betaview_${data.jobId}.mp4`}
          className="btn-tape focus-inset hover:border-[rgb(var(--neon-yellow))] hover:text-[rgb(var(--neon-yellow))]"
        >
          <div className="flex items-center justify-center gap-3">
            <Download aria-hidden="true" className="w-5 h-5" />
            <span className="font-display text-lg tracking-wide">DOWNLOAD VIDEO</span>
          </div>
        </a>
        <button
          type="button"
          onClick={onReset}
          className="btn-tape focus-inset hover:border-[rgb(var(--neon-pink))] hover:text-[rgb(var(--neon-pink))]"
        >
          <div className="flex items-center justify-center gap-3">
            <RotateCcw aria-hidden="true" className="w-5 h-5" />
            <span className="font-display text-lg tracking-wide">ANALYZE ANOTHER</span>
          </div>
        </button>
      </div>
    </div>
  )
}

function MetricCard({ 
  icon, 
  label, 
  value, 
  rating, 
  description,
  subtext,
  delay
}: { 
  icon: React.ReactNode
  label: string
  value: string
  rating?: string
  description?: string
  subtext?: string
  delay: string
}) {
  return (
    <div className="metric-card animate-slide-in-right" style={{ animationDelay: delay }}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-[10px] tracking-widest opacity-70 uppercase">{label}</h3>
        <div aria-hidden="true" className="text-[rgb(var(--neon-yellow))]">
          {icon}
        </div>
      </div>
      <div className="font-display text-5xl mb-3">{value}</div>
      {rating && (
        <span className={`inline-block px-3 py-1 text-xs rating-${rating}`}>
          {rating.replace('_', ' ')}
        </span>
      )}
      {subtext && (
        <p className="text-xs mt-3 opacity-70 uppercase tracking-wider">{subtext}</p>
      )}
      {description && (
        <p className="text-xs mt-4 leading-relaxed opacity-70">{description}</p>
      )}
    </div>
  )
}
