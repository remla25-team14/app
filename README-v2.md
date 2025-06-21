# App v2 - Feedback Experiment

This is the experimental version (v2) of the sentiment analysis application used for A/B testing. It includes enhanced feedback collection and user experience features.

## Key Differences from v1

### Enhanced Feedback Collection
- **Unique Review IDs**: Each analysis generates a unique UUID for tracking
- **Feedback Storage**: In-memory storage of review data and user feedback
- **Feedback Statistics**: New `/api/feedback/stats` endpoint for A/B testing metrics
- **User Satisfaction Tracking**: Real-time calculation of user satisfaction scores

### Enhanced User Experience
- **Detailed Confidence Levels**: Shows confidence as "Very High", "High", "Medium", "Low"
- **Enhanced Messages**: More descriptive sentiment analysis messages
- **Feedback Prompts**: Automatic prompts for user feedback after each analysis
- **Variant Identification**: API responses include variant information for tracking

### Additional Metrics
- **Feedback Submissions**: Tracks correct vs incorrect feedback
- **User Satisfaction Score**: Gauge metric for overall user satisfaction
- **Feedback Rate**: Percentage of reviews that receive user feedback

## API Endpoints

### New/Enhanced Endpoints

#### `GET /api/version`
Returns version information including variant identification:
```json
{
  "app": {
    "app_version": "0.1.1-pre",
    "variant": "v2-feedback-experiment"
  },
  "model_service": {
    "service_version": "v0.1.6-rc.1",
    "model_version": "v0.1.5"
  }
}
```

#### `POST /api/analyze` (Enhanced)
Returns enhanced response with feedback tracking:
```json
{
  "review_id": "uuid-string",
  "sentiment": true,
  "confidence": 0.85,
  "confidence_level": "High",
  "emoji": "😊",
  "message": "This review appears to be positive!",
  "feedback_prompt": "Was this prediction correct? Click here to provide feedback (ID: uuid-string)"
}
```

#### `POST /api/feedback` (Enhanced)
Enhanced feedback collection with satisfaction tracking:
```json
{
  "status": "success",
  "message": "Thank you for your feedback! This helps us improve our model.",
  "feedback_id": "uuid-string",
  "model_feedback_sent": true,
  "satisfaction_score": 0.85
}
```

#### `GET /api/feedback/stats` (New)
Returns feedback statistics for A/B testing:
```json
{
  "total_reviews": 100,
  "feedback_received": 25,
  "correct_predictions": 20,
  "accuracy": 0.8,
  "feedback_rate": 0.25
}
```

## A/B Testing Features

### Traffic Splitting
- Uses Istio header-based routing with `x-user-experiment: B`
- 10% of traffic receives v2 experience
- Consistent user experience throughout session

### Metrics Collection
- Enhanced Prometheus metrics for feedback analysis
- Real-time dashboard updates in Grafana
- Statistical significance tracking for experiment evaluation

### Experiment Goals
1. **User Engagement**: Measure feedback submission rates
2. **Model Accuracy**: Compare user-reported accuracy between versions
3. **User Satisfaction**: Track overall satisfaction scores
4. **Response Quality**: Evaluate confidence level usefulness

## Deployment

This version is deployed as part of the A/B testing setup in Kubernetes with Istio:

```yaml
# values.yaml
app:
  images:
    v1: ghcr.io/remla25-team14/app/app:sha-06d792c
    v2: ghcr.io/remla25-team14/app/app:v2-feedback-experiment
```

## Building the v2 Image

```bash
# Build v2 image
docker build -f Dockerfile-v2 -t ghcr.io/remla25-team14/app/app:v2-feedback-experiment .

# Push to registry
docker push ghcr.io/remla25-team14/app/app:v2-feedback-experiment
```

## Monitoring

Monitor the experiment through:
- Grafana dashboard: "Sentiment Analysis A/B Testing"
- Prometheus metrics: `feedback_submissions_total`, `user_satisfaction_score`
- Application logs for feedback collection patterns 