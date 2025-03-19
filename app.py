from flask import Flask, request, jsonify, render_template
import os
import torch
import torchvision.transforms as transforms
import torchvision.models as models
from PIL import Image
import requests

app = Flask(__name__)

# Define model storage path
MODEL_DIR = "model"
MODEL_PATH = os.path.join(MODEL_DIR, "mobilenet_v2.pth")
LABELS_PATH = os.path.join(MODEL_DIR, "imagenet_classes.txt")

# Ensure model directory exists
os.makedirs(MODEL_DIR, exist_ok=True)

# Download ImageNet class labels if not present
if not os.path.exists(LABELS_PATH):
    LABELS_URL = "https://raw.githubusercontent.com/pytorch/hub/master/imagenet_classes.txt"
    imagenet_classes = requests.get(LABELS_URL).text.splitlines()
    with open(LABELS_PATH, "w") as f:
        f.write("\n".join(imagenet_classes))
else:
    with open(LABELS_PATH, "r") as f:
        imagenet_classes = f.read().splitlines()

def load_model():
    model = models.mobilenet_v2(weights=None)  # Initialize model without weights

    if os.path.exists(MODEL_PATH):
        state_dict = torch.load(MODEL_PATH, map_location=torch.device('cpu'))  # Removed weights_only=True
        model.load_state_dict(state_dict)  # Load only the weights
    else:
        model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)  # Load pretrained weights
        torch.save(model.state_dict(), MODEL_PATH)  # Save only the state_dict

    model.eval()  # Set to evaluation mode
    return model

# Load the model
model = load_model()

# Define transformations
transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def predict_image(image):
    """Predicts the class of an image using MobileNetV2."""
    image = transform(image)
    image = image.unsqueeze(0)  # Add batch dimension

    with torch.no_grad():
        outputs = model(image)
        _, predicted_idx = torch.max(outputs, 1)

    # Load ImageNet class labels from the correct file
    with open(LABELS_PATH, "r") as f:
        class_names = [line.strip() for line in f.readlines()]

    predicted_class_name = class_names[predicted_idx.item()]
    
    return predicted_class_name, predicted_idx.item()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    image_file = request.files['image']
    try:
        image = Image.open(image_file).convert('RGB')
        predicted_class_name, predicted_class_idx = predict_image(image)  # Fixed unpacking

        return jsonify({
            'predicted_class': predicted_class_name,
            'predicted_index': predicted_class_idx
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
