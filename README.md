# Agri-AI Project 🌱

Agri-AI is a geospatial artificial intelligence project designed to recommend the most optimal crops for agricultural regions based on atmospheric conditions and soil parameters. It utilizes remote sensing APIs to fetch topographical, atmospheric, and soil data, combining them with a trained machine learning model to provide evidence-based crop recommendations.

## 🚀 Features

* **Crop Recommendation API (`main.py`)**: A `FastAPI` endpoint that takes environmental parameters (Nitrogen, Phosphorus, Potassium, Temperature, Humidity, pH, and Rainfall) and returns the ideal crop using a pre-trained pipeline (`crop_model.joblib`).
* **GeoAI Predictor (`earth_predictor.py`)**: Gathers live remote sensing and GIS data (via Copernicus, Open-Meteo, and OpenWeather), queries the trained model, and generates a `.kml` file for visualization in Google Earth.

## 🛠️ Setup and Installation

### 1. Requirements

Ensure you have Python 3.8+ installed. You'll need the following standard dependencies:
- `fastapi`
- `uvicorn`
- `pydantic`
- `joblib`
- `pandas`
- `requests`
- `python-dotenv`

(You can install the requirements by running `pip install fastapi uvicorn pydantic joblib pandas requests python-dotenv`)

### 2. Configure Environment Variables

Create a `.env` file in the root directory and add your OpenWeatherMap API key:
```env
OPENWEATHER_API_KEY=your_actual_api_key_here
```

## 💻 Usage

### Starting the API

Launch the FastAPI prediction service on your localhost:
```bash
uvicorn main:app --reload
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
