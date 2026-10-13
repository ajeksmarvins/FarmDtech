"""Sync cleaned prices to private Supabase database (optional).

Run: python scripts/sync_supabase.py
"""
import os
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.storage import upsert_prices

csv_path = ROOT / 'data/processed/prices_long.csv'
if not csv_path.exists():
    sys.exit('Run python scripts/prepare_data.py first')
if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_SERVICE_ROLE_KEY'):
    sys.exit('Environment variables SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required. Never commit keys.')
df = pd.read_csv(csv_path)
columns = ['date','crop','crop_code','market_id','market','state','latitude','longitude','price_ngn_per_kg','price_kind','source','original_unit_kg','source_value_ngn','data_coverage_recent','survey_confidence']
records = df[columns].astype(object).where(pd.notna(df[columns]), None).to_dict(orient='records')
print(f"Upserted {upsert_prices(records)} records to Supabase")
