# GeoAI Decision Support System 🌱

GeoAI is a full-stack geospatial artificial intelligence project designed to recommend the most optimal crops for agricultural regions based on atmospheric conditions and soil parameters. 

The system utilizes remote sensing APIs (Copernicus DEM, Open-Meteo, OpenWeatherMap) to fetch topographical and 10-year seasonal climate data, combining them with a trained machine learning model (`crop_model.joblib`) to provide evidence-based agronomic prescriptions and 3D visual diagnostics.

## 🚀 System Architecture

* **FastAPI Backend (`api.py`)**: A robust REST API that processes climate data, runs the Random Forest AI model, applies agronomic guardrails to prevent Extrapolation Bias, and calculates fertilizer prescriptions.
* **React 3D Frontend (`/frontend`)**: An interactive, animated web interface built with Vite and Three.js, allowing users to select locations, view climate diagnostics, and generate targeted soil prescriptions.
* **GeoAI CLI Predictor (`earth_predictor.py`)**: A standalone terminal tool that runs the same data pipelines and outputs a `.kml` file for global visualization in Google Earth.

## 🛠️ Setup and Installation

### 1. Requirements
- **Python 3.8+** (for the backend & CLI)
- **Node.js 18+** (for the frontend)
- **Docker** (optional, for containerized running)

### 2. Configure Environment Variables
Create a `.env` file in the root directory and add your OpenWeatherMap API key (used as a fallback if Open-Meteo fails):
```env
OPENWEATHER_API_KEY=your_actual_api_key_here
```

## 💻 Usage

### Starting the API

Launch the FastAPI prediction service on your localhost:
```bash
uvicorn api:app --reload --port 8000
```
The API will be available at `http://127.0.0.1:8000`. You can visit `http://127.0.0.1:8000/docs` to interact with the endpoints.

### Requesting Live Diagnostics & Generating a Google Earth Map

Run the geospatial prediction script:
```bash
python earth_predictor.py
```
This will:
1. Ping Copernicus for Elevation/Topography.
2. Query Open-Meteo for Soil Moisture & Temperature.
3. Query OpenWeather for Atmospheric limits.
4. Pass these attributes through the ML model.
5. Emits `Sfax_GeoAI_Prediction.kml`

You can open the resulting `.kml` file in **Google Earth** to visualize the recommendation on an interactive global map.

## 📊 Notebooks

- `GeoAI.ipynb` - The primary Jupyter notebook containing the experimental pipelines, data analysis, or machine learning routines used to structure `crop_model.joblib`.
