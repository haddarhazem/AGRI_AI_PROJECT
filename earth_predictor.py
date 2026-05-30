import requests
import joblib
import pandas as pd
import os
import webbrowser
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENWEATHER_API_KEY", "your_default_api_key_here")

# ===========================================================================
# IDEAL SOIL PROFILES — derived from dataset mean values per crop
# Used by the Agronomist Engine to compute fertilizer prescriptions
# ===========================================================================
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

# Training bounds for climate validator
CLIMATE_BOUNDS = {
    'temperature': (1.2,  43.7),
    'humidity':    (14.3, 100.0),
    'rainfall':    (20.2, 298.6),
}

# ===========================================================================
# HEADER
# ===========================================================================
print("=" * 60)
print("   🌍  GEO-AI DECISION SUPPORT SYSTEM  🌍")
print("   Climate Engine  +  Agronomist Engine")
print("=" * 60)
print("\nOpening Google Maps... Drop a pin on your target farm.")
webbrowser.open("https://www.google.com/maps")
print("\n1. Right-click anywhere on the map.")
print("2. Click the coordinates at the top of the menu to copy them.")
print("3. Paste them below.")

# ===========================================================================
# STEP 0 — COORDINATE INPUT
# ===========================================================================
while True:
    try:
        raw = input("\nPaste Coordinates (Latitude, Longitude): ")
        parts = raw.replace(" ", "").split(",")
        LAT = float(parts[0])
        LON = float(parts[1])
        CITY_NAME = f"GeoTarget_{LAT:.2f}_{LON:.2f}"
        print(f"   -> Locked on: Latitude {LAT}, Longitude {LON}")
        break
    except (ValueError, IndexError):
        print("Invalid format. Example: 34.7405, 10.7603")

# ===========================================================================
# STEP 0b — SEASON SELECTION
# ===========================================================================
SEASON_CONFIG = {
    "1": {"name": "Spring / Summer", "months": [3,4,5,6,7,8],        "label": "Mar–Aug"},
    "2": {"name": "Autumn / Winter", "months": [9,10,11,12,1,2],     "label": "Sep–Feb"},
    "3": {"name": "Full Year",        "months": list(range(1, 13)),   "label": "Jan–Dec"},
}

print("\n🌱 Select the growing season you are planning for:")
print("   [1] Spring / Summer  (Mar–Aug)  — Warm crops: rice, maize, cotton")
print("   [2] Autumn / Winter  (Sep–Feb)  — Cool crops: lentil, chickpea, wheat")
print("   [3] Full Year        (Annual)   — Perennial crops: mango, coconut, coffee")

while True:
    choice = input("\nEnter season [1/2/3]: ").strip()
    if choice in SEASON_CONFIG:
        season = SEASON_CONFIG[choice]
        print(f"   -> Planning for: {season['name']} ({season['label']})")
        break
    print("Invalid choice. Please enter 1, 2, or 3.")

# ===========================================================================
# STEP 1 — CLIMATE ENGINE: fetch 10-year seasonal averages
# ===========================================================================
print("\n" + "=" * 60)
print("   STEP 1: CLIMATE ENGINE")
print("=" * 60)

# Pipeline A: Elevation
print("\n🛰️  Fetching Topography (Copernicus DEM)...")
try:
    elev_res = requests.get(
        f"https://api.open-meteo.com/v1/elevation?latitude={LAT}&longitude={LON}"
    ).json()
    elevation = elev_res['elevation'][0]
    print(f"   -> Elevation: {elevation}m above sea level")
except:
    elevation = "Unknown"
    print("   -> Topography unavailable.")

# Pipeline B: 10-year seasonal climate
print(f"\n🌤️  Fetching 10-Year Seasonal Climate ({season['name']})...")
target_months = season['months']

