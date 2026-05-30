import requests
import joblib
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

# --- 1. GEOSPATIAL CONFIGURATION ---
LAT = 34.74
LON = 10.76
API_KEY = os.getenv("OPENWEATHER_API_KEY", "your_default_api_key_here")

# --- 2. REMOTE SENSING & GIS PIPELINES ---

# PIPELINE A: Copernicus Satellite Elevation (DEM)
print("🛰️ Pinging Copernicus Satellite Network for Topography...")
elevation_url = f"https://api.open-meteo.com/v1/elevation?latitude={LAT}&longitude={LON}"
try:
    elev_res = requests.get(elevation_url).json()
    elevation = elev_res['elevation'][0]
    print(f"   -> Altitude detected: {elevation} meters above sea level")
except Exception as e:
    print("   -> Topography API failed.")
    elevation = "Unknown"


# PIPELINE B: Open-Meteo Soil Temperature/Moisture (ISRIC is currently down globally)
print("🌍 Querying Open-Meteo for Soil Data...")
soil_url = "https://api.open-meteo.com/v1/forecast"
soil_params = {
    "latitude": LAT,
    "longitude": LON,
    "hourly": "soil_temperature_0cm,soil_moisture_0_to_1cm",
    "forecast_days": 1
}

try:
    soil_res = requests.get(soil_url, params=soil_params, timeout=15).json()
    soil_temp = soil_res['hourly']['soil_temperature_0cm'][0]
    soil_moisture = soil_res['hourly']['soil_moisture_0_to_1cm'][0]
    # Estimate pH from soil moisture (arid low-moisture = alkaline, high = neutral)
    ph = round(8.2 - (soil_moisture * 10), 1)
    ph = max(5.5, min(9.0, ph))  # clamp to realistic range
    print(f"   -> Soil Temp: {soil_temp}°C | Moisture: {soil_moisture} | Estimated pH: {ph}")
except Exception as e:
    print(f"   -> Soil Pipeline Error: {e}")
    ph = 7.8


# PIPELINE C: OpenWeather Atmospheric Data
print("🌤️ Fetching Live Atmospheric Metrics...")
weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric"
weather_res = requests.get(weather_url).json()

if weather_res.get('cod') == 200:
    temp = weather_res['main']['temp']
    humidity = weather_res['main']['humidity']
    rain = weather_res.get('rain', {}).get('1h', 0.0)
    print(f"   -> Temp: {temp}°C | Humidity: {humidity}% | Rain: {rain}mm")
else:
    print(f"   -> Weather API Error. Using safety baselines.")
    temp, humidity, rain = 25.0, 60.0, 0.0

# Regional baseline nutrients for the model payload
n, p, k = 40.0, 25.0, 35.0 

# --- 3. AI PREDICTION ---
print("\n🧠 Processing AI Recommendation...")
try:
    model = joblib.load('crop_model.joblib')
    features = pd.DataFrame([[n, p, k, temp, humidity, ph, rain]], 
                            columns=['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall'])
    prediction = model.predict(features)[0].upper()
    print(f"   -> AI selected: {prediction}")
except Exception as e:
    print(f"   🚨 Model Loading Error: {e}")
    exit()

# --- 4. GOOGLE EARTH INTEGRATION (KML) ---
print("\n🗺️ Generating Geospatial KML Mapping File...")

kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Placemark>
    <name>AI Recommendation: {prediction}</name>
    <description>
      <![CDATA[
        <h2>Optimal Crop: {prediction}</h2>
        <hr>
        <h3>Remote Sensing Data</h3>
        <ul>
          <li><b>Topography (Copernicus DEM):</b> {elevation}m</li>
          <li><b>Soil pH (Open-Meteo Estimation):</b> {ph}</li>
          <li><b>Atmospheric Temp:</b> {temp}°C</li>
          <li><b>Humidity:</b> {humidity}%</li>
        </ul>
      ]]>
    </description>
    <Point>
      <coordinates>{LON},{LAT},0</coordinates>
    </Point>
  </Placemark>
</kml>
"""

with open("Sfax_GeoAI_Prediction.kml", "w") as file:
    file.write(kml_content)

print("🎉 Done! 'Sfax_GeoAI_Prediction.kml' has been generated.")