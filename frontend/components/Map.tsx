"use client"

import { useEffect, useRef } from "react"
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet"
import L, { LeafletEvent } from "leaflet"
import { Pizza, Utensils } from "lucide-react"
import "leaflet/dist/leaflet.css"
import dynamic from "next/dynamic"

const AnimatedFlow = dynamic(() => import("./AnimatedFlow"), { ssr: false })

// Pentagon coordinates
const PENTAGON_CENTER = [38.8719, -77.0563] as [number, number]

// Custom marker icons
const createCustomIcon = (color: string) => {
  const iconHtml = `
    <div class="relative group">
      <div class="absolute -inset-2 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full blur opacity-20 group-hover:opacity-40 animate-pulse transition-opacity duration-300"></div>
      <div class="w-4 h-4 rounded-full ${color} border-2 border-white shadow-lg relative">
        <div class="absolute inset-0 rounded-full animate-ping ${color} opacity-30"></div>
      </div>
    </div>
  `
  
  return L.divIcon({
    html: iconHtml,
    className: "custom-div-icon",
    iconSize: [20, 20],
    iconAnchor: [10, 10],
    popupAnchor: [0, -10],
  })
}

// Pentagon building marker
const pentagonIcon = L.divIcon({
  html: `
    <div class="relative group">
      <div class="w-10 h-10 relative flex items-center justify-center">
        <div class="absolute w-full h-full" style="clip-path: polygon(50% 0%, 100% 38%, 82% 100%, 18% 100%, 0% 38%)">
          <div class="w-full h-full bg-gray-800/90 shadow-lg relative overflow-hidden backdrop-blur-sm border border-gray-700/30">
            <div class="absolute inset-0 bg-gradient-to-b from-gray-700/50 via-gray-800/30 to-gray-900/50"></div>
            <div class="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-black/30"></div>
          </div>
        </div>
      </div>
      <span class="absolute -bottom-6 left-1/2 transform -translate-x-1/2 text-xs font-medium text-gray-300 bg-gray-900/80 px-2 py-0.5 rounded-full shadow-lg backdrop-blur-sm border border-gray-700/30">
        Pentagon
      </span>
    </div>
  `,
  className: "pentagon-marker",
  iconSize: [40, 40],
  iconAnchor: [20, 20],
})

// Legend component
const MapLegend = ({ isDarkMode }: { isDarkMode: boolean }) => {
  const map = useMap()
  
  useEffect(() => {
    const legend = new L.Control({ position: "bottomleft" })
    
    legend.onAdd = () => {
      const div = L.DomUtil.create("div", "map-legend")
      div.innerHTML = `
        <div class="${isDarkMode ? "bg-gray-800/90 text-white" : "bg-white/90 text-gray-900"} p-3 rounded-lg shadow-lg border border-gray-700/50 backdrop-blur-sm">
          <div class="flex gap-4 text-xs font-medium">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-red-500 animate-pulse"></div>
              <span>Critical Activity</span>
            </div>
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-yellow-500 animate-pulse"></div>
              <span>Moderate</span>
            </div>
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-green-500 animate-pulse"></div>
              <span>Normal</span>
            </div>
          </div>
        </div>
      `
      return div
    }
    
    legend.addTo(map)
    
    return () => {
      legend.remove()
    }
  }, [map, isDarkMode])
  
  return null
}

interface Restaurant {
  id: number
  name: string
  type: "pizza" | "restaurant"
  lat: number
  lng: number
  activity: string
  rating: number
  orders: number
}

interface MapProps {
  restaurants: Restaurant[]
  isDarkMode: boolean
  getActivityColor: (activity: string) => string
  getActivityLabel: (activity: string) => string
}

