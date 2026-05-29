from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import pandas as pd

# 1. Start the API
app = FastAPI(title="Agri-AI API")

# 2. Load your saved model
model = joblib.load('crop_model.joblib')

# 3. Define the expected data structure
class CropData(BaseModel):
    N: float
    P: float
    K: float
    temperature: float
    humidity: float
    ph: float
    rainfall: float

# 4. Create the listening endpoint
@app.post("/predict")
def predict_crop(data: CropData):
    # Package the incoming data into a DataFrame with the correct column names
    features = pd.DataFrame(
        [[data.N, data.P, data.K, data.temperature, data.humidity, data.ph, data.rainfall]],
        columns=['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']
    )
    
    # Make the prediction
    prediction = model.predict(features)
    
    return {"status": "success", "recommended_crop": prediction[0]}