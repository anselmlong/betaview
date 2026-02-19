'use client'

import { useState } from 'react'
import { TrendingUp, Target, Timer, Mountain } from 'lucide-react'
import VideoUpload from '@/components/VideoUpload'
import AnalysisResults from '@/components/AnalysisResults'
import ProcessingStatus from '@/components/ProcessingStatus'

type AppState = 'upload' | 'processing' | 'results'

interface AnalysisData {
  jobId: string
  metrics: any
  formattedMetrics: any
  feedback: string
  videoUrl: string
  cleanVideoUrl: string
}

export default function Home() {
  const [state, setState] = useState<AppState>('upload')
  const [jobId, setJobId] = useState<string | null>(null)
  const [analysisData, setAnalysisData] = useState<AnalysisData | null>(null)

  const handleUploadComplete = (id: string) => {
    setJobId(id)
    setState('processing')
  }

  const handleProcessingComplete = (data: AnalysisData) => {
    setAnalysisData(data)
    setState('results')
  }

  const handleReset = () => {
    setJobId(null)
    setAnalysisData(null)
    setState('upload')
  }

  return (
    <div className="relative min-h-screen">
      <div className="container mx-auto px-6 py-12 max-w-6xl relative z-10">
        <header className="mb-16 animate-slide-up">
          <div className="flex items-baseline gap-4 mb-3">
            <div className="w-3 h-3 bg-[rgb(var(--neon-yellow))] rotate-45" 
                 style={{ animationDelay: '0.1s' }} />
            <h1 className="font-display text-7xl md:text-8xl tracking-tight" 
                style={{ 
                  background: 'linear-gradient(135deg, rgb(var(--neon-yellow)) 0%, rgb(var(--neon-pink)) 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text'
                }}>
              BETAVIEW
            </h1>
          </div>
          <div className="flex items-center gap-3 ml-7">
            <div className="h-px w-12 bg-[rgb(var(--neon-yellow))]" />
            <p className="text-sm tracking-widest opacity-60 uppercase">
              Computer Vision Technique Analysis
            </p>
          </div>
        </header>

        <div className="space-y-12">
          {state === 'upload' && (
            <>
              <div className="animate-slide-up" style={{ animationDelay: '0.2s' }}>
                <VideoUpload onUploadComplete={handleUploadComplete} />
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 animate-slide-up" 
                   style={{ animationDelay: '0.4s' }}>
                <FeatureCard
                  icon={<TrendingUp className="w-8 h-8" />}
                  number="01"
                  title="Path Efficiency"
                  description="Hip trajectory analysis"
                  delay="0.5s"
                />
                <FeatureCard
                  icon={<Target className="w-8 h-8" />}
                  number="02"
                  title="Foot Precision"
                  description="Micro-adjustment detection"
                  delay="0.6s"
                />
                <FeatureCard
                  icon={<Timer className="w-8 h-8" />}
                  number="03"
                  title="Movement Rhythm"
                  description="Tempo pattern metrics"
                  delay="0.7s"
                />
              </div>

              <div className="flex items-center gap-4 pt-8 opacity-40 animate-slide-up" 
                   style={{ animationDelay: '0.8s' }}>
                <Mountain className="w-4 h-4" />
                <div className="h-px flex-1 bg-current opacity-20" />
                <p className="text-xs tracking-widest uppercase">
                  Upload • Analyze • Improve
                </p>
                <div className="h-px flex-1 bg-current opacity-20" />
              </div>
            </>
          )}

          {state === 'processing' && jobId && (
            <ProcessingStatus
              jobId={jobId}
              onComplete={handleProcessingComplete}
              onError={(error) => {
                alert(error)
                handleReset()
              }}
            />
          )}

          {state === 'results' && analysisData && (
            <AnalysisResults
              data={analysisData}
              onReset={handleReset}
            />
          )}
        </div>

        <footer className="mt-24 pt-8 border-t border-chalk/10 text-center opacity-40">
          <p className="text-xs tracking-wider uppercase mb-1">
            Video Auto-Deletion After 24 Hours
          </p>
          <p className="text-[10px] tracking-widest opacity-60">
            POSE ESTIMATION × MEDIAPIPE × HEURISTIC ANALYSIS
          </p>
        </footer>
      </div>

      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 opacity-20">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="w-2 h-2 border border-current" />
        ))}
      </div>
    </div>
  )
}

function FeatureCard({ 
  icon, 
  number, 
  title, 
  description,
  delay 
}: { 
  icon: React.ReactNode
  number: string
  title: string
  description: string
  delay: string
}) {
  return (
    <div className="metric-card group animate-slide-in-right" style={{ animationDelay: delay }}>
      <div className="flex items-start justify-between mb-4">
        <span className="font-display text-5xl opacity-10 leading-none">
          {number}
        </span>
        <div className="text-[rgb(var(--neon-yellow))] transition-transform group-hover:scale-110">
          {icon}
        </div>
      </div>
      <h3 className="font-display text-xl mb-2 tracking-wide">
        {title}
      </h3>
      <p className="text-xs opacity-60 tracking-wide uppercase">
        {description}
      </p>
    </div>
  )
}
