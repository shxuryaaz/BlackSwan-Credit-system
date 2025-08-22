'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, AreaChart, Area, Cell } from 'recharts'
import { ArrowLeft, TrendingUp, TrendingDown, AlertTriangle, Activity, Calendar, DollarSign, BarChart3, Users, Globe, Clock, Target } from 'lucide-react'

interface IssuerDetail {
  id: number
  name: string
  ticker: string
  sector: string
  country: string
  score: number
  bucket: string
  delta_24h: number
  components: {
    base: number
    market: number
    event_delta: number
    macro_adj: number
  }
  top_features: Array<{
    name: string
    impact: number
  }>
  events: Array<{
    id: number
    ts: string
    type: string
    sentiment: number
    weight: number
    headline: string
    source: string
  }>
  score_ts: string
}

interface ScoreHistory {
  ts: string
  score: number
  bucket: string
}

export default function IssuerDetailPage({ params }: { params: { id: string } }) {
  const [issuer, setIssuer] = useState<IssuerDetail | null>(null)
  const [scoreHistory, setScoreHistory] = useState<ScoreHistory[]>([])
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    fetchIssuerData()
  }, [params.id])

  const fetchIssuerData = async () => {
    try {
      const [issuerResponse, historyResponse] = await Promise.all([
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/issuer/${params.id}`),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/${params.id}/history`)
      ])

      if (issuerResponse.ok) {
        const issuerData = await issuerResponse.json()
        setIssuer(issuerData)
      }

      if (historyResponse.ok) {
        const historyData = await historyResponse.json()
        setScoreHistory(historyData)
      }
    } catch (error) {
      console.error('Error fetching issuer data:', error)
    } finally {
      setLoading(false)
    }
  }

  const getBucketColor = (bucket: string) => {
    switch (bucket) {
      case 'AA': return '#00d4aa'
      case 'A': return '#0066cc'
      case 'BBB': return '#ffaa00'
      case 'BB': return '#ff4444'
      default: return '#999'
    }
  }

  const getDeltaColor = (delta: number) => {
    if (delta > 0) return 'text-green-400'
    if (delta < 0) return 'text-red-400'
    return 'text-yellow-400'
  }

  const getDeltaIcon = (delta: number) => {
    if (delta > 0) return <TrendingUp className="w-4 h-4 text-green-400" />
    if (delta < 0) return <TrendingDown className="w-4 h-4 text-red-400" />
    return <Activity className="w-4 h-4 text-yellow-400" />
  }

  const formatDelta = (delta: number) => {
    const sign = delta > 0 ? '+' : ''
    return `${sign}${delta.toFixed(1)}`
  }

  const getSentimentColor = (sentiment: number) => {
    if (sentiment > 0.3) return 'text-green-400'
    if (sentiment < -0.3) return 'text-red-400'
    return 'text-yellow-400'
  }

  const getEventTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'earnings': return 'bg-green-500'
      case 'regulatory': return 'bg-red-500'
      case 'product launch': return 'bg-blue-500'
      case 'partnership': return 'bg-purple-500'
      case 'acquisition': return 'bg-orange-500'
      default: return 'bg-gray-500'
    }
  }

  if (loading) {
    return (
      <div className="bloomberg-bg min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="bloomberg-loading mx-auto mb-4"></div>
          <p className="financial-text">Loading issuer details...</p>
        </div>
      </div>
    )
  }

  if (!issuer) {
    return (
      <div className="bloomberg-bg min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="financial-text">Issuer not found</p>
        </div>
      </div>
    )
  }

  const chartData = scoreHistory.map(item => ({
    date: new Date(item.ts).toLocaleDateString(),
    score: item.score,
    bucket: item.bucket
  }))

  const componentsData = [
    { component: 'Base Fundamentals', value: 62.0, color: '#00d4aa' },
    { component: 'Market Risk', value: 13.3, color: '#0066cc' },
    { component: 'Event Impact', value: 8.9, color: '#ffaa00' },
    { component: 'Macro Adjustment', value: 4.4, color: '#ff4444' }
  ]

  return (
    <div className="bloomberg-bg min-h-screen">
      {/* Header */}
      <header className="bloomberg-header p-4 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button 
              onClick={() => router.back()}
              className="bloomberg-btn-secondary flex items-center space-x-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Dashboard</span>
            </button>
            <div className="status-indicator status-live"></div>
            <div>
              <h1 className="financial-title">{issuer.name}</h1>
              <p className="financial-text">{issuer.ticker} • {issuer.sector} • {issuer.country}</p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <p className="financial-text">Last Updated</p>
              <p className="text-sm text-gray-400">{new Date(issuer.score_ts).toLocaleString()}</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="p-6">
        {/* Score Overview */}
        <div className="bloomberg-grid mb-6">
          <div className="bloomberg-card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="financial-subtitle">Current Credit Score</h3>
              <span 
                className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bucket-${issuer.bucket.toLowerCase()}`}
              >
                {issuer.bucket}
              </span>
            </div>
            <div className="text-center">
              <div 
                className="text-6xl font-bold mb-2"
                style={{ color: getBucketColor(issuer.bucket) }}
              >
                {issuer.score.toFixed(1)}
              </div>
              <div className="flex items-center justify-center space-x-2">
                {getDeltaIcon(issuer.delta_24h)}
                <span className={getDeltaColor(issuer.delta_24h)}>
                  {formatDelta(issuer.delta_24h)} (24h)
                </span>
              </div>
            </div>
          </div>

          <div className="bloomberg-card p-6">
            <h3 className="financial-subtitle mb-4">Score Components</h3>
            <div className="space-y-3">
              {componentsData.map((component, index) => (
                <div key={index} className="data-point">
                  <span className="data-label">{component.component}</span>
                  <span 
                    className="data-value"
                    style={{ color: component.color }}
                  >
                    {component.value.toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="bloomberg-card p-6">
            <h3 className="financial-subtitle mb-4">Top Features</h3>
            <div className="space-y-3">
              {issuer.top_features.slice(0, 5).map((feature, index) => (
                <div key={index} className="data-point">
                  <span className="data-label">{feature.name}</span>
                  <span 
                    className="data-value"
                    style={{ color: feature.impact > 0 ? '#00d4aa' : '#ff4444' }}
                  >
                    {feature.impact > 0 ? '+' : ''}{feature.impact.toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Charts Section */}
        <div className="bloomberg-grid mb-6">
          <div className="bloomberg-card p-6">
            <h3 className="financial-subtitle mb-4">Credit Score History (30 Days)</h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis 
                    dataKey="date" 
                    stroke="#ccc"
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis 
                    stroke="#ccc"
                    domain={[0, 100]}
                    tick={{ fontSize: 12 }}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1a1a1a', 
                      border: '1px solid #333',
                      borderRadius: '8px'
                    }}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="score" 
                    stroke="#00d4aa" 
                    fill="rgba(0, 212, 170, 0.1)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bloomberg-card p-6">
            <h3 className="financial-subtitle mb-4">Score Components Breakdown</h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart 
                  data={componentsData} 
                  layout="horizontal"
                  margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis 
                    type="number" 
                    stroke="#ccc" 
                    domain={[0, 70]}
                    tickFormatter={(value) => value.toString()}
                  />
                  <YAxis 
                    dataKey="component" 
                    type="category" 
                    stroke="#ccc" 
                    width={140}
                    tick={{ fontSize: 12 }}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1a1a1a', 
                      border: '1px solid #333',
                      borderRadius: '8px',
                      color: '#fff'
                    }}
                    formatter={(value, name) => [`${value}`, 'Score']}
                    labelFormatter={(label) => `Component: ${label}`}
                  />
                  <Bar 
                    dataKey="value" 
                    fill="#00d4aa"
                    radius={[0, 4, 4, 0]}
                  >
                    {componentsData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Recent Events */}
        <div className="bloomberg-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="financial-subtitle">Recent Market Events</h3>
            <div className="flex items-center space-x-2">
              <Clock className="w-4 h-4 text-gray-400" />
              <span className="financial-text">Last 5 days</span>
            </div>
          </div>

          <div className="space-y-4">
            {issuer.events.slice(0, 10).map((event) => (
              <div key={event.id} className="border border-gray-700 rounded-lg p-4 hover:bg-gray-800 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <span 
                        className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getEventTypeColor(event.type)}`}
                      >
                        {event.type}
                      </span>
                      <span className="text-sm text-gray-400">
                        {new Date(event.ts).toLocaleDateString()}
                      </span>
                      <span className="text-sm text-gray-400">
                        {event.source}
                      </span>
                    </div>
                    <h4 className="text-white font-medium mb-2">{event.headline}</h4>
                    <div className="flex items-center space-x-4 text-sm">
                      <div className="flex items-center space-x-1">
                        <span className="text-gray-400">Sentiment:</span>
                        <span className={getSentimentColor(event.sentiment)}>
                          {event.sentiment > 0 ? '+' : ''}{event.sentiment.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <span className="text-gray-400">Impact:</span>
                        <span className={event.weight > 0 ? 'text-green-400' : 'text-red-400'}>
                          {event.weight > 0 ? '+' : ''}{event.weight.toFixed(1)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
