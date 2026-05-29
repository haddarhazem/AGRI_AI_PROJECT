
'''
import requests
import sqlite3
import os

# --- CONFIGURATION ---
API_KEY = os.getenv("OPENWEATHER_API_KEY", "your_default_api_key_here")
CITY = "Sfax,TN"
LAT = 34.74
LON = 10.76

# --- HELPER: OFFLINE DATABASE QUERY ---
def get_offline_soil_data(city_name):
    try:
        conn = sqlite3.connect('hwsd_local.db')
        cursor = conn.cursor()
        cursor.execute("SELECT ph, nitrogen, phosphorus, potassium FROM regional_soil WHERE region=?", (city_name,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {"ph": result[0], "N": result[1], "P": result[2], "K": result[3]}
    except Exception:
        pass
    return None # If all else fails

# --- PART 1: FETCH WEATHER (OpenWeatherMap) ---
print("🌤️ Fetching live atmospheric data...")
weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric"
weather_data = requests.get(weather_url).json()

current_temp = weather_data['main']['temp']
current_humidity = weather_data['main']['humidity']
current_rain = weather_data.get('rain', {}).get('1h', 0.0)
print(f"   -> Temp: {current_temp}°C | Humidity: {current_humidity}% | Rain: {current_rain}mm")

# --- PART 2: FETCH SOIL (Live vs Offline) ---
print("\n🌍 Attempting to fetch live edaphic data...")
soil_url = f"https://rest.isric.org/soilgrids/v2.0/properties/query?lon={LON}&lat={LAT}&property=nitrogen&property=phh2o&depth=5-15cm&value=mean"

# Default values
actual_ph, actual_n, actual_p, actual_k = 7.0, 40.0, 25.0, 35.0 

live_soil_success = False
raw_soil_response = requests.get(soil_url)

if raw_soil_response.status_code == 200:
    try:
        soil_data = raw_soil_response.json()
        raw_ph = soil_data['properties']['layers'][1]['depths'][0]['values']['mean']
        raw_n = soil_data['properties']['layers'][0]['depths'][0]['values']['mean']
        
        actual_ph = raw_ph / 10.0 if raw_ph else actual_ph
        actual_n = (raw_n / 100.0) if raw_n else actual_n
        live_soil_success = True
        print("   -> ✅ Successfully retrieved live SoilGrids data!")
    except Exception:
        pass

# The Safety Net activates if the live API failed
if not live_soil_success:
    print(f"   -> 🚨 Live API Error (Status {raw_soil_response.status_code}).")
    print("   -> 🛡️ Engaging offline HWSD database fallback...")
    
    offline_data = get_offline_soil_data(CITY)
    if offline_data:
        actual_ph = offline_data["ph"]
        actual_n = offline_data["N"]
        actual_p = offline_data["P"]
        actual_k = offline_data["K"]
        print("   -> ✅ Offline data retrieved successfully!")

print(f"   -> Active Soil Parameters - pH: {actual_ph} | N: {actual_n} | P: {actual_p} | K: {actual_k}")

# --- PART 3: ASK THE AI ---
print("\n🧠 Sending harmonized dataset to local AI...")
ai_payload = {
  "N": actual_n, "P": actual_p, "K": actual_k,
  "temperature": current_temp, "humidity": current_humidity,
  "ph": actual_ph, "rainfall": current_rain
}

local_api_url = "http://127.0.0.1:8000/predict"
response = requests.post(local_api_url, json=ai_payload)

print(f"\n🌱 AI RECOMMENDATION: {response.json()['recommended_crop'].upper()}")
'''