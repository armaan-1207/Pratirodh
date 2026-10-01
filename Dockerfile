FROM python:3.11-slim@sha256:e41613d42d4891e4930f79523f93f81bbc7632584ec65e36ab055f41a800b41e
WORKDIR /app
COPY requirements-deploy.txt /app/
RUN pip install --no-cache-dir -r requirements-deploy.txt
COPY pratirodh /app/pratirodh
COPY benchmark /app/benchmark
COPY docs/*.json /app/docs/
ENV PRATIRODH_ENV=production PRATIRODH_READ_ONLY=1 PYTHONDONTWRITEBYTECODE=1
USER 65534:65534
EXPOSE 8765
CMD ["python", "-m", "pratirodh", "serve", "--host", "0.0.0.0"]
