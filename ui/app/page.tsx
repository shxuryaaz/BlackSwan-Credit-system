'use client'

import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts'
import { TrendingUp, TrendingDown, AlertTriangle, Activity, DollarSign, BarChart3, Users, Globe, Upload } from 'lucide-react'

interface Issuer {
  id: number
  name: string
  ticker: string
  sector: string
  country: string
  score: number
  bucket: string
  delta_24h: number
  score_ts: string
}

interface Metrics {
  total_issuers: number
  improving: number
  declining: number
  alerts: number
  avg_score: number
  sector_distribution: { sector: string; count: number }[]
  score_distribution: { bucket: string; count: number }[]
}

export default function Dashboard() {
  const [issuers, setIssuers] = useState<Issuer[]>([])
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedSector, setSelectedSector] = useState<string>('All')
  const [selectedBucket, setSelectedBucket] = useState<string>('All')

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000) // Refresh every 5 seconds for live updates
    return () => clearInterval(interval)
  }, [])

  const fetchData = async () => {
    try {
      const [issuersResponse, metricsResponse] = await Promise.all([
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/issuers`),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/metrics`)
      ])

      if (issuersResponse.ok) {
        const data = await issuersResponse.json()
        setIssuers(data.issuers || [])
      }

      if (metricsResponse.ok) {
        const metricsData = await metricsResponse.json()
        setMetrics(metricsData)
      }
    } catch (error) {
      console.error('Error fetching data:', error)
    } finally {
      setLoading(false)
    }
  }

  const filteredIssuers = issuers.filter(issuer => {
    const sectorMatch = selectedSector === 'All' || issuer.sector === selectedSector
    const bucketMatch = selectedBucket === 'All' || issuer.bucket === selectedBucket
    return sectorMatch && bucketMatch
  })

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

  const chartData = issuers.slice(0, 10).map(issuer => ({
    name: issuer.ticker,
    score: issuer.score,
    delta: issuer.delta_24h,
    bucket: issuer.bucket,
    fullName: issuer.name
  }))

  // Professional color scheme - subtle and clean
  const getScoreColor = (score: number, bucket: string) => {
    if (score >= 80) return '#00d4aa' // AA and AAA - Teal
    if (score >= 60) return '#0066cc' // A and BBB - Blue
    return '#ff4444' // BB and B - Red
  }

  const sectorData = metrics?.sector_distribution || []
  const bucketData = metrics?.score_distribution || []

  if (loading) {
    return (
      <div className="bloomberg-bg min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="bloomberg-loading mx-auto mb-4"></div>
          <p className="financial-text">Loading Credit Intelligence Platform...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bloomberg-bg min-h-screen">
      {/* Header */}
      <header className="bloomberg-header p-4 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="status-indicator status-live"></div>
            <h1 className="financial-title">BlackSwan Credit Terminal</h1>
            <span className="financial-text">Real-time Credit Scoring & Analytics</span>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4 text-green-400" />
              <span className="financial-text">Live Data</span>
            </div>
            <div className="text-sm text-gray-400">
              Last Updated: {new Date().toLocaleTimeString()}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex">
        {/* Sidebar */}
        <aside className="bloomberg-sidebar w-64 p-4 min-h-screen">
          <div className="space-y-6">
            {/* Filters */}
            <div className="bloomberg-card p-4">
              <h3 className="financial-subtitle mb-4">Filters</h3>
              
              <div className="space-y-3">
                <div>
                  <label className="financial-text block mb-2">Sector</label>
                  <select 
                    value={selectedSector}
                    onChange={(e) => setSelectedSector(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white"
                  >
                    <option value="All">All Sectors</option>
                    {Array.from(new Set(issuers.map(i => i.sector))).map(sector => (
                      <option key={sector} value={sector}>{sector}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="financial-text block mb-2">Credit Rating</label>
                  <select 
                    value={selectedBucket}
                    onChange={(e) => setSelectedBucket(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white"
                  >
                    <option value="All">All Ratings</option>
                    <option value="AA">AA</option>
                    <option value="A">A</option>
                    <option value="BBB">BBB</option>
                    <option value="BB">BB</option>
                  </select>
                </div>
              </div>
            </div>

            {/* News Upload */}
            <div className="bloomberg-card p-4 mb-4">
              <h3 className="financial-subtitle mb-4">News Analysis</h3>
              <a 
                href="/upload" 
                className="bloomberg-btn-primary w-full flex items-center justify-center space-x-2"
              >
                <Upload className="w-4 h-4" />
                <span>Upload News for Analysis</span>
              </a>
              <p className="text-xs text-gray-400 mt-2 text-center">
                Upload .txt files or enter text for real-time analysis
              </p>
            </div>

            {/* Quick Stats */}
            <div className="bloomberg-card p-4">
              <h3 className="financial-subtitle mb-4">Quick Stats</h3>
              <div className="space-y-3">
                <div className="data-point">
                  <span className="data-label">Total Issuers</span>
                  <span className="data-value">{metrics?.total_issuers || 0}</span>
                </div>
                <div className="data-point">
                  <span className="data-label">Avg Score</span>
                  <span className="data-value">{(metrics?.avg_score || 0).toFixed(1)}</span>
                </div>
                <div className="data-point">
                  <span className="data-label">Improving</span>
                  <span className="data-value score-positive">{metrics?.improving || 0}</span>
                </div>
                <div className="data-point">
                  <span className="data-label">Declining</span>
                  <span className="data-value score-negative">{metrics?.declining || 0}</span>
                </div>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Dashboard */}
        <main className="flex-1 p-6">
          {/* Metrics Cards */}
          <div className="bloomberg-grid mb-6">
            <div className="bloomberg-card p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="financial-text">Total Issuers</p>
                  <p className="financial-title text-3xl">{metrics?.total_issuers || 0}</p>
                </div>
                <Users className="w-8 h-8 text-blue-400" />
              </div>
            </div>

            <div className="bloomberg-card p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="financial-text">Improving</p>
                  <p className="financial-title text-3xl score-positive">{metrics?.improving || 0}</p>
                </div>
                <TrendingUp className="w-8 h-8 text-green-400" />
              </div>
            </div>

            <div className="bloomberg-card p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="financial-text">Declining</p>
                  <p className="financial-title text-3xl score-negative">{metrics?.declining || 0}</p>
                </div>
                <TrendingDown className="w-8 h-8 text-red-400" />
              </div>
            </div>

            <div className="bloomberg-card p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="financial-text">Alerts</p>
                  <p className="financial-title text-3xl score-neutral">{metrics?.alerts || 0}</p>
                </div>
                <AlertTriangle className="w-8 h-8 text-yellow-400" />
              </div>
            </div>
          </div>

          {/* Charts Section */}
          <div className="bloomberg-grid mb-6">
            <div className="bloomberg-card p-6">
              <h3 className="financial-subtitle mb-4">Top 10 Credit Scores</h3>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis 
                      dataKey="name" 
                      stroke="#ccc" 
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis 
                      stroke="#ccc" 
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                      domain={[0, 100]}
                      tickFormatter={(value) => `${value}`}
                    />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#1a1a1a', 
                        border: '1px solid #333',
                        borderRadius: '8px',
                        color: '#fff'
                      }}
                      formatter={(value: any, name: any, props: any) => [
                        <div key="tooltip">
                          <div className="font-bold text-white">{props.payload.fullName}</div>
                          <div className="text-sm text-gray-300">Score: <span className="text-green-400">{value}</span></div>
                          <div className="text-sm text-gray-300">Rating: <span className="text-blue-400">{props.payload.bucket}</span></div>
                          <div className="text-sm text-gray-300">24h: <span className={props.payload.delta > 0 ? 'text-green-400' : 'text-red-400'}>
                            {props.payload.delta > 0 ? '+' : ''}{props.payload.delta.toFixed(1)}
                          </span></div>
                        </div>
                      ]}
                    />
                    <Bar 
                      dataKey="score" 
                      radius={[4, 4, 0, 0]}
                    >
                      {chartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={getScoreColor(entry.score, entry.bucket)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              {/* Legend */}
              <div className="flex flex-wrap gap-4 mt-4 text-xs">
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 rounded" style={{backgroundColor: '#00d4aa'}}></div>
                  <span className="text-gray-300">Investment Grade (80+)</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 rounded" style={{backgroundColor: '#0066cc'}}></div>
                  <span className="text-gray-300">Good Credit (60-79)</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 rounded" style={{backgroundColor: '#ff4444'}}></div>
                  <span className="text-gray-300">Speculative (&lt;60)</span>
                </div>
              </div>
            </div>

            <div className="bloomberg-card p-6">
              <h3 className="financial-subtitle mb-4">Sector Distribution</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={sectorData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ sector, percent }) => `${sector} ${(percent * 100).toFixed(0)}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="count"
                    >
                      {sectorData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={['#00d4aa', '#0066cc', '#ffaa00', '#ff4444', '#9b59b6', '#1abc9c'][index % 6]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#1a1a1a', 
                        border: '1px solid #333',
                        borderRadius: '8px'
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Issuers Table */}
          <div className="bloomberg-card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="financial-subtitle">Credit Intelligence Dashboard</h3>
              <div className="flex items-center space-x-2">
                <span className="financial-text">Showing {filteredIssuers.length} of {issuers.length} issuers</span>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="bloomberg-table w-full">
                <thead>
                  <tr>
                    <th className="px-4 py-3 text-left">Company</th>
                    <th className="px-4 py-3 text-left">Sector</th>
                    <th className="px-4 py-3 text-center">Score</th>
                    <th className="px-4 py-3 text-center">Rating</th>
                    <th className="px-4 py-3 text-center">24h Change</th>
                    <th className="px-4 py-3 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredIssuers.map((issuer) => (
                    <tr key={issuer.id} className="hover:bg-gray-800 transition-colors">
                      <td className="px-4 py-3">
                        <div>
                          <div className="font-medium text-white">{issuer.name}</div>
                          <div className="text-sm text-gray-400">{issuer.ticker}</div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-300">{issuer.sector}</td>
                      <td className="px-4 py-3 text-center">
                        <span className="font-bold text-lg" style={{ color: getBucketColor(issuer.bucket) }}>
                          {issuer.score.toFixed(1)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span 
                          className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold border"
                          style={{ 
                            color: getScoreColor(issuer.score, issuer.bucket),
                            borderColor: getScoreColor(issuer.score, issuer.bucket),
                            backgroundColor: `${getScoreColor(issuer.score, issuer.bucket)}20`
                          }}
                        >
                          {issuer.bucket}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="flex items-center justify-center space-x-1">
                          {getDeltaIcon(issuer.delta_24h)}
                          <span className={getDeltaColor(issuer.delta_24h)}>
                            {formatDelta(issuer.delta_24h)}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <a 
                          href={`/issuer/${issuer.id}`}
                          className="bloomberg-btn text-sm"
                        >
                          View Details
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
