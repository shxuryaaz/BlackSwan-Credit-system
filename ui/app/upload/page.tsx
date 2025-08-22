'use client'

import { useState } from 'react'
import { Upload, FileText, Send, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'

interface UploadResponse {
  message: string
  file_name?: string
  issuer_id: number
  analysis: {
    sentiment: number
    weight: number
    type: string
    confidence: number
    reasoning: string
    keywords: string[]
    risk_factors: string[]
  }
  score_update: {
    old_score: number
    new_score: number
    change: number
    bucket: string
  }
  timestamp: string
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [newsText, setNewsText] = useState('')
  const [issuerId, setIssuerId] = useState<number | ''>('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<UploadResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleFileUpload = async () => {
    if (!file) {
      setError('Please select a file')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      if (issuerId) {
        formData.append('issuer_id', issuerId.toString())
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/upload/news-file`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`)
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  const handleTextAnalysis = async () => {
    if (!newsText.trim()) {
      setError('Please enter news text')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/upload/news-text`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          news_text: newsText,
          issuer_id: issuerId || undefined,
        }),
      })

      if (!response.ok) {
        throw new Error(`Analysis failed: ${response.statusText}`)
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  const getSentimentColor = (sentiment: number) => {
    if (sentiment > 0.3) return 'text-green-400'
    if (sentiment < -0.3) return 'text-red-400'
    return 'text-yellow-400'
  }

  const getSentimentIcon = (sentiment: number) => {
    if (sentiment > 0.3) return '📈'
    if (sentiment < -0.3) return '📉'
    return '➡️'
  }

  return (
    <div className="bloomberg-bg min-h-screen p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <header className="mb-8">
          <h1 className="financial-title text-3xl mb-2">Data Ingestion Demo</h1>
          <p className="financial-text">
            Upload news files or enter text for real-time credit score analysis and market impact assessment
          </p>
        </header>

        <div className="bloomberg-grid">
          {/* File Upload Section */}
          <div className="bloomberg-card p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Upload className="w-6 h-6 text-blue-400" />
              <h2 className="financial-subtitle">Upload News File</h2>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block financial-text mb-2">Select .txt file</label>
                <input
                  type="file"
                  accept=".txt"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="w-full p-3 border border-gray-600 rounded-lg bg-gray-800 text-white file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-500 file:text-white hover:file:bg-blue-600"
                />
              </div>
              
              <div>
                <label className="block financial-text mb-2">Issuer ID (optional)</label>
                <input
                  type="number"
                  value={issuerId}
                  onChange={(e) => setIssuerId(e.target.value ? Number(e.target.value) : '')}
                  placeholder="Leave empty for random issuer"
                  className="w-full p-3 border border-gray-600 rounded-lg bg-gray-800 text-white"
                />
              </div>
              
              <button
                onClick={handleFileUpload}
                disabled={loading || !file}
                className="bloomberg-btn-primary w-full flex items-center justify-center space-x-2"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Upload className="w-4 h-4" />
                )}
                <span>{loading ? 'Analyzing...' : 'Upload & Analyze'}</span>
              </button>
            </div>
          </div>

          {/* Text Input Section */}
          <div className="bloomberg-card p-6">
            <div className="flex items-center space-x-3 mb-4">
              <FileText className="w-6 h-6 text-green-400" />
              <h2 className="financial-subtitle">Enter News Text</h2>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block financial-text mb-2">News Text</label>
                <textarea
                  value={newsText}
                  onChange={(e) => setNewsText(e.target.value)}
                  placeholder="Enter news text to analyze..."
                  rows={6}
                  className="w-full p-3 border border-gray-600 rounded-lg bg-gray-800 text-white resize-none"
                />
              </div>
              
              <div>
                <label className="block financial-text mb-2">Issuer ID (optional)</label>
                <input
                  type="number"
                  value={issuerId}
                  onChange={(e) => setIssuerId(e.target.value ? Number(e.target.value) : '')}
                  placeholder="Leave empty for random issuer"
                  className="w-full p-3 border border-gray-600 rounded-lg bg-gray-800 text-white"
                />
              </div>
              
              <button
                onClick={handleTextAnalysis}
                disabled={loading || !newsText.trim()}
                className="bloomberg-btn-primary w-full flex items-center justify-center space-x-2"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
                <span>{loading ? 'Analyzing...' : 'Analyze Text'}</span>
              </button>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bloomberg-card p-4 mt-6 border-l-4 border-red-500 bg-red-900/20">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-5 h-5 text-red-400" />
              <span className="text-red-400">{error}</span>
            </div>
          </div>
        )}

        {/* Results Display */}
        {result && (
          <div className="bloomberg-card p-6 mt-6">
            <div className="flex items-center space-x-3 mb-4">
              <CheckCircle className="w-6 h-6 text-green-400" />
              <h2 className="financial-subtitle">Analysis Results</h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* AI Analysis */}
              <div>
                <h3 className="financial-text mb-3">🤖 AI Analysis</h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Sentiment:</span>
                    <span className={`font-medium ${getSentimentColor(result.analysis.sentiment)}`}>
                      {getSentimentIcon(result.analysis.sentiment)} {result.analysis.sentiment.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Impact Weight:</span>
                    <span className={`font-medium ${result.analysis.weight > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {result.analysis.weight > 0 ? '+' : ''}{result.analysis.weight.toFixed(1)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Event Type:</span>
                    <span className="font-medium text-white">{result.analysis.type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Confidence:</span>
                    <span className="font-medium text-white">{(result.analysis.confidence * 100).toFixed(0)}%</span>
                  </div>
                </div>
                
                <div className="mt-4">
                  <h4 className="financial-text mb-2">Reasoning:</h4>
                  <p className="text-sm text-gray-300">{result.analysis.reasoning}</p>
                </div>
                
                {result.analysis.keywords.length > 0 && (
                  <div className="mt-4">
                    <h4 className="financial-text mb-2">Keywords Found:</h4>
                    <div className="flex flex-wrap gap-2">
                      {result.analysis.keywords.map((keyword, index) => (
                        <span key={index} className="px-2 py-1 bg-blue-500/20 text-blue-300 rounded text-xs">
                          {keyword}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Score Update */}
              <div>
                <h3 className="financial-text mb-3">📊 Credit Score Update</h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Issuer ID:</span>
                    <span className="font-medium text-white">{result.issuer_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Old Score:</span>
                    <span className="font-medium text-white">{result.score_update.old_score}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">New Score:</span>
                    <span className="font-medium text-white">{result.score_update.new_score}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Change:</span>
                    <span className={`font-medium ${result.score_update.change > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {result.score_update.change > 0 ? '+' : ''}{result.score_update.change.toFixed(1)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Bucket:</span>
                    <span className="font-medium text-white">{result.score_update.bucket}</span>
                  </div>
                </div>
                
                <div className="mt-4 p-3 bg-gray-800 rounded-lg">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-white">{result.score_update.new_score}</div>
                    <div className="text-sm text-gray-400">{result.score_update.bucket}</div>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="mt-6 pt-4 border-t border-gray-700">
              <p className="text-sm text-gray-400">
                Analysis completed at: {new Date(result.timestamp).toLocaleString()}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
