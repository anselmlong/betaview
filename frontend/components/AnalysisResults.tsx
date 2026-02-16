'use client'

import { useState } from 'react'
import { 
  Download, RotateCcw, TrendingUp, Target, 
  Timer, Activity, ChevronDown, ChevronUp 
} from 'lucide-react'

interface AnalysisResultsProps {
  data: {
    jobId: string
    metrics: any
    formattedMetrics: any
    feedback: string
    videoUrl: string
  }
  onReset: () => void
}

export default function AnalysisResults({ data, onReset }: AnalysisResultsProps) {
  const [showFeedback, setShowFeedback] = useState(true)
  const { formattedMetrics, feedback, videoUrl } = data

  return (
    <div className="space-y-8">
      {/* Video Player */}
      <div className="metric-card p-0 overflow-hidden">
        <video
          src={videoUrl}
          controls
          className="w-full aspect-video bg-black"
          poster="/video-poster.png"
        />
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          icon={<TrendingUp className="w-5 h-5" />}
          label={formattedMetrics.pathEfficiency.label}
          value={`${(formattedMetrics.pathEfficiency.value * 100).toFixed(0)}%`}
          rating={formattedMetrics.pathEfficiency.rating}
          description={formattedMetrics.pathEfficiency.description}
        />
        <MetricCard
          icon={<Target className="w-5 h-5" />}
          label={formattedMetrics.stability.label}
          value={`${(formattedMetrics.stability.value * 100).toFixed(0)}%`}
          rating={formattedMetrics.stability.rating}
          description={formattedMetrics.stability.description}
        />
        <MetricCard
          icon={<Activity className="w-5 h-5" />}
          label={formattedMetrics.bodyTension.label}
          value={`${(formattedMetrics.bodyTension.value * 100).toFixed(0)}%`}
          rating={formattedMetrics.bodyTension.rating}
          description={formattedMetrics.bodyTension.description}
        />
        <MetricCard
          icon={<Timer className="w-5 h-5" />}
          label="Duration"
          value={`${formattedMetrics.duration.toFixed(1)}s`}
          subtext={`${formattedMetrics.rhythm.moveCount} moves`}
        />
      </div>

      {/* Coach Feedback */}
      <div className="metric-card">
        <button
          onClick={() => setShowFeedback(!showFeedback)}
          className="w-full flex items-center justify-between text-left"
        >
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            🧗 Coach Feedback
          </h3>
          {showFeedback ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </button>
        
        {showFeedback && (
          <div className="mt-4 prose prose-invert prose-sm max-w-none">
            {feedback.split('\n\n').map((paragraph, i) => (
              <p key={i} className="text-gray-300 leading-relaxed">
                {paragraph}
              </p>
            ))}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-4 justify-center">
        <a
          href={videoUrl}
          download={`betaview_${data.jobId}.mp4`}
          className="flex items-center justify-center gap-2 px-6 py-3 bg-brand-600 hover:bg-brand-700 text-white font-medium rounded-lg transition-colors"
        >
          <Download className="w-5 h-5" />
          Download Video
        </a>
        <button
          onClick={onReset}
          className="flex items-center justify-center gap-2 px-6 py-3 bg-gray-800 hover:bg-gray-700 text-white font-medium rounded-lg transition-colors"
        >
          <RotateCcw className="w-5 h-5" />
          Analyze Another
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
  subtext 
}: { 
  icon: React.ReactNode
  label: string
  value: string
  rating?: string
  description?: string
  subtext?: string
}) {
  return (
    <div className="metric-card group relative">
      <div className="flex items-center gap-2 text-gray-400 mb-2">
        {icon}
        <span className="text-sm">{label}</span>
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {rating && (
        <span className={`inline-block mt-2 px-2 py-0.5 text-xs font-medium rounded-full border rating-${rating}`}>
          {rating.replace('_', ' ')}
        </span>
      )}
      {subtext && (
        <span className="text-sm text-gray-500 mt-1 block">{subtext}</span>
      )}
      
      {/* Tooltip */}
      {description && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-xs text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
          {description}
        </div>
      )}
    </div>
  )
}