try:
    climate_res = requests.get(
        "https://climate-api.open-meteo.com/v1/climate",
        params={
            "latitude":   LAT,
            "longitude":  LON,
            "start_date": "2014-01-01",
            "end_date":   "2024-12-31",
            "models":     "EC_Earth3P_HR",
            "daily":      "temperature_2m_mean,relative_humidity_2m_max,precipitation_sum"
        },
        timeout=30
    ).json()

    dates      = climate_res['daily']['time']
    temps      = climate_res['daily']['temperature_2m_mean']
    humidities = climate_res['daily']['relative_humidity_2m_max']
    rains      = climate_res['daily']['precipitation_sum']

    s_temps, s_hums, s_rains = [], [], []
    for i, d in enumerate(dates):
        if int(d[5:7]) in target_months:
            if temps[i]      is not None: s_temps.append(temps[i])
            if humidities[i] is not None: s_hums.append(humidities[i])
            if rains[i]      is not None: s_rains.append(rains[i])

    temp     = round(sum(s_temps) / len(s_temps), 2)
    humidity = round(sum(s_hums)  / len(s_hums),  1)
    rain     = round(sum(s_rains) / 10, 1)

    print(f"   -> Avg Temperature : {temp}°C  (10-yr seasonal mean)")
    print(f"   -> Avg Humidity    : {humidity}%  (10-yr seasonal mean)")
    print(f"   -> Seasonal Rainfall: {rain}mm/year  (10-yr avg)")

except Exception as e:
    print(f"   -> Climate API unavailable: {e}")
    print("   -> Falling back to live weather...")
    try:
        w = requests.get(
            f"http://api.openweathermap.org/data/2.5/weather"
            f"?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric",
            timeout=10
        ).json()
        if str(w.get('cod')) == '200':
            temp     = w['main']['temp']
            humidity = w['main']['humidity']
        else:
            temp, humidity = 25.0, 60.0
    except:
        temp, humidity = 25.0, 60.0
    rain = 80.0
    print(f"   -> Live Temp: {temp}°C | Humidity: {humidity}% | Fallback Rain: {rain}mm")

# Climate validator
warnings = []
for feature, value in [('temperature', temp), ('humidity', humidity), ('rainfall', rain)]:
    lo, hi = CLIMATE_BOUNDS[feature]
    if not (lo <= value <= hi):
        warnings.append(f"   ⚠️  {feature} = {value} outside training range ({lo}–{hi})")

if warnings:
    print("\n🚨 CLIMATE OUT-OF-DISTRIBUTION WARNING:")
    for w in warnings:
        print(w)
    print("   -> Values will be clamped. Treat recommendation with caution.")

temp_c     = max(1.2,  min(43.7,  temp))
humidity_c = max(14.3, min(100.0, humidity))
rain_c     = max(20.2, min(298.6, rain))

# ===========================================================================
# AI PREDICTION — climate features only
# ===========================================================================
print("\n🧠 Running Climate Engine AI...")
try:
    model = joblib.load('crop_model.joblib')
    features = pd.DataFrame(
        [[temp_c, humidity_c, rain_c]],
        columns=['temperature', 'humidity', 'rainfall']
    )
    probs      = model.predict_proba(features)[0]
    results    = pd.DataFrame({'Crop': model.classes_, 'Confidence': probs})
    
    # ── AGRONOMIC GUARDRAILS (Heuristic Overrides) ──────────────────────────
    TROPICAL_CROPS = ['tea', 'banana', 'coconut', 'papaya', 'rubber', 'mango', 'coffee', 'orange']
    COLD_CROPS = ['apple', 'barley', 'oats', 'potato', 'wheat']
    
    for i, row in results.iterrows():
        crop_name = row['Crop'].lower()
        if crop_name in TROPICAL_CROPS and temp_c < 21.0:
            results.at[i, 'Confidence'] *= 0.05
        elif crop_name in COLD_CROPS and temp_c > 28.0:
            results.at[i, 'Confidence'] *= 0.10
            
    results['Confidence'] = results['Confidence'] / results['Confidence'].sum()
    # ────────────────────────────────────────────────────────────────────────

    top3       = results.sort_values('Confidence', ascending=False).head(3)

    prediction     = top3.iloc[0]['Crop']
    top_confidence = top3.iloc[0]['Confidence'] * 100
    alt_1          = top3.iloc[1]['Crop'].title()
    alt_1_conf     = top3.iloc[1]['Confidence'] * 100
    alt_2          = top3.iloc[2]['Crop'].title()
    alt_2_conf     = top3.iloc[2]['Confidence'] * 100

    print(f"\n   ✅ Climate Engine says the sky suits: {prediction.upper()}")
    print(f"      Confidence: {top_confidence:.1f}%")
    print(f"      Alternatives: {alt_1} ({alt_1_conf:.1f}%)  |  {alt_2} ({alt_2_conf:.1f}%)")

    if top_confidence < 50:
        print(f"\n   ⚠️  Low confidence ({top_confidence:.1f}%)")
        print(f"   The climate matches a group of similar crops.")
        print(f"   Your soil data in Step 2 will determine the final answer.")

