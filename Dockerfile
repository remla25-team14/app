FROM node:16 AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./

RUN npm install

COPY frontend/ ./

RUN npm run build

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

COPY --from=frontend-build /app/frontend/build ./static

ARG APP_VERSION=development
ENV APP_VERSION=${APP_VERSION}
ENV MODEL_VERSION=${APP_VERSION}

ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV MODEL_SERVICE_URL=http://model-service:5000

EXPOSE 5001

CMD ["python", "app.py"] 
