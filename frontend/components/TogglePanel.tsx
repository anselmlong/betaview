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
      className="absolute top-4 right-4 z-10 p-3 border-2 border-current bg-[rgb(var(--concrete))] space-y-2"
      style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px))' }}
    >
      <div className="text-[10px] tracking-widest opacity-60 uppercase mb-2 font-display">
        Overlays
      </div>
      {toggleOptions.map(({ key, label, icon }) => {
        const isEnabled = config[key]
        return (
          <button
            key={key}
            onClick={() => handleToggle(key)}
            className={`flex items-center gap-2 w-full text-left text-xs transition-all duration-200 px-2 py-1.5 ${
              isEnabled
                ? 'opacity-100 bg-[rgb(var(--neon-yellow))] text-[rgb(var(--concrete))]'
                : 'opacity-60 hover:opacity-100'
            }`}
          >
            {isEnabled ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
            {icon}
            <span className="uppercase tracking-wider">{label}</span>
          </button>
        )
      })}
    </div>
  )
}
