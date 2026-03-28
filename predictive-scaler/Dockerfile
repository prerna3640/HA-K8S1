FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY controller.py scaler.py ./

ENV PREDICTOR_URL="http://ml-predictor.monitoring.svc.cluster.local:5000" \
    NAMESPACE="myapp" \
    DEPLOYMENT_NAME="web" \
    CPU_PER_REPLICA="0.10" \
    SCALE_UP_BUFFER="0.80" \
    MIN_REPLICAS="2" \
    MAX_REPLICAS="5" \
    CHECK_INTERVAL_SECONDS="60" \
    SCALE_DOWN_COOLDOWN_SECONDS="300" \
    PREDICTION_HORIZON="30"

CMD ["python", "-u", "controller.py"]
