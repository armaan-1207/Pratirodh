FROM python:3.11-slim-trixie@sha256:0dd364ba7e10242f07755449e3a3d0e35f9efd987952737b90def6709ab0c5ce
RUN printf '%s\n' \
    'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20261006T000000Z/ trixie main' \
    'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian-security/20261006T000000Z/ trixie-security main' \
    > /etc/apt/sources.list.d/release.list \
    && rm /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
COPY requirements-runner.txt /opt/requirements-runner.txt
RUN pip install --no-cache-dir --only-binary=:all: --require-hashes -r /opt/requirements-runner.txt \
    && pip uninstall -y pip setuptools wheel
USER 65534:65534
WORKDIR /tmp
ENTRYPOINT ["python", "-B", "/runner/worker.py"]

