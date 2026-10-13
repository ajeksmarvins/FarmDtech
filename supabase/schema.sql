-- FarmDtech database schema (run in Supabase SQL editor).
-- Designed for server-side sync using the protected service-role key.
CREATE TABLE IF NOT EXISTS public.prices (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date DATE NOT NULL,
    crop TEXT NOT NULL,
    crop_code TEXT NOT NULL,
    market_id TEXT NOT NULL,
    market TEXT NOT NULL,
    state TEXT NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    price_ngn_per_kg DOUBLE PRECISION NOT NULL CHECK (price_ngn_per_kg > 0),
    price_kind TEXT NOT NULL CHECK (price_kind IN ('observed', 'estimated')),
    source TEXT NOT NULL,
    original_unit_kg DOUBLE PRECISION,
    source_value_ngn DOUBLE PRECISION,
    data_coverage_recent DOUBLE PRECISION,
    survey_confidence DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(market_id, crop, date, price_kind)
);
CREATE INDEX IF NOT EXISTS farmdtech_lookup_idx ON public.prices(crop, date DESC, market_id);
CREATE TABLE IF NOT EXISTS public.advice_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    crop TEXT NOT NULL,
    origin_market_id TEXT,
    recommended_market_id TEXT,
    estimated_net_ngn DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
-- No phone-number table by default: minimize unnecessary personal data.
-- RLS denies access through the public/anon key. Service-role access is restricted.
ALTER TABLE public.prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.advice_events ENABLE ROW LEVEL SECURITY;
