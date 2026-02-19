'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, Film, AlertCircle, Play } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface VideoUploadProps {
  onUploadComplete: (jobId: string) => void
}

export default function VideoUpload({ onUploadComplete }: VideoUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    setError(null)
    setUploading(true)

    try {
      const formData = new FormData()
      formData.append('file', file)

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
  }, [onUploadComplete])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.mov', '.avi', '.webm']
    },
    maxFiles: 1,
    maxSize: 100 * 1024 * 1024,
    disabled: uploading,
  })

  return (
    <div className="space-y-6">
      <div
        {...getRootProps()}
        className={`upload-zone cursor-pointer relative overflow-hidden ${
          isDragActive ? 'active' : ''
        } ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
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
            <div className="relative group">
              <div className="w-24 h-24 border-4 border-dashed border-current flex items-center justify-center transition-all duration-300 group-hover:border-[rgb(var(--neon-yellow))]"
                   style={{ clipPath: 'polygon(20% 0%, 80% 0%, 100% 20%, 100% 80%, 80% 100%, 20% 100%, 0% 80%, 0% 20%)' }}>
                {isDragActive ? (
                  <Film className="w-10 h-10 text-[rgb(var(--neon-pink))]" />
                ) : (
                  <Upload className="w-10 h-10 text-[rgb(var(--neon-yellow))] transition-transform group-hover:scale-110" />
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
              <p className="text-[10px] tracking-widest opacity-40 uppercase">
                MP4 / MOV / AVI / WEBM • Max 100MB
              </p>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="relative border-2 border-[rgb(var(--safety-red))] p-4 animate-slide-up"
             style={{ 
               background: 'rgba(220, 38, 38, 0.1)',
               clipPath: 'polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px))'
             }}>
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-[rgb(var(--safety-red))] flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-display text-sm tracking-wide text-[rgb(var(--safety-red))] mb-1">
                UPLOAD ERROR
              </p>
              <p className="text-xs opacity-80">{error}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
