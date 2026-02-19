import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import TogglePanel from '@/components/TogglePanel'
import { OverlayConfig } from '@/components/VideoOverlay'

describe('TogglePanel', () => {
  const defaultConfig: OverlayConfig = {
    skeleton: true,
    bodyTension: false,
    footStability: true,
    elbowAngles: false,
    hipPath: true,
  }

  it('renders all toggle options', () => {
    const onChange = vi.fn()
    render(<TogglePanel config={defaultConfig} onChange={onChange} />)

    expect(screen.getByText('SKELETON')).toBeInTheDocument()
    expect(screen.getByText('BODY TENSION')).toBeInTheDocument()
    expect(screen.getByText('FOOT STABILITY')).toBeInTheDocument()
    expect(screen.getByText('ELBOW ANGLES')).toBeInTheDocument()
    expect(screen.getByText('HIP PATH')).toBeInTheDocument()
  })

  it('calls onChange when a toggle is clicked', () => {
    const onChange = vi.fn()
    render(<TogglePanel config={defaultConfig} onChange={onChange} />)

    const bodyTensionButton = screen.getByText('BODY TENSION').closest('button')
    fireEvent.click(bodyTensionButton!)

    expect(onChange).toHaveBeenCalledWith({
      ...defaultConfig,
      bodyTension: true,
    })
  })

  it('disables toggle when clicked again', () => {
    const onChange = vi.fn()
    render(<TogglePanel config={defaultConfig} onChange={onChange} />)

    const skeletonButton = screen.getByText('SKELETON').closest('button')
    fireEvent.click(skeletonButton!)

    expect(onChange).toHaveBeenCalledWith({
      ...defaultConfig,
      skeleton: false,
    })
  })
})