// Add a component to manage flows
const FlowsOverlay = ({ restaurants, isDarkMode }: { restaurants: Restaurant[], isDarkMode: boolean }) => {
  const map = useMap()
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const animationFrameRef = useRef<number | null>(null)

  useEffect(() => {
    if (!map || !map.getPanes() || !map.getPanes().overlayPane) {
      console.warn('Map not fully initialized')
      return
    }

    // Create and setup canvas
    const canvas = document.createElement('canvas')
    canvasRef.current = canvas
    canvas.style.position = 'absolute'
    canvas.style.top = '0'
    canvas.style.left = '0'
    canvas.style.width = '100%'
    canvas.style.height = '100%'
    canvas.style.pointerEvents = 'none'
    canvas.style.zIndex = '400'

    const overlayPane = map.getPanes().overlayPane
    overlayPane.appendChild(canvas)

    const ctx = canvas.getContext('2d')
    if (!ctx) {
      console.warn('Could not get canvas context')
      return
    }

    // Set initial canvas size and transform
    const updateCanvas = () => {
      const mapSize = map.getSize()
      const pixelRatio = window.devicePixelRatio || 1
      
      // Update canvas size only if it changed
      if (canvas.width !== mapSize.x * pixelRatio || canvas.height !== mapSize.y * pixelRatio) {
        canvas.style.width = `${mapSize.x}px`
        canvas.style.height = `${mapSize.y}px`
        canvas.width = mapSize.x * pixelRatio
        canvas.height = mapSize.y * pixelRatio
      }
      
      // Reset transform and scale
      ctx.setTransform(1, 0, 0, 1, 0, 0)
      ctx.scale(pixelRatio, pixelRatio)
      
      // Apply map's current transform to canvas for smooth dragging
      const pos = map.containerPointToLayerPoint([0, 0])
      canvas.style.transform = `translate3d(${pos.x}px,${pos.y}px,0)`
    }

    // Create particles
    const allParticles = restaurants.map(restaurant => ({
      restaurant,
      particles: Array.from({ length: 8 }, () => ({
        progress: Math.random(),
        speed: 0.002 * (0.8 + Math.random() * 0.4), // Increased base speed
        size: 1.5 + Math.random(),
        pulsePhase: Math.random() * Math.PI * 2,
        offset: Math.random() * 0.2 - 0.1 // Random offset for varied paths
      }))
    }))

    // Get flow color based on activity with opacity support
    const getFlowColor = (activity: string, opacity: number = 1) => {
      let color
      switch (activity.toLowerCase()) {
        case "very busy":
        case "busier":
          color = isDarkMode ? "#ef4444" : "#dc2626"
          break
        case "busy":
          color = isDarkMode ? "#f97316" : "#ea580c"
          break
        case "typical":
          color = isDarkMode ? "#eab308" : "#ca8a04"
          break
        case "less busy":
        case "quiet":
          color = isDarkMode ? "#22c55e" : "#16a34a"
          break
        default:
          color = isDarkMode ? "#6b7280" : "#4b5563"
      }
      return opacity < 1 ? `${color}${Math.round(opacity * 255).toString(16).padStart(2, '0')}` : color
    }

    // Animation state
    let isAnimating = true
    let lastFrameTime = Date.now()

    // Animation loop
    const animate = () => {
      if (!isAnimating || !canvas || !ctx) return

      const currentTime = Date.now()
      const deltaTime = (currentTime - lastFrameTime) / 1000 // Convert to seconds
      lastFrameTime = currentTime

      // Update canvas position and size
      updateCanvas()

      const pixelRatio = window.devicePixelRatio || 1
      ctx.clearRect(0, 0, canvas.width / pixelRatio, canvas.height / pixelRatio)

      const mapBounds = map.getBounds()
      const padding = map.getSize().x * 0.5 // Show flows beyond visible area

      allParticles.forEach(({ restaurant, particles }) => {
        // Convert geographic coordinates to pixel coordinates
        const startLatLng = L.latLng(restaurant.lat, restaurant.lng)
        const endLatLng = L.latLng(PENTAGON_CENTER[0], PENTAGON_CENTER[1])
        
        // Get points in container coordinates (accounts for current map position)
        const startContainer = map.latLngToContainerPoint(startLatLng)
        const endContainer = map.latLngToContainerPoint(endLatLng)
        
        // Use container points directly for drawing (they automatically update with map movement)
        const startPoint = startContainer
        const endPoint = endContainer

        // Check if either point is within the padded viewport
        const mapSize = map.getSize()
        if (
          startContainer.x < -padding || startContainer.x > mapSize.x + padding ||
          startContainer.y < -padding || startContainer.y > mapSize.y + padding ||
          endContainer.x < -padding || endContainer.x > mapSize.x + padding ||
          endContainer.y < -padding || endContainer.y > mapSize.y + padding
        ) return

        // Calculate base control points for the curve
        const dx = endPoint.x - startPoint.x
        const dy = endPoint.y - startPoint.y
        const distance = Math.sqrt(dx * dx + dy * dy)
        
        // Draw base connection line
        ctx.beginPath()
        ctx.moveTo(startPoint.x, startPoint.y)

        particles.forEach(particle => {
          // Update particle progress
          particle.progress += particle.speed * deltaTime * 60 // Normalize to 60fps
          if (particle.progress >= 1) {
            particle.progress = 0
            particle.offset = Math.random() * 0.2 - 0.1 // New random offset when resetting
          }

          // Calculate control point with offset
          const midPoint = {
            x: (startPoint.x + endPoint.x) / 2,
            y: (startPoint.y + endPoint.y) / 2 - 0.2 * distance + (distance * particle.offset)
          }

          const t = particle.progress
          const currentX = Math.pow(1 - t, 2) * startPoint.x +
                          2 * (1 - t) * t * midPoint.x +
                          Math.pow(t, 2) * endPoint.x
          const currentY = Math.pow(1 - t, 2) * startPoint.y +
                          2 * (1 - t) * t * midPoint.y +
                          Math.pow(t, 2) * endPoint.y

          // Draw flowing node
          const pulseScale = 0.5 + 0.5 * Math.sin(currentTime * 0.005 + particle.pulsePhase)
          const size = particle.size * (1 + 0.3 * pulseScale)

          // Draw outer glow
          const gradient = ctx.createRadialGradient(
            currentX, currentY, 0,
            currentX, currentY, size * 2
          )
          gradient.addColorStop(0, getFlowColor(restaurant.activity, 0.3))
          gradient.addColorStop(1, getFlowColor(restaurant.activity, 0))
          
          ctx.beginPath()
          ctx.arc(currentX, currentY, size * 2, 0, Math.PI * 2)
          ctx.fillStyle = gradient
          ctx.fill()

          // Draw node core
          ctx.beginPath()
          ctx.arc(currentX, currentY, size, 0, Math.PI * 2)
          ctx.fillStyle = getFlowColor(restaurant.activity)
          ctx.fill()
        })

        // Draw the path after particles to ensure it's always visible
        const baseMidPoint = {
          x: (startPoint.x + endPoint.x) / 2,
          y: (startPoint.y + endPoint.y) / 2 - 0.2 * distance
        }
        ctx.beginPath()
        ctx.moveTo(startPoint.x, startPoint.y)
        ctx.quadraticCurveTo(baseMidPoint.x, baseMidPoint.y, endPoint.x, endPoint.y)
        ctx.strokeStyle = getFlowColor(restaurant.activity, 0.15)
        ctx.lineWidth = 1.5
        ctx.stroke()
      })

      animationFrameRef.current = requestAnimationFrame(animate)
    }

    // Start animation
    animate()

    // Add map event listeners
    map.on('move', updateCanvas)
    map.on('movestart', updateCanvas)
    map.on('moveend', updateCanvas)
    map.on('drag', updateCanvas)
    map.on('zoom', updateCanvas)
    map.on('zoomstart', updateCanvas)
    map.on('zoomend', updateCanvas)
    map.on('resize', updateCanvas)

    // Cleanup
    return () => {
      isAnimating = false
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
      if (canvas && canvas.parentNode) {
        canvas.parentNode.removeChild(canvas)
      }
      map.off('move', updateCanvas)
      map.off('movestart', updateCanvas)
      map.off('moveend', updateCanvas)
      map.off('drag', updateCanvas)
      map.off('zoom', updateCanvas)
      map.off('zoomstart', updateCanvas)
      map.off('zoomend', updateCanvas)
      map.off('resize', updateCanvas)
    }
  }, [map, restaurants, isDarkMode])

  return null
}

