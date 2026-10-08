# Experimental only. Default worker selection and release policy are unchanged.
# Build context: pratirodh/projects
FROM node:24-bookworm-slim@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20 AS node
FROM python:3.11-slim-trixie@sha256:0dd364ba7e10242f07755449e3a3d0e35f9efd987952737b90def6709ab0c5ce AS trust
FROM ubuntu:24.04@sha256:534baea6a22c03a63003dbc8dbe78fe34bc0d7e595d9a9dc9834884ff530eb55
COPY --from=trust /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
RUN printf 'Types: deb\nURIs: https://snapshot.ubuntu.com/ubuntu/20261007T000000Z/\nSuites: noble noble-updates noble-security\nComponents: main universe\nSigned-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n' > /etc/apt/sources.list.d/ubuntu.sources && apt-get -o Acquire::https::Timeout=20 -o Acquire::Retries=0 -o APT::Update::Error-Mode=any update && apt-get upgrade -y && apt-get install -y --no-install-recommends python3 python3-venv clang-18 libclang-rt-18-dev cmake make ca-certificates && dpkg-query -W > /opt/package-inventory.txt && rm -rf /var/lib/apt/lists/* && python3 -m venv /opt/python && ln -s /usr/bin/clang-18 /usr/local/bin/clang && ln -s /usr/bin/clang++-18 /usr/local/bin/clang++
ENV PATH="/opt/python/bin:$PATH"
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY npm-worker-pins.json install_worker_npm.py /opt/pratirodh/
RUN python /opt/pratirodh/install_worker_npm.py && ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
COPY requirements-worker.txt /opt/pratirodh/requirements-worker.txt
RUN pip install --no-cache-dir --only-binary=:all: --require-hashes -r /opt/pratirodh/requirements-worker.txt
COPY requirements-pip-vendor.txt update_pip_vendor.py /opt/pratirodh/
RUN pip download --no-cache-dir --only-binary=:all: --require-hashes --no-deps -r /opt/pratirodh/requirements-pip-vendor.txt -d /opt/pip-vendor-wheels && python /opt/pratirodh/update_pip_vendor.py && rm -rf /opt/pip-vendor-wheels
COPY worker_entry.py /opt/pratirodh/worker_entry.py
USER 0:0
WORKDIR /work
ENTRYPOINT ["python", "-B", "/opt/pratirodh/worker_entry.py"]
RUN printf '#!/bin/sh\nexec /opt/python/bin/python "$@"\n' > /usr/local/bin/python && chmod 0755 /usr/local/bin/python
