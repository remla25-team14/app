### Using Docker

1. Clone the repository:
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Build the Docker image:
   ```
   docker build -t restaurant-sentiment-app .
   ```

3. Run the application:
   ```
   docker run -p 5001:5001 restaurant-sentiment-app
   ```

4. Access the application in your web browser:
   ```
   http://localhost:5001
   ```

