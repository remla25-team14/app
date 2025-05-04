from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import random

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app) 

# placeholderes we need to edit later
MODEL_SERVICE_URL = os.environ.get('MODEL_SERVICE_URL', 'http://localhost:5000')

# placeholderes we need to edit later
APP_VERSION = os.environ.get('APP_VERSION', '0.1.0-placeholder')
MODEL_VERSION = os.environ.get('MODEL_VERSION', '0.1.0-placeholder')

# root that loads the react app frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# placeholderes we need to edit later
@app.route('/api/version', methods=['GET'])
def version():
    return jsonify({
        "app": {
            "app_version": APP_VERSION
        },
        "model_service": {
            "model_version": MODEL_VERSION
        }
    })
    
# this is for the sentiment analysis later on, we need to edit this later
@app.route('/api/analyze', methods=['POST'])
def analyze_sentiment():
    data = request.json
    
    if not data or 'review' not in data:
        return jsonify({"error": "Missing review text"}), 400
    
    review_text = data['review']
    
    # placeholderes we need to edit later
    is_positive = random.choice([True, False])
    confidence = random.uniform(0.6, 0.95)
    
    return jsonify({
        "review_id": str(random.randint(1000, 9999)),
        "review": review_text,
        "sentiment": is_positive,
        "confidence": confidence
    })

# placeholderes we need to edit later
@app.route('/api/feedback', methods=['POST'])
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