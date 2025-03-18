from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from googleapiclient import discovery
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
import io
import os
import tensorflow as tf  # Or your ML framework (e.g., torch)
from PIL import Image  # For image processing
import numpy as np
import logging

app = FastAPI()

# Configuration (Replace with your values)
MODEL_FILE_ID = "YOUR_GOOGLE_DRIVE_FILE_ID"  # The ID of your model file in Google Drive
#export SERVICE_ACCOUNT_FILE = "/home/suvendu/VCC/VCC_m22aie218_assignment_1/project-1-autoscale-gcp-vm-e4be10f24915.json"  # Path to your service account key file
#GOOGLE_APPLICATION_CREDENTIALS="/home/suvendu/VCC/VCC_m22aie218_assignment_1/project-1-autoscale-gcp-vm-e4be10f24915.json" 
MODEL_LOCAL_PATH = "model"  # Directory to store the downloaded model

# Global variables
model = None  # ML model instance
drive_service = None  # Google Drive API service instance

# Initialize logging
logging.basicConfig(level=logging.INFO)

def load_model_from_drive():
    """Downloads the model from Google Drive and loads it."""
    global model, drive_service

    try:
        logging.info("Loading model...")

        # Authenticate with Google Drive API
        if not drive_service:
            creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
            drive_service = discovery.build('drive', 'v3', credentials=creds)

        # Create the directory if it doesn't exist
        if not os.path.exists(MODEL_LOCAL_PATH):
            os.makedirs(MODEL_LOCAL_PATH)

        # Download the model
        request = drive_service.files().get_media(fileId=MODEL_FILE_ID)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            logging.info(f"Download %d%%" % int(status.progress() * 100))

        # Save the model locally (you might need to adjust this based on your model format)
        model_path = os.path.join(MODEL_LOCAL_PATH, "model_file")  # Adjust as needed
        with open(model_path, "wb") as f:
            fh.seek(0)
            f.write(fh.getvalue())

        # Load the model (adjust based on your ML framework)
        model = tf.keras.models.load_model(model_path)  # Example for TensorFlow
        logging.info("Model loaded successfully.")

    except Exception as e:
        logging.error(f"Error loading model: {e}")
        raise

async def process_image(file: UploadFile):
    """Processes the uploaded image and performs classification."""
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")  # Adjust as needed
        image = image.resize((224, 224))  # Resize as needed for your model
        image_array = np.array(image) / 255.0  # Normalize
        image_array = np.expand_dims(image_array, axis=0)  # Add batch dimension

        # Perform inference
        prediction = model.predict(image_array)  # Adjust based on your model output
        predicted_class = np.argmax(prediction)  # Get the class with the highest probability

        return {"predicted_class": int(predicted_class)}  # Ensure JSON serializable

    except Exception as e:
        logging.error(f"Error processing image: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """Loads the ML model when the FastAPI app starts."""
    try:
        load_model_from_drive()
    except Exception as e:
        logging.error("Application startup failed: Model loading error")
        # Handle the error appropriately, e.g., by raising an exception to prevent the app from starting
        # or by setting a flag to indicate that the model is not loaded.
        raise  # Re-raise the exception to stop the app

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """Endpoint for image classification."""
    try:
        result = await process_image(file)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)