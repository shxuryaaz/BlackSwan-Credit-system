'use client';

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts';

interface ScoreData {
  ts: string;
  score: number;
  bucket: string;
  base: number;
  market: number;
  event_delta: number;
  macro_adj: number;
}

interface ScoreChartProps {
  data: ScoreData[];
  issuerName: string;
  height?: number;
}

const COLORS = {
  score: '#2563eb',
  base: '#059669',
  market: '#dc2626',
  event_delta: '#f59e0b',
  macro_adj: '#7c3aed',
  grid: '#e5e7eb',
  text: '#374151'
};

const BUCKET_COLORS = {
  'AAA': '#059669',
  'AA': '#10b981',
  'A': '#34d399',
  'BBB': '#fbbf24',
  'BB': '#f59e0b',
  'B': '#ef4444',
  'CCC': '#dc2626'
};

export const ScoreTrendChart: React.FC<ScoreChartProps> = ({ data, issuerName, height = 300 }) => {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatScore = (value: number) => `${value.toFixed(1)}`;

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-semibold text-gray-900">{formatDate(label)}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ color: entry.color }} className="text-sm">
              {entry.name}: {formatScore(entry.value)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Score Trend - {issuerName}
      </h3>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
          <XAxis
            dataKey="ts"
            tickFormatter={formatDate}
            stroke={COLORS.text}
            fontSize={12}
          />
          <YAxis
            domain={[0, 100]}
            stroke={COLORS.text}
            fontSize={12}
            tickFormatter={formatScore}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Area
            type="monotone"
            dataKey="score"
            stackId="1"
            stroke={COLORS.score}
            fill={COLORS.score}
            fillOpacity={0.3}
            name="Total Score"
          />
          <Area
            type="monotone"
            dataKey="base"
            stackId="2"
            stroke={COLORS.base}
            fill={COLORS.base}
            fillOpacity={0.2}
            name="Base Score"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export const ScoreComponentsChart: React.FC<ScoreChartProps> = ({ data, issuerName, height = 300 }) => {
  const latestData = data[data.length - 1];
  
  if (!latestData) return null;

  const componentsData = [
    { name: 'Base', value: latestData.base, color: COLORS.base },
    { name: 'Market', value: latestData.market, color: COLORS.market },
    { name: 'Event Δ', value: latestData.event_delta, color: COLORS.event_delta },
    { name: 'Macro Adj', value: latestData.macro_adj, color: COLORS.macro_adj }
  ].filter(item => item.value !== 0);

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Score Components - {issuerName}
      </h3>
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={componentsData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {componentsData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip formatter={(value: number) => value.toFixed(2)} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

export const BucketDistributionChart: React.FC<{ data: ScoreData[] }> = ({ data }) => {
  const bucketCounts = data.reduce((acc, item) => {
    acc[item.bucket] = (acc[item.bucket] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const chartData = Object.entries(bucketCounts).map(([bucket, count]) => ({
    bucket,
    count,
    color: BUCKET_COLORS[bucket as keyof typeof BUCKET_COLORS] || '#6b7280'
  }));

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Rating Distribution
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
          <XAxis dataKey="bucket" stroke={COLORS.text} fontSize={12} />
          <YAxis stroke={COLORS.text} fontSize={12} />
          <Tooltip />
          <Bar dataKey="count" fill="#2563eb" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export const ScoreComparisonChart: React.FC<{ data: ScoreData[] }> = ({ data }) => {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Score Components Over Time
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
          <XAxis
            dataKey="ts"
            tickFormatter={formatDate}
            stroke={COLORS.text}
            fontSize={12}
          />
          <YAxis stroke={COLORS.text} fontSize={12} />
          <Tooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="base"
            stroke={COLORS.base}
            strokeWidth={2}
            name="Base"
          />
          <Line
            type="monotone"
            dataKey="market"
            stroke={COLORS.market}
            strokeWidth={2}
            name="Market"
          />
          <Line
            type="monotone"
            dataKey="event_delta"
            stroke={COLORS.event_delta}
            strokeWidth={2}
            name="Event Δ"
          />
          <Line
            type="monotone"
            dataKey="macro_adj"
            stroke={COLORS.macro_adj}
            strokeWidth={2}
            name="Macro Adj"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
