FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libgomp1 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    flask==3.0.3 requests==2.32.3 pandas==2.2.2 numpy==1.26.4 \
    prophet==1.1.5 gunicorn==22.0.0 && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY data_collector.py model.py predictor_api.py ./

RUN mkdir -p /models

ENV PROMETHEUS_URL="http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090" \
    RETRAIN_INTERVAL_HOURS="1" \
    HISTORY_HOURS="168" \
    PORT="5000"

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "120", "predictor_api:app"]
