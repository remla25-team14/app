# Restaurant Sentiment Analysis App

This application analyzes restaurant reviews for sentiment using an ML model service.

## Using Docker Compose (Recommended)

1. Start the application stack with Docker Compose:
   ```
   docker-compose up -d
   ```

2. Access the application in your web browser:
   ```
   http://localhost:5001
   ```

3. To download model artifacts, you may need to provide a GitHub token:
   ```
   GITHUB_TOKEN=your_token docker-compose up -d
   ```

4. To stop the application:
   ```
   docker-compose down
   ```

## Using Docker Standalone

1. Build the Docker image:
   ```
   docker build -t restaurant-sentiment-app .
   ```

2. Run the application:
   ```
   docker run -p 5001:5001 restaurant-sentiment-app
   ```

3. Access the application in your web browser:
   ```
   http://localhost:5001
   ```

Note: In standalone mode, you'll need to run the model service separately.

