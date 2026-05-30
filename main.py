from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import joblib
import pandas as pd
import requests

# 1. Start the API
app = FastAPI(title="Agri-AI API")

# Add CORS middleware to allow requests from the React frontend (running on localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Since it's local dev, "*" is fine
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Load your saved model
try:
    model = joblib.load('crop_model.joblib')
except FileNotFoundError:
    model = None

# 3. Define the expected data structure
class CropData(BaseModel):
    temperature: float
    humidity: float
    rainfall: float

# 4. Create the climate fetching endpoint
@app.get("/api/climate")
def get_climate(lat: float, lon: float, season: int):
    SEASON_CONFIG = {
        1: [3,4,5,6,7,8],
        2: [9,10,11,12,1,2],
        3: list(range(1, 13)),
    }
    target_months = SEASON_CONFIG.get(season, SEASON_CONFIG[3])
    
    try:
        # Elevation
        elev_res = requests.get(f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}").json()
        elevation = elev_res.get('elevation', [0])[0]
        
        # Climate
        climate_res = requests.get(
            "https://climate-api.open-meteo.com/v1/climate",
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": "2014-01-01",
                "end_date": "2024-12-31",
                "models": "EC_Earth3P_HR",
                "daily": "temperature_2m_mean,relative_humidity_2m_max,precipitation_sum"
            },
            timeout=30
        ).json()
        
        dates = climate_res['daily']['time']
        temps = climate_res['daily']['temperature_2m_mean']
        humidities = climate_res['daily']['relative_humidity_2m_max']
        rains = climate_res['daily']['precipitation_sum']

        s_temps, s_hums, s_rains = [], [], []
        for i, d in enumerate(dates):
            month = int(d[5:7])
            if month in target_months:
                if temps[i] is not None: s_temps.append(temps[i])
                if humidities[i] is not None: s_hums.append(humidities[i])
                if rains[i] is not None: s_rains.append(rains[i])

        temp = round(sum(s_temps) / len(s_temps), 2) if s_temps else 25.0
        humidity = round(sum(s_hums) / len(s_hums), 1) if s_hums else 60.0
        rain = round(sum(s_rains) / 10, 1) if s_rains else 100.0

    except Exception as e:
        # Fallback to mock data if API fails
        elevation = 50
        temp = 25.0
        humidity = 60.0
        rain = 100.0

    return {
        "elevation": elevation,
        "temperature": temp,
        "humidity": humidity,
        "rainfall": rain
    }

# 5. Create the prediction endpoint
@app.post("/api/predict")
def predict_crop(data: CropData):
    if not model:
        return {"error": "Model not found. Please train it first."}

    # Package the incoming data into a DataFrame with the correct column names
    features = pd.DataFrame(
        [[data.temperature, data.humidity, data.rainfall]],
        columns=['temperature', 'humidity', 'rainfall']
    )
    
    probs = model.predict_proba(features)[0]
    results = pd.DataFrame({'Crop': model.classes_, 'Confidence': probs})
    top3 = results.sort_values('Confidence', ascending=False).head(3)

    return {
        "crop": top3.iloc[0]['Crop'],
        "confidence": float(top3.iloc[0]['Confidence']),
        "alternatives": [
            {"crop": top3.iloc[1]['Crop'], "confidence": float(top3.iloc[1]['Confidence'])},
            {"crop": top3.iloc[2]['Crop'], "confidence": float(top3.iloc[2]['Confidence'])}
        ]
    }