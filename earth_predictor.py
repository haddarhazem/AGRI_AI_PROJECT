import requests
import joblib
import pandas as pd
import os

# --- 1. CONFIGURATION ---
LAT = 34.74
LON = 10.76
API_KEY = os.getenv("OPENWEATHER_API_KEY", "your_default_api_key_here")

# --- 2. FETCH STABLE DATA ---
# Weather (OpenWeatherMap)
weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric"
weather_res = requests.get(weather_url).json()
temp = weather_res['main']['temp']
humidity = weather_res['main']['humidity']
rain = weather_res.get('rain', {}).get('1h', 0.0)

# Soil (OpenLandMap - Stable replacement for ISRIC)
soil_url = f"https://api.openlandmap.org/query/point?lon={LON}&lat={LAT}"
try:
    soil_res = requests.get(soil_url, timeout=10).json()
    # Extract surface pH. If the API fails, it defaults to 7.0
    raw_ph = soil_res.get('ph.h2o_md_fao.5.5_m_250m_b0..0cm_1950..2017_v0.2', 70)
    ph = raw_ph / 10.0 if raw_ph else 7.0
except requests.exceptions.RequestException:
    print("⚠️ Soil API timed out or failed. Using fallback pH value.")
    ph = 7.0

# Baseline estimates for Sfax region
n, p, k = 40.0, 25.0, 35.0 

# --- 3. AI PREDICTION ---
print("🧠 Processing AI Recommendation...")
model = joblib.load('crop_model.joblib')

# Package the data for the Random Forest
features = pd.DataFrame([[n, p, k, temp, humidity, ph, rain]], 
                        columns=['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall'])

prediction = model.predict(features)[0].upper()
print(f"   -> AI selected: {prediction}")

# --- 4. GOOGLE EARTH INTEGRATION (KML) ---
print("🗺️ Generating Google Earth file...")

kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Placemark>
    <name>AI Recommendation: {prediction}</name>
    <description>
      <![CDATA[
        <h2>Optimal Crop: {prediction}</h2>
        <hr>
        <ul>
          <li><b>Temperature:</b> {temp}°C</li>
          <li><b>Humidity:</b> {humidity}%</li>
          <li><b>Soil pH:</b> {ph}</li>
          <li><b>Nitrogen Est:</b> {n}</li>
        </ul>
      ]]>
    </description>
    <Point>
      <coordinates>{LON},{LAT},0</coordinates>
    </Point>
  </Placemark>
</kml>
"""

# Save the file to your hard drive
with open("Sfax_Crop_Prediction.kml", "w") as file:
    file.write(kml_content)

print("🎉 Done! A file named 'Sfax_Crop_Prediction.kml' has been created in your folder.")