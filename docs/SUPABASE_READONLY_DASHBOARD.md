# Connect the live FarmDtech dashboard to Supabase — read-only

## Status
The project has 52,283 historical World Bank price rows in \`public.prices\` (67 market identifiers, 15 state labels). The dashboard currently includes a bundled local CSV backup, so cloud errors should not cause an outage.

**Important:** Supabase storing old data does NOT make it current market data. Price records are historical observed or World Bank model-estimated, not verified buyer quotes.

## 1. Review whether your raw historic crop-price records may be publicly read
This capstone app is publicly accessible. To allow an unauthenticated read-only client, you must authorize public access to *all rows in public.prices*. If these rows should not be exposed as a dataset, **do not run the policy**; the Streamlit app continues using the local CSV. Review data source licensing/redistribution obligations first.

Open Supabase → SQL Editor. Review and run:
\`supabase/readonly_prices_policy.sql\`

It:
- explicitly revokes anonymous/authenticated privileges;
- grants **SELECT only** on \`public.prices\` to the \`anon\` role;
- adds an RLS SELECT-only policy;
- leaves \`public.advice_events\` inaccessible to anonymous callers;
- does not alter the elevated \`service_role\` used by the one-time importer.

**Never disable RLS** or grant \`INSERT/UPDATE/DELETE\` to anonymous visitors just to get this dashboard working.

## 2. Get the low-privilege publishable key

In Supabase, choose FarmDtech → Project Settings → API Keys (or project Connect panel). Copy the key whose prefix is **\`sb_publishable_\`**. It does not have database-admin privileges.

Do **not** use:
- \`service_role\` / legacy role secret;
- \`sb_secret_\` key;
- database password.

## 3. Configure Streamlit Cloud secrets
Go to https://share.streamlit.io → FarmDtech → Manage app → Settings → Secrets.

Enter TOML as follows, replacing placeholders ONLY in the Streamlit secrets editor (not GitHub):

\`\`\`toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_YOUR_KEY"
\`\`\`

Save. Streamlit may restart the application. Do not add a service-role key to a public web application's configuration.

## 4. Verify

Open https://farmdtech.streamlit.app in Incognito.

A caption near the top should read:
**Price database: Supabase (historical World Bank prices).**

- If you see **Bundled historical CSV**, the publishable key and/or Project URL are not configured.
- If you see **Bundled historical CSV (fallback)** with a warning, your read-only API request failed. Verify SQL RLS/GRANT, project status and key. Never replace the publishable key with a service-role key.
- Dashboard's data rows remain historic or estimated, regardless of where they are stored. The previously saved monthly forecasts remain precomputed and are *not retrained* when the database changes.

The loader pages through at most 100,000 records, with a stable ID sort and a 30-minute Streamlit cache. It selects only columns needed for the dashboard. If your dataset grows beyond 100,000 rows or requests become slow, introduce a server-side materialized view or dedicated short response endpoint with a narrower read-only policy before scaling.

## 5. Local verification without secrets

\`\`\`powershell
git pull origin main
python -m pytest -q
\`\`\`

Without \`SUPABASE_PUBLISHABLE_KEY\`, the local Streamlit app intentionally uses the bundled CSV. Service-role environment variables remain for the **separate data-import script**, not for fetching public app data.

## Revoke public reading if needed
If you later decide the source records should no longer be publicly readable, run in Supabase SQL Editor:

\`\`\`sql
DROP POLICY IF EXISTS farmdtech_public_historical_prices_read ON public.prices;
REVOKE SELECT ON public.prices FROM anon;
\`\`\`

The live app will safely fall back to bundled CSV after the next cache refresh, assuming the CSV remains deployed.
