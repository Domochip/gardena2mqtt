FROM python:3-alpine

RUN pip install websocket-client==0.57.0 py-smart-gardena paho-mqtt

WORKDIR /app

COPY gardena2mqtt.py .

ENTRYPOINT ["python", "/app/gardena2mqtt.py"]