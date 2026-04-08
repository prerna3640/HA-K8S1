FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir kubernetes requests
COPY controller_v2.py controller.py scaler.py ./
ENV PREDICTOR_URL="http://ml-predictor.monitoring.svc.cluster.local:5000" \
    NAMESPACE="myapp" DEPLOYMENT_NAME="web" \
    MIN_REPLICAS="2" MAX_REPLICAS="5" \
    CHECK_INTERVAL_SECONDS="60" PREDICTION_HORIZON="30" \
    COST_PER_POD_HOUR="0.05" MIN_CONFIDENCE="0.3"
CMD ["python", "-u", "controller_v2.py"]
