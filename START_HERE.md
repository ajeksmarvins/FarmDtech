# FarmDtech — your first 5 minutes

The core software, processed dataset, forecasts and model files are included.

## Run locally in Windows VS Code

1. Unzip FarmDtech and open the folder in VS Code.
2. Open Terminal > New Terminal.
3. Run the following commands in this order:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

4. Visit **http://localhost:8501**.
5. Use the sidebar to select a crop, choose your nearest market, adjust quantity and transportation costs.

## Next priorities

- Use `README.md` for full deployment and optional n8n/Supabase setup.
- To reconstruct the data: `python scripts/prepare_data.py`.
- To retrain the models: `python scripts/train_models.py`.
- To verify the code: `python -m pip install pytest` then `python -m pytest -q`.

**Data warning:** the source is monthly. Any displayed next-month forecasts are research-model outputs, not verified current market prices. n8n acknowledgement is NOT SMS delivery. Public URL and external account integrations are not included.
