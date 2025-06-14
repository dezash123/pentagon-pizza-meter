"use client"

import { useState, useEffect } from "react"
import dynamic from "next/dynamic"
import Image from "next/image"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { TrendingUp, TrendingDown, Activity, Clock, Pizza, AlertCircle } from "lucide-react"

// Dynamically import map component to avoid SSR issues
const Map = dynamic(() => import("@/components/Map"), { ssr: false })

interface NewsArticle {
  title: string
  published: string
  link: string
  source: string
  severity: number
  explanation: string
}

interface DefenseStock {
  ticker: string
  change_percent: number
  current_price: number
  status: string
}

interface PizzaPlace {
  name: string
  coordinates: {
    lat: number
    lng: number
  }
  current_status: {
    status: string
    current_popularity: number
    typical_popularity: number
  }
  ratings: {
    google_rating: number
    number_of_ratings: number
  }
}

interface ApiResponse {
  news_analysis: {
    detailed_news_analysis: {
      articles: NewsArticle[]
    }
    severity_distribution: {
      counts: {
        critical: number
        low: number
        high: number
        medium: number
      }
    }
  }
  defense_stocks_analysis: {
    detailed_stocks_data: DefenseStock[]
    market_summary: {
      volatility: number
      overall_trend: string
    }
  }
  local_pizza_analysis: {
    detailed_places: PizzaPlace[]
    busyness_metrics: {
      places_by_status: {
        places: {
          very_busy: string[]
          busy: string[]
          typical: string[]
          quiet: string[]
          very_quiet: string[]
        }
      }
    }
  }
}

