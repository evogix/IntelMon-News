FROM python:3.11-slim

WORKDIR /app

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY monitor.py config.json.example setup.sh ./
COPY README.md ./

# Create dirs and example config
RUN mkdir -p data logs && \
    cp config.json.example config.json || true

# Healthcheck
HEALTHCHECK --interval=5m --timeout=10s --retries=3 CMD python3 -c "import sqlite3; sqlite3.connect('data/intel.db').execute('SELECT 1')"

CMD ["python3", "monitor.py", "--loop", "180"]
