# Kubernetes Deployment & Monitoring

## Prerequisites

- Minikube installed
- kubectl configured
- Docker installed

## Repository Files

- `model-deployment.yaml`
- `monitoring.yml`
- GitHub token saved in `operations/secrets/github_token.txt`

## Setup Instructions

1. Start your Minikube cluster

```bash
minikube start
```

2. Create the GitHub token secret

This is required for the model service to download the sentiment analysis model.

```bash
# Create the GitHub token secret
kubectl create secret generic github-token --from-file=GITHUB_TOKEN=operations/secrets/github_token.txt
```

3. Deploy the applications

```bash
# Deploy the model service first
kubectl apply -f model-deployment.yaml

# Deploy the app with Prometheus monitoring
kubectl apply -f monitoring.yml
```

4. Verify deployments

Ensure all pods and services are running correctly:

```bash
# Check if pods are running
kubectl get pods

# Check services
kubectl get services
```

Wait until all pods show status 'Running' and all services are created.

5. Access your application

Open two terminal windows:

**Terminal 1 - Application URL:**

```bash
minikube service sentiment-app-service --url
```

Copy the URL (e.g., http://127.0.0.1:64975) and open it in your browser to access the sentiment analysis interface.

**Terminal 2 - Prometheus URL:**

```bash
minikube service myprom-kube-prometheus-sta-prometheus --url
```

Copy the URL and open it in your browser to access the Prometheus dashboard.

## Accessing Grafana Dashboard

1. First, get the Grafana admin password:
```bash
kubectl get secret myprom-grafana -o jsonpath="{.data.admin-password}" | base64 --decode; echo
```

2. Set up port forwarding to access Grafana:
```bash
kubectl port-forward service/myprom-grafana 3000:80
```

3. Extract the dashboard JSON:
```bash
kubectl get configmap grafana-dashboard-sentiment -o jsonpath="{.data['sentiment-dashboard\.json']}" > dashboard.json
```

4. Access Grafana:
   - Open your browser and go to http://localhost:3000
   - Login with:
     * Username: `admin`
     * Password: (use the password obtained in step 1)

5. Import the Sentiment Analysis Dashboard:
   - Click the "+" icon in the left sidebar
   - Select "Import"
   - Click "Upload JSON file"
   - Select the `dashboard.json` file you created in step 3
   - Select "Prometheus" as the data source
   - Click "Import"

The dashboard includes the following panels:
- Application Version
- Positive Sentiment Ratio (with thresholds at 0.3 and 0.7)
- Sentiment Predictions Over Time
- Sentiment Distribution
- Model Response Time

The dashboard is configured to refresh every 5 seconds and shows data from the last 15 minutes.

## Testing the Metrics

1. Verify Prometheus is scraping your app

In the Prometheus UI:

- Go to **Status → Targets**
- Look for your ServiceMonitor target (should mention **mymonitor**)
- Check if state is **UP** - this confirms Prometheus is scraping your metrics

2. Generate test traffic

Use the application UI or send direct API requests:

```bash
# Get your app URL
APP_URL=$(minikube service sentiment-app-service --url)

# Generate API traffic
for i in {1..5}; do
  curl -X POST "$APP_URL/api/analyze" \
    -H "Content-Type: application/json" \
    -d '{"review":"This product is amazing! I love it."}'
  sleep 1
done
```

3. Query your metrics in Prometheus

In the Prometheus UI, go to the **Graph** tab and try these queries:

- **API Call Rate:** `rate(api_calls_analyze_total[1m])`
- **Average Response Time:** `rate(model_response_time_seconds_sum[1m]) / rate(model_response_time_seconds_count[1m])`
- **Response Time Percentiles:** `histogram_quantile(0.9, sum(rate(model_response_time_seconds_bucket[5m])) by (le))`
- **Sentiment Ratio:** `sum(sentiment_predictions_total) by (sentiment)`

Or go to {APPURL}/metrics to see all the monitoring results!

## Troubleshooting

**Model Service Issues**

If you're seeing 503 errors from the model service, it might be due to:

- **GitHub Token Issues**: Ensure the token is properly formatted without any prefixes or newlines.
- **Artifact Access Problems**: The model artifact might no longer be available at the expected ID.

To check model service logs:

```bash
kubectl logs $(kubectl get pods | grep sentiment-model | awk '{print $1}')
```

**Prometheus Connection Issues**

If Prometheus isn't connecting to your application:

- Check that your ServiceMonitor has the correct label selector.
- Verify that your app is exposing metrics on the `/metrics` endpoint.
- Ensure the `release: myprom` label is set on your ServiceMonitor.

## Notes

- The sentiment analysis feature requires the model service to be operating correctly.
- Even if the model service has issues, you can still validate that Prometheus monitoring is working by checking other metrics.
- For a complete test, the model service needs access to a valid model artifact.

