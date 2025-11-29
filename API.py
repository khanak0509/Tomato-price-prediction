from fastapi import FastAPI , HTTPException
import numpy as np
import pandas as pd 
import mysql.connector
import joblib
from pydantic import BaseModel
import redis
import json
from healper_function import *
from datetime import datetime, timedelta

connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="tomato_db"
)

cache = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True  
)
CACHE_TTL = 3600

app = FastAPI()

class PredictRequest(BaseModel):
    market_name: str
    horizon_days: int = 7

class MarketHistoryRequest(BaseModel):
    market_name: str
    weeks: int = 20

class ScenarioPredictRequest(BaseModel):
    market_name: str

    horizon_days: int = 7 
    scenarios: list[str] = []

class BatchPredictRequest(BaseModel):
    market_names: list[str]
    horizon_days: int = 7

XGBoost_model = joblib.load('models/xgboost_tomato_model_20251128.pkl')
features =  joblib.load('models/feature_columns.pkl')

def _predict_price_logic(market_name, horizon_days):
    cache_key = f"predict:{market_name}:{horizon_days}"
    cached_value = cache.get(cache_key)

    if cached_value:
            print("Returning from CACHE")
            return json.loads(cached_value)
    
    current_data = get_current_market_data(market_name)
    if current_data is None:
            raise HTTPException(status_code=404, detail="Market not found")
    
    features_df = prepare_features(current_data, horizon_days)
    predicted_price = XGBoost_model.predict(features_df)[0]
    confidence = calculate_confidence(market_name, horizon_days)
    
    current_price_float = float(current_data['price_per_quintal'])
    current_price_date = current_data['week_start_date']
    
    if isinstance(current_price_date, datetime):
        base_date = current_price_date
        current_price_date_str = current_price_date.strftime('%Y-%m-%d')
    elif isinstance(current_price_date, str):
        base_date = datetime.strptime(current_price_date, '%Y-%m-%d')
        current_price_date_str = current_price_date
    else:
        base_date = datetime.strptime(str(current_price_date), '%Y-%m-%d')
        current_price_date_str = str(current_price_date)
    
    prediction_date = base_date + timedelta(days=horizon_days)
    
    result = {
            "market_name": market_name,
            "current_price": current_price_float,
            "current_price_date": current_price_date_str,
            "predicted_price": float(predicted_price),
            "horizon_days": horizon_days,
            "prediction_date": prediction_date.strftime('%Y-%m-%d'),
            "confidence": float(confidence),
            "change_percent": float(
                (predicted_price - current_price_float) /
                current_price_float * 100
            ),
            "trend": "up" if predicted_price > current_price_float else "down",
            "timestamp": datetime.now().isoformat()
        }
    
    cache.setex(cache_key, CACHE_TTL, json.dumps(result))
    return result

@app.get("/")
def health():
    return {"health" : "ok"}

@app.post('/predict')
def predict_price(request : PredictRequest):
    return _predict_price_logic(request.market_name, request.horizon_days)

@app.post('/markets')
def get_markets():
    markets = get_all_market()
    return {
        "markets": markets,
        'count' : len(markets),
        'timestamp' : datetime.now().isoformat()
    }

@app.post('/market/history')
def get_market_history(request : MarketHistoryRequest):
    market_name = request.market_name
    weeks = request.weeks
    history = get_price_history(market_name, weeks)
    return {
        "market_name": market_name,
        "history": history,
        "count": len(history),
        "timestamp": datetime.now().isoformat()
    }   

@app.post('/predict/batch')
def predict_batch(request : BatchPredictRequest):
    market_names = request.market_names
    horizon_days = request.horizon_days
    results = []
    for market_name in market_names:
        try:
            result = _predict_price_logic(market_name, horizon_days)
            results.append(result)
        except HTTPException as e:
            results.append({
                "market_name": market_name,
                "error": e.detail
            })
    return {
        "results": results,
        'count' : len(results),
        "timestamp": datetime.now().isoformat()
    }
    
@app.post('/predict/scenarios')
def predict_scenarios(request : ScenarioPredictRequest):
    market_name = request.market_name
    # Use the helper function for scenarios
    # We need to pass the model and feature columns
    scenarios = predict_market_scenarios(market_name, XGBoost_model, features)
    
    return {
        "market_name": market_name,
        "scenarios": scenarios,
        'count' : len(scenarios),
        "timestamp": datetime.now().isoformat()
    }   


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
