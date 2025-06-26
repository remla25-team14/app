from flask import send_from_directory, request as flask_request
from flask_cors import CORS
from flask_openapi3 import OpenAPI, Info, Tag
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from libversion import VersionUtil  
import os
import requests
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

# OpenAPI Info
info = Info(title="Sentiment Analysis App API", version=VersionUtil.get_version())
app = OpenAPI(__name__, info=info, static_folder='static', static_url_path='')
CORS(app)

# OpenAPI Tags
version_tag = Tag(name="version", description="Version information operations")
sentiment_tag = Tag(name="sentiment", description="Sentiment analysis operations")
feedback_tag = Tag(name="feedback", description="User feedback operations")
metrics_tag = Tag(name="metrics", description="Prometheus metrics")
docs_tag = Tag(name="docs", description="API documentation")

# Pydantic Models
class VersionResponse(BaseModel):
    app: Dict[str, str] = Field(..., description="Application version information")
    model_service: Dict[str, str] = Field(..., description="Model service version information")

class ReviewRequest(BaseModel):
    review: str = Field(..., min_length=1, description="Restaurant review text to analyze")

class AnalysisResponse(BaseModel):
    review_id: Optional[str] = Field(None, description="Unique identifier for this analysis")
    review: str = Field(..., description="Original review text")
    sentiment: bool = Field(..., description="Predicted sentiment (true=positive, false=negative)")
    confidence: Optional[float] = Field(None, description="Confidence score (0.0-1.0) of the prediction")
    emoji: str = Field(..., description="Emoji representation of sentiment")

class FeedbackRequest(BaseModel):
    review_id: str = Field(..., description="ID of the analyzed review")
    correct_sentiment: bool = Field(..., description="The correct sentiment (true=positive, false=negative)")

class FeedbackResponse(BaseModel):
    status: str = Field(..., description="Status of the feedback submission")
    message: str = Field(..., description="Additional information about the feedback submission")

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")

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

@app.get('/metrics', tags=[metrics_tag])
def metrics_endpoint():
    """
    Get Prometheus metrics.
    
    This endpoint returns Prometheus-formatted metrics for monitoring
    and observability of the application.
    """
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

MODEL_SERVICE_URL = os.environ.get('MODEL_SERVICE_URL', 'http://localhost:5000')

APP_VERSION = VersionUtil.get_version()

@app.get('/', defaults={'path': ''}, tags=[docs_tag])
@app.get('/<path:path>', tags=[docs_tag])
def serve(path=''):
    """
    Serve static frontend files.
    
    This endpoint serves the React frontend application files.
    If a specific file is requested and exists, it returns that file.
    Otherwise, it returns the main index.html for SPA routing.
    """
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# Get version info from both local app and model service
@app.get('/api/version', tags=[version_tag], responses={"200": VersionResponse})
@metrics.counter('api_calls_version', 'Number of calls to version endpoint')
def version():
    """
    Get version information.
    
    This endpoint returns version information for both the app backend
    and the connected model service.
    """
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
    
    from flask import jsonify
    return jsonify({
        "app": {
            "app_version": APP_VERSION
        },
        "model_service": {
            "service_version": service_version,
            "model_version": model_version
        }
    })
    
# Connect to model service for sentiment analysis
@app.post('/api/analyze', tags=[sentiment_tag], 
          responses={"200": AnalysisResponse, "400": ErrorResponse, "503": ErrorResponse})
@metrics.counter('api_calls_analyze', 'Number of calls to analyze endpoint')
def analyze_sentiment(body: ReviewRequest):
    """
    Analyze sentiment of a restaurant review.
    
    This endpoint forwards review text to the model service for sentiment analysis
    and returns the prediction along with an emoji representation and confidence score.
    """
    from flask import jsonify
    
    if not body.review:
        return jsonify({"error": "Missing review text"}), 400
    
    # Track model service response time
    start_time = time.time()
    
    try:
        # Forward the request to the model service
        response = requests.post(
            f"{MODEL_SERVICE_URL}/analyze",
            json={"review": body.review},
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
@app.post('/api/feedback', tags=[feedback_tag],
          responses={"200": FeedbackResponse, "400": ErrorResponse})
@metrics.counter('api_calls_feedback', 'Number of calls to feedback endpoint')
def submit_feedback(body: FeedbackRequest):
    """
    Submit user feedback on sentiment analysis results.
    
    This endpoint allows users to provide feedback on whether the sentiment
    prediction was correct, which can be used for model improvement and monitoring.
    """
    from flask import jsonify
    
    if not body.review_id:
        return jsonify({"error": "Missing review_id"}), 400
        
    # Here we would ideally send the feedback to the model service, or do something with it
    return jsonify({
        "status": "success",
        "message": "Feedback received"
    })


# OpenAPI Documentation Endpoints
@app.get('/openapi.json', tags=[docs_tag])
def get_openapi_spec():
    """
    Get the OpenAPI specification for this API.
    
    This endpoint returns the OpenAPI JSON specification that describes all
    available endpoints, request parameters, and response formats.
    """
    from flask import jsonify
    return jsonify(app.api_doc)


@app.get('/docs', tags=[docs_tag])
def get_docs():
    """
    Redirect to API documentation.
    
    This endpoint redirects to the Swagger UI documentation interface.
    """
    from flask import redirect
    return redirect('/swagger')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)