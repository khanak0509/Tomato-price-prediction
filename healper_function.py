from fastapi import FastAPI , HTTPException
import numpy as np
import pandas as pd 
import mysql.connector
import joblib
from pydantic import BaseModel
import redis
import json
from datetime import datetime, timedelta
from sklearn.preprocessing import LabelEncoder
import math
connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="tomato_db"
)
def get_current_market_data(market_name):
     cursor = connection.cursor(dictionary=True)
     query = """
SELECT * FROM tomato_prices
WHERE market_name = %s AND price_per_quintal IS NOT NULL
ORDER BY week_start_date DESC
LIMIT 1
"""
     cursor.execute(query, ([market_name]))
     result = cursor.fetchone()
     cursor.close()
     return result
def get_all_market():
    cursor = connection.cursor(dictionary=True)
    query = "SELECT DISTINCT market_name FROM tomato_prices"
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    markets = [row['market_name'] for row in results]
    return markets
def get_price_history(market_name, weeks=20):
    query = """
SELECT week_start_date, price_per_quintal
FROM tomato_prices
WHERE market_name = %s AND price_per_quintal IS NOT NULL
ORDER BY week_start_date DESC
LIMIT %s
"""
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, (market_name, weeks))
    results = cursor.fetchall()
    cursor.close()
    return [
        {
            'date' : h['week_start_date'], 
            'price' : float(h['price_per_quintal'])
        }
        for h in results
    ]
def get_market_stats(market_name):
    cursor = connection.cursor(dictionary=True)
    query = """
    SELECT AVG(price_per_quintal) as avg_price, STDDEV(price_per_quintal) as std_price
    FROM tomato_prices
    WHERE market_name = %s AND price_per_quintal IS NOT NULL
    """
    cursor.execute(query, ([market_name]))
    result = cursor.fetchone()
    cursor.close()
    return result
def calculate_confidence(market_name, horizon_days):
    base_confidence = 0.95
    decay = (horizon_days / 30) * 0.2  
    confidence = base_confidence - decay
    return max(0.5, min(confidence, 0.99))