// Add MapInitializer component
const MapInitializer = () => {
  const map = useMap()
  
  useEffect(() => {
    // Ensure the map is properly initialized
    map.invalidateSize()

    // Add smooth zoom handler
    const handleZoom = () => {
      const container = map.getContainer();
      container.style.transition = 'transform 0.25s cubic-bezier(0,0,0.25,1)';
    };

    map.on('zoomstart', handleZoom);

    // Configure zoom behavior
    map.options.zoomDelta = 0.25;
    map.options.minZoom = 11;
    map.options.maxZoom = 18;

    return () => {
      map.off('zoomstart', handleZoom);
    };
  }, [map])
  
  return null
}

export default function Map({ restaurants, isDarkMode, getActivityColor, getActivityLabel }: MapProps) {
  return (
    <div className="w-full h-full">
      <style jsx global>{`
        .leaflet-popup-content-wrapper {
          background: rgba(17, 24, 39, 0.95) !important;
          border: 1px solid rgba(75, 85, 99, 0.3) !important;
          border-radius: 0.5rem !important;
          backdrop-filter: blur(8px) !important;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
        }
        .leaflet-popup-tip {
          background: rgba(17, 24, 39, 0.95) !important;
          border: 1px solid rgba(75, 85, 99, 0.3) !important;
          backdrop-filter: blur(8px) !important;
        }
        .leaflet-popup-close-button {
          color: rgba(156, 163, 175, 0.8) !important;
        }
        .leaflet-popup-close-button:hover {
          color: rgba(209, 213, 219, 1) !important;
        }
      `}</style>
      <MapContainer
        center={PENTAGON_CENTER}
        zoom={13}
        style={{ height: "100%", width: "100%" }}
        zoomControl={false}
        attributionControl={false}
        dragging={true}
        zoomAnimation={true}
        wheelDebounceTime={100}
        wheelPxPerZoomLevel={100}
        className={`${isDarkMode ? "map-dark" : "map-light"} transition-all duration-300 ease-in-out`}
      >
        <MapInitializer />
        <TileLayer
          url={isDarkMode 
            ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          }
        />
        
        {/* Pentagon Marker */}
        <Marker position={PENTAGON_CENTER} icon={pentagonIcon}>
          <Popup className="custom-popup">
            <div className="text-center p-3 rounded-lg min-w-[200px]">
              <h3 className="font-bold text-lg mb-1 text-white">The Pentagon</h3>
              <p className="text-sm text-gray-300">United States Department of Defense</p>
              <div className="mt-2 pt-2 border-t border-gray-700/30">
                <p className="text-xs text-gray-400">Monitoring {restaurants.length} locations</p>
              </div>
            </div>
          </Popup>
        </Marker>
        
        {/* Restaurant Markers */}
        {restaurants.map((restaurant) => {
          const colorClass = getActivityColor(restaurant.activity)
          const activityLabel = getActivityLabel(restaurant.activity)
          
          return (
            <Marker
              key={restaurant.id}
              position={[restaurant.lat, restaurant.lng]}
              icon={createCustomIcon(colorClass)}
            >
              <Popup>
                <div className="p-3 rounded-lg min-w-[220px]">
                  <h3 className="font-bold text-lg mb-2 text-white">{restaurant.name}</h3>
                  
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between items-center">
                      <span className="text-gray-400">Status</span>
                      <span className={`font-medium px-2 py-0.5 rounded-full text-xs ${
                        restaurant.activity.toLowerCase().includes("busy") ? "bg-red-500/20 text-red-300" :
                        restaurant.activity.toLowerCase().includes("typical") ? "bg-yellow-500/20 text-yellow-300" :
                        "bg-green-500/20 text-green-300"
                      }`}>
                        {activityLabel}
                      </span>
                    </div>
                    
                    <div className="flex justify-between items-center">
                      <span className="text-gray-400">Rating</span>
                      <div className="flex items-center gap-1">
                        <span className="text-yellow-400">★</span>
                        <span className="font-medium text-white">{restaurant.rating.toFixed(1)}</span>
                      </div>
                    </div>
                    
                    <div className="flex justify-between items-center">
                      <span className="text-gray-400">Current Orders</span>
                      <span className="font-medium text-white">{restaurant.orders}</span>
                    </div>
                    
                    <div className="mt-2 pt-2 border-t border-gray-700/30">
                      <div className="text-xs text-gray-500">
                        Live monitoring active
                      </div>
                    </div>
                  </div>
                </div>
              </Popup>
            </Marker>
          )
        })}
        
        <FlowsOverlay restaurants={restaurants} isDarkMode={isDarkMode} />
        
        <MapLegend isDarkMode={isDarkMode} />
      </MapContainer>
    </div>
  )
} 