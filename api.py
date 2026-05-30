from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import joblib
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="GeoAI Decision Support System", version="1.0.0")

# Allow React frontend (localhost:5173) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# ── Load model once at startup ──────────────────────────────────────────────
try:
    model = joblib.load("crop_model.joblib")
    print("✅ Model loaded successfully")
except Exception as e:
    model = None
    print(f"❌ Model loading failed: {e}")

# ── Ideal soil profiles (copied exactly from earth_predictor.py) ────────────
IDEAL_SOIL = {
    'apple':       {'N': 20.8,  'P': 134.2, 'K': 199.9, 'ph': 5.93},
    'banana':      {'N': 100.2, 'P': 82.0,  'K': 50.0,  'ph': 5.98},
    'barley':      {'N': 70.6,  'P': 51.5,  'K': 44.4,  'ph': 7.27},
    'blackgram':   {'N': 40.0,  'P': 67.5,  'K': 19.2,  'ph': 7.13},
    'chickpea':    {'N': 40.1,  'P': 67.8,  'K': 79.9,  'ph': 7.34},
    'coconut':     {'N': 22.0,  'P': 16.9,  'K': 30.6,  'ph': 5.98},
    'coffee':      {'N': 101.2, 'P': 28.7,  'K': 29.9,  'ph': 6.79},
    'cotton':      {'N': 117.8, 'P': 46.2,  'K': 19.6,  'ph': 6.91},
    'grapes':      {'N': 23.2,  'P': 132.5, 'K': 200.1, 'ph': 6.03},
    'jute':        {'N': 78.4,  'P': 46.9,  'K': 40.0,  'ph': 6.73},
    'kidneybeans': {'N': 20.8,  'P': 67.5,  'K': 20.0,  'ph': 5.75},
    'lentil':      {'N': 18.8,  'P': 68.4,  'K': 19.4,  'ph': 6.93},
    'maize':       {'N': 77.8,  'P': 48.4,  'K': 19.8,  'ph': 6.25},
    'mango':       {'N': 20.1,  'P': 27.2,  'K': 29.9,  'ph': 5.77},
    'mothbeans':   {'N': 21.4,  'P': 48.0,  'K': 20.2,  'ph': 6.83},
    'mungbean':    {'N': 21.0,  'P': 47.3,  'K': 19.9,  'ph': 6.72},
    'muskmelon':   {'N': 100.3, 'P': 17.7,  'K': 50.1,  'ph': 6.36},
    'oats':        {'N': 65.1,  'P': 40.2,  'K': 39.6,  'ph': 6.23},
    'olive':       {'N': 29.1,  'P': 24.4,  'K': 24.8,  'ph': 7.42},
    'orange':      {'N': 19.6,  'P': 16.6,  'K': 10.0,  'ph': 7.02},
    'papaya':      {'N': 49.9,  'P': 59.0,  'K': 50.0,  'ph': 6.74},
    'pigeonpeas':  {'N': 20.7,  'P': 67.7,  'K': 20.3,  'ph': 5.79},
    'pomegranate': {'N': 18.9,  'P': 18.8,  'K': 40.2,  'ph': 6.43},
    'potato':      {'N': 99.3,  'P': 58.2,  'K': 90.2,  'ph': 5.65},
    'rice':        {'N': 79.9,  'P': 47.6,  'K': 39.9,  'ph': 6.43},
    'rubber':      {'N': 40.7,  'P': 27.2,  'K': 25.3,  'ph': 5.47},
    'soybean':     {'N': 14.5,  'P': 53.4,  'K': 52.5,  'ph': 6.45},
    'sugarcane':   {'N': 88.2,  'P': 37.4,  'K': 192.9, 'ph': 6.79},
    'sunflower':   {'N': 81.5,  'P': 34.1,  'K': 45.4,  'ph': 6.98},
    'tea':         {'N': 56.3,  'P': 33.7,  'K': 39.4,  'ph': 5.19},
    'watermelon':  {'N': 99.4,  'P': 17.0,  'K': 50.2,  'ph': 6.50},
    'wheat':       {'N': 91.9,  'P': 59.2,  'K': 59.5,  'ph': 6.71},
}

# ── Training bounds (copied exactly from earth_predictor.py) ────────────────
CLIMATE_BOUNDS = {
    'temperature': (1.2,  43.7),
    'humidity':    (14.3, 100.0),
    'rainfall':    (20.2, 298.6),
}

SEASON_CONFIG = {
    "1": {"name": "Spring / Summer", "months": [3,4,5,6,7,8],      "label": "Mar–Aug"},
    "2": {"name": "Autumn / Winter", "months": [9,10,11,12,1,2],   "label": "Sep–Feb"},
    "3": {"name": "Full Year",       "months": list(range(1, 13)), "label": "Jan–Dec"},
}

# ── Pydantic request/response models ────────────────────────────────────────

class ClimateRequest(BaseModel):
    lat: float
    lon: float
    season: str  # "1", "2", or "3"

