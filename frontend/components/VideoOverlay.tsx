'use client'

import { useRef, useEffect, useCallback } from 'react'

export interface OverlayConfig {
  skeleton: boolean
  bodyTension: boolean
  footStability: boolean
  elbowAngles: boolean
  hipPath: boolean
}

export interface PoseKeypoint {
  0: number  // x
  1: number  // y
  2: number  // visibility
}

export interface PoseFrame {
  frame_id: number
  timestamp: number
  keypoints: Record<string, PoseKeypoint>
}

export interface PoseData {
  fps: number
  width: number
  height: number
  frames: PoseFrame[]
}

interface VideoOverlayProps {
  videoRef: React.RefObject<HTMLVideoElement | null>
  poseData: PoseData | null
  config: OverlayConfig
  width: number
  height: number
}

export default function VideoOverlay({
  videoRef,
  poseData,
  config,
  width,
  height,
}: VideoOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const hipHistoryRef = useRef<{ x: number; y: number }[]>([])
  const lastFrameRef = useRef<number>(-1)

  const getFrameAtTime = useCallback((currentTime: number): PoseFrame | null => {
    if (!poseData || poseData.frames.length === 0) return null

    const frameIndex = Math.min(
      Math.floor(currentTime * poseData.fps),
      poseData.frames.length - 1
    )
    return poseData.frames[Math.max(0, frameIndex)]
  }, [poseData])

  const scaleCoordinates = useCallback((x: number, y: number) => {
    if (!poseData) return { x: 0, y: 0 }
    const scaleX = width / poseData.width
    const scaleY = height / poseData.height
    return { x: x * scaleX, y: y * scaleY }
  }, [poseData, width, height])

  const drawSkeleton = useCallback((ctx: CanvasRenderingContext2D, frame: PoseFrame) => {
    const connections = [
      ['left_shoulder', 'right_shoulder'],
      ['left_shoulder', 'left_elbow'],
      ['left_elbow', 'left_wrist'],
      ['right_shoulder', 'right_elbow'],
      ['right_elbow', 'right_wrist'],
      ['left_shoulder', 'left_hip'],
      ['right_shoulder', 'right_hip'],
      ['left_hip', 'right_hip'],
      ['left_hip', 'left_knee'],
      ['left_knee', 'left_ankle'],
      ['right_hip', 'right_knee'],
      ['right_knee', 'right_ankle'],
    ] as const

    ctx.strokeStyle = '#00ff00'
    ctx.lineWidth = 2
    ctx.globalAlpha = 0.6

    for (const [startName, endName] of connections) {
      const start = frame.keypoints[startName]
      const end = frame.keypoints[endName]

      if (start && end && start[2] > 0.5 && end[2] > 0.5) {
        const startPos = scaleCoordinates(start[0], start[1])
        const endPos = scaleCoordinates(end[0], end[1])
        ctx.beginPath()
        ctx.moveTo(startPos.x, startPos.y)
        ctx.lineTo(endPos.x, endPos.y)
        ctx.stroke()
      }
    }

    // Draw keypoints
    ctx.fillStyle = '#00ff00'
    for (const [, pos] of Object.entries(frame.keypoints)) {
      if (pos[2] > 0.5) {
        const { x, y } = scaleCoordinates(pos[0], pos[1])
        ctx.beginPath()
        ctx.arc(x, y, 5, 0, Math.PI * 2)
        ctx.fill()
      }
    }

    ctx.globalAlpha = 1
  }, [scaleCoordinates])

  const drawBodyTension = useCallback((ctx: CanvasRenderingContext2D, frame: PoseFrame) => {
    const leftShoulder = frame.keypoints['left_shoulder']
    const rightShoulder = frame.keypoints['right_shoulder']
    const leftHip = frame.keypoints['left_hip']
    const rightHip = frame.keypoints['right_hip']

    if (!leftShoulder || !rightShoulder || !leftHip || !rightHip) return

    const midShoulder = {
      x: (leftShoulder[0] + rightShoulder[0]) / 2,
      y: (leftShoulder[1] + rightShoulder[1]) / 2,
      visibility: Math.min(leftShoulder[2], rightShoulder[2]),
    }
    const midHip = {
      x: (leftHip[0] + rightHip[0]) / 2,
      y: (leftHip[1] + rightHip[1]) / 2,
      visibility: Math.min(leftHip[2], rightHip[2]),
    }

    if (midShoulder.visibility < 0.5 || midHip.visibility < 0.5) return

    // Calculate body tension based on shoulder-hip alignment
    const shoulderY = midShoulder.y
    const hipY = midHip.y
    const height = Math.abs(shoulderY - hipY)

    // Simple heuristic: if shoulder and hip are aligned (similar x), tension is good
    const alignment = Math.abs(midShoulder.x - midHip.x) / height
    const tension = Math.max(0, 1 - alignment)

    // Color: green = good tension, yellow = moderate, red = sagging
    let color: string
    if (tension > 0.7) {
      color = '#00ff00'
    } else if (tension > 0.4) {
      color = '#ffff00'
    } else {
      color = '#ff0000'
    }

    const start = scaleCoordinates(midShoulder.x, midShoulder.y)
    const end = scaleCoordinates(midHip.x, midHip.y)

    ctx.strokeStyle = color
    ctx.lineWidth = 4
    ctx.beginPath()
    ctx.moveTo(start.x, start.y)
    ctx.lineTo(end.x, end.y)
    ctx.stroke()
  }, [scaleCoordinates])

  const drawFootStability = useCallback((ctx: CanvasRenderingContext2D, frame: PoseFrame) => {
    const ankles = ['left_ankle', 'right_ankle'] as const

    for (const ankleName of ankles) {
      const ankle = frame.keypoints[ankleName]
      if (!ankle || ankle[2] < 0.5) continue

      const { x, y } = scaleCoordinates(ankle[0], ankle[1])

      // For now, show static circles
      // Future: compute jitter from frame-to-frame comparison
      ctx.strokeStyle = '#00ff00'
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.arc(x, y, 15, 0, Math.PI * 2)
      ctx.stroke()

      ctx.fillStyle = '#00ff00'
      ctx.globalAlpha = 0.3
      ctx.beginPath()
      ctx.arc(x, y, 10, 0, Math.PI * 2)
      ctx.fill()
      ctx.globalAlpha = 1
    }
  }, [scaleCoordinates])

  const drawElbowAngles = useCallback((ctx: CanvasRenderingContext2D, frame: PoseFrame) => {
    const elbows = [
      { elbow: 'left_elbow', shoulder: 'left_shoulder', wrist: 'left_wrist' },
      { elbow: 'right_elbow', shoulder: 'right_shoulder', wrist: 'right_wrist' },
    ] as const

    for (const { elbow: elbowName, shoulder: shoulderName, wrist: wristName } of elbows) {
      const elbow = frame.keypoints[elbowName]
      const shoulder = frame.keypoints[shoulderName]
      const wrist = frame.keypoints[wristName]

      if (!elbow || !shoulder || !wrist) continue
      if (elbow[2] < 0.5 || shoulder[2] < 0.5 || wrist[2] < 0.5) continue

      const elbowPos = scaleCoordinates(elbow[0], elbow[1])

      // Calculate angle
      const dx1 = shoulder[0] - elbow[0]
      const dy1 = shoulder[1] - elbow[1]
      const dx2 = wrist[0] - elbow[0]
      const dy2 = wrist[1] - elbow[1]

      const angle1 = Math.atan2(dy1, dx1)
      const angle2 = Math.atan2(dy2, dx2)
      let angleDiff = angle2 - angle1

      // Normalize to positive angle
      if (angleDiff < 0) angleDiff += Math.PI * 2

      // Draw arc
      ctx.strokeStyle = '#ffff00'
      ctx.lineWidth = 3
      ctx.beginPath()
      ctx.arc(elbowPos.x, elbowPos.y, 30, angle1, angle2, angleDiff > Math.PI)
      ctx.stroke()
    }
  }, [scaleCoordinates])

  const drawHipPath = useCallback((ctx: CanvasRenderingContext2D, frame: PoseFrame) => {
    const midHip = frame.keypoints['mid_hip']
    if (!midHip || midHip[2] < 0.5) return

    const hip = { x: midHip[0], y: midHip[1] }

    // Add to history
    hipHistoryRef.current.push(hip)

    // Keep last 90 frames (~3 seconds at 30fps)
    if (hipHistoryRef.current.length > 90) {
      hipHistoryRef.current.shift()
    }

    if (hipHistoryRef.current.length < 2) return

    // Draw trail
    ctx.strokeStyle = '#00ffff'
    ctx.lineWidth = 3
    ctx.beginPath()

    for (let i = 0; i < hipHistoryRef.current.length; i++) {
      const point = scaleCoordinates(hipHistoryRef.current[i].x, hipHistoryRef.current[i].y)
      if (i === 0) {
        ctx.moveTo(point.x, point.y)
      } else {
        ctx.lineTo(point.x, point.y)
      }
    }

    ctx.stroke()
  }, [scaleCoordinates])

  useEffect(() => {
    const canvas = canvasRef.current
    const video = videoRef.current
    if (!canvas || !video || !poseData) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const renderFrame = () => {
      // Get current frame
      const frame = getFrameAtTime(video.currentTime)
      if (!frame) return

      // Clear canvas
      ctx.clearRect(0, 0, width, height)

      // Reset hip history when seeking backwards
      if (frame.frame_id < lastFrameRef.current) {
        hipHistoryRef.current = []
      }
      lastFrameRef.current = frame.frame_id

      // Draw enabled overlays
      if (config.skeleton) {
        drawSkeleton(ctx, frame)
      }
      if (config.bodyTension) {
        drawBodyTension(ctx, frame)
      }
      if (config.footStability) {
        drawFootStability(ctx, frame)
      }
      if (config.elbowAngles) {
        drawElbowAngles(ctx, frame)
      }
      if (config.hipPath) {
        drawHipPath(ctx, frame)
      }
    }

    // Render on video events
    const handleTimeUpdate = () => renderFrame()
    const handleSeek = () => {
      hipHistoryRef.current = []
      renderFrame()
    }

    video.addEventListener('timeupdate', handleTimeUpdate)
    video.addEventListener('seeked', handleSeek)

    // Initial render
    renderFrame()

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate)
      video.removeEventListener('seeked', handleSeek)
    }
  }, [
    videoRef,
    poseData,
    config,
    width,
    height,
    getFrameAtTime,
    drawSkeleton,
    drawBodyTension,
    drawFootStability,
    drawElbowAngles,
    drawHipPath,
  ])

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className="absolute inset-0 pointer-events-none"
      style={{ width: '100%', height: '100%' }}
    />
  )
}
