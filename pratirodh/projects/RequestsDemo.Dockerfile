FROM pratirodh-project-worker:0.2
# Preparation only. Demo target execution retains --network none.
# Modern dependencies support the in-memory redirect harness. Legacy Requests
# warnings are retained as an adaptation; this is not real network qualification.
COPY requirements-requests-demo.txt /opt/pratirodh/requirements-requests-demo.txt
RUN pip install --no-cache-dir --only-binary=:all: --require-hashes --no-deps -r /opt/pratirodh/requirements-requests-demo.txt