except Exception as e:
    print(f"   🚨 Model error: {e}")
    exit()

# ===========================================================================
# STEP 2 — AGRONOMIST ENGINE: soil input + fertilizer prescription
# ===========================================================================
print("\n" + "=" * 60)
print("   STEP 2: AGRONOMIST ENGINE")
print("=" * 60)
print(f"\nThe climate suits {prediction.upper()}.")
print("Now let's check if your soil is ready.\n")
print("Enter your current soil test results:")
print("(These come from a soil test kit or local agricultural lab)\n")

while True:
    try:
        user_n  = float(input("   Your Nitrogen   (N)  kg/ha : "))
        user_p  = float(input("   Your Phosphorus (P)  kg/ha : "))
        user_k  = float(input("   Your Potassium  (K)  kg/ha : "))
        user_ph = float(input("   Your Soil pH              : "))
        break
    except ValueError:
        print("   Invalid input. Please enter numbers only.")

# Retrieve ideal profile for the predicted crop
ideal = IDEAL_SOIL.get(prediction.lower(), None)

if ideal is None:
    print(f"\n   No ideal profile found for {prediction}. Cannot generate prescription.")
else:
    delta_n  = round(ideal['N']  - user_n,  1)
    delta_p  = round(ideal['P']  - user_p,  1)
    delta_k  = round(ideal['K']  - user_k,  1)
    delta_ph = round(ideal['ph'] - user_ph, 2)

    print(f"\n📊 SOIL ANALYSIS FOR {prediction.upper()}")
    print(f"{'Nutrient':<12} {'Your Soil':>10} {'Ideal':>10} {'Gap':>10} {'Action':>20}")
    print("-" * 65)

    def status(delta, nutrient):
        if abs(delta) < 2:
            return "✅ Optimal"
        elif delta > 0:
            return f"⬆️  Add {abs(delta):.1f} kg/ha"
        else:
            return f"⬇️  Excess by {abs(delta):.1f}"

    print(f"{'Nitrogen':<12} {user_n:>10.1f} {ideal['N']:>10.1f} {delta_n:>+10.1f} {status(delta_n, 'N'):>20}")
    print(f"{'Phosphorus':<12} {user_p:>10.1f} {ideal['P']:>10.1f} {delta_p:>+10.1f} {status(delta_p, 'P'):>20}")
    print(f"{'Potassium':<12} {user_k:>10.1f} {ideal['K']:>10.1f} {delta_k:>+10.1f} {status(delta_k, 'K'):>20}")

    # pH recommendation
    print(f"\n{'pH':<12} {user_ph:>10.2f} {ideal['ph']:>10.2f} {delta_ph:>+10.2f}", end="  ")
    if abs(delta_ph) < 0.3:
        print("✅ Optimal")
        ph_action = "Soil pH is optimal — no amendment needed."
    elif delta_ph > 0:
        print("⬆️  Too Acidic")
        lime_kg = round(delta_ph * 200, 0)
        ph_action = f"Apply ~{lime_kg:.0f} kg/ha of agricultural lime (calcium carbonate) to raise pH."
    else:
        print("⬇️  Too Alkaline")
        sulfur_kg = round(abs(delta_ph) * 100, 0)
        ph_action = f"Apply ~{sulfur_kg:.0f} kg/ha of elemental sulfur to lower pH."

    # Fertilizer prescription summary
    print(f"\n🧪 FERTILIZER PRESCRIPTION FOR {prediction.upper()}")
    print("-" * 65)

    if delta_n > 2:
        urea_kg = round(delta_n * 2.17, 1)
        print(f"   Nitrogen  : Apply {delta_n:.1f} kg/ha N → {urea_kg} kg/ha of Urea (46% N)")
    elif delta_n < -2:
        print(f"   Nitrogen  : Excess detected. Reduce organic inputs. Consider a nitrogen-fixing cover crop.")
    else:
        print(f"   Nitrogen  : ✅ No action needed.")

    if delta_p > 2:
        ssp_kg = round(delta_p * 5.56, 1)
        print(f"   Phosphorus: Apply {delta_p:.1f} kg/ha P → {ssp_kg} kg/ha of SSP (18% P₂O₅)")
    elif delta_p < -2:
        print(f"   Phosphorus: Excess detected. Avoid phosphate fertilizers this season.")
    else:
        print(f"   Phosphorus: ✅ No action needed.")

    if delta_k > 2:
        mop_kg = round(delta_k * 1.67, 1)
        print(f"   Potassium : Apply {delta_k:.1f} kg/ha K → {mop_kg} kg/ha of MOP (60% K₂O)")
    elif delta_k < -2:
        print(f"   Potassium : Excess detected. Skip potash fertilizers this season.")
    else:
        print(f"   Potassium : ✅ No action needed.")

    print(f"   pH        : {ph_action}")

