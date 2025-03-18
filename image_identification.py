from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from googleapiclient import discovery
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
import io
import os
import torch  # Changed from tensorflow
from PIL import Image
import numpy as np
import logging
from torchvision import transforms  # PyTorch image transforms

app = FastAPI()

# Configuration (Replace with your values)
#"https://drive.google.com/file/d/1-JWQ0SmgvJD8GC3kT3j_5L78T-tdPDrM/view?usp=drive_link"
#https://drive.google.com/file/d/18B0RwsxvlW4CjX2PNqVIAp7vOBoe6pJW/view?usp=drive_link"
MODEL_FILE_ID = "18B0RwsxvlW4CjX2PNqVIAp7vOBoe6pJW" 
#SERVICE_ACCOUNT_FILE = "/home/suvendu/VCC/VCC_m22aie218_assignment_1/project-1-autoscale-gcp-vm-e4be10f24915.json"
MODEL_LOCAL_PATH = "model"

# Global variables
model = None
drive_service = None

# Initialize logging
logging.basicConfig(level=logging.INFO)

def load_model_from_drive():
    """Downloads the model from Google Drive and loads it (PyTorch version)."""
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

        # Save the model locally (adjust based on your model format)
        model_path = os.path.join(MODEL_LOCAL_PATH, "model.pth")  # Assuming a .pth file extension
        with open(model_path, "wb") as f:
            fh.seek(0)
            f.write(fh.getvalue())

        # Load the model (PyTorch)
        model = torch.load(model_path)
        model.eval()  # Set the model to evaluation mode
        logging.info("Model loaded successfully.")

    except Exception as e:
        logging.error(f"Error loading model: {e}")
        raise

async def process_image(file: UploadFile):
    """Processes the uploaded image and performs classification (PyTorch version)."""
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")

        # Define transformations (adjust as needed for your model)
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010))  # Example normalization
        ])

        image = transform(image)
        image = image.unsqueeze(0)  # Add batch dimension

        # Perform inference
        with torch.no_grad():  # Disable gradient calculation for inference
            prediction = model(image)
            predicted_class = torch.argmax(prediction).item()  # Get the class with the highest probability

        return {"predicted_class": predicted_class}

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
        raise

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