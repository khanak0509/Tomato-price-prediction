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


XGBoost_model = joblib.load('models/xgboost_tomato_model_20251128.pkl')
features =  joblib.load('models/feature_columns.pkl')


print(features)