class PredictRequest(BaseModel):
    temperature: float
    humidity: float
    rainfall: float

class PrescriptionRequest(BaseModel):
    crop: str
    n: float
    p: float
    k: float
    ph: float

# ════════════════════════════════════════════════════════════════════════════
# ENDPOINT 1 — GET /api/climate
# Fetches elevation + 10-year seasonal climate averages for a coordinate
# Mirrors the logic from earth_predictor.py Pipeline A and Pipeline B
# ════════════════════════════════════════════════════════════════════════════
@app.post("/api/climate")
async def get_climate(req: ClimateRequest):
    if req.season not in SEASON_CONFIG:
        raise HTTPException(status_code=400, detail="Season must be '1', '2', or '3'")

    season = SEASON_CONFIG[req.season]
    target_months = season["months"]
    result = {}

    # ── Pipeline A: Elevation (Copernicus DEM via Open-Meteo) ──
    try:
        elev_res = requests.get(
            f"https://api.open-meteo.com/v1/elevation?latitude={req.lat}&longitude={req.lon}",
            timeout=10
        ).json()
        result["elevation"] = elev_res["elevation"][0]
    except Exception:
        result["elevation"] = None

    # ── Pipeline B: 10-year seasonal climate (Open-Meteo Climate API) ──
    try:
        climate_res = requests.get(
            "https://climate-api.open-meteo.com/v1/climate",
            params={
                "latitude":   req.lat,
                "longitude":  req.lon,
                "start_date": "2014-01-01",
                "end_date":   "2024-12-31",
                "models":     "EC_Earth3P_HR",
                "daily":      "temperature_2m_mean,relative_humidity_2m_max,precipitation_sum"
            },
            timeout=30
        ).json()

        dates      = climate_res["daily"]["time"]
        temps      = climate_res["daily"]["temperature_2m_mean"]
        humidities = climate_res["daily"]["relative_humidity_2m_max"]
        rains      = climate_res["daily"]["precipitation_sum"]

        s_temps, s_hums, s_rains = [], [], []
        for i, d in enumerate(dates):
            if int(d[5:7]) in target_months:
                if temps[i]      is not None: s_temps.append(temps[i])
                if humidities[i] is not None: s_hums.append(humidities[i])
                if rains[i]      is not None: s_rains.append(rains[i])

        result["temperature"] = round(sum(s_temps) / len(s_temps), 2)
        result["humidity"]    = round(sum(s_hums)  / len(s_hums),  1)
        result["rainfall"]    = round(sum(s_rains) / 10, 1)
        result["source"]      = "climate_api"

    except Exception as e:
        # Fallback: live OpenWeatherMap data
        try:
            w = requests.get(
                f"http://api.openweathermap.org/data/2.5/weather"
                f"?lat={req.lat}&lon={req.lon}&appid={API_KEY}&units=metric",
                timeout=10
            ).json()
            if str(w.get("cod")) == "200":
                result["temperature"] = w["main"]["temp"]
                result["humidity"]    = w["main"]["humidity"]
            else:
                result["temperature"] = 25.0
                result["humidity"]    = 60.0
        except Exception:
            result["temperature"] = 25.0
            result["humidity"]    = 60.0
        result["rainfall"] = 80.0
        result["source"]   = "fallback_live"

    # ── Validate against training bounds ──
    warnings = []
    for feature in ["temperature", "humidity", "rainfall"]:
        value = result.get(feature)
        if value is not None:
            lo, hi = CLIMATE_BOUNDS[feature]
            if not (lo <= value <= hi):
                warnings.append({
                    "feature": feature,
                    "value": value,
                    "min": lo,
                    "max": hi
                })

    result["warnings"]           = warnings
    result["is_out_of_distribution"] = len(warnings) > 0
    result["season_name"]        = season["name"]
    result["season_label"]       = season["label"]

    return result


