FROM python:3.11-slim@sha256:e41613d42d4891e4930f79523f93f81bbc7632584ec65e36ab055f41a800b41e
RUN pip install --no-cache-dir Flask==3.1.3 Werkzeug==3.1.9
USER 65534:65534
WORKDIR /tmp
ENTRYPOINT ["python", "-B", "/runner/worker.py"]

