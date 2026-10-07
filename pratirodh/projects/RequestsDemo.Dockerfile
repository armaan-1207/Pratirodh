# A Python-only reference demo must not inherit compiler/native XML libraries.
FROM python:3.11-slim-trixie@sha256:0dd364ba7e10242f07755449e3a3d0e35f9efd987952737b90def6709ab0c5ce
RUN printf '%s\n' \
    'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20261006T000000Z/ trixie main' \
    'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian-security/20261006T000000Z/ trixie-security main' \
    > /etc/apt/sources.list.d/release.list \
    && rm /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
# Modern dependencies support the in-memory redirect harness. Legacy Requests
# warnings are retained; this image does not qualify real network/TLS behavior.
COPY requirements-requests-tools.txt requirements-requests-demo.txt /opt/pratirodh/
RUN pip install --no-cache-dir --only-binary=:all: --require-hashes \
    -r /opt/pratirodh/requirements-requests-tools.txt \
    -r /opt/pratirodh/requirements-requests-demo.txt \
    && pip uninstall -y pip setuptools wheel
COPY worker_entry.py /opt/pratirodh/worker_entry.py
# Preserve the trusted supervisor and target UID/capability restrictions.
USER 0:0
WORKDIR /work
ENTRYPOINT ["python", "-B", "/opt/pratirodh/worker_entry.py"]
