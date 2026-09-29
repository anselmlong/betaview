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

    expect(screen.getByRole('button', { name: /skeleton/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /body tension/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /foot stability/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /elbow angles/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /hip path/i })).toBeInTheDocument()
  })

  it('exposes each toggle state via aria-pressed', () => {
    render(<TogglePanel config={defaultConfig} onChange={vi.fn()} />)

    expect(screen.getByRole('button', { name: /skeleton/i })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: /body tension/i })).toHaveAttribute('aria-pressed', 'false')
  })

  it('calls onChange when a toggle is clicked', () => {
    const onChange = vi.fn()
    render(<TogglePanel config={defaultConfig} onChange={onChange} />)

    const bodyTensionButton = screen.getByRole('button', { name: /body tension/i })
    fireEvent.click(bodyTensionButton!)

    expect(onChange).toHaveBeenCalledWith({
      ...defaultConfig,
      bodyTension: true,
    })
  })

  it('disables toggle when clicked again', () => {
    const onChange = vi.fn()
    render(<TogglePanel config={defaultConfig} onChange={onChange} />)

    const skeletonButton = screen.getByRole('button', { name: /skeleton/i })
    fireEvent.click(skeletonButton!)

    expect(onChange).toHaveBeenCalledWith({
      ...defaultConfig,
      skeleton: false,
    })
  })
})
