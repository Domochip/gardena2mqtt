FROM python:3-alpine

RUN pip install py-smart-gardena==0.7.12 paho-mqtt

WORKDIR /app

COPY gardena2mqtt.py .

ENTRYPOINT ["python", "/app/gardena2mqtt.py"]