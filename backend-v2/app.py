from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from libversion import VersionUtil
import os
import requests
import uuid
import json
from datetime import datetime
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Initialize with your app and explicitly set the metrics path
metrics = PrometheusMetrics(app, path=None)
metrics.info('app_info', 'Application info', version=VersionUtil.get_version())

# Enhanced metrics for A/B testing
sentiment_ratio = Gauge('sentiment_ratio', 'Ratio of positive to total reviews')
total_reviews = 0
positive_reviews = 0

# Counter with labels for tracking model predictions by sentiment
sentiment_predictions = Counter('sentiment_predictions_total', 'Number of sentiment predictions', ['sentiment'])

# Histogram to track response times from model service
model_response_time = Histogram('model_response_time_seconds', 'Model service response time in seconds', 
                               buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0])

# New metrics for feedback experiment
feedback_submissions = Counter('feedback_submissions_total', 'Number of feedback submissions', ['correctness'])
user_satisfaction = Gauge('user_satisfaction_score', 'Average user satisfaction score')

# In-memory storage for feedback (in production, this would be a database)
feedback_store = {}

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
    service_version = 'unavailable'
    try:
        response = requests.get(f"{MODEL_SERVICE_URL}/version", timeout=5)
        if response.status_code == 200:
            data = response.json()
            model_version = data.get('model_version', 'unknown')
            service_version = data.get('service_version', 'unknown')
    except requests.RequestException:
        pass
    
    return jsonify({
        "app": {
            "app_version": APP_VERSION,
            "variant": "v2-feedback-experiment"
        },
        "model_service": {
            "service_version": service_version,
            "model_version": model_version
        }
    })
    
# Enhanced sentiment analysis with feedback collection
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
            
            # Generate unique review ID for feedback tracking
            review_id = str(uuid.uuid4())
            response_data['review_id'] = review_id
            
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
            
            # Enhanced emoji and confidence display for v2
            if sentiment_value is True:
                response_data['emoji'] = '😊'
                response_data['message'] = 'This review appears to be positive!'
            else:
                response_data['emoji'] = '😔'
                response_data['message'] = 'This review appears to be negative.'
            
            # Add confidence level description
            confidence = response_data.get('confidence')
            if confidence is not None:
                if confidence > 0.8:
                    response_data['confidence_level'] = 'Very High'
                elif confidence > 0.6:
                    response_data['confidence_level'] = 'High'
                elif confidence > 0.4:
                    response_data['confidence_level'] = 'Medium'
                else:
                    response_data['confidence_level'] = 'Low'
            else:
                response_data['confidence_level'] = 'Not Available'
            
            # Store review data for feedback collection
            feedback_store[review_id] = {
                'review': data['review'],
                'predicted_sentiment': sentiment_value,
                'confidence': confidence,
                'timestamp': datetime.now().isoformat(),
                'feedback_received': False
            }
            
            # Add feedback prompt to response
            response_data['feedback_prompt'] = f"Was this prediction correct? Click here to provide feedback (ID: {review_id})"
                
            return jsonify(response_data)
        else:
            return jsonify({"error": f"Model service error: {response.status_code}"}), 500
    except requests.RequestException as e:
        # Record response time for failed requests too
        response_time = time.time() - start_time
        model_response_time.observe(response_time)
        return jsonify({"error": f"Failed to connect to model service: {str(e)}"}), 503

# Enhanced feedback collection for A/B testing
@app.route('/api/feedback', methods=['POST'])
@metrics.counter('api_calls_feedback', 'Number of calls to feedback endpoint')
def submit_feedback():
    data = request.json
    
    if not data or 'review_id' not in data or 'correct_sentiment' not in data:
        return jsonify({"error": "Missing review_id or correct_sentiment"}), 400
    
    review_id = data['review_id']
    correct_sentiment = data['correct_sentiment']
    
    # Check if review exists in our store
    if review_id not in feedback_store:
        return jsonify({"error": "Review ID not found"}), 404
    
    # Update feedback store
    feedback_store[review_id]['feedback_received'] = True
    feedback_store[review_id]['user_feedback'] = correct_sentiment
    feedback_store[review_id]['feedback_timestamp'] = datetime.now().isoformat()
    
    # Track feedback metrics
    correctness_label = 'correct' if correct_sentiment else 'incorrect'
    feedback_submissions.labels(correctness=correctness_label).inc()
    
    # Calculate and update user satisfaction score
    total_feedback = sum(1 for review in feedback_store.values() if review.get('feedback_received', False))
    correct_feedback = sum(1 for review in feedback_store.values() 
                          if review.get('feedback_received', False) and review.get('user_feedback', False))
    
    if total_feedback > 0:
        satisfaction_score = correct_feedback / total_feedback
        user_satisfaction.set(satisfaction_score)
    
    # Send feedback to model service if available
    try:
        model_feedback_response = requests.post(
            f"{MODEL_SERVICE_URL}/feedback",
            json={
                "review_id": review_id,
                "correct_sentiment": correct_sentiment
            },
            timeout=5
        )
        model_feedback_success = model_feedback_response.status_code == 200
    except requests.RequestException:
        model_feedback_success = False
    
    return jsonify({
        "status": "success",
        "message": "Thank you for your feedback! This helps us improve our model.",
        "feedback_id": review_id,
        "model_feedback_sent": model_feedback_success,
        "satisfaction_score": satisfaction_score if total_feedback > 0 else None
    })

# New endpoint to get feedback statistics for A/B testing
@app.route('/api/feedback/stats', methods=['GET'])
@metrics.counter('api_calls_feedback_stats', 'Number of calls to feedback stats endpoint')
def get_feedback_stats():
    total_reviews = len(feedback_store)
    feedback_received = sum(1 for review in feedback_store.values() if review.get('feedback_received', False))
    correct_predictions = sum(1 for review in feedback_store.values() 
                             if review.get('feedback_received', False) and review.get('user_feedback', False))
    
    accuracy = correct_predictions / feedback_received if feedback_received > 0 else 0
    
    return jsonify({
        "total_reviews": total_reviews,
        "feedback_received": feedback_received,
        "correct_predictions": correct_predictions,
        "accuracy": accuracy,
        "feedback_rate": feedback_received / total_reviews if total_reviews > 0 else 0
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True) 