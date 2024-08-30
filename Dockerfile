# Separate build image
FROM python:3.11-slim-bullseye as compile-image
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements_server.txt .
RUN apt-get update \
 && apt-get install -y gcc \
 && pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir setuptools wheel \
 && pip install --no-cache-dir -r requirements_server.txt \
 && rm -rf /var/lib/apt/lists/*

# Final image
FROM python:3.11-slim-bullseye
COPY --from=compile-image /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app
COPY orbisat_server_runner.py .
WORKDIR /app
COPY . /app/orbisat
CMD ["python", "-u", "/app/orbisat_server_runner.py"]
