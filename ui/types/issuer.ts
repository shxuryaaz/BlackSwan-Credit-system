export interface Issuer {
  id: number
  name: string
  ticker: string | null
  sector: string | null
  country: string | null
  score: number | null
  bucket: string | null
  delta_24h: number
  score_ts: string | null
}

export interface IssuerDetail extends Issuer {
  components: {
    base: number | null
    market: number | null
    event_delta: number | null
    macro_adj: number | null
  } | null
  top_features: Array<{
    name: string
    impact: number
  }>
  events: Array<{
    id: number
    type: string
    headline: string
    sentiment: number
    weight: number
    url: string
    ts: string
  }>
}

export interface ScoreTimeline {
  ts: string
  score: number
  bucket: string
  events: Array<{
    type: string
    headline: string
    impact: number
  }>
}





