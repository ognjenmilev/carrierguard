# CarrierGuard live demo image.
# Build from the REPOSITORY ROOT so the `core/` package is in the build context:
#   docker build -f webdemo/Dockerfile -t carrierguard-demo .
FROM python:3.12-slim

WORKDIR /app

COPY webdemo/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core ./core
COPY webdemo/main.py webdemo/live.html ./

ENV PORT=8080
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
