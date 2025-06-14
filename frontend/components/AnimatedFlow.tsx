import { useEffect, useRef } from 'react'

interface AnimatedFlowProps {
  startLat: number
  startLng: number
  endLat: number
  endLng: number
  color: string
  isDarkMode: boolean
}

const AnimatedFlow: React.FC<AnimatedFlowProps> = ({
  startLat,
  startLng,
  endLat,
  endLng,
  color,
  isDarkMode,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Set canvas size to match parent
    const resizeCanvas = () => {
      const parent = canvas.parentElement
      if (!parent) return
      canvas.width = parent.clientWidth
      canvas.height = parent.clientHeight
    }
    resizeCanvas()
    window.addEventListener('resize', resizeCanvas)

    // Convert lat/lng to pixel coordinates
    const latLngToPixel = (lat: number, lng: number) => {
      const mapBounds = {
        north: 38.9300,  // Approximate Pentagon area bounds
        south: 38.8500,
        east: -77.0300,
        west: -77.0700,
      }
      
      const x = ((lng - mapBounds.west) / (mapBounds.east - mapBounds.west)) * canvas.width
      const y = ((mapBounds.north - lat) / (mapBounds.north - mapBounds.south)) * canvas.height
      return { x, y }
    }

    const start = latLngToPixel(startLat, startLng)
    const end = latLngToPixel(endLat, endLng)

    // Animation variables
    let particles: { x: number; y: number; progress: number; speed: number }[] = []
    const numParticles = 3
    const baseSpeed = 0.002

    // Initialize particles
    for (let i = 0; i < numParticles; i++) {
      particles.push({
        x: start.x,
        y: start.y,
        progress: (i / numParticles),
        speed: baseSpeed * (0.8 + Math.random() * 0.4), // Random speed variation
      })
    }

    // Animation loop
    let animationFrameId: number
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Update and draw particles
      particles.forEach((particle, i) => {
        // Update position
        particle.progress += particle.speed
        if (particle.progress >= 1) {
          particle.progress = 0
        }

        // Calculate current position
        const t = particle.progress
        const curve = 0.2 // Curve amount
        const midX = (start.x + end.x) / 2
        const midY = (start.y + end.y) / 2 - curve * Math.abs(end.x - start.x)
        
        // Quadratic bezier curve
        const currentX = Math.pow(1 - t, 2) * start.x + 
                        2 * (1 - t) * t * midX + 
                        Math.pow(t, 2) * end.x
        const currentY = Math.pow(1 - t, 2) * start.y + 
                        2 * (1 - t) * t * midY + 
                        Math.pow(t, 2) * end.y

        // Draw particle
        ctx.beginPath()
        ctx.arc(currentX, currentY, 2, 0, Math.PI * 2)
        ctx.fillStyle = color
        ctx.fill()

        // Draw trail
        ctx.beginPath()
        ctx.moveTo(currentX, currentY)
        ctx.lineTo(
          currentX - (10 * Math.cos(Math.atan2(end.y - start.y, end.x - start.x))),
          currentY - (10 * Math.sin(Math.atan2(end.y - start.y, end.x - start.x)))
        )
        ctx.strokeStyle = color
        ctx.globalAlpha = 0.3
        ctx.lineWidth = 1
        ctx.stroke()
        ctx.globalAlpha = 1
      })

      animationFrameId = requestAnimationFrame(animate)
    }

    animate()

    return () => {
      window.removeEventListener('resize', resizeCanvas)
      cancelAnimationFrame(animationFrameId)
    }
  }, [startLat, startLng, endLat, endLng, color, isDarkMode])

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        pointerEvents: 'none',
        zIndex: 10,
      }}
    />
  )
}

export default AnimatedFlow 