from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import random

app = Flask(__name__)
CORS(app) 

# placeholder for now, we should implement this later
MODEL_SERVICE_URL = os.environ.get('MODEL_SERVICE_URL', 'http://localhost:5000')

# placeholder for now, we should implement this later
APP_VERSION = "0.1.0-placeholder"

# this is for the versioning
@app.route('/version', methods=['GET'])
def version():
    return jsonify({
        "app": {
            "app_version": APP_VERSION
        },
        "model_service": {
            "model_version": "0.1.0-placeholder"
        }
    })
    
# this is for tje sentiment analysis later on
@app.route('/analyze', methods=['POST'])
def analyze_sentiment():
    data = request.json
    
    if not data or 'review' not in data:
        return jsonify({"error": "Missing review text"}), 400
    
    review_text = data['review']
    
    # placeholder for now
    is_positive = random.choice([True, False])
    confidence = random.uniform(0.6, 0.95)
    
    return jsonify({
        "review_id": str(random.randint(1000, 9999)),
        "review": review_text,
        "sentiment": is_positive,
        "confidence": confidence
    })

#feedback based on the sentiment analysis
@app.route('/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    
    if not data or 'review_id' not in data or 'correct_sentiment' not in data:
        return jsonify({"error": "Missing review_id or correct_sentiment"}), 400
        
    return jsonify({
        "status": "success",
        "message": "Feedback received"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)