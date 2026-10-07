FROM python:3.11-slim-trixie@sha256:0dd364ba7e10242f07755449e3a3d0e35f9efd987952737b90def6709ab0c5ce
RUN printf '%s\n' \
    'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20261006T000000Z/ trixie main' \
    'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian-security/20261006T000000Z/ trixie-security main' \
    > /etc/apt/sources.list.d/release.list \
    && rm /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-deploy.txt /app/
RUN pip install --no-cache-dir --only-binary=:all: --require-hashes -r requirements-deploy.txt \
    && pip uninstall -y pip setuptools wheel
COPY pratirodh /app/pratirodh
COPY benchmark /app/benchmark
COPY docs/*.json /app/docs/
ENV PRATIRODH_ENV=production PRATIRODH_READ_ONLY=1 PYTHONDONTWRITEBYTECODE=1
USER 65534:65534
EXPOSE 8765
CMD ["python", "-m", "pratirodh", "serve", "--host", "0.0.0.0"]
