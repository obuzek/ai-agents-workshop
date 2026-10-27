# EHR API container — serves the synthetic patient data over HTTP so agent
# tools running in the cloud (e.g. watsonx Orchestrate) can reach it.
#
# Build from the repo root:
#   docker build -f deploy/ehr-api/Dockerfile -t ehr-api .
#
# Run exactly ONE instance with ONE worker (Code Engine: --min-scale 1 --max-scale 1).
# Tenant data lives in that process's memory; a second process would hold its own,
# diverging copy and the two would overwrite each other's saves in Object Storage.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /srv
# Versions match uv.lock, so the image is the code the tests ran against.
RUN pip install --no-cache-dir \
        "fastapi==0.136.1" "starlette==1.0.0" "pydantic==2.13.3" "anyio==4.13.0" \
        "uvicorn==0.46.0" "requests==2.33.1" "python-dotenv==1.2.2"

COPY app/ app/
COPY data/patients data/patients

# Don't run as root.
RUN useradd --system --uid 1001 ehr
USER 1001

# Code Engine routes traffic to $PORT (default 8080).
ENV PORT=8080
EXPOSE 8080
# exec: uvicorn becomes PID 1 and gets SIGTERM, so a redeploy finishes in-flight requests.
# --timeout-keep-alive above the platform proxy's idle timeout avoids sporadic 502s on reused connections.
CMD ["sh", "-c", "exec uvicorn app.api:app --host 0.0.0.0 --port ${PORT} --workers 1 --proxy-headers --forwarded-allow-ips '*' --timeout-keep-alive 75"]
