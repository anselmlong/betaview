'use client'

import { useCallback, useState } from 'react'
import { useDropzone, FileRejection } from 'react-dropzone'
import { Upload, Film, AlertCircle, Play } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type Personality = 'normal' | 'abusive'

const COACHES: { id: Personality; label: string; hint: string; tone: { border: string; text: string } }[] = [
  {
    id: 'normal',
    label: 'NORMAL',
    hint: 'Encouraging, direct technique notes',
    tone: { border: 'border-[rgb(var(--neon-green))]', text: 'text-[rgb(var(--neon-green))]' },
  },
  {
    id: 'abusive',
    label: 'ABUSIVE',
    hint: 'A brutal roast. Swearing included.',
    tone: { border: 'border-[rgb(var(--neon-pink))]', text: 'text-[rgb(var(--signal-pink))]' },
  },
]

interface VideoUploadProps {
  onUploadComplete: (jobId: string) => void
  initialError?: string | null
}

export default function VideoUpload({ onUploadComplete, initialError = null }: VideoUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(initialError)
  // A failure handed back from processing is not an upload problem; title it accordingly
  const [errorTitle, setErrorTitle] = useState(initialError ? 'ANALYSIS FAILED' : 'UPLOAD ERROR')
  const [personality, setPersonality] = useState<Personality>('normal')

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    setError(null)
    setErrorTitle('UPLOAD ERROR')
    setUploading(true)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('personality', personality)

      const response = await fetch(`${API_URL}/analyze`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Upload failed')
      }

      const data = await response.json()
      onUploadComplete(data.job_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }, [onUploadComplete, personality])

  const onDropRejected = useCallback((rejections: FileRejection[]) => {
    setErrorTitle('UPLOAD ERROR')
    const code = rejections[0]?.errors[0]?.code
    if (code === 'file-too-large') {
      setError('File is larger than 50MB. Trim the clip and try again.')
    } else if (code === 'file-invalid-type') {
      setError('Unsupported format. Use MP4, MOV, AVI or WEBM.')
    } else if (code === 'too-many-files') {
      setError('Drop one video at a time.')
    } else {
      setError('That file could not be used. Try another video.')
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    onDropRejected,
    accept: {
      'video/*': ['.mp4', '.mov', '.avi', '.webm']
    },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024,
    disabled: uploading,
  })

  return (
    <div className="space-y-6">
      <div
        {...getRootProps({
          role: 'button',
          'aria-label': 'Upload climbing video: drop a file or press Enter to browse',
          'aria-disabled': uploading,
          'aria-busy': uploading,
        })}
        className={`upload-zone group focus-inset cursor-pointer relative overflow-hidden ${
          isDragActive ? 'active' : ''
        } ${uploading ? 'cursor-wait' : ''}`}
      >
        <input {...getInputProps()} />
        
        {uploading ? (
          <div className="flex flex-col items-center gap-6">
            <div className="relative">
              <div className="spinner-neon" />
              <div className="absolute inset-0 flex items-center justify-center">
                <Play className="w-6 h-6 text-[rgb(var(--neon-yellow))]" />
              </div>
            </div>
            <div className="text-center">
              <p className="font-display text-2xl tracking-wide mb-1">UPLOADING</p>
              <p className="text-xs tracking-widest opacity-60">PROCESSING VIDEO FILE</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-8">
            <div className="relative">
              <div className="w-24 h-24 border-4 border-dashed border-current flex items-center justify-center transition-colors duration-300 group-hover:border-[rgb(var(--neon-yellow))] group-focus-visible:border-[rgb(var(--neon-yellow))]"
                   style={{ clipPath: 'polygon(20% 0%, 80% 0%, 100% 20%, 100% 80%, 80% 100%, 20% 100%, 0% 80%, 0% 20%)' }}>
                {isDragActive ? (
                  <Film aria-hidden="true" className="w-10 h-10 text-[rgb(var(--neon-pink))]" />
                ) : (
                  <Upload aria-hidden="true" className="w-10 h-10 text-[rgb(var(--neon-yellow))] transition-transform duration-300 group-hover:scale-110 group-focus-visible:scale-110" />
                )}
              </div>
              <div className="absolute -top-1 -left-1 w-2 h-2 bg-[rgb(var(--neon-yellow))]" />
              <div className="absolute -bottom-1 -right-1 w-2 h-2 bg-[rgb(var(--neon-pink))]" />
            </div>
            
            <div className="text-center space-y-3">
              <p className="font-display text-3xl tracking-wide">
                {isDragActive ? 'RELEASE TO UPLOAD' : 'DROP VIDEO HERE'}
              </p>
              <div className="flex items-center gap-3 justify-center">
                <div className="h-px w-8 bg-current opacity-30" />
                <p className="text-xs tracking-widest opacity-60 uppercase">
                  or click to browse
                </p>
                <div className="h-px w-8 bg-current opacity-30" />
              </div>
              <p className="text-[10px] tracking-widest opacity-60 uppercase">
                MP4 / MOV / AVI / WEBM • Max 50MB / 60s
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Coach personality toggle */}
      <div className="flex flex-col items-center gap-3">
        <div role="group" aria-labelledby="coach-label" className="flex items-center justify-center gap-3 sm:gap-4">
          <span id="coach-label" className="text-xs tracking-widest opacity-70 uppercase">Coach:</span>
          {COACHES.map(({ id, label, tone }) => {
            const isActive = personality === id
            return (
              <button
                key={id}
                type="button"
                aria-pressed={isActive}
                aria-describedby={isActive ? 'coach-hint' : undefined}
                onClick={() => setPersonality(id)}
                className={`notch [--notch:8px] focus-inset min-h-[44px] px-4 text-xs tracking-wider border-2 transition-colors duration-200 ${
                  isActive
                    ? `${tone.border} ${tone.text}`
                    : 'border-chalk/30 text-chalk/70 hover:border-chalk/60 hover:text-chalk'
                }`}
              >
                {label}
              </button>
            )
          })}
        </div>
        <p
          id="coach-hint"
          className={`text-[10px] tracking-widest uppercase ${
            personality === 'abusive' ? 'text-[rgb(var(--signal-pink))]' : 'opacity-70'
          }`}
        >
          {COACHES.find((c) => c.id === personality)?.hint}
        </p>
      </div>

      {error && (
        <div role="alert" className="notch relative border-2 border-[rgb(var(--safety-red))] bg-[rgb(var(--safety-red)/0.1)] p-4 animate-slide-up">
          <div className="flex items-start gap-3">
            <AlertCircle aria-hidden="true" className="w-5 h-5 text-[rgb(var(--signal-red))] flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-display text-sm tracking-wide text-[rgb(var(--signal-red))] mb-1">
                {errorTitle}
              </p>
              <p className="text-xs opacity-80">{error}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
