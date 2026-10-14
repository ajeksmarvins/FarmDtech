-- FarmDtech PRIVATE server-side reader policy.
--
-- 1. In Supabase Authentication -> Users, create a dedicated email/password
--    user controlled by your team for the Streamlit server.
-- 2. Copy ONLY the user's UUID (safe to use in SQL; NOT the password).
-- 3. Replace REPLACE_WITH_READER_UUID in this file before running it.
-- 4. Run as project administrator in Supabase SQL Editor.
--
-- The policy does NOT make prices publicly readable. Only the named Auth
-- user may SELECT them. All visitors to the public website still see the
-- *derived* information the Streamlit UI displays.

BEGIN;

ALTER TABLE public.prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.advice_events ENABLE ROW LEVEL SECURITY;

-- If an earlier public-read policy was applied, revoke that access first.
DROP POLICY IF EXISTS farmdtech_public_historical_prices_read ON public.prices;
DROP POLICY IF EXISTS farmdtech_private_reader_select ON public.prices;

-- Fail closed rather than unintentionally leaving other permissive policies.
DO $$
BEGIN
  IF EXISTS (
      SELECT 1 FROM pg_policies
      WHERE schemaname = 'public' AND tablename = 'prices'
  ) THEN
    RAISE EXCEPTION 'Existing prices policies remain: inspect pg_policies before allowing private reader access';
  END IF;
  IF NOT EXISTS (
      SELECT 1 FROM auth.users
      WHERE id = 'REPLACE_WITH_READER_UUID'::uuid
  ) THEN
    RAISE EXCEPTION 'Reader user UUID does not match an auth.users record';
  END IF;
END;
$$;

-- Privilege grants and RLS are two separate controls.
REVOKE ALL PRIVILEGES ON TABLE public.prices FROM anon, authenticated;
GRANT SELECT ON TABLE public.prices TO authenticated;
REVOKE ALL PRIVILEGES ON TABLE public.advice_events FROM anon, authenticated;

CREATE POLICY farmdtech_private_reader_select
ON public.prices
FOR SELECT
TO authenticated
USING ((SELECT auth.uid()) = 'REPLACE_WITH_READER_UUID'::uuid);

COMMIT;

-- After running, check:
-- SELECT policyname, roles, cmd, qual FROM pg_policies
-- WHERE schemaname='public' AND tablename='prices';
-- SELECT grantee, privilege_type FROM information_schema.role_table_grants
-- WHERE table_schema='public' AND table_name='prices'
--   AND grantee IN ('anon','authenticated');
--
-- Expected: 1 SELECT policy for authenticated, no anon privileges,
-- and no INSERT/UPDATE/DELETE grants for authenticated.
