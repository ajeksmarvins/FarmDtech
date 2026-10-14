-- FarmDtech — optional read-only access for a public Streamlit price dashboard.
-- Run this in Supabase SQL Editor ONLY if you intend to make ALL rows in
-- public.prices publicly readable. They are World Bank historic/estimated data.
-- Review dataset redistribution terms before exposing raw records through API.
-- This does NOT permit anonymous writes and does NOT publish advice_events.

BEGIN;

ALTER TABLE public.prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.advice_events ENABLE ROW LEVEL SECURITY;

-- Restrict anonymous client privileges explicitly.
REVOKE ALL PRIVILEGES ON TABLE public.prices FROM anon, authenticated;
REVOKE ALL PRIVILEGES ON TABLE public.advice_events FROM anon, authenticated;

-- Published agricultural prices are public research information. No writes.
GRANT SELECT ON TABLE public.prices TO anon;

DROP POLICY IF EXISTS farmdtech_public_historical_prices_read ON public.prices;
CREATE POLICY farmdtech_public_historical_prices_read
ON public.prices
FOR SELECT
TO anon
USING (true);

COMMIT;

-- Review permissions with:
-- SELECT grantee, privilege_type
-- FROM information_schema.role_table_grants
-- WHERE table_schema='public' AND table_name IN ('prices','advice_events')
--   AND grantee IN ('anon','authenticated')
-- ORDER BY table_name, grantee, privilege_type;
