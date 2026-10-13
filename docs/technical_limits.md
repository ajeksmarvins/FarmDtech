# Honest Scope & Technical Limitations

1. The bundled World Bank RTFP source is **monthly**, and its estimated `c_*` series are **model-generated closing-price estimates**, NOT observed current transactions. We do not equate forecast accuracy against these estimates with external real-world price accuracy.
2. The clean dataset includes **67 physical market IDs in 15 state labels**, not every state in Nigeria. The raw file has 74 unique identifiers including averages; the cleaned file excludes those aggregates.
3. Crop definitions: Beans=`beans` (2.5 kg raw basket), Maize=`maize_fao` (1 kg), Rice=`rice_fao` (1 kg). The `rice` series is a distinct 2.8 kg basket and is not mixed with `rice_fao`.
4. XGBoost lag-feature forecasting is **next month**. The actual brief wants **next week**; add verified *weekly observed* historical price data and retrain before describing it as complete.
5. The value used for each market is the **latest available date for that crop and selected evidence type**. `stale` warns if >65 days old. Price for October 2026 is a dataset estimate as of its October 5 revision, not a verified trade on the current day.
6. Transport cost uses haversine **straight-line kilometers** and a farmer-entered NGN/km estimate. Real road distance, border risk, freight type, spoilage and physical market access can change the decision.
7. Supabase database tables and synchronization script are included but require external account and server-side keys; app runs from bundled local CSV until connected. No service-role key belongs in GitHub.
8. n8n workflow receives and acknowledges alert payloads; this is **not SMS delivery**. A second Twilio workflow template requires credentials, number, sender and actual integration testing. Secure webhooks, protect subscribers' phone numbers, get consent and verify provider receipts.
9. New sources/reports import to a pending verification CSV. No automatic merger of unverified data into farmer recommendations.
10. The capstone requires three independent projects; this archive implements **only the FarmDtech/FarmToMarket agritech project**. Presentation video and public hosted URL still need to be recorded/deployed by the team.
