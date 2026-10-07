# Runtime versions, wheel hashes and Debian repository time are release inputs.
FROM node:24-bookworm-slim@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20 AS node
FROM python:3.11-slim-trixie@sha256:0dd364ba7e10242f07755449e3a3d0e35f9efd987952737b90def6709ab0c5ce
RUN printf '%s\n' \
    'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20261006T000000Z/ trixie main' \
    'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian-security/20261006T000000Z/ trixie-security main' \
    > /etc/apt/sources.list.d/release.list \
    && rm /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends clang-19 libclang-rt-19-dev cmake make ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/clang-19 /usr/local/bin/clang \
    && ln -s /usr/bin/clang++-19 /usr/local/bin/clang++
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY npm-worker-pins.json install_worker_npm.py /opt/pratirodh/
RUN python /opt/pratirodh/install_worker_npm.py
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
COPY requirements-worker.txt /opt/pratirodh/requirements-worker.txt
RUN pip install --no-cache-dir --only-binary=:all: --require-hashes -r /opt/pratirodh/requirements-worker.txt
COPY requirements-pip-vendor.txt update_pip_vendor.py /opt/pratirodh/
RUN pip download --no-cache-dir --only-binary=:all: --require-hashes --no-deps \
    -r /opt/pratirodh/requirements-pip-vendor.txt -d /opt/pip-vendor-wheels \
    && python /opt/pratirodh/update_pip_vendor.py \
    && rm -rf /opt/pip-vendor-wheels
COPY worker_entry.py /opt/pratirodh/worker_entry.py
# The supervisor needs SETUID/SETGID; target code runs as 65534, without caps.
USER 0:0
WORKDIR /work
ENTRYPOINT ["python", "-B", "/opt/pratirodh/worker_entry.py"]
