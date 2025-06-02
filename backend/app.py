from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from libversion import VersionUtil
import os
import requests
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST, REGISTRY, CollectorRegistry
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily, HistogramMetricFamily
import time

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

class SentimentMetricsCollector:
    def __init__(self):
        self.metrics = {
            'v1': {
                'positive': 0,
                'negative': 0,
                'response_times': [],
                'feedback_correct': 0,
                'feedback_incorrect': 0
            },
            'v2': {
                'positive': 0,
                'negative': 0,
                'response_times': [],
                'feedback_correct': 0,
                'feedback_incorrect': 0
            }
        }

    def collect(self):
        # Sentiment predictions
        c = CounterMetricFamily('sentiment_predictions_total', 'Number of sentiment predictions', labels=['sentiment', 'version'])
        for version in ['v1', 'v2']:
            c.add_metric(['positive', version], self.metrics[version]['positive'])
            c.add_metric(['negative', version], self.metrics[version]['negative'])
        yield c

        # Sentiment ratio
        g = GaugeMetricFamily('sentiment_ratio', 'Ratio of positive to total reviews', labels=['version'])
        for version in ['v1', 'v2']:
            total = self.metrics[version]['positive'] + self.metrics[version]['negative']
            if total > 0:
                g.add_metric([version], self.metrics[version]['positive'] / total)
            else:
                g.add_metric([version], 0)
        yield g

        # Response times
        h = HistogramMetricFamily('model_response_time_seconds', 'Model service response time in seconds', labels=['version'])
        buckets = [0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        for version in ['v1', 'v2']:
            bucket_values = [0] * len(buckets)
            for rt in self.metrics[version]['response_times']:
                for i, bound in enumerate(buckets):
                    if rt <= bound:
                        bucket_values[i] += 1
            h.add_metric([version], bucket_values, sum(self.metrics[version]['response_times']))
        yield h

        # Feedback accuracy
        f = CounterMetricFamily('feedback_accuracy_total', 'Number of correct/incorrect model predictions', labels=['accuracy', 'version'])
        for version in ['v1', 'v2']:
            f.add_metric(['correct', version], self.metrics[version]['feedback_correct'])
            f.add_metric(['incorrect', version], self.metrics[version]['feedback_incorrect'])
        yield f

# Create a new registry and collector
REGISTRY = CollectorRegistry()
collector = SentimentMetricsCollector()
REGISTRY.register(collector)

# Initialize with your app and explicitly set the metrics path
metrics = PrometheusMetrics(app, path=None, registry=REGISTRY)
metrics.info('app_info', 'Application info', version=VersionUtil.get_version())

# gauge for tracking sentiment ratio (positive vs negative reviews)
sentiment_ratio = Gauge('sentiment_ratio', 'Ratio of positive to total reviews', ['version'], registry=REGISTRY)
total_reviews = 0
positive_reviews = 0

# counter with labels for tracking model predictions by sentiment
sentiment_predictions = Counter('sentiment_predictions_total', 'Number of sentiment predictions', ['sentiment', 'version'], registry=REGISTRY)

# Add success/failure tracking for analyze endpoint
analyze_requests = Counter('analyze_requests_total', 'Number of analyze requests', ['status', 'version'], registry=REGISTRY)

# histogram to track response times from model service
model_response_time = Histogram('model_response_time_seconds', 'Model service response time in seconds', 
                              ['version'], buckets=[0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0], registry=REGISTRY)

# Metrics for feedback
feedback_timing = Histogram('feedback_timing_seconds', 'Time taken to submit feedback after analysis',
                          ['version'], buckets=[1, 5, 10, 30, 60, 120], registry=REGISTRY)
feedback_rate = Counter('feedback_submissions_total', 'Number of feedback submissions', ['version'], registry=REGISTRY)
feedback_accuracy = Counter('feedback_accuracy_total', 'Number of correct/incorrect model predictions', ['accuracy', 'version'], registry=REGISTRY)

@app.route('/metrics')
def metrics_endpoint():
    return generate_latest(REGISTRY), 200, {'Content-Type': CONTENT_TYPE_LATEST}

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
    version = request.headers.get('x-user-experiment', 'A')
    version = 'v2' if version == 'B' else 'v1'
    
    if not data or 'review' not in data:
        analyze_requests.labels(status='error', version=version).inc()
        return jsonify({"error": "Missing review text"}), 400
    
    start_time = time.time()
    try:
        response = requests.post(
            f"{MODEL_SERVICE_URL}/analyze",
            json={"text": data['review']},
            headers={"x-user-experiment": version}
        )
        response.raise_for_status()
        result = response.json()
        
        # Track response time
        response_time = time.time() - start_time
        collector.metrics[version]['response_times'].append(response_time)
        
        # Update sentiment predictions counter
        if result['sentiment']:
            collector.metrics[version]['positive'] += 1
        else:
            collector.metrics[version]['negative'] += 1
        
        analyze_requests.labels(status='success', version=version).inc()
        return jsonify(result)
    except Exception as e:
        analyze_requests.labels(status='error', version=version).inc()
        return jsonify({"error": str(e)}), 500

# Save user feedback for model improvement
@app.route('/api/feedback', methods=['POST'])
@metrics.counter('api_calls_feedback', 'Number of calls to feedback endpoint')
def submit_feedback():
    data = request.json
    version = request.headers.get('x-user-experiment', 'A')
    version = 'v2' if version == 'B' else 'v1'
    
    if not data or 'review_id' not in data or 'correct_sentiment' not in data:
        return jsonify({"error": "Missing review_id or correct_sentiment"}), 400
    
    # Track feedback metrics
    if data['correct_sentiment']:
        collector.metrics[version]['feedback_correct'] += 1
    else:
        collector.metrics[version]['feedback_incorrect'] += 1
        
    return jsonify({
        "status": "success",
        "message": "Feedback received"
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)