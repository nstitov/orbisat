FROM python:3-alpine
WORKDIR /app
COPY . .
RUN pip install -r requirements_server.txt
CMD python -u /app/influxdb_writer.py
