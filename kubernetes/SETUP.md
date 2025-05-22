# Sentiment Analysis Application Setup Guide

This guide will walk you through setting up the complete sentiment analysis application from scratch, including both the model service and the web application.

## Prerequisites

- Docker installed
- Minikube installed
- kubectl configured
- Git repository cloned

## Step 1: Initial Setup

1. Start Minikube:
```bash
minikube start
```

2. Clone both repositories (if not done already):
```bash
# Clone the operation repository
git clone https://github.com/remla25-team14/operation.git

# Clone the app repository (if separate)
git clone https://github.com/remla25-team14/app.git
```

## Step 2: Build and Test Images Locally

1. Navigate to the operation directory:
```bash
cd operation
```

2. Create GitHub token file:
```bash
# Create secrets directory if it doesn't exist
mkdir -p secrets

# Add your GitHub token to the file
echo "your-github-token" > secrets/github_token.txt
```

3. Pull and build the images using Docker Compose:
```bash
# Pull the model service image
docker compose pull model-service

# Build the app image
docker compose build app
```

4. Test the services locally:
```bash
# Start both services
docker compose up

# In a new terminal, test if the services are running:
curl http://localhost:5001  # Should return the web interface
curl http://localhost:5000/health  # Should return model service health status
```

## Step 3: Kubernetes Deployment

1. Create the GitHub token secret in Kubernetes:
```bash
kubectl create secret generic github-token --from-file=GITHUB_TOKEN=operation/secrets/github_token.txt
```

2. Deploy Prometheus and Grafana for monitoring:
```bash
# Add Prometheus Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus and Grafana stack
helm install myprom prometheus-community/kube-prometheus-stack
```

3. Deploy the model service:
```bash
kubectl apply -f app/kubernetes/model-deployment.yaml
```

4. Deploy the sentiment analysis app and monitoring:
```bash
kubectl apply -f app/kubernetes/monitoring.yml
```

5. Verify all pods are running:
```bash
kubectl get pods

# Expected output should show:
# - sentiment-model pod (Running)
# - sentiment-app pod (Running)
# - Prometheus pods (Running)
# - Grafana pods (Running)
```

## Step 4: Access the Applications

1. Get the sentiment analysis app URL:
```bash
minikube service sentiment-app-service --url
```

2. Access Grafana dashboard:
```bash
# Get Grafana admin password
kubectl get secret myprom-grafana -o jsonpath="{.data.admin-password}" | base64 --decode; echo

# Set up port forwarding for Grafana
kubectl port-forward service/myprom-grafana 3000:80
```

3. Configure Grafana:
- Open http://localhost:3000 in your browser
- Login with:
  * Username: admin
  * Password: (use the password obtained from the previous command)
  * Note: If you need to get the password again later, you can always run:
    ```bash
    kubectl get secret myprom-grafana -o jsonpath="{.data.admin-password}" | base64 --decode; echo
    ```
- Import the dashboard from `app/kubernetes/grafana_dashboard.json`
- If you need to stop port forwarding, use Ctrl+C in the terminal where you ran the port-forward command
- To restart Grafana access later, just run the port-forward command again:
  ```bash
  kubectl port-forward service/myprom-grafana 3000:80
  ```

## Step 5: Test the Application

1. Test the sentiment analysis:
- Open the application URL from step 4.1
- Enter a text in the input field
- Click "Analyze" to see the sentiment prediction

2. Monitor the metrics:
- Open Grafana (http://localhost:3000)
- Navigate to the imported dashboard
- You should see:
  * Request Rate by Sentiment
  * Average Response Time
  * Positive Sentiment Ratio
  * Application Version

## Troubleshooting

### Common Issues and Solutions

1. **Image Pull Errors**
- If `sentiment-app` shows `ErrImageNeverPull`:
  ```bash
  # Ensure you've built the image locally
  cd operation
  docker compose build app
  ```

2. **Image Registry and Pull Policy Issues**
- If you see `ImagePullBackOff` or permission-related errors:
  * Check your deployment's image pull policy:
    ```bash
    kubectl describe deployment sentiment-app
    ```
  * For local images, ensure:
    1. The image is built locally (`docker compose build app`)
    2. The deployment uses `imagePullPolicy: Never`
    3. Update your deployment YAML:
    ```yaml
    spec:
      containers:
      - name: sentiment-app
        image: sentiment-app:latest
        imagePullPolicy: Never
    ```
  * For GitHub Container Registry (ghcr.io) images:
    1. Ensure you have a valid GitHub token with `read:packages` scope
    2. Create a Kubernetes secret for GitHub authentication:
    ```bash
    kubectl create secret docker-registry github-registry \
      --docker-server=ghcr.io \
      --docker-username=YOUR_GITHUB_USERNAME \
      --docker-password=YOUR_GITHUB_TOKEN
    ```
    3. Add the secret to your deployment:
    ```yaml
    spec:
      imagePullSecrets:
      - name: github-registry
      containers:
      - name: sentiment-app
        image: ghcr.io/your-org/sentiment-app:latest
        imagePullPolicy: Always
    ```

3. **Model Service Issues**
- If the model service fails to start:
  * Verify the GitHub token is correct
  * Check the logs: `kubectl logs deployment/sentiment-model`

4. **Monitoring Issues**
- If metrics aren't showing in Grafana:
  * Verify ServiceMonitor is running
  * Check Prometheus target status in Grafana

### Useful Commands

```bash
# View pod logs
kubectl logs <pod-name>

# Describe pod status
kubectl describe pod <pod-name>

# Restart a deployment
kubectl rollout restart deployment <deployment-name>

# View all resources
kubectl get all
```

## Cleanup

To remove everything:
```bash
# Delete Kubernetes resources
kubectl delete -f app/kubernetes/monitoring.yml
kubectl delete -f app/kubernetes/model-deployment.yaml
helm uninstall myprom

# Stop Minikube
minikube stop

# Optional: Delete Minikube cluster
minikube delete
``` 