export default function PentagonPizzaTracker() {
  const [lastUpdate, setLastUpdate] = useState(new Date())
  const [isDarkMode, setIsDarkMode] = useState(true)
  const [data, setData] = useState<ApiResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('https://pentagon-pizza-index.onrender.com/read')
        if (!response.ok) {
          throw new Error('Failed to fetch data')
        }
        const jsonData = await response.json()
        setData(jsonData)
        setError(null)
      } catch (err) {
        setError('Failed to fetch data. Please try again later.')
        console.error('Error fetching data:', err)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 30000) // Refresh every 30 seconds

    return () => clearInterval(interval)
  }, [])

  const getActivityColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "very busy":
      case "busier":
        return "bg-red-500"
      case "busy":
        return "bg-orange-500"
      case "typical":
        return "bg-yellow-500"
      case "less busy":
      case "quiet":
        return "bg-green-500"
      default:
        return "bg-gray-500"
    }
  }

  const getActivityLabel = (status: string) => {
    return status.charAt(0).toUpperCase() + status.slice(1)
  }

  if (error) {
    return (
      <div className="h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
        <div className="bg-red-500/10 backdrop-blur-sm border border-red-500/20 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="h-6 w-6 text-red-500 animate-pulse" />
          <span className="text-red-200 font-medium">{error}</span>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
        <div className="flex flex-col items-center gap-3">
          <div className="w-12 h-12 rounded-full border-4 border-blue-500/30 border-t-blue-500 animate-spin" />
          <span className="text-blue-200 font-medium animate-pulse">Initializing System...</span>
        </div>
      </div>
    )
  }

  const pizzaPlaces = data.local_pizza_analysis.detailed_places.map((place, index) => ({
    id: index + 1,
    name: place.name,
    type: "pizza" as const,
    lat: place.coordinates.lat,
    lng: place.coordinates.lng,
    activity: place.current_status.status,
    rating: place.ratings.google_rating,
    orders: place.current_status.current_popularity
  }))

  const stockData = data.defense_stocks_analysis.detailed_stocks_data
    .sort((a, b) => Math.abs(b.change_percent) - Math.abs(a.change_percent))
    .map(stock => ({
      symbol: stock.ticker,
      name: stock.ticker,
      price: stock.current_price,
      change: stock.change_percent,
      changePercent: stock.change_percent
    }))

  const newsData = data.news_analysis.detailed_news_analysis.articles
    .sort((a, b) => b.severity - a.severity)
    .slice(0, 5)
    .map((article, index) => ({
      id: index + 1,
      title: article.title,
      time: new Date(article.published).toLocaleTimeString(),
      source: article.source,
      severity: article.severity
    }))

  return (
    <div className={`min-h-screen lg:h-screen lg:overflow-hidden ${isDarkMode ? "bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900" : "bg-gradient-to-br from-gray-50 via-gray-100 to-gray-50"}`}>
      <div className="h-full flex flex-col px-4 py-3 lg:overflow-hidden overflow-y-auto">
        {/* Enhanced Header */}
        <div className="flex items-center justify-between mb-4 relative flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="relative group">
              <Image
                src="/logo.png"
                alt="Pentagon Pizza Index Logo"
                width={32}
                height={32}
                className="object-contain"
              />
            </div>
            <div>
              <h1 className={`text-xl font-bold ${isDarkMode ? "text-white" : "text-gray-900"} tracking-tight`}>
                Pentagon Pizza Index
              </h1>
              <p className={`text-xs ${isDarkMode ? "text-gray-400" : "text-gray-600"}`}>
                Real-time Defense & Pizza Analytics
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => setIsDarkMode(!isDarkMode)} 
              className={`h-8 px-3 transition-all duration-200 ${
                isDarkMode 
                  ? "bg-gray-800 border-gray-700 hover:bg-gray-700 text-gray-200" 
                  : "bg-white border-gray-200 hover:bg-gray-50 text-gray-700"
              }`}
            >
              {isDarkMode ? "☀️ Light" : "🌙 Dark"}
            </Button>
            <div className={`flex items-center gap-2 ${isDarkMode ? "text-gray-400" : "text-gray-600"} bg-opacity-20 backdrop-blur-sm px-3 py-1 rounded-full ${isDarkMode ? "bg-gray-700" : "bg-gray-200"}`}>
              <Clock className="h-3.5 w-3.5" />
              <span className="text-xs font-medium">{lastUpdate.toLocaleTimeString()}</span>
            </div>
          </div>
        </div>

        {/* Enhanced Pizza Index Banner */}
        <Card
          className={`mb-2 overflow-hidden flex-shrink-0 ${
            isDarkMode 
              ? "bg-gradient-to-r from-orange-900/50 to-red-900/50 border-orange-700/50" 
              : "bg-gradient-to-r from-orange-100 to-red-100 border-orange-300"
          } backdrop-blur-sm`}
        >
          <CardContent className="py-4">
            <div className="flex items-center justify-center gap-8 flex-wrap lg:flex-nowrap">
              <div className="text-center relative group">
                <div className={`text-xs font-medium mb-1 ${isDarkMode ? "text-orange-300" : "text-orange-700"}`}>
                  PENTAGON PIZZA ACTIVITY
                </div>
                <div className={`text-4xl font-bold ${isDarkMode ? "text-white" : "text-gray-900"} relative`}>
                  <div className="absolute -inset-1 bg-gradient-to-r from-orange-500 to-red-500 rounded-lg blur opacity-25 group-hover:opacity-40 transition duration-300"></div>
                  <span className="relative">
                    {(data.local_pizza_analysis.detailed_places.reduce((acc, place) => acc + place.current_status.current_popularity, 0) / data.local_pizza_analysis.detailed_places.length).toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="text-center">
                <div className={`text-xs font-medium mb-1 ${isDarkMode ? "text-gray-300" : "text-gray-600"}`}>
                  CRITICAL ACTIVITY ZONES
                </div>
                <div className={`text-2xl font-bold flex items-center gap-2 justify-center ${isDarkMode ? "text-orange-400" : "text-orange-600"}`}>
                  <span className="relative group">
                    <div className="absolute -inset-2 bg-orange-500 rounded-lg blur opacity-25 group-hover:opacity-40 transition duration-300"></div>
                    <span className="relative">{data.local_pizza_analysis.busyness_metrics.places_by_status.places.very_busy.length}</span>
                  </span>
                  <span className="text-sm font-medium text-gray-500">locations</span>
                </div>
              </div>
              <div className="text-center">
                <div className={`text-xs font-medium mb-1 ${isDarkMode ? "text-gray-300" : "text-gray-600"}`}>
                  MARKET SIGNAL
                </div>
                <div className={`text-lg font-bold ${
                  data.defense_stocks_analysis.market_summary.overall_trend.toLowerCase() === "bullish" 
                    ? "text-green-400" 
                    : "text-red-400"
                } relative group`}>
                  <div className="absolute -inset-2 bg-current rounded-lg blur opacity-25 group-hover:opacity-40 transition duration-300"></div>
                  <span className="relative">{data.defense_stocks_analysis.market_summary.overall_trend.toUpperCase()}</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Main Dashboard Grid */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-1 lg:min-h-0">
          {/* Map Section */}
          <div className="lg:col-span-7 h-96 lg:h-auto">
            <Card className={`h-full overflow-hidden ${isDarkMode ? "bg-gray-800/50 border-gray-700/50" : "bg-white/50 border-gray-200"} backdrop-blur-sm`}>
              <CardContent className="h-full p-0">
                <div className="relative w-full h-full rounded-lg overflow-hidden">
                  <Map 
                    restaurants={pizzaPlaces}
                    isDarkMode={isDarkMode}
                    getActivityColor={getActivityColor}
                    getActivityLabel={getActivityLabel}
                  />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right Panel */}
          <div className="lg:col-span-5 flex flex-col gap-2">
            {/* Defense Stocks */}
            <Card className={`flex-shrink-0 ${isDarkMode ? "bg-gray-800/50 border-gray-700/50" : "bg-white/50 border-gray-200"} backdrop-blur-sm`}>
              <CardContent className="py-2">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {stockData.map((stock) => (
                    <div
                      key={stock.symbol}
                      className={`p-2 rounded-lg ${
                        isDarkMode 
                          ? "bg-gray-900/50 hover:bg-gray-900/70" 
                          : "bg-gray-50/50 hover:bg-gray-100/50"
                      } backdrop-blur-sm transition duration-200 group`}
                    >
                      <div className="flex justify-between items-center mb-1">
                        <span className={`font-bold ${isDarkMode ? "text-white" : "text-gray-900"}`}>
                          {stock.symbol}
                        </span>
                        <span className={`font-medium ${isDarkMode ? "text-white" : "text-gray-900"}`}>
                          ${stock.price.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className={`text-xs ${isDarkMode ? "text-gray-400" : "text-gray-600"}`}>
                          {stock.name}
                        </span>
                        <div className={`flex items-center gap-1 ${
                          stock.change >= 0 
                            ? "text-green-400 group-hover:text-green-300" 
                            : "text-red-400 group-hover:text-red-300"
                        } transition-colors duration-200`}>
                          {stock.change >= 0 ? (
                            <TrendingUp className="h-3 w-3" />
                          ) : (
                            <TrendingDown className="h-3 w-3" />
                          )}
                          <span className="text-xs font-medium">
                            {stock.changePercent >= 0 ? "+" : ""}
                            {stock.changePercent.toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* News Feed */}
            <Card className={`flex-1 lg:flex-1 ${isDarkMode ? "bg-gray-800/50 border-gray-700/50" : "bg-white/50 border-gray-200"} backdrop-blur-sm`}>
              <CardContent className="py-2">
                <div className="space-y-3">
                  {data.news_analysis.detailed_news_analysis.articles
                    .sort((a, b) => b.severity - a.severity)
                    .slice(0, 5)
                    .map((article, index) => (
                      <div
                        key={index}
                        className={`p-2 rounded-lg ${
                          isDarkMode 
                            ? "bg-gray-900/50 hover:bg-gray-900/70" 
                            : "bg-gray-50/50 hover:bg-gray-100/50"
                        } backdrop-blur-sm transition duration-200 group border-l-4 ${
                          article.severity > 0.7 
                            ? "border-red-500" 
                            : article.severity > 0.4 
                            ? "border-yellow-500" 
                            : "border-green-500"
                        }`}
                      >
                        <h3 className={`text-sm font-medium mb-1 line-clamp-1 ${isDarkMode ? "text-white" : "text-gray-900"}`}>
                          {article.title}
                        </h3>
                        <div className="flex items-center gap-2 text-xs flex-wrap">
                          <span className={`px-2 py-0.5 rounded-full text-xs ${
                            article.severity > 0.7 
                              ? "bg-red-500/20 text-red-300" 
                              : article.severity > 0.4 
                              ? "bg-yellow-500/20 text-yellow-300" 
                              : "bg-green-500/20 text-green-300"
                          }`}>
                            {(article.severity * 100).toFixed(0)}% Severity
                          </span>
                          <span className={`${isDarkMode ? "text-gray-500" : "text-gray-600"} hidden sm:inline`}>•</span>
                          <span className={isDarkMode ? "text-gray-400" : "text-gray-600"}>
                            {article.source}
                          </span>
                          <span className={`${isDarkMode ? "text-gray-500" : "text-gray-600"} hidden sm:inline`}>•</span>
                          <span className={isDarkMode ? "text-gray-400" : "text-gray-600"}>
                            {new Date(article.published).toLocaleTimeString()}
                          </span>
                        </div>
                      </div>
                    ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
