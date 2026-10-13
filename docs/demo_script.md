# FarmDtech: 7-minute live demo

- **0:00–1:00 Problem.** Market prices differ; smallholder farmers often lack timely transparent price data. State the exact coverage: 67 physical markets in 15 state labels in this dataset (NOT all Nigerian states).
- **1:00–2:00 Solution.** Show the architecture SVG. Explain monthly historic observed and model-estimated price series and conversion to NGN/kg.
- **2:00–4:00 Demonstration.** Launch `streamlit run app.py`. Choose Maize, nearby market, 1,000 kg and edit transport cost. Show recommendation change when cost rises. Download comparison table. Go to Forecast and review chart.
- **4:00–5:30 Under the hood.** Run or show `python scripts/prepare_data.py`, test summary, chronologically held-out score, XGBoost vs baseline, and optional n8n execution screenshot **only after actual configuration and test**.
- **5:30–6:30 Business case.** Use the clearly labelled illustrative calculation, not a verified savings claim. Discuss data-source limitations and need for verified weekly data.
- **6:30–7:00 Q&A.** Why next-month not next-week? The provided input is monthly. Why estimated prices? Source has sparse observations. Why transport input? Road distance & negotiated fees are not in source. What is not yet production-ready? Live verified quotes, notification-provider connection, public hosting, authenticated collection of market reports.

## Suggested demo queries

1. Select Maize, increase volume to 2,000 kg and compare top markets.
2. Increase estimated transport NGN/km and show how recommendation changes.
3. Select Beans and observe that 2.5kg basket prices were standardized to NGN/kg.
4. Compare XGBoost held-out error with the naive last-month baseline; **note baseline currently performs better**.
5. Show imported n8n demo workflow; never describe webhook acknowledgment as SMS delivery.
