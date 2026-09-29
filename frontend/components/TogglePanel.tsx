'use client'

import { OverlayConfig } from '@/components/VideoOverlay'
import { Eye, EyeOff, Bone, Activity, Footprints, Move, GitCommit } from 'lucide-react'

interface TogglePanelProps {
  config: OverlayConfig
  onChange: (config: OverlayConfig) => void
}

const toggleOptions: { key: keyof OverlayConfig; label: string; icon: React.ReactNode }[] = [
  { key: 'skeleton', label: 'Skeleton', icon: <Bone className="w-4 h-4" /> },
  { key: 'bodyTension', label: 'Body Tension', icon: <Activity className="w-4 h-4" /> },
  { key: 'footStability', label: 'Foot Stability', icon: <Footprints className="w-4 h-4" /> },
  { key: 'elbowAngles', label: 'Elbow Angles', icon: <GitCommit className="w-4 h-4" /> },
  { key: 'hipPath', label: 'Hip Path', icon: <Move className="w-4 h-4" /> },
]

export default function TogglePanel({ config, onChange }: TogglePanelProps) {
  const handleToggle = (key: keyof OverlayConfig) => {
    onChange({
      ...config,
      [key]: !config[key],
    })
  }

  return (
    <div
      role="group"
      aria-labelledby="overlay-toggles-label"
      className="sm:notch [--notch:8px] relative sm:absolute sm:top-4 sm:right-4 z-10 p-3 border-t-4 sm:border-2 border-current bg-[rgb(var(--concrete))]"
    >
      <div
        id="overlay-toggles-label"
        className="text-xs tracking-widest opacity-70 uppercase mb-2 font-display"
      >
        Overlays
      </div>
      <div className="flex flex-wrap gap-2 sm:flex-col sm:gap-1">
        {toggleOptions.map(({ key, label, icon }) => {
          const isEnabled = config[key]
          return (
            <button
              key={key}
              type="button"
              aria-pressed={isEnabled}
              onClick={() => handleToggle(key)}
              className={`flex items-center gap-2 sm:w-full text-left text-xs transition-colors duration-200 px-3 sm:px-2 py-2.5 sm:py-1.5 border sm:border-0 ${
                isEnabled
                  ? 'bg-[rgb(var(--neon-yellow))] text-[rgb(var(--concrete))] border-[rgb(var(--neon-yellow))]'
                  : 'opacity-70 hover:opacity-100 border-chalk/30'
              }`}
            >
              <span aria-hidden="true" className="flex items-center gap-2">
                {isEnabled ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                {icon}
              </span>
              <span className="uppercase tracking-wider">{label}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
