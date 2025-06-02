from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from libversion import VersionUtil
import os
import requests
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Initialize with your app and explicitly set the metrics path
metrics = PrometheusMetrics(app, path=None)
metrics.info('app_info', 'Application info', version=VersionUtil.get_version())

# gauge for tracking sentiment ratio (positive vs negative reviews)
sentiment_ratio = Gauge('sentiment_ratio', 'Ratio of positive to total reviews')
total_reviews = 0
positive_reviews = 0

# counter with labels for tracking model predictions by sentiment
sentiment_predictions = Counter('sentiment_predictions_total', 'Number of sentiment predictions', ['sentiment'])

# histogram to track response times from model service
model_response_time = Histogram('model_response_time_seconds', 'Model service response time in seconds', 
                               buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0])

# Metrics for feedback
feedback_timing = Histogram('feedback_timing_seconds', 'Time taken to submit feedback after analysis',
                          buckets=[1, 5, 10, 30, 60, 120])
feedback_rate = Counter('feedback_submissions_total', 'Number of feedback submissions')
feedback_accuracy = Counter('feedback_accuracy_total', 'Number of correct/incorrect model predictions', ['accuracy'])

@app.route('/metrics')
def metrics_endpoint():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

MODEL_SERVICE_URL = os.environ.get('MODEL_SERVICE_URL', 'http://localhost:5000')

APP_VERSION = VersionUtil.get_version()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# Get version info from both local app and model service
@app.route('/api/version', methods=['GET'])
@metrics.counter('api_calls_version', 'Number of calls to version endpoint')
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
@metrics.counter('api_calls_analyze', 'Number of calls to analyze endpoint')
def analyze_sentiment():
    data = request.json
    
    if not data or 'review' not in data:
        return jsonify({"error": "Missing review text"}), 400
    
    # Track model service response time
    start_time = time.time()
    
    try:
        # Forward the request to the model service
        response = requests.post(
            f"{MODEL_SERVICE_URL}/analyze",
            json={"review": data['review']},
            timeout=10
        )
        
        # Record response time
        response_time = time.time() - start_time
        model_response_time.observe(response_time)
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Track sentiment prediction
            sentiment_value = response_data.get('sentiment')
            sentiment_label = 'positive' if sentiment_value is True else 'negative'
            sentiment_predictions.labels(sentiment=sentiment_label).inc()
            
            # Update sentiment ratio gauge
            global total_reviews, positive_reviews
            total_reviews += 1
            if sentiment_value is True:
                positive_reviews += 1
            
            if total_reviews > 0:
                sentiment_ratio.set(positive_reviews / total_reviews)
            
            if sentiment_value is True:
                response_data['emoji'] = '😊'  
            else:
                response_data['emoji'] = '😔' 
            if 'confidence' not in response_data:
                response_data['confidence'] = None
                
            return jsonify(response_data)
        else:
            return jsonify({"error": f"Model service error: {response.status_code}"}), 500
    except requests.RequestException as e:
        # Record response time for failed requests too
        response_time = time.time() - start_time
        model_response_time.observe(response_time)
        return jsonify({"error": f"Failed to connect to model service: {str(e)}"}), 503

# Save user feedback for model improvement
@app.route('/api/feedback', methods=['POST'])
@metrics.counter('api_calls_feedback', 'Number of calls to feedback endpoint')
def submit_feedback():
    data = request.json
    
    if not data or 'review_id' not in data or 'correct_sentiment' not in data:
        return jsonify({"error": "Missing review_id or correct_sentiment"}), 400
    
    # Track feedback metrics
    feedback_rate.inc()
    feedback_accuracy.labels(accuracy='correct' if data['correct_sentiment'] else 'incorrect').inc()
    
    # Track timing if provided
    if 'time_to_feedback' in data:
        feedback_timing.observe(data['time_to_feedback'] / 1000)  # Convert ms to seconds
        
    return jsonify({
        "status": "success",
        "message": "Feedback received"
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)