FROM python:3-alpine

RUN pip install requests websocket-client paho-mqtt

WORKDIR /app

COPY gardena2mqtt.py .

ENTRYPOINT ["python", "/app/gardena2mqtt.py"]