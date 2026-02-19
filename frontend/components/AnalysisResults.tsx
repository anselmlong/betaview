'use client'

import { useState, useRef } from 'react'
import { 
  Download, RotateCcw, TrendingUp, Target, 
  Timer, Activity, ChevronRight, Play
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
          <div className="relative border-4 border-current overflow-hidden animate-slide-up"
               style={{ clipPath: 'polygon(0 0, calc(100% - 20px) 0, 100% 20px, 100% 100%, 20px 100%, 0 calc(100% - 20px))' }}>
            <div className="relative w-full aspect-video bg-[rgb(var(--concrete))]">
              <video
                ref={videoRef}
                src={cleanVideoUrl}
                controls
                className="w-full h-full"
                crossOrigin="anonymous"
                preload="metadata"
              />
              {poseData && (
                <>
                  <VideoOverlay
                    videoRef={videoRef}
                    poseData={poseData}
                    config={overlayConfig}
                    width={poseData.width}
                    height={poseData.height}
                  />
                  <TogglePanel
                    config={overlayConfig}
                    onChange={setOverlayConfig}
                  />
                </>
              )}
            </div>
            <div className="absolute top-4 left-4 flex gap-2">
              <div className="w-3 h-3 bg-[rgb(var(--safety-red))]" />
              <div className="w-3 h-3 bg-[rgb(var(--neon-yellow))]" />
              <div className="w-3 h-3 bg-[rgb(var(--neon-green))]" />
            </div>
          </div>

          <div className="metric-card animate-slide-up" style={{ animationDelay: '0.1s' }}>
            <button
              onClick={() => setShowFeedback(!showFeedback)}
              className="w-full flex items-center justify-between text-left group"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 border-2 border-[rgb(var(--neon-yellow))] flex items-center justify-center">
                  <ChevronRight className={`w-4 h-4 transition-transform ${showFeedback ? 'rotate-90' : ''}`} />
                </div>
                <h3 className="font-display text-2xl tracking-wide">
                  COACH FEEDBACK
                </h3>
              </div>
            </button>
            
            {showFeedback && (
              <div className="mt-6 space-y-4 pl-11 animate-slide-up">
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
          className="flex-1 group relative border-3 border-current p-4 transition-all duration-300 hover:translate-x-1 hover:border-[rgb(var(--neon-yellow))]"
          style={{ clipPath: 'polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px))' }}
        >
          <div className="flex items-center justify-center gap-3">
            <Download className="w-5 h-5" />
            <span className="font-display text-lg tracking-wide">DOWNLOAD VIDEO</span>
          </div>
        </a>
        <button
          onClick={onReset}
          className="flex-1 group relative border-3 border-current p-4 transition-all duration-300 hover:translate-x-1 hover:border-[rgb(var(--neon-pink))]"
          style={{ clipPath: 'polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px))' }}
        >
          <div className="flex items-center justify-center gap-3">
            <RotateCcw className="w-5 h-5" />
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
    <div className="metric-card group animate-slide-in-right" style={{ animationDelay: delay }}>
      <div className="flex items-center justify-between mb-4">
        <span className="text-[10px] tracking-widest opacity-40 uppercase">{label}</span>
        <div className="text-[rgb(var(--neon-yellow))]">
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
        <p className="text-xs mt-3 opacity-50 uppercase tracking-wider">{subtext}</p>
      )}
      
      {description && (
        <div className="absolute -right-2 top-1/2 -translate-y-1/2 translate-x-full ml-4 px-4 py-3 border-2 border-current bg-[rgb(var(--concrete))] text-xs opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-20"
             style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px))' }}>
          {description}
        </div>
      )}
    </div>
  )
}
