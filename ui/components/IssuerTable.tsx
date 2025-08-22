'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ChevronRight, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { Issuer } from '../types/issuer'

interface IssuerTableProps {
  issuers: Issuer[]
}

export default function IssuerTable({ issuers }: IssuerTableProps) {
  const router = useRouter()
  const [sortField, setSortField] = useState<keyof Issuer>('score')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')

  const handleSort = (field: keyof Issuer) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const sortedIssuers = [...issuers].sort((a, b) => {
    const aValue = a[sortField]
    const bValue = b[sortField]
    
    if (aValue === null && bValue === null) return 0
    if (aValue === null) return 1
    if (bValue === null) return -1
    
    if (typeof aValue === 'string' && typeof bValue === 'string') {
      return sortDirection === 'asc' 
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue)
    }
    
    if (typeof aValue === 'number' && typeof bValue === 'number') {
      return sortDirection === 'asc' ? aValue - bValue : bValue - aValue
    }
    
    return 0
  })

  const getScoreBadgeClass = (bucket: string | null) => {
    if (!bucket) return 'score-badge bg-gray-100 text-gray-800'
    
    const bucketLower = bucket.toLowerCase()
    if (bucketLower.includes('aaa') || bucketLower.includes('aa')) return 'score-badge score-aaa'
    if (bucketLower.includes('bbb')) return 'score-badge score-bbb'
    if (bucketLower.includes('bb')) return 'score-badge score-bb'
    if (bucketLower === 'b') return 'score-badge score-b'
    if (bucketLower.includes('ccc') || bucketLower.includes('cc')) return 'score-badge score-ccc'
    
    return 'score-badge bg-gray-100 text-gray-800'
  }

  const getDeltaIcon = (delta: number) => {
    if (delta > 0) return <TrendingUp className="h-4 w-4 text-success-600" />
    if (delta < 0) return <TrendingDown className="h-4 w-4 text-danger-600" />
    return <Minus className="h-4 w-4 text-gray-400" />
  }

  const getDeltaColor = (delta: number) => {
    if (delta > 0) return 'text-success-600'
    if (delta < 0) return 'text-danger-600'
    return 'text-gray-500'
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th 
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              onClick={() => handleSort('name')}
            >
              Issuer
            </th>
            <th 
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              onClick={() => handleSort('sector')}
            >
              Sector
            </th>
            <th 
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              onClick={() => handleSort('score')}
            >
              Score
            </th>
            <th 
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              onClick={() => handleSort('delta_24h')}
            >
              24h Change
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {sortedIssuers.map((issuer) => (
            <tr key={issuer.id} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center">
                  <div>
                    <div className="text-sm font-medium text-gray-900">
                      {issuer.name}
                    </div>
                    <div className="text-sm text-gray-500">
                      {issuer.ticker}
                    </div>
                  </div>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-gray-900">{issuer.sector}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium text-gray-900">
                    {issuer.score?.toFixed(1) || 'N/A'}
                  </span>
                  {issuer.bucket && (
                    <span className={getScoreBadgeClass(issuer.bucket)}>
                      {issuer.bucket}
                    </span>
                  )}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center space-x-1">
                  {getDeltaIcon(issuer.delta_24h)}
                  <span className={`text-sm font-medium ${getDeltaColor(issuer.delta_24h)}`}>
                    {issuer.delta_24h > 0 ? '+' : ''}{issuer.delta_24h.toFixed(1)}
                  </span>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <a 
                  href={`/issuer/${issuer.id}`}
                  className="text-primary-600 hover:text-primary-900 flex items-center space-x-1"
                >
                  <span>View Details</span>
                  <ChevronRight className="h-4 w-4" />
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {sortedIssuers.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">No issuers found</p>
        </div>
      )}
    </div>
  )
}





