# Prototype tools only. Prepare application dependencies in a derived image.
FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm clang cmake make ca-certificates && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pytest==8.3.5 bandit==1.8.3 Flask==3.1.2 fastapi==0.115.12 httpx==0.28.1
RUN apt-get update && apt-get install -y --no-install-recommends libclang-rt-14-dev && rm -rf /var/lib/apt/lists/*
COPY worker_entry.py /opt/pratirodh/worker_entry.py
USER 0:0
WORKDIR /work
ENTRYPOINT ["python", "-B", "/opt/pratirodh/worker_entry.py"]
