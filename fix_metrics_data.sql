-- Fix metrics data by adding historical scores for delta calculations
-- This will make the improving/declining counters show realistic values

-- First, let's add some historical scores for each issuer
-- We'll create scores from 2 days ago to create proper deltas

INSERT INTO score (issuer_id, ts, score, bucket, base, market, event_delta, macro_adj, model_version, explanation) VALUES
-- Apple Inc - historical data
(1, NOW() - INTERVAL '48 hours', 87.2, 'AA', 60.5, 12.8, 8.5, 5.4, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),
(1, NOW() - INTERVAL '24 hours', 88.1, 'AA', 61.2, 12.9, 8.6, 5.4, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),

-- Microsoft - historical data
(2, NOW() - INTERVAL '48 hours', 88.5, 'AA', 61.8, 13.1, 8.7, 4.9, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),
(2, NOW() - INTERVAL '24 hours', 89.2, 'AA', 62.1, 13.2, 8.8, 5.1, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),

-- Google - historical data
(3, NOW() - INTERVAL '48 hours', 82.1, 'A', 58.3, 11.2, 7.8, 4.8, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),
(3, NOW() - INTERVAL '24 hours', 83.1, 'A', 58.9, 11.5, 7.9, 4.8, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),

-- Amazon - historical data (declining trend)
(4, NOW() - INTERVAL '48 hours', 81.2, 'A', 59.1, 11.8, 7.5, 2.8, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),
(4, NOW() - INTERVAL '24 hours', 80.1, 'A', 58.7, 11.5, 7.3, 2.6, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),

-- Tesla - historical data (declining trend)
(5, NOW() - INTERVAL '48 hours', 68.5, 'BBB', 52.3, 8.9, 5.2, 2.1, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),
(5, NOW() - INTERVAL '24 hours', 67.2, 'BBB', 51.8, 8.7, 5.1, 1.6, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),

-- JPMorgan - historical data
(6, NOW() - INTERVAL '48 hours', 85.3, 'AA', 60.2, 12.1, 8.2, 4.8, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),
(6, NOW() - INTERVAL '24 hours', 86.1, 'AA', 60.8, 12.3, 8.3, 4.7, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),

-- Bank of America - historical data
(7, NOW() - INTERVAL '48 hours', 78.9, 'A', 56.4, 10.2, 7.1, 5.2, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),
(7, NOW() - INTERVAL '24 hours', 79.8, 'A', 57.1, 10.4, 7.2, 5.1, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),

-- Wells Fargo - historical data
(8, NOW() - INTERVAL '48 hours', 76.2, 'A', 54.8, 9.8, 6.9, 4.7, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),
(8, NOW() - INTERVAL '24 hours', 77.1, 'A', 55.3, 10.1, 7.0, 4.7, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),

-- Walmart - historical data
(9, NOW() - INTERVAL '48 hours', 82.7, 'A', 58.9, 11.3, 7.8, 4.7, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),
(9, NOW() - INTERVAL '24 hours', 83.5, 'A', 59.4, 11.6, 7.9, 4.6, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),

-- Procter & Gamble - historical data
(10, NOW() - INTERVAL '48 hours', 87.1, 'AA', 61.2, 12.5, 8.4, 5.0, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),
(10, NOW() - INTERVAL '24 hours', 87.9, 'AA', 61.7, 12.7, 8.5, 5.0, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),

-- Johnson & Johnson - historical data
(11, NOW() - INTERVAL '48 hours', 89.3, 'AA', 62.8, 13.1, 8.6, 4.8, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),
(11, NOW() - INTERVAL '24 hours', 90.1, 'AA', 63.2, 13.3, 8.7, 4.9, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),

-- Pfizer - historical data
(12, NOW() - INTERVAL '48 hours', 75.8, 'A', 54.2, 9.6, 6.8, 5.2, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),
(12, NOW() - INTERVAL '24 hours', 76.7, 'A', 54.8, 9.8, 6.9, 5.2, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),

-- Exxon Mobil - historical data
(13, NOW() - INTERVAL '48 hours', 71.4, 'BBB', 51.8, 8.9, 6.2, 4.5, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),
(13, NOW() - INTERVAL '24 hours', 72.3, 'BBB', 52.3, 9.1, 6.3, 4.6, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),

-- Chevron - historical data
(14, NOW() - INTERVAL '48 hours', 73.8, 'BBB', 53.1, 9.3, 6.5, 4.9, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),
(14, NOW() - INTERVAL '24 hours', 74.7, 'BBB', 53.6, 9.5, 6.6, 5.0, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),

-- Berkshire Hathaway - historical data
(15, NOW() - INTERVAL '48 hours', 91.2, 'AA', 64.5, 13.8, 8.9, 4.0, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}'),
(15, NOW() - INTERVAL '24 hours', 92.1, 'AA', 65.1, 14.0, 9.0, 4.0, 'v1.0-mock', '{"source": "mock", "explanation": "Previous score"}');
