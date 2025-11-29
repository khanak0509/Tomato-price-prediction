# Tomato Price Prediction API Documentation

This document provides `curl` commands to test the various endpoints of the Tomato Price Prediction API.

**Base URL:** `http://127.0.0.1:8000`

## 1. Health Check

Check if the API is running.

```bash
curl -X GET "http://127.0.0.1:8000/"
```

## 2. Get All Markets

Retrieve a list of all available markets in the database.

```bash
curl -X POST "http://127.0.0.1:8000/markets" \
     -H "Content-Type: application/json" \
     -d '{}'
```

## 3. Get Market History

Retrieve historical price data for a specific market.

- `market_name`: Name of the market (e.g., "Achalda APMC")
- `weeks`: Number of weeks of history to retrieve (default: 20)

```bash
curl -X POST "http://127.0.0.1:8000/market/history" \
     -H "Content-Type: application/json" \
     -d '{
           "market_name": "Achalda APMC",
           "weeks": 10
         }'
```

## 4. Predict Price (Single)

Predict the price for a single market for a specific horizon.

- `market_name`: Name of the market
- `horizon_days`: Number of days into the future to predict (default: 7)

```bash
curl -X POST "http://127.0.0.1:8000/predict" \
     -H "Content-Type: application/json" \
     -d '{
           "market_name": "Achalda APMC",
           "horizon_days": 7
         }'
```

## 5. Predict Batch

Predict prices for multiple markets simultaneously.

- `market_names`: List of market names
- `horizon_days`: Number of days into the future to predict (default: 7)

```bash
curl -X POST "http://127.0.0.1:8000/predict/batch" \
     -H "Content-Type: application/json" \
     -d '{
           "market_names": ["Achalda APMC", "Varanasi APMC", "Agra APMC"],
           "horizon_days": 7
         }'
```

## 6. Predict Scenarios

Generate predictions for a specific market across multiple time horizons (7, 14, 21, 30, 45, 60 days).

- `market_name`: Name of the market

```bash
curl -X POST "http://127.0.0.1:8000/predict/scenarios" \
     -H "Content-Type: application/json" \
     -d '{
           "market_name": "Achalda APMC"
         }'
```
