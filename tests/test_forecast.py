import numpy as np
import pandas as pd
from src.forecast import make_features, evaluate


def test_features_no_same_month_leakage():
    dates = pd.date_range('2024-01-01', periods=7, freq='MS')
    data = pd.DataFrame({'date': dates, 'crop': ['Maize']*7, 'price_kind':['estimated']*7,
        'market_id':['x']*7, 'price_ngn_per_kg': np.arange(100,107),
        'latitude':[10.0]*7, 'longitude':[8.0]*7})
    data['date'] = data['date'].astype(str)
    feats=make_features(data,'Maize')
    assert feats.iloc[0]['lag1'] == 102
    assert feats.iloc[0]['price_ngn_per_kg'] == 103


def test_perfect_forecast():
    score=evaluate(np.array([100,200]),np.array([100,200]))
    assert score['wmape_percent'] == 0
