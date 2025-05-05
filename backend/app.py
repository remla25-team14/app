from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from libversion import get_version
import os
import requests

# TODO: Replace this with dependency on lib-version package
app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app) 

MODEL_SERVICE_URL = os.environ.get('MODEL_SERVICE_URL', 'http://localhost:5000')

# TODO: Replace this with dependency on lib-version package
#APP_VERSION = os.environ.get('APP_VERSION', 'development')
APP_VERSION = get_version()
MODEL_VERSION = None

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# Get version info from both local app and model service
@app.route('/api/version', methods=['GET'])
def version():
    model_version = 'unavailable'
    try:
        response = requests.get(f"{MODEL_SERVICE_URL}/version", timeout=5)
        if response.status_code == 200:
            model_version = response.json().get('model_version', 'unknown')
    except requests.RequestException:
        pass
    
    return jsonify({
        "app": {
            "app_version": APP_VERSION
        },
        "model_service": {
            "model_version": model_version
        }
    })
    
# Connect to model service for sentiment analysis
@app.route('/api/analyze', methods=['POST'])
def analyze_sentiment():
    data = request.json
    
    if not data or 'review' not in data:
        return jsonify({"error": "Missing review text"}), 400
    
    try:
        # Forward the request to the model service
        response = requests.post(
            f"{MODEL_SERVICE_URL}/analyze",
            json={"review": data['review']},
            timeout=10
        )
        
        if response.status_code == 200:
            response_data = response.json()
            
            if response_data.get('sentiment') is True:
                response_data['emoji'] = '😊'  
            else:
                response_data['emoji'] = '😔' 
            if 'confidence' not in response_data:
                response_data['confidence'] = None
                
            return jsonify(response_data)
        else:
            return jsonify({"error": f"Model service error: {response.status_code}"}), 500
    except requests.RequestException as e:
        return jsonify({"error": f"Failed to connect to model service: {str(e)}"}), 503

# Save user feedback for model improvement
@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    
    if not data or 'review_id' not in data or 'correct_sentiment' not in data:
        return jsonify({"error": "Missing review_id or correct_sentiment"}), 400
        
    # Here we would ideally send the feedback to the model service, or do something with it
    return jsonify({
        "status": "success",
        "message": "Feedback received"
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)