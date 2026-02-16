'use client'

import { useState } from 'react'
import { Upload, Loader2, Mountain, Activity, Target, Timer } from 'lucide-react'
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
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      {/* Header */}
      <header className="text-center mb-12">
        <div className="flex items-center justify-center gap-3 mb-4">
          <Mountain className="w-10 h-10 text-brand-500" />
          <h1 className="text-4xl font-bold bg-gradient-to-r from-brand-400 to-brand-600 bg-clip-text text-transparent">
            BetaView
          </h1>
        </div>
        <p className="text-gray-400 text-lg">
          AI-powered climbing technique analysis
        </p>
      </header>

      {/* Main Content */}
      <div className="space-y-8">
        {state === 'upload' && (
          <>
            <VideoUpload onUploadComplete={handleUploadComplete} />
            
            {/* Feature highlights */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
              <FeatureCard
                icon={<Activity className="w-6 h-6" />}
                title="Path Analysis"
                description="Track your hip movement to measure climbing efficiency"
              />
              <FeatureCard
                icon={<Target className="w-6 h-6" />}
                title="Foot Precision"
                description="Detect micro-adjustments and improve silent feet"
              />
              <FeatureCard
                icon={<Timer className="w-6 h-6" />}
                title="Movement Rhythm"
                description="Analyze your tempo and pause patterns"
              />
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

      {/* Footer */}
      <footer className="mt-16 text-center text-gray-500 text-sm">
        <p>Upload a bouldering video to get technique feedback</p>
        <p className="mt-1">Videos are auto-deleted after 24 hours</p>
      </footer>
    </div>
  )
}

function FeatureCard({ icon, title, description }: { 
  icon: React.ReactNode
  title: string
  description: string 
}) {
  return (
    <div className="metric-card text-center">
      <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-brand-500/10 text-brand-500 mb-4">
        {icon}
      </div>
      <h3 className="font-semibold text-white mb-2">{title}</h3>
      <p className="text-gray-400 text-sm">{description}</p>
    </div>
  )
}
