FROM pratirodh-project-worker:0.2
# Preparation only. Demo target execution retains --network none.
# urllib3 1.26 supports this prepared Python 3.11 environment; the legacy
# Requests version warning is recorded as a dependency adaptation.
RUN pip install --no-cache-dir urllib3==1.26.20 chardet==3.0.4 idna==2.10 certifi==2024.8.30