# ===========================================================================
# KML GENERATION
# ===========================================================================
print("\n" + "=" * 60)
print("   GENERATING GEOSPATIAL OUTPUT")
print("=" * 60)

safe_filename = CITY_NAME.replace(" ", "_")
ood_note = "⚠️ OUT-OF-DISTRIBUTION — treat with caution" if warnings else "✅ Within training bounds"

if ideal:
    prescription_html = f"""
        <h3>Fertilizer Prescription</h3>
        <table border="1" cellpadding="4">
          <tr><th>Nutrient</th><th>Your Soil</th><th>Ideal</th><th>Gap</th></tr>
          <tr><td>N</td><td>{user_n}</td><td>{ideal['N']}</td><td>{delta_n:+.1f}</td></tr>
          <tr><td>P</td><td>{user_p}</td><td>{ideal['P']}</td><td>{delta_p:+.1f}</td></tr>
          <tr><td>K</td><td>{user_k}</td><td>{ideal['K']}</td><td>{delta_k:+.1f}</td></tr>
          <tr><td>pH</td><td>{user_ph}</td><td>{ideal['ph']}</td><td>{delta_ph:+.2f}</td></tr>
        </table>"""
else:
    prescription_html = "<p>No soil profile available for this crop.</p>"

kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Placemark>
    <name>🌾 {prediction.upper()} — {season['name']}</name>
    <description>
      <![CDATA[
        <h2>Recommended Crop: {prediction.upper()}</h2>
        <p><b>Confidence:</b> {top_confidence:.1f}% | <b>Data Quality:</b> {ood_note}</p>
        <p><b>Alternatives:</b> {alt_1} ({alt_1_conf:.1f}%) | {alt_2} ({alt_2_conf:.1f}%)</p>
        <hr>
        <h3>Climate Data — {season['name']} ({season['label']})</h3>
        <ul>
          <li><b>Elevation:</b> {elevation}m</li>
          <li><b>Avg Temperature (10yr):</b> {temp}°C</li>
          <li><b>Avg Humidity (10yr):</b> {humidity}%</li>
          <li><b>Seasonal Rainfall (10yr):</b> {rain}mm/year</li>
        </ul>
        <hr>
        {prescription_html}
      ]]>
    </description>
    <Point>
      <coordinates>{LON},{LAT},0</coordinates>
    </Point>
  </Placemark>
</kml>
"""

output_file = f"{safe_filename}_{choice}_GeoAI_Prediction.kml"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(kml_content)

print(f"\n🎉 Done! '{output_file}' has been generated.")