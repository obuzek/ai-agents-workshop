# EHR API container — serves the synthetic patient data over HTTP so agent
# tools running in the cloud (e.g. watsonx Orchestrate) can reach it.
#
# Build from the repo root:
#   docker build -f deploy/ehr-api/Dockerfile -t ehr-api .
FROM python:3.12-slim

WORKDIR /srv
RUN pip install --no-cache-dir "fastapi>=0.115" "uvicorn>=0.34" "requests>=2.32" "python-dotenv>=1.0"

COPY app/ app/
COPY data/patients data/patients

# Code Engine routes traffic to $PORT (default 8080).
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.api:app --host 0.0.0.0 --port ${PORT}"]