def prepare_features(current_data, horizon_days):
    market_name = current_data['market_name']
    current_date = current_data['week_start_date']
    if isinstance(current_date, str):
        current_date = datetime.strptime(current_date, '%Y-%m-%d').date()
    elif isinstance(current_date, datetime):
        current_date = current_date.date()
    target_date = current_date + timedelta(days=horizon_days)
    history = get_price_history(market_name, weeks=20)
    if not history:
        history = [{'date': current_date, 'price': float(current_data['price_per_quintal'])}]
    df_hist = pd.DataFrame(history)
    df_hist['date'] = pd.to_datetime(df_hist['date'])
    df_hist = df_hist.sort_values('date')
    current_price = float(current_data['price_per_quintal'])
    features = {}
    features['month'] = target_date.month
    features['week_number'] = target_date.isocalendar()[1]
    features['year'] = target_date.year
    features['day_of_week'] = target_date.weekday()
    features['quarter'] = (target_date.month - 1) // 3 + 1
    features['is_month_start'] = 1 if target_date.day == 1 else 0
    features['is_month_end'] = 1 if (target_date + timedelta(days=1)).month != target_date.month else 0
    features['month_sin'] = np.sin(2 * np.pi * features['month'] / 12)
    features['month_cos'] = np.cos(2 * np.pi * features['month'] / 12)
    features['week_sin'] = np.sin(2 * np.pi * features['week_number'] / 52)
    features['week_cos'] = np.cos(2 * np.pi * features['week_number'] / 52)
    month = features['month']
    features['season_winter'] = 1 if month in [11, 12, 1, 2] else 0
    features['season_summer'] = 1 if month in [3, 4, 5, 6] else 0
    features['season_monsoon'] = 1 if month in [7, 8, 9, 10] else 0
    all_markets = get_all_market()
    all_markets.sort()
    le = LabelEncoder()
    le.fit(all_markets)
    try:
        features['market_encoded'] = le.transform([market_name])[0]
    except:
        features['market_encoded'] = 0
    stats = get_market_stats(market_name)
    market_avg = float(stats['avg_price']) if stats['avg_price'] else current_price
    market_std = float(stats['std_price']) if stats['std_price'] else 0.0
    features['market_avg_price'] = market_avg
    features['market_volatility'] = market_std
    features['price_vs_market_avg'] = current_price - market_avg
    def get_price_at_lag(lag_weeks):
        lag_date = pd.to_datetime(target_date - timedelta(weeks=lag_weeks))
        past_data = df_hist[df_hist['date'] <= lag_date]
        if not past_data.empty:
            return past_data.iloc[-1]['price']
        else:
            return df_hist.iloc[0]['price']
    features['price_lag_1'] = get_price_at_lag(1)
    features['price_lag_2'] = get_price_at_lag(2)
    features['price_lag_4'] = get_price_at_lag(4)
    features['price_lag_8'] = get_price_at_lag(8)
    features['price_lag_12'] = get_price_at_lag(12)
    prices = df_hist['price'].values
    def get_rolling_stats(window):
        if len(prices) >= window:
            window_slice = prices[-window:]
            return {
                'mean': np.mean(window_slice),
                'std': np.std(window_slice),
                'min': np.min(window_slice),
                'max': np.max(window_slice)
            }
        else:
            return {
                'mean': np.mean(prices),
                'std': np.std(prices) if len(prices) > 1 else 0,
                'min': np.min(prices),
                'max': np.max(prices)
            }
    stats_4 = get_rolling_stats(4)
    features['price_ma_4'] = stats_4['mean']
    features['price_std_4'] = stats_4['std']
    features['price_min_4'] = stats_4['min']
    features['price_max_4'] = stats_4['max']
    stats_8 = get_rolling_stats(8)
    features['price_ma_8'] = stats_8['mean']
    features['price_std_8'] = stats_8['std']
    features['price_min_8'] = stats_8['min']
    features['price_max_8'] = stats_8['max']
    stats_12 = get_rolling_stats(12)
    features['price_ma_12'] = stats_12['mean']
    features['price_std_12'] = stats_12['std']
    features['price_min_12'] = stats_12['min']
    features['price_max_12'] = stats_12['max']
    def get_growth(weeks):
        if len(prices) > weeks:
            curr = prices[-1]
            prev = prices[-(weeks+1)]
            return (curr - prev) / prev if prev != 0 else 0
        return 0
    features['price_growth_1w'] = get_growth(1)
    features['price_growth_4w'] = get_growth(4)
    features['price_growth_12w'] = get_growth(12)
    features['price_momentum'] = current_price - features['price_ma_4']
    features['price_relative_strength'] = current_price / features['price_ma_12'] if features['price_ma_12'] != 0 else 0
    feature_cols = joblib.load('models/feature_columns.pkl')
    df_features = pd.DataFrame([features])
    for col in feature_cols:
        if col not in df_features.columns:
            df_features[col] = 0
    return df_features[feature_cols]

def predict_market_scenarios(market_name, model, feature_cols):
    horizons = [7, 14, 21, 30, 45, 60]
    scenarios = []
    
    current_data = get_current_market_data(market_name)
    if current_data is None:
        return []

    current_price_float = float(current_data['price_per_quintal'])

    for days in horizons:
        try:
            features = prepare_features(current_data, days)
            predicted_price = float(model.predict(features)[0])
            confidence = calculate_confidence(market_name, days)
            
            scenarios.append({
                "horizon_days": days,
                "prediction_date": (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d'),
                "predicted_price": predicted_price,
                "confidence": float(confidence),
                "change_percent": float(
                    (predicted_price - current_price_float) /
                    current_price_float * 100
                ),
                "trend": "up" if predicted_price > current_price_float else "down"
            })
        except Exception as e:
            print(f"Error predicting for {market_name} at {days} days: {e}")
            continue
            
    return scenarios