# FarmDtech: private Supabase price access from the public Streamlit server

This replaces the proposed public-SELECT approach. Do NOT run
\`supabase/readonly_prices_policy.sql\` for this setup.

## Goal
The Streamlit website stays publicly usable, but anonymous requests directly
to Supabase cannot list \`public.prices\`. A dedicated Supabase Auth account
signs in from the Streamlit Python SERVER. Its UUID alone is allowed to read
historical prices under Row Level Security. The credentials are never sent
to visitor browsers or saved in GitHub.

**Important distinction:** End users still see the prices and charts that
the public FarmDtech UI displays. A public page cannot keep all displayed
information confidential.

## One-time setup (in order)

### 1. Create a dedicated reader user

Supabase Dashboard → FarmDtech → Authentication → Users → Add user.
Create a new email/password user (or invite a project-owned email account,
finish confirmation, and set its password).

Use a long unique password. This is a *service reader user*, not the
database owner, not your GitHub account, and not \`service_role\`.

Copy that user's UUID from Authentication → Users. **Do not send passwords
or API secret keys in chat or screenshots.** User UUID is not a credential.

### 2. Enable SELECT-only RLS for precisely that user

Open \`supabase/private_reader_policy.sql\`. In the Supabase SQL Editor,
replace BOTH occurrences of \`REPLACE_WITH_READER_UUID\` with that exact
reader UUID, then run the complete script.

The script:
- enables RLS;
- revokes all client-role privileges on \`prices\`;
- grants only table SELECT to the \`authenticated\` role;
- adds exactly one SELECT RLS policy for the one named reader UUID;
- revokes privileges on \`advice_events\` for anon/authenticated;
- removes the earlier permissive anonymous price-reading policy if present;
- **refuses to proceed if an unexpected existing price policy remains**.

With that combination, an anonymous REST request cannot read the table,
and other signed-in users see no rows. The reader cannot write.

### 3. Locate the publishable project key

Supabase Settings → API Keys → Publishable key, beginning
\`sb_publishable_\`. This key is not a privileged secret.

Do NOT use any \`sb_secret_\`, \`service_role\`, or legacy admin JWT in the
Streamlit dashboard.

### 4. Configure only Streamlit server-side secrets

Streamlit Community Cloud → Manage FarmDtech → Settings → Secrets.
Paste the following TOML with actual values **inside the Streamlit UI only**:

\`\`\`toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_YOUR_KEY"
SUPABASE_READER_EMAIL = "private-reader@your-team-controlled-domain.example"
SUPABASE_READER_PASSWORD = "YOUR_LONG_PRIVATE_READER_PASSWORD"
\`\`\`

No Supabase service-role key belongs here. Avoid saving any real
credentials in \`.env.example\` (committed to Git) or in screenshots.
The local importer \`scripts/sync_supabase.py\` remains separate and
may continue to use temporary service-role credentials for bulk writes.

### 5. Check the live app

Open https://farmdtech.streamlit.app in a new Incognito window.

Expected caption:
**Price database: Private Supabase reader (historical World Bank prices).**

If your reader account or RLS policy is not configured, the app remains
operational with **Bundled historical CSV (fallback)** and a warning.
The application caches cloud rows for 30 minutes and handles fresh
sign-ins after cache expiry.

Local test (without any credentials):
\`\`\`powershell
git pull origin main
python -m pytest -q
\`\`\`

**The cloud loader has automated mocked tests, but real Supabase RLS access
and deployment must still be tested end-to-end.** Never fix a denied read by
turning off RLS or installing an admin key in Streamlit.

## Test protection in SQL Editor

You can inspect policies/grants (safe to screenshot if no secrets shown):

\`\`\`sql
SELECT policyname, roles, cmd, qual
FROM pg_policies
WHERE schemaname='public' AND tablename='prices';

SELECT grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema='public' AND table_name='prices'
AND grantee IN ('anon','authenticated')
ORDER BY grantee, privilege_type;
\`\`\`

Expect ONE \`SELECT\` policy restricted to the dedicated reader UUID;
\`authenticated\` has SELECT only and \`anon\` has no privileges.

## If you must revoke access

\`\`\`sql
DROP POLICY IF EXISTS farmdtech_private_reader_select ON public.prices;
REVOKE SELECT ON public.prices FROM authenticated;
\`\`\`

Then reset or delete the dedicated Auth reader user as needed. With no
cloud access, the app safely falls back to the bundled historical CSV.

## Limits

- Storage in Supabase does **not** make the World Bank historical/modelled
  estimates current market quotes.
- Your weekly FEWS NET backtests are separate, ending in 2024.
- The dashboard reads 52,283 rows in pages and caches them for 30 minutes.
  Later, improve performance with an authorized narrow aggregation or
  paginated view after checking dataset redistribution rights.
- The public Streamlit interface still reveals the information users see
  on it, even though the underlying database cannot be queried anonymously.