# ════════════════════════════════════════════════════════════════════════════
# ENDPOINT 2 — POST /api/predict
# Runs the Random Forest climate model and returns top 5 crop predictions
# Mirrors the AI prediction block from earth_predictor.py
# ════════════════════════════════════════════════════════════════════════════
@app.post("/api/predict")
async def predict_crop(req: PredictRequest):
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    # Clamp to training bounds before prediction
    temp_c     = max(1.2,  min(43.7,  req.temperature))
    humidity_c = max(14.3, min(100.0, req.humidity))
    rain_c     = max(20.2, min(298.6, req.rainfall))

    features = pd.DataFrame(
        [[temp_c, humidity_c, rain_c]],
        columns=["temperature", "humidity", "rainfall"]
    )

    probs   = model.predict_proba(features)[0]
    results = pd.DataFrame({"crop": model.classes_, "confidence": probs})

    # ── AGRONOMIC GUARDRAILS (Heuristic Overrides) ──────────────────────────
    # Penalize tropical crops in cool climates to fix the "Tea Dominance" bias
    TROPICAL_CROPS = ['tea', 'banana', 'coconut', 'papaya', 'rubber', 'mango', 'coffee', 'orange']
    COLD_CROPS = ['apple', 'barley', 'oats', 'potato', 'wheat']

    for i, row in results.iterrows():
        crop_name = row['crop'].lower()
        if crop_name in TROPICAL_CROPS and req.temperature < 21.0:
            results.at[i, 'confidence'] *= 0.05  # 95% penalty for frost/cool risk
        elif crop_name in COLD_CROPS and req.temperature > 28.0:
            results.at[i, 'confidence'] *= 0.10  # 90% penalty for heat stress

    # Re-normalize confidences so they still equal 100%
    results['confidence'] = results['confidence'] / results['confidence'].sum()
    # ────────────────────────────────────────────────────────────────────────

    top5    = results.sort_values("confidence", ascending=False).head(5)

    prediction     = top5.iloc[0]["crop"]
    top_confidence = float(top5.iloc[0]["confidence"])
    is_low_confidence = top_confidence < 0.50

    alternatives = [
        {"crop": row["crop"], "confidence": float(row["confidence"])}
        for _, row in top5.iloc[1:].iterrows()
    ]

    return {
        "crop":               prediction,
        "confidence":         top_confidence,
        "is_low_confidence":  is_low_confidence,
        "alternatives":       alternatives,
        "inputs_clamped": {
            "temperature": temp_c,
            "humidity":    humidity_c,
            "rainfall":    rain_c,
        }
    }


# ════════════════════════════════════════════════════════════════════════════
# ENDPOINT 3 — POST /api/prescription
# Computes fertilizer prescription by comparing user soil to ideal profile
# Mirrors the Agronomist Engine block from earth_predictor.py
# ════════════════════════════════════════════════════════════════════════════
@app.post("/api/prescription")
async def get_prescription(req: PrescriptionRequest):
    crop_key = req.crop.lower()
    ideal = IDEAL_SOIL.get(crop_key)

    if ideal is None:
        raise HTTPException(status_code=404, detail=f"No ideal profile for crop: {req.crop}")

    delta_n  = round(ideal["N"]  - req.n,  1)
    delta_p  = round(ideal["P"]  - req.p,  1)
    delta_k  = round(ideal["K"]  - req.k,  1)
    delta_ph = round(ideal["ph"] - req.ph, 2)

    def nutrient_action(delta, fertilizer, conversion, unit):
        if abs(delta) < 2:
            return {"status": "optimal", "message": "No action needed", "amount_kg_ha": 0}
        elif delta > 0:
            product_kg = round(abs(delta) * conversion, 1)
            return {
                "status":        "deficient",
                "message":       f"Apply {abs(delta):.1f} kg/ha {fertilizer}",
                "gap_kg_ha":     abs(delta),
                "amount_kg_ha":  product_kg,
                "product":       fertilizer,
                "unit":          unit
            }
        else:
            return {
                "status":    "excess",
                "message":   f"Excess by {abs(delta):.1f} kg/ha — skip {fertilizer} this season",
                "gap_kg_ha": abs(delta),
                "amount_kg_ha": 0
            }

    # pH action
    if abs(delta_ph) < 0.3:
        ph_action = {"status": "optimal", "message": "Soil pH is optimal — no amendment needed", "amount_kg_ha": 0}
    elif delta_ph > 0:
        lime_kg = round(delta_ph * 200, 0)
        ph_action = {
            "status":       "too_acidic",
            "message":      f"Apply ~{lime_kg:.0f} kg/ha of agricultural lime (calcium carbonate) to raise pH",
            "amount_kg_ha": lime_kg,
            "product":      "Agricultural Lime (CaCO₃)"
        }
    else:
        sulfur_kg = round(abs(delta_ph) * 100, 0)
        ph_action = {
            "status":       "too_alkaline",
            "message":      f"Apply ~{sulfur_kg:.0f} kg/ha of elemental sulfur to lower pH",
            "amount_kg_ha": sulfur_kg,
            "product":      "Elemental Sulfur"
        }

    return {
        "crop": req.crop,
        "ideal": ideal,
        "user_soil": {"N": req.n, "P": req.p, "K": req.k, "ph": req.ph},
        "deltas": {"N": delta_n, "P": delta_p, "K": delta_k, "ph": delta_ph},
        "prescription": {
            "nitrogen":   nutrient_action(delta_n,  "Urea (46% N)",      2.17, "kg/ha"),
            "phosphorus": nutrient_action(delta_p,  "SSP (18% P₂O₅)",   5.56, "kg/ha"),
            "potassium":  nutrient_action(delta_k,  "MOP (60% K₂O)",    1.67, "kg/ha"),
            "ph":         ph_action
        }
    }


# ════════════════════════════════════════════════════════════════════════════
# ENDPOINT 4 — GET /api/health
# Simple health check to verify the backend is running
# ════════════════════════════════════════════════════════════════════════════
@app.get("/api/health")
async def health():
    return {
        "status": "online",
        "model_loaded": model is not None,
        "crops_available": len(IDEAL_SOIL)
    }