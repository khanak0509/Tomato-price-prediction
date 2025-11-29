import pandas as pd
import mysql.connector
import numpy as np
import json
import joblib
from datetime import datetime, timedelta
from healper_function import prepare_features, get_current_market_data, calculate_confidence

def insert_data():
    print("Starting database population script...")
    
    print("\nConnecting to database...")
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="1234",
            database="tomato_db"
        )
        cursor = connection.cursor()
    except mysql.connector.Error as err:
        print(f"Database Connection Error: {err}")
        return

    print("\nReading CSV file...")
    try:
        df = pd.read_csv("fial_tomato.csv")
    except FileNotFoundError:
        print("Error: fial_tomato.csv not found.")
        return

    df = df.rename(columns={
        "market": "market_name",
        "date_started": "week_start_date",
        "week_end_date": "week_end_date",
        "price_per_quintal": "price_per_quintal",
        "year": "year",
        "month": "month"
    })
    df["price_per_quintal"] = pd.to_numeric(df["price_per_quintal"], errors='coerce')
    df["district"] = None
    df["state"] = "Uttar Pradesh"
    df["volume_traded"] = None
    df["week_number"] = pd.to_datetime(df["week_start_date"]).dt.isocalendar().week.astype(int)
    df["data_source"] = "Agmarknet"
    df = df.replace({np.nan: None})

    print("\nPopulating markets_master...")
    unique_markets = df['market_name'].unique()
    market_data = [(m, "Uttar Pradesh") for m in unique_markets]
    
    market_query = """
    INSERT INTO markets_master (market_name, state)
    VALUES (%s, %s)
    ON DUPLICATE KEY UPDATE market_name=market_name;
    """
    cursor.executemany(market_query, market_data)
    connection.commit()
    print(f"Processed {len(unique_markets)} markets.")

    print("\nPopulating tomato_prices...")
    columns_to_insert = [
        "market_name", "district", "state", "week_start_date", "week_end_date",
        "price_per_quintal", "volume_traded", "year", "month", "week_number", "data_source"
    ]
    df_prices = df[columns_to_insert]
    data_to_insert = [tuple(x) for x in df_prices.to_numpy()]

    price_query = """
    INSERT INTO tomato_prices
    (market_name, district, state, week_start_date, week_end_date,
     price_per_quintal, volume_traded, year, month, week_number, data_source)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
    price_per_quintal = VALUES(price_per_quintal),
    updated_at = CURRENT_TIMESTAMP;
    """
    
    batch_size = 1000
    for i in range(0, len(data_to_insert), batch_size):
        batch = data_to_insert[i:i + batch_size]
        cursor.executemany(price_query, batch)
        connection.commit()
        print(f"Inserted {min(i + batch_size, len(data_to_insert))} price records...")

    print("\nPopulating model_metrics...")
    try:
        with open('models/model_metadata.json', 'r') as f:
            metadata = json.load(f)
        
        model_name = metadata.get('model_name', 'XGBoost'). # i have only data of XGBoost so i am assuming it is XGBoost
        model_version = 'v1.0' # for now i am assuming 
        eval_date = datetime.now().strftime('%Y-%m-%d')
        
        metrics = [
            ('MAE', metadata.get('test_mae', 0)),
            ('MAPE', metadata.get('test_mape', 0)),
            ('Accuracy', metadata.get('test_accuracy', 0))
        ]
        
        metric_query = """
        INSERT INTO model_metrics 
        (model_name, model_version, metric_type, metric_value, evaluation_date, test_samples)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE metric_value=VALUES(metric_value);
        """
        
        for m_type, m_val in metrics:
            cursor.execute(metric_query, (
                model_name, model_version, m_type, m_val, eval_date, metadata.get('test_samples', 0)
            ))
        connection.commit()
        print("Model metrics inserted.")
    except FileNotFoundError:
        print("Warning: models/model_metadata.json not found. Skipping metrics.")

    print("\nPopulating price_predictions (Generating samples)...")
    try:
        model = joblib.load('models/xgboost_tomato_model_20251128.pkl')
        feature_cols = joblib.load('models/feature_columns.pkl')
        
        sample_markets = unique_markets[:5]
        horizon_days = 7
        prediction_date = datetime.now().date()
        target_date = prediction_date + timedelta(days=horizon_days)
        
        predictions_data = []
        for market in sample_markets:
            try:
                current_data = get_current_market_data(market)
                if current_data:
                    features = prepare_features(current_data, horizon_days)
                    pred_price = float(model.predict(features)[0])
                    conf_score = calculate_confidence(market, horizon_days)
                    actual_price = None # Future price unknown
                    
                    predictions_data.append((
                        market, 'tomato', prediction_date, target_date, 
                        pred_price, conf_score, 'XGBoost', 'v1.0', horizon_days,
                        actual_price, None
                    ))
            except Exception as e:
                print(f"Skipping prediction for {market}: {e}")

        pred_query = """
        INSERT INTO price_predictions
        (market_name, crop_type, prediction_date, target_date, predicted_price, 
         confidence_score, model_name, model_version, horizon_days, actual_price, prediction_error)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        if predictions_data:
            cursor.executemany(pred_query, predictions_data)
            connection.commit()
            print(f"Inserted {len(predictions_data)} sample predictions.")
        else:
            print("No predictions generated.")

    except Exception as e:
        print(f"Error generating predictions: {e}")

    cursor.close()
    connection.close()
    print("\nAll operations completed successfully!")

if __name__ == "__main__":
    insert_data